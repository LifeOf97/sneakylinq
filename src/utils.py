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
    did: device id. Default is None
    device: redis key for a consumer's data. Default is None
    device_groups: redis key for a consumer groups data. Default is None
    device_alias: redis hash to store all connected device aliases.
            Where key is device:did and value is alias. Hash name is device:alias"
    alias_device: redis hash to store all connected device aliases.
            Where key is alias and value is device:did. Hash name is alias:device"
    """

    groups = ["broadcast"]

    did: uuid.UUID | None = None
    device: str | None = None
    device_groups: str | None = None
    device_alias: str = "device:alias"
    alias_device: str = "alias:device"

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
            raise IndexError(
                f"Key/value error, length of value must be even: Length ({len(value)})"
            )

        return {value[x]: value[x + 1] for x in range(0, len(value), 2)}

    else:
        raise TypeError("Wrong type provided, expecting 'list' or 'tuple'")
