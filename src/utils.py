import uuid

import redis

from src import env

redis_client = redis.Redis(
    host=env.REDIS_SERVER, port=env.REDIS_PORT, decode_responses=True
)


def is_valid_uuid(value: uuid.UUID):
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, SyntaxError):
        return False