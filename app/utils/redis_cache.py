import base64
import logging

import redis
import zlib
import json
from flask import current_app
from orjson import orjson

from app.models.sheet_models import SheetData


class RedisCache:
    _instance = None

    def __init__(self):
        self.redis = redis.Redis(
            host=current_app.config['REDIS_HOST'],
            port=current_app.config['REDIS_PORT'],
            db=current_app.config['REDIS_DB']
        )

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def set(self, key: str, value: SheetData, expire: int = 10800) -> bool:
        try:
            serialized_value = orjson.dumps(value.dict())
            encoded_value = base64.b64encode(serialized_value).decode('ascii')
            return self.redis.set(key, encoded_value, ex=expire)
        except Exception as e:
            logging.error(f"Error serializing or setting Redis cache: {str(e)}")
            return False

    def get(self, key: str) -> SheetData | None:
        try:
            value = self.redis.get(key)
            if value:
                decoded_value = base64.b64decode(value)
                deserialized_value = orjson.loads(decoded_value)
                return SheetData.parse_obj(deserialized_value)
        except Exception as e:
            logging.error(f"Error retrieving or deserializing Redis cache: {str(e)}")
        return None

    def delete(self, key: str):
        self.redis.delete(key)


def get_redis_cache():
    return RedisCache.get_instance()
