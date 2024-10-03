from threading import Event
from typing import Any
from typing import List

import orjson
from flask import current_app
from pydantic import BaseModel
from pydantic_core import Url

from app.services.contact_processing_service import ContactProcessingService


def _custom_json_encoder(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    elif isinstance(obj, Url):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def _dumps(v: Any, *, default: Any = None) -> str:
    return orjson.dumps(v, default=_custom_json_encoder).decode('utf-8')


def process_and_stream_contacts(spreadsheet_ids: List[str], continue_event: Event, small_batch_size: int = 2,
                                large_batch_size: int = 10):
    processors = {id: ContactProcessingService(id, small_batch_size) for id in
                  spreadsheet_ids}
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
