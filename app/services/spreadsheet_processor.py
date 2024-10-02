import logging
import re
from app.utils.google_utils.google_sheets import get_sheet_data, get_colored_cells, get_sheet_names
from app.services.data_processor import filter_data, process_new_connections, process_pq, process_nubela_data
from app.utils.external_apis import search_company_about_page, search_company_case_studies, \
    search_person_interviews_podcasts, get_nubela_data_for_user


class SpreadsheetProcessor:
    def __init__(self, spreadsheet_id, batch_size=2):
        self.spreadsheet_id = spreadsheet_id
        self.batch_size = batch_size
        self.colored_cells = []
        self.result = {
            'spreadsheet_id': spreadsheet_id,
            'new_connections': [],
            'pq_data': {},
        }

    def process(self):
        self._process_new_connections_sheet()
        self.colored_cells = get_colored_cells(self.spreadsheet_id, 'New Connections')
        self._process_pq_sheet()
        yield from self._process_batches()

    def _process_new_connections_sheet(self):
        new_connections_data = get_sheet_data(self.spreadsheet_id, 'New Connections', 'A:ZZ')

        if new_connections_data is None or len(new_connections_data) < 2:
            self.result['error'] = 'No data found in New Connections sheet or sheet does not exist'
            return

        headers = new_connections_data[0]
        processed_data = [dict(zip(headers, row + [''] * (len(headers) - len(row)))) for row in
                          new_connections_data[1:]]

        filtered_data = filter_data(processed_data)
        self.important_data = process_new_connections(filtered_data)

    def _process_pq_sheet(self):
        sheet_names = get_sheet_names(self.spreadsheet_id)
        pq_sheet_name = next((name for name in sheet_names if name.endswith('PQ')), None)

        if pq_sheet_name:
            pq_data = get_sheet_data(self.spreadsheet_id, pq_sheet_name, 'A:ZZ')
            if pq_data and len(pq_data) > 1:
                pq_headers = pq_data[0]
                pq_processed_data = [dict(zip(pq_headers, row + [''] * (len(pq_headers) - len(row)))) for row in
                                     pq_data[1:]]
                self.result['pq_data'] = process_pq(pq_processed_data)
            else:
                self.result['pq_data'] = {}
        else:
            self.result['pq_data'] = {}

    def _process_batches(self):
        for i in range(0, len(self.important_data), self.batch_size):
            batch = self.important_data[i:i + self.batch_size]
            processed_batch = []

            for row in batch:
                processed_row = self._process_row(row)
                processed_batch.append(processed_row)

            self.result['new_connections'] = processed_batch
            yield self.result

        self._log_processing_results()

    def _process_row(self, row):
        row['spreadsheet_id'] = self.spreadsheet_id
        row['colored_cells'] = self.colored_cells

        company_name = row.get('contact_company_name', '').strip().lower()
        full_name = f"{row.get('contact_first_name', '').strip()} {row.get('contact_last_name', '').strip()}".strip()
        company_website = self.result['pq_data'].get(company_name, '')

        if company_name and company_website:
            row['company_website'] = company_website
            clean_website = re.sub(r'^https?://www\.', '', company_website)
            self._process_company_links(row, company_name, clean_website)

        self._process_media_links(row, full_name, company_name)
        self._process_linkedin_data(row)

        return row

    def _process_company_links(self, row, company_name, clean_website):
        company_links = search_company_about_page(clean_website, row)
        if company_links:
            row['company_about_link'] = []
            for link in company_links[:3]:
                row['company_about_link'].append({
                    'title': link.get('title', ''),
                    'url': link.get('url', ''),
                    'description': link.get('description', ''),
                })
                logging.info(f"About page links for {company_name}: {link.get('url')}")

        case_study_links = search_company_case_studies(clean_website, row['linkedin_username'])
        if case_study_links:
            row['case_study_links'] = case_study_links
            logging.info(f"Case study links for {company_name}: {case_study_links}")

    def _process_media_links(self, row, full_name, company_name):
        media_links = search_person_interviews_podcasts(full_name, company_name, row['linkedin_username'])
        if media_links:
            row['interviews_and_podcasts'] = []
            for link in media_links:
                row['interviews_and_podcasts'].append({
                    'url': link.get('url', ''),
                    'title': link.get('title', ''),
                    'date': link.get('date', ''),
                    'description': link.get('description', ''),
                })

    def _process_linkedin_data(self, row):
        linkedin_profile_url = row.get('contact_profile_link', '')
        if linkedin_profile_url:
            nubela_data = get_nubela_data_for_user(linkedin_profile_url)
            if nubela_data:
                row.update(process_nubela_data(nubela_data))

    def _log_processing_results(self):
        logging.info(
            f"Spreadsheet {self.spreadsheet_id}: Number of rows after processing New Connections: {len(self.important_data)}")
        logging.info(
            f"Spreadsheet {self.spreadsheet_id}: Number of rows after processing PQ sheet: {len(self.result['pq_data'])}")
