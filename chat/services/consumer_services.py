import uuid

from django.utils import timezone
from django.utils.text import slugify

from chat.lua_scripts import LuaScripts
from src.utils import convert_array_to_dict, redis_client


class ConsumerServices:
    """
    Commonly needed consumer services.
    """

    @staticmethod
    def set_device_data(device: str, did: uuid.UUID, channel: str) -> None:
        """
        Set/update device hash in redis store, also set an expire option to
        the device hash in redis store using the ttl as value.

        :param device: Unique device id
        :param did: Device uuid, from the connection subprotocols
        :param channel: Channel given to the consumer on connect
        """
        ttl = timezone.now() + timezone.timedelta(hours=2)

        redis_client.hset(
            name=device,
            mapping={
                "did": f"{did}",
                "channel": f"{channel}",
                "ttl": ttl.timestamp(),
            },
        )
        redis_client.expireat(device, ttl)

        # call method to update the 'alias:device' redis hash
        ConsumerServices.set_alias_device(device=device)

    @staticmethod
    def set_device_alias(
        device: str,
        alias: str,
        device_alias: str = "device:alias",
        alias_device: str = "alias:device",
    ) -> None:
        """
        Add the device alias to device:alias & alias:device hashes in redis store.

        :param device: The name of the hash in redis that holds a particular device data
        :param alias: The alias for the device.
        :param device_alias: This holds the name of the redis hash. Default is 'device:alias'
        :param alias_device: This holds the name of the redis hash. Default is 'alias:device'

        In redis store, update device data ttl value. And also set an expire
        option to the device data in redis store using the ttl as the value.
        """
        redis_client.hset(device_alias, key=device, value=alias)
        redis_client.hset(alias_device, key=alias, value=device)

        ttl = timezone.now() + timezone.timedelta(hours=2)

        redis_client.hset(device, key="ttl", value=ttl.timestamp())
        redis_client.expireat(device, ttl)

    @staticmethod
    def get_device_data(device: str) -> dict:
        """Get and return device data, from redis store. By calling a lua script"""
        return (
            convert_array_to_dict(
                LuaScripts.get_device_data(
                    keys=[device],
                    client=redis_client,
                )
            ),
        )

    @staticmethod
    def set_alias_device(device: str) -> int:
        """
        Call lua script to add the connected device and it's alias
        to the 'alias:device' hash in redis store.
        """
        return LuaScripts.set_alias_device(keys=[device], client=redis_client)

    @staticmethod
    def format_and_validate_alias(alias: str) -> tuple[str, str, bool]:
        """
        Converts spaces and hyphens to underscores then validates the validity
        of an alias.

        Required
        :param alias: The value to format then validate.
        """
        alias: str = slugify(str(alias).lower()).replace("-", "_")

        message: str = "Alias formated successfully"
        status: bool = True

        if alias.isnumeric():
            status = False
            message = "Alias must be a mix of alphanumeric characters"

        elif len(alias) < 4 or len(alias) > 15:
            status = False
            message = "Alias must be between 4 to 15 characters long"

        elif alias in ["none", "sneaky", "linq", "sneakylinq", "sneaky_linq"]:
            status = False
            message = f"{alias} is not allowed"

        return message, alias, status

    @staticmethod
    def format_and_verify_alias(device: str, alias: str) -> tuple[str, str, bool]:
        """
        Appends the word ".linq" to alias.

        Check if the alias already belongs to another device or is already the
        alias of the device trying to set it's alias in the redis store.

        Alias are stored in redis as hash, with name "device:alias" using
        'device' as key and 'alias' as value.

        :param device: Device used as the key.
        :param alias: The new device alias to set, used as the value.
        """
        message, alias, status = ConsumerServices.format_and_validate_alias(alias)

        if status:
            device_alias: str = "device:alias"
            alias: str = f"{alias}.linq"

            message = "Alias accepted"
            status = True

            if alias == redis_client.hget(device_alias, key=device):
                status = False
                message = f"{alias} is already your device alias"

            elif alias in redis_client.hvals(device_alias):
                status = False
                message = "Alias already taken"

            return message, alias, status

        return message, alias, status
