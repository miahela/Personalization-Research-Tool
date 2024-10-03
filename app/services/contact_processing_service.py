from typing import List
from app.models import ContactData, SheetRow, CompanyData
from app.services.contact_service import ContactService
from app.services.spreadsheet_service import SpreadsheetService
from flask import current_app


class ContactProcessingService:
    def __init__(self, spreadsheet_id: str, batch_size: int = 2):
        self.spreadsheet_id = spreadsheet_id
        self.batch_size = batch_size
        self.contact_service = ContactService.get_instance()
        self.spreadsheet_service = SpreadsheetService.get_instance()
        self.processed_row_numbers = set()

    def process_batch(self) -> List[ContactData]:
        spreadsheet_data = self.spreadsheet_service.get_spreadsheet(self.spreadsheet_id)
        unprocessed_rows = self.spreadsheet_service.calculate_unprocessed_rows_in_sheet(spreadsheet_data.new_connections)

        batch = []
        for row in unprocessed_rows:
            if len(batch) >= self.batch_size:
                break
            if row.row_number in self.processed_row_numbers:
                continue
            try:
                processed_contact = self._process_contact(row, spreadsheet_data)
                batch.append(processed_contact)
                self.processed_row_numbers.add(row.row_number)
            except Exception as e:
                current_app.logger.error(f"Error processing contact: {str(e)}")

        return batch

    def has_more_contacts(self) -> bool:
        spreadsheet_data = self.spreadsheet_service.get_spreadsheet(self.spreadsheet_id)
        unprocessed_rows = self.spreadsheet_service.calculate_unprocessed_rows_in_sheet(spreadsheet_data.new_connections)
        return any(row.row_number not in self.processed_row_numbers for row in unprocessed_rows)

    def _process_contact(self, row: SheetRow, spreadsheet_data) -> ContactData:
        company_data = self._get_company_data(row, spreadsheet_data)
        contact_data = self.contact_service.create_or_update_contact(
            row, company_data, self.spreadsheet_id, spreadsheet_data.new_connections.colored_cells
        )
        self.contact_service.add_relevant_experience(contact_data, spreadsheet_data.keywords)
        return contact_data

    @staticmethod
    def _get_company_data(row: SheetRow, spreadsheet_data) -> CompanyData:
        company_name = row.get('contact_company_name', '')
        pq_row = spreadsheet_data.pq_data.get_row_by_text(company_name)
        if pq_row:
            company_website = pq_row.get('Website URL', '')
            return CompanyData(name=company_name, website=company_website)
        return CompanyData(name=company_name)
