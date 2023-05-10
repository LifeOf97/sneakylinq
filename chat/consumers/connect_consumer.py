import json
import uuid
from json.decoder import JSONDecodeError

from django.utils import timezone

from chat.events import DEVICE_EVENT_TYPES, SCAN_EVENT_TYPES
from chat.lua_scripts import LuaScripts
from src.helpers import format_alias, is_valid_alias
from src.utils import (
    BaseAsyncJsonWebsocketConsumer,
    convert_array_to_dict,
    is_valid_uuid,
    redis_client,
)


class ConnectConsumer(BaseAsyncJsonWebsocketConsumer):
    """Connect client to websocket server and carry out setup"""

    async def connect(self):
        headers: dict = dict(self.scope["headers"])

        try:
            # get device did
            did: str | uuid.UUID = headers[b"did"].decode()
        except KeyError:
            await self.close()
        else:
            if is_valid_uuid(did):
                await self.channel_layer.group_add("broadcast", self.channel_name)

                # set instance variables _did, _device & _device_groups values
                self._did = did
                self._device = f"device:{self._did}"
                self._device_groups = f"{self._device}:groups"

                # accept connection
                await self.accept()

                # store data in redis as hash and give it an expire option
                redis_client.hset(
                    name=self._device,
                    mapping={
                        "did": f"{self._did}",
                        "channel": f"{self.channel_name}",
                    },
                )

                # store users groups in redis also
                redis_client.sadd(self._device_groups, *self.groups)

                # send device data back to client
                await self.send_json(
                    {
                        "event": DEVICE_EVENT_TYPES.DEVICE_CONNECT.value,
                        "status": True,
                        "message": "Current device data",
                        "data": convert_array_to_dict(
                            LuaScripts.get_device_data(
                                keys=[self._device],
                                client=redis_client,
                            )
                        )
                    }
                )

            else:
                await self.close()

    async def disconnect(self, code):
        await self.channel_layer.group_discard("broadcast", self.channel_name)
        redis_client.hdel(self._device_aliases, self._device)
        redis_client.delete(self._device)

    async def receive(self, text_data=None, bytes_data=None):
        """Receive device alias and store in redis"""

        try:
            alias: str = json.loads(text_data)["alias"]
        except (TypeError, JSONDecodeError):
            await self.send_json(
                {
                    "event": DEVICE_EVENT_TYPES.DEVICE_SETUP.value,
                    "status": False,
                    "message": "Message(s) must be in json format",
                }
            )
        except KeyError:
            await self.send_json(
                {
                    "event": DEVICE_EVENT_TYPES.DEVICE_SETUP.value,
                    "status": False,
                    "message": "Please provide your alias",
                }
            )
        else:
            alias_msg, alias_name, alias_status = is_valid_alias(alias=alias)

            if alias_status:
                alias_msg, alias_name, alias_status = format_alias(
                    device=self._device, alias=alias_name
                )

                if alias_status:
                    # add the device alias to device aliases in redis store
                    redis_client.hset(
                        self._device_aliases, key=self._device, value=alias_name
                    )

                    # connection time-to-live date object
                    ttl = timezone.now() + timezone.timedelta(hours=2)

                    # update device data to include the time to live value. And also
                    # set an expire option to the device data in redis store using the
                    # ttl as the value.
                    redis_client.hset(self._device, key="ttl", value=ttl.timestamp())
                    redis_client.expireat(self._device, ttl)

                    # notify client if successfull.
                    await self.channel_layer.send(
                        redis_client.hget(self._device, key="channel"),
                        {
                            "type": "chat.message",
                            "data": {
                                "event": DEVICE_EVENT_TYPES.DEVICE_SETUP.value,
                                "status": True,
                                "message": alias_msg,
                                "data": convert_array_to_dict(
                                    LuaScripts.get_device_data(keys=[self._device], client=redis_client)
                                )
                            },
                        },
                    )

                    return

            # notify client for errors
            await self.send_json(
                {
                    "event": DEVICE_EVENT_TYPES.DEVICE_SETUP.value,
                    "status": alias_status,
                    "message": alias_msg,
                    "data": {"alias": alias_name},
                }
            )

    async def chat_message(self, event):
        await self.send_json(event["data"])


class ScanConnectConsumer(BaseAsyncJsonWebsocketConsumer):
    """
    Implements a scan to connect feature via QR Code scanning
    and carries out device setup.
    """

    async def connect(self):
        self._did = self.scope["url_route"]["kwargs"]["did"]
        self._device = f"device:{self._did}"
        self._device_groups = f"{self._device}:groups"

        await self.accept()

        if (
            redis_client.hget(self._device, key="channel")
            and redis_client.hget(self._device_aliases, key=self._device) == None
        ):
            # notify the client of the scanned device details
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_CONNECT.value,
                    "status": True,
                    "message": "Scanned device data",
                    "data": convert_array_to_dict(
                        LuaScripts.get_device_data(
                            keys=[self._device],
                            client=redis_client,
                        )
                    ),
                }
            )

            # also notify device with the qr code.
            await self.channel_layer.send(
                redis_client.hget(self._device, key="channel"),
                {
                    "type": "chat.message",
                    "data": {
                        "event": SCAN_EVENT_TYPES.SCAN_CONNECT.value,
                        "status": True,
                        "message": "QR code scanned successfully",
                    },
                },
            )

        else:
            # notify the client of the scanned device details, then close connection
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_CONNECT.value,
                    "status": False,
                    "message": "Invalid channel or device already setup",
                }
            )
            await self.close()

    async def receive(self, text_data=None, bytes_data=None):
        """Receive device alias and store in redis"""

        try:
            alias: str = json.loads(text_data)["alias"]
        except (TypeError, JSONDecodeError):
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_SETUP.value,
                    "status": False,
                    "message": "Message(s) must be in json format",
                }
            )
        except KeyError:
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_SETUP.value,
                    "status": False,
                    "message": "Please provide your alias",
                }
            )
        else:
            alias_msg, alias_name, alias_status = is_valid_alias(alias=alias)

            if alias_status:
                alias_msg, alias_name, alias_status = format_alias(
                    device=self._device, alias=alias_name
                )

                if alias_status:
                    # add the device alias to device aliases in redis store
                    redis_client.hset(
                        self._device_aliases, key=self._device, value=alias_name
                    )

                    # connection time-to-live date object
                    ttl = timezone.now() + timezone.timedelta(hours=2)

                    # update device data to include the time to live value. And also
                    # set an expire option to the device data in redis store using the
                    # ttl as the value.
                    redis_client.hset(self._device, key="ttl", value=ttl.timestamp())
                    redis_client.expireat(self._device, ttl)


                    # SUCCESS: notify device with the qr code.
                    await self.channel_layer.send(
                        redis_client.hget(self._device, key="channel"),
                        {
                            "type": "chat.message",
                            "data": {
                                "event": SCAN_EVENT_TYPES.SCAN_SETUP.value,
                                "status": True,
                                "message": alias_msg,
                                "data": convert_array_to_dict(
                                    LuaScripts.get_device_data(
                                        keys=[self._device],
                                        client=redis_client,
                                    )
                                ),
                            },
                        },
                    )

            # SUCCESS | FAILURE: notify the client only
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_SETUP.value,
                    "status": alias_status,
                    "message": alias_msg,
                    "data": {"alias": alias_name},
                }
            )

    async def chat_message(self, event):
        await self.send_json(event["data"])
