from datetime import datetime, timedelta
import logging
from os.path import basename
from typing import List, Generator
from app.models import SpreadsheetData, SheetData, ContactData, CompanyData, SheetRow, PqKeywords
from app.models.contact_models import ExperiencesWithMetadata
from app.models.nubela_response_models import Experience, NubelaResponse
from app.services.data_processor import filter_unprocessed_rows, initialize_contact_data
from app.services.sheet_listing_service import get_or_fetch_sheet_data
from app.utils.external_apis import get_nubela_data_for_contact, search_person_interviews_podcasts, \
    search_company_case_studies, search_company_about_page
from app.utils.google_utils.google_sheets import fetch_colored_cells_from_google, fetch_sheet_names_from_google
from flask import current_app
from typing import List, Dict, Any, Tuple


class SpreadsheetProcessor:
    def __init__(self, spreadsheet_id: str, small_batch_size: int = 2):
        self.spreadsheet_id = spreadsheet_id
        self.small_batch_size = small_batch_size
        self.spreadsheet_data = SpreadsheetData(id=spreadsheet_id, new_connections=SheetData(headers=[], rows=[]),
                                                pq_data=SheetData(headers=[], rows=[]), keywords=PqKeywords())
        self.unprocessed_rows = []
        self.processed_row_numbers = set()
        self.is_data_loaded = False

    def _load_data_if_needed(self):
        if not self.is_data_loaded:
            self._load_spreadsheet_data()
            self.unprocessed_rows = filter_unprocessed_rows(self.spreadsheet_data.new_connections.rows)
            self.is_data_loaded = True

    def process_small_batch(self) -> List[ContactData]:
        self._load_data_if_needed()

        batch = []
        for _ in range(self.small_batch_size):
            if not self.unprocessed_rows:
                break
            row = self.unprocessed_rows.pop(0)
            if row.row_number in self.processed_row_numbers:
                continue
            try:
                processed_contact = self._process_contact(row)
                batch.append(processed_contact)
                self.processed_row_numbers.add(row.row_number)
            except Exception as e:
                current_app.logger.error(f"Error processing contact: {str(e)}")

        return batch

    def has_more_contacts(self) -> bool:
        self._load_data_if_needed()
        return bool(self.unprocessed_rows)

    def _load_spreadsheet_data(self):
        self._load_new_connections_sheet()
        self._load_pq_sheet()
        self._load_keywords()

    def _load_new_connections_sheet(self):
        new_connections_data = get_or_fetch_sheet_data(self.spreadsheet_id, 'New Connections', 'A:ZZ')
        if new_connections_data:
            self.spreadsheet_data.new_connections = new_connections_data
        else:
            logging.error(f"No data found in New Connections sheet for spreadsheet {self.spreadsheet_id}")

    def _load_pq_sheet(self):
        sheet_names = fetch_sheet_names_from_google(self.spreadsheet_id)
        pq_sheet_names = [name for name in sheet_names if name.lower().endswith('pq')]

        if pq_sheet_names:
            all_pq_data = []
            headers = None
            for pq_sheet_name in pq_sheet_names:
                pq_data = get_or_fetch_sheet_data(self.spreadsheet_id, pq_sheet_name, 'A:ZZ')
                if pq_data and pq_data.rows:
                    if headers is None:
                        headers = pq_data.headers
                        all_pq_data.extend(pq_data.rows)
                    else:
                        all_pq_data.extend(pq_data.rows)
                else:
                    logging.warning(
                        f"No data found in PQ sheet '{pq_sheet_name}' for spreadsheet {self.spreadsheet_id}")

            if all_pq_data:
                self.spreadsheet_data.pq_data = SheetData(headers=headers, rows=all_pq_data)
            else:
                logging.warning(f"No data found in any PQ sheets for spreadsheet {self.spreadsheet_id}")
        else:
            logging.warning(f"No PQ sheets found for spreadsheet {self.spreadsheet_id}")

    def _load_keywords(self):
        titles = []
        seniorities = []
        negative_keywords = []
        for row in self.spreadsheet_data.pq_data.rows:
            title = row.get('Titles', '')
            seniority = row.get('Seniority', '')
            negative = row.get('Negative', '')

            if title and title not in titles:
                titles.append(title)
            if seniority and seniority not in seniorities:
                seniorities.append(seniority)
            if negative and negative not in negative_keywords:
                negative_keywords.append(negative)

        self.spreadsheet_data.keywords = PqKeywords(titles=titles, seniority=seniorities,
                                                    negative_keywords=negative_keywords)

    def _process_contact(self, row: SheetRow) -> ContactData:
        company_data = self._get_company_data(row)
        contact_data = initialize_contact_data(row, company_data, self.spreadsheet_id,
                                               self.spreadsheet_data.new_connections.colored_cells)

        SpreadsheetProcessor._add_company_links(contact_data)
        SpreadsheetProcessor._add_media_links(contact_data)
        SpreadsheetProcessor._add_nubela_data(contact_data)

        contact_data.relevant_experiences = self._add_relevant_experience(contact_data.nubela_response.experiences,
                                                                          contact_data.contact_job_title,
                                                                          contact_data.company.name,
                                                                          self.spreadsheet_data.keywords)
        return contact_data

    def _get_company_data(self, row: SheetRow) -> CompanyData:
        company_name = basename(row.data.get('contact_company_name', ''))
        pq_row = self.spreadsheet_data.pq_data.get_row_by_text(company_name)
        if pq_row:
            company_website = pq_row.data.get('Website URL', '')
            return CompanyData(name=company_name, website=company_website)
        return CompanyData(name=company_name)

    @staticmethod
    def _add_relevant_experience(experiences_data: List[Experience], contact_job_title: str, current_company: str,
                                 keywords: PqKeywords) -> ExperiencesWithMetadata:
        relevant_experiences = []
        most_likely_current_title = contact_job_title
        title_mismatch = False
        # Sort experiences by start date, most recent first
        sorted_experiences = sorted(experiences_data,
                                    key=lambda x: datetime(
                                        x.starts_at.year if x.starts_at and x.starts_at.year else 1,
                                        x.starts_at.month if x.starts_at and x.starts_at.month else 1,
                                        x.starts_at.day if x.starts_at and x.starts_at.day else 1
                                    ), reverse=True)

        for exp in sorted_experiences:
            if (exp.is_current or exp.company.lower() == current_company.lower()) and exp.matches_keywords(keywords):
                relevant_experiences.append(exp)

                # Update most likely current title if this is a current role and we haven't set it yet
                if exp.is_current and most_likely_current_title == contact_job_title:
                    most_likely_current_title = exp.title
                    if most_likely_current_title.lower() != contact_job_title.lower():
                        title_mismatch = True

        return ExperiencesWithMetadata(experiences=relevant_experiences, title_mismatch=title_mismatch,
                                       most_likely_current_title=most_likely_current_title)

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
    def _add_nubela_data(contact_data: ContactData):
        if contact_data.contact_profile_link:
            nubela_data_and_pictures = get_nubela_data_for_contact(contact_data.contact_profile_link)
            nubela_data: NubelaResponse = nubela_data_and_pictures.get('nubela_response')
            profile_picture = nubela_data_and_pictures.get('local_profile_pic_url')
            banner_picture = nubela_data_and_pictures.get('local_banner_pic_url')

            if profile_picture:
                contact_data.profile_picture = profile_picture

            if banner_picture:
                contact_data.banner_picture = banner_picture

            if nubela_data:
                contact_data.bio = nubela_data.summary
                contact_data.headline = nubela_data.headline
                contact_data.industry = nubela_data.industry
                contact_data.languages = nubela_data.languages
                contact_data.volunteer_work = nubela_data.volunteer_work
                contact_data.nubela_response = nubela_data
