import logging
from typing import Any

import redis
from flask import current_app
from orjson import orjson


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

    def set(self, key: str, value: Any, expire: int = 10800) -> bool:
        try:
            serialized_value = orjson.dumps(value)
            return self.redis.set(key, serialized_value, ex=expire)
        except Exception as e:
            logging.error(f"Error serializing or setting Redis cache: {str(e)}")
            return False

    def get(self, key: str) -> Any | None:
        try:
            value = self.redis.get(key)
            if value:
                return orjson.loads(value)
        except Exception as e:
            logging.error(f"Error retrieving or deserializing Redis cache: {str(e)}")
        return None

    def delete(self, key: str):
        self.redis.delete(key)


def get_redis_cache():
    return RedisCache.get_instance()
