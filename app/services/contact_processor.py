from threading import Event
from typing import List, Any, Generator
from flask import current_app
import orjson
from pydantic import BaseModel
from pydantic_core import Url

from app.models import ContactData
from app.services.contact_service import ContactService
from app.services.spreadsheet_service import SpreadsheetService


class ContactProcessor:
    def __init__(self, spreadsheet_id: str, batch_size: int = 2):
        self.spreadsheet_id = spreadsheet_id
        self.batch_size = batch_size
        self.contact_service = ContactService.get_instance()
        self.spreadsheet_service = SpreadsheetService.get_instance()
        self.processed_row_numbers = set()

    def process_batch(self) -> List[ContactData]:
        spreadsheet_data = self.spreadsheet_service.get_spreadsheet(self.spreadsheet_id)
        unprocessed_rows = self.spreadsheet_service.calculate_unprocessed_rows_in_sheet(
            spreadsheet_data.new_connections)

        batch = []
        for row in unprocessed_rows:
            if len(batch) >= self.batch_size:
                break
            if row.row_number in self.processed_row_numbers:
                continue
            try:
                processed_contact = self.contact_service.get_or_create_contact(row, self.spreadsheet_id)
                batch.append(processed_contact)
                self.processed_row_numbers.add(row.row_number)
            except Exception as e:
                current_app.logger.error(f"Error processing contact: {str(e)}")

        return batch

    def has_more_contacts(self) -> bool:
        spreadsheet_data = self.spreadsheet_service.get_spreadsheet(self.spreadsheet_id)
        unprocessed_rows = self.spreadsheet_service.calculate_unprocessed_rows_in_sheet(
            spreadsheet_data.new_connections)
        return any(row.row_number not in self.processed_row_numbers for row in unprocessed_rows)


def _custom_json_encoder(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    elif isinstance(obj, Url):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def _dumps(v: Any, *, default: Any = None) -> str:
    return orjson.dumps(v, default=_custom_json_encoder).decode('utf-8')


def stream_processed_contacts(spreadsheet_ids: List[str], continue_event: Event, small_batch_size: int = 2,
                              large_batch_size: int = 10) -> Generator[str, None, None]:
    processors = {id: ContactProcessor(id, small_batch_size) for id in spreadsheet_ids}
    total_processed = 0

    while processors:
        for spreadsheet_id, processor in list(processors.items()):
            if not processor.has_more_contacts():
                del processors[spreadsheet_id]
                continue

            batch = processor.process_batch()
            if batch:
                total_processed += len(batch)
                yield f"data: {_dumps({'contacts': [contact.model_dump() for contact in batch]})}\n\n"

            if total_processed >= large_batch_size:
                current_app.logger.info(f"Processed {total_processed} contacts. Waiting for user action.")
                yield "data: " + orjson.dumps({'await_user_action': True}).decode('utf-8') + "\n\n"
                continue_event.clear()
                continue_event.wait()  # This will block until the event is set
                total_processed = 0  # Reset the counter
                current_app.logger.info("Received continue action. Resuming processing.")

    current_app.logger.info("All processors finished. Sending complete signal.")
    yield "data: " + orjson.dumps({'complete': True}).decode('utf-8') + "\n\n"
