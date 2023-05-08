import uuid

import redis
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from src import env

redis_client = redis.Redis(
    host=env.REDIS_SERVER, port=env.REDIS_PORT, decode_responses=True
)

class BaseAsyncJsonWebsocketConsumer(AsyncJsonWebsocketConsumer):
    """
    Base async json websocket consumer, which extends the base class
    by providing the following instance variables, for reusability.

    Variables names

    groups: list of groups
    _did: device id. Default is None
    _device: redis key for a consumer's data. Default is None
    _device_groups: redis key for a consumer groups data. Default is None
    _device_aliases: redis key for all connected device aliases. Default is "device:aliases"
    """

    groups = ["broadcast"]

    _did: uuid.UUID | None = None
    _device: str | None = None
    _device_groups: str | None = None
    _device_aliases: str = "device:aliases"

    class Meta:
        abstract = True


def is_valid_uuid(value: uuid.UUID):
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, SyntaxError):
        return False


def convert_array_to_dict(value: list | tuple) -> dict:
    """
    Using dictionary comprehension, convert list or tuple to dict.

    The number of following elements must be even
    """
    if isinstance(value, (tuple, list)):

        if len(value) % 2:
            raise IndexError(f"Key/value error, length of value must be even: Length ({len(value)})")
        
        return {value[x]: value[x + 1] for x in range(0, len(value), 2)}

    else:
        raise TypeError("Wrong type provided, expecting 'list' or 'tuple'")
