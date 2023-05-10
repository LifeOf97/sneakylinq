from django.utils.text import slugify

from src.utils import redis_client


def is_valid_alias(alias: str) -> tuple[str, str, bool]:
    """
    Checks the validity of an alias.
    
    converts spaces and hyphens to underscores before checks.
    """

    alias: str = slugify(str(alias).lower()).replace("-", "_")

    message: str | None = None
    status: bool = True

    if "." in alias:
        status = False
        message = "Alias cannot contain period (.) sign."

    elif alias.isnumeric():
        status = False
        message = (
            "Alias must be a mix of letters & numbers, and can contain underscores"
        )

    elif len(alias) < 4 or len(alias) > 15:
        status = False
        message = "Alias must be between 4 to 15 characters long"

    elif alias in ["none", "sneaky", "linq", "sneakylinq", "sneaky_linq"]:
        status = False
        message = f"{alias} is not allowed"

    return message, alias, status


def format_alias(device: str, alias: str) -> tuple[str, str, bool]:
    """
    Append the word (.linq) to alias, check if the alias already belongs
    to another device or is already the alias of the device trying to set their
    alias, in the redis store.

    User's alias are stored in redis as hash, with key "device:aliases"

    did: user's pid as key
    alias: the new alias to set
    """
    _device_aliases: str = "device:aliases"
    alias: str = f"{alias}.linq"

    message: str = "Alias accepted"
    status: bool = True

    if alias == redis_client.hget(_device_aliases, key=device):
        status = False
        message = f"{alias} is already your device alias"

    elif alias in redis_client.hvals(_device_aliases):
        status = False
        message = "Alias already taken"

    return message, alias, status
