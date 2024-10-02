# app/services/stream_processed_spreadsheet_service.py
import asyncio
import time
from datetime import datetime
from threading import Event

from app.services.spreadsheet_processor import SpreadsheetProcessor
from app.models import ContactData, CompanyData
import orjson
import traceback
from typing import List, Dict, Any
from flask import current_app


def _custom_default_serialization(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (ContactData, CompanyData)):
        return obj.dict()
    raise TypeError


def ensure_bytes(data):
    if isinstance(data, bytes):
        return data
    elif isinstance(data, str):
        return data.encode('utf-8')
    else:
        return str(data).encode('utf-8')


def _serialize_contact(contact: ContactData) -> Dict[str, Any]:
    try:
        return contact.dict()
    except Exception as e:
        return {
            'error': f'Error serializing contact: {str(e)}',
            'traceback': traceback.format_exc(),
            'contact_data': str(contact)
        }


def _process_spreadsheet(spreadsheet_id: str) -> List[Dict[str, Any]]:
    try:
        processor = SpreadsheetProcessor(spreadsheet_id)
        return [_serialize_contact(contact) for batch in processor.process() for contact in batch]
    except Exception as e:
        return [{
            'error': f'Spreadsheet {spreadsheet_id} generated an exception: {str(e)}',
            'traceback': traceback.format_exc()
        }]


def stream_processed_spreadsheets(spreadsheet_ids: List[str], continue_event: Event, small_batch_size: int = 2,
                                  large_batch_size: int = 10):
    processors = {id: SpreadsheetProcessor(id, small_batch_size=small_batch_size) for id in spreadsheet_ids}
    total_processed = 0

    while processors:
        for spreadsheet_id, processor in list(processors.items()):
            if not processor.has_more_contacts():
                del processors[spreadsheet_id]
                continue

            batch = processor.process_small_batch()
            if batch:
                total_processed += len(batch)
                yield f"data: {orjson.dumps({'contacts': [contact.dict() for contact in batch]}).decode('utf-8')}\n\n"

            if total_processed >= large_batch_size:
                current_app.logger.info(f"Processed {total_processed} contacts. Waiting for user action.")
                yield "data: " + orjson.dumps({'await_user_action': True}).decode('utf-8') + "\n\n"
                continue_event.clear()
                continue_event.wait()  # This will block until the event is set
                total_processed = 0  # Reset the counter
                current_app.logger.info("Received continue action. Resuming processing.")

    current_app.logger.info("All processors finished. Sending complete signal.")
    yield "data: " + orjson.dumps({'complete': True}).decode('utf-8') + "\n\n"
