from datetime import datetime

from app.services.spreadsheet_processor import SpreadsheetProcessor
import json


class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def stream_processed_spreadsheets(spreadsheet_ids):
    for spreadsheet_id in spreadsheet_ids:
        try:
            processor = SpreadsheetProcessor(spreadsheet_id)
            for batch_result in processor.process():
                yield f"data: {json.dumps(batch_result, cls=CustomJSONEncoder)}\n\n"
        except Exception as exc:
            error_message = f'Spreadsheet {spreadsheet_id} generated an exception: {str(exc)}'
            yield f"data: {json.dumps({'error': error_message}, cls=CustomJSONEncoder)}\n\n"

    yield f"data: {json.dumps({'complete': True}, cls=CustomJSONEncoder)}\n\n"
