# app/services/stream_processed_spreadsheet_service.py

from datetime import datetime
from app.services.spreadsheet_processor import SpreadsheetProcessor
from app.models import ContactData, CompanyData
import orjson
import traceback
from typing import List, Dict, Any


def _custom_default_serialization(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, (ContactData, CompanyData)):
        return obj.dict()
    raise TypeError


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


def stream_processed_spreadsheets(spreadsheet_ids: List[str]):
    for spreadsheet_id in spreadsheet_ids:
        results = _process_spreadsheet(spreadsheet_id)
        yield f"data: {orjson.dumps(results, default=_custom_default_serialization, option=orjson.OPT_SERIALIZE_NUMPY).decode('utf-8')}\n\n"

    yield f"data: {orjson.dumps({'complete': True}).decode('utf-8')}\n\n"
