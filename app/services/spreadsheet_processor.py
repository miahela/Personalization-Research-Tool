import logging
from typing import List, Generator

from app.models import SpreadsheetData, SheetData, ContactData, CompanyData, SheetRow
from app.services.data_processor import filter_unprocessed_rows, process_contact_data
from app.services.sheet_listing_service import get_or_fetch_sheet_data
from app.utils.external_apis import get_nubela_data_for_user, search_person_interviews_podcasts, \
    search_company_case_studies, search_company_about_page
from app.utils.google_utils.google_sheets import fetch_colored_cells_from_google, fetch_sheet_names_from_google


class SpreadsheetProcessor:
    def __init__(self, spreadsheet_id: str, batch_size: int = 2):
        self.spreadsheet_id = spreadsheet_id
        self.batch_size = batch_size
        self.spreadsheet_data = SpreadsheetData(id=spreadsheet_id, new_connections=SheetData(headers=[], rows=[]),
                                                pq_data=SheetData(headers=[], rows=[]))
        self.processed_contacts: List[ContactData] = []

    def process(self) -> Generator[List[ContactData], None, None]:
        self._load_spreadsheet_data()
        yield from self._process_contacts_in_batches()

    def _load_spreadsheet_data(self):
        self._load_new_connections_sheet()
        self._load_pq_sheet()

    def _load_new_connections_sheet(self):
        new_connections_data = get_or_fetch_sheet_data(self.spreadsheet_id, 'New Connections', 'A:ZZ')
        if new_connections_data:
            self.spreadsheet_data.new_connections = new_connections_data
        else:
            logging.error(f"No data found in New Connections sheet for spreadsheet {self.spreadsheet_id}")

    def _load_pq_sheet(self):
        sheet_names = fetch_sheet_names_from_google(self.spreadsheet_id)
        pq_sheet_name = next((name for name in sheet_names if name.lower().endswith('pq')), None)
        if pq_sheet_name:
            pq_data = get_or_fetch_sheet_data(self.spreadsheet_id, pq_sheet_name, 'A:ZZ')
            if pq_data:
                self.spreadsheet_data.pq_data = pq_data
            else:
                logging.warning(f"No data found in PQ sheet for spreadsheet {self.spreadsheet_id}")
        else:
            logging.warning(f"No PQ sheet found for spreadsheet {self.spreadsheet_id}")

    def _process_contacts_in_batches(self) -> Generator[List[ContactData], None, None]:
        unprocessed_rows = filter_unprocessed_rows(self.spreadsheet_data.new_connections.rows)
        for i in range(0, len(unprocessed_rows), self.batch_size):
            batch = unprocessed_rows[i:i + self.batch_size]
            processed_batch = []
            for row in batch:
                try:
                    processed_contact = self._process_contact(row)
                    processed_batch.append(processed_contact)
                except Exception as e:
                    logging.error(f"Error processing contact: {str(e)}")
                    # You might want to create a special ContactData object to represent errors
                    # error_contact = ContactData(
                    #     first_name="Error",
                    #     last_name="Processing Contact",
                    #     job_title="N/A",
                    #     company=CompanyData(name="N/A", website="N/A"),
                    #     linkedin_url="N/A",
                    #     linkedin_username="N/A",
                    #     error_message=str(e)
                    # )
                    # processed_batch.append(error_contact)
            self.processed_contacts.extend(processed_batch)
            yield processed_batch

        self._log_processing_results()

    def _process_contact(self, row: SheetRow) -> ContactData:
        company_data = self._get_company_data(row)
        contact_data = process_contact_data(row, company_data, self.spreadsheet_id,
                                            self.spreadsheet_data.new_connections.colored_cells)
        self._enrich_contact_data(contact_data)
        return contact_data

    def _get_company_data(self, row: SheetRow) -> CompanyData:
        company_name = row.data.get('contact_company_name', '').strip().lower()
        company_website = next((r.data.get('Website URL') for r in self.spreadsheet_data.pq_data.rows if
                                r.data.get('Company Name', '').strip().lower() == company_name), '')
        return CompanyData(name=company_name, website=company_website)

    @staticmethod
    def _enrich_contact_data(contact_data: ContactData):
        SpreadsheetProcessor._add_company_links(contact_data)
        SpreadsheetProcessor._add_media_links(contact_data)
        SpreadsheetProcessor._add_linkedin_data(contact_data)

    @staticmethod
    def _add_company_links(contact_data: ContactData):
        if contact_data.company.website:
            about_links = search_company_about_page(contact_data.company.website, contact_data)
            case_study_links = search_company_case_studies(contact_data.company.website, contact_data.linkedin_username)
            contact_data.company.about_links = about_links[:3] if about_links else []
            contact_data.company.case_study_links = case_study_links if case_study_links else []

    @staticmethod
    def _add_media_links(contact_data: ContactData):
        media_links = search_person_interviews_podcasts(contact_data.parsed_name, contact_data.company.name,
                                                        contact_data.linkedin_username)
        contact_data.interviews_and_podcasts = media_links if media_links else []

    @staticmethod
    def _add_linkedin_data(contact_data: ContactData):
        if contact_data.contact_profile_link:
            linkedin_data = get_nubela_data_for_user(contact_data.contact_profile_link)
            if linkedin_data:
                contact_data.bio = linkedin_data.get('summary')
                contact_data.headline = linkedin_data.get('headline')
                contact_data.industry = linkedin_data.get('industry')
                contact_data.profile_picture = linkedin_data.get('local_profile_pic_url')
                contact_data.banner_picture = linkedin_data.get('local_banner_pic_url')
                contact_data.languages = linkedin_data.get('languages', [])
                contact_data.experiences = linkedin_data.get('experiences', [])
                contact_data.volunteer_work = linkedin_data.get('volunteer_work', [])

    def _log_processing_results(self):
        logging.info(f"Spreadsheet {self.spreadsheet_id}: Processed {len(self.processed_contacts)} contacts")
        logging.info(f"Spreadsheet {self.spreadsheet_id}: PQ data rows: {len(self.spreadsheet_data.pq_data.rows)}")
