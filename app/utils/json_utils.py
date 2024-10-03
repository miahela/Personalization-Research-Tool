# app/utils/json_utils.py

from typing import Any
import orjson
from pydantic import BaseModel
from pydantic_core import Url

def custom_json_encoder(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    elif isinstance(obj, Url):
        return str(obj)
    raise TypeError(f"Type {type(obj)} not serializable")

def dumps(v: Any, *, default: Any = None) -> str:
    return orjson.dumps(v, default=custom_json_encoder).decode('utf-8')