import json
import uuid
from json.decoder import JSONDecodeError

from django.utils import timezone

from chat.events import CONNECT_EVENT_TYPES, SCAN_EVENT_TYPES
from src.helpers import format_alias, is_valid_alias
from src.utils import BaseAsyncJsonWebsocketConsumer, is_valid_uuid, redis_client


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

                # set instance variables _did,  _device & _device_groups values
                self._did = did
                self._device = f"device:{self._did}"
                self._device_groups = f"{self._device}:groups"

                # store data in redis
                redis_client.hset(
                    name=self._device,
                    mapping={
                        "did": f"{self._did}",
                        "channel": f"{self.channel_name}",
                        "last_seen": f"{timezone.now()}",
                        "alias": f"{redis_client.hget(self._device_aliases, key=self._did)}",
                    },
                )

                # store users groups in redis also
                redis_client.sadd(self._device_groups, *self.groups)

                # accept connection and send device data back to client
                await self.accept()
                await self.send_json(
                    {
                        "event": CONNECT_EVENT_TYPES.CONNECT_DEVICE.value,
                        "status": True,
                        "message": "Current device data",
                        "data": {
                            **redis_client.hgetall(self._device),
                            **{
                                "groups": list(
                                    redis_client.smembers(self._device_groups)
                                )
                            },
                        },
                    }
                )

            else:
                await self.close()

    async def disconnect(self, code):
        await self.channel_layer.group_discard("broadcast", self.channel_name)
        redis_client.hdel(self._device, "channel")

    async def receive(self, text_data=None, bytes_data=None):
        """Receive device alias and store in redis"""

        try:
            alias: str = json.loads(text_data)["alias"]
        except (TypeError, JSONDecodeError):
            await self.send_json(
                {
                    "event": CONNECT_EVENT_TYPES.CONNECT_SETUP.value,
                    "status": False,
                    "message": "Message(s) must be in json format",
                }
            )
        except KeyError:
            await self.send_json(
                {
                    "event": CONNECT_EVENT_TYPES.CONNECT_SETUP.value,
                    "status": False,
                    "message": "Please provide your alias",
                }
            )
        else:
            alias_msg, alias_name, alias_status = is_valid_alias(alias=alias)

            if alias_status:
                alias_msg, alias_name, alias_status = format_alias(
                    did=self._did, alias=alias_name
                )

                if alias_status:
                    # add the device alias to device data and device aliases in redis store
                    redis_client.hset(self._device, key="alias", value=alias_name)
                    redis_client.hset(
                        self._device_aliases, key=self._did, value=alias_name
                    )

                    # notify device with the qr code.
                    await self.channel_layer.send(
                        redis_client.hget(self._device, key="channel"),
                        {
                            "type": "chat.message",
                            "data": {
                                "event": CONNECT_EVENT_TYPES.CONNECT_SETUP.value,
                                "status": True,
                                "message": alias_msg,
                                "data": {
                                    **redis_client.hgetall(self._device),
                                    **{
                                        "groups": list(
                                            redis_client.smembers(self._device_groups)
                                        )
                                    },
                                },
                            },
                        },
                    )

            await self.send_json(
                {
                    "event": CONNECT_EVENT_TYPES.CONNECT_SETUP.value,
                    "status": alias_status,
                    "message": alias_msg,
                    "data": {"alias": alias_name if alias_status else None},
                }
            )

    async def chat_message(self, event):
        await self.send_json(event["data"])


class ScanConnectConsumer(BaseAsyncJsonWebsocketConsumer):
    """
    Implements a scan to connect feature via QR Code scanning
    and carry out setup
    """

    async def connect(self):
        self._did = self.scope["url_route"]["kwargs"]["did"]
        self._device = f"device:{self._did}"
        self._device_groups = f"{self._device}:groups"

        await self.accept()

        if (
            redis_client.hget(self._device, key="channel")
            and redis_client.hget(self._device, key="alias") == "None"
        ):
            # notify the client of the scanned device details
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_NOTIFY.value,
                    "status": True,
                    "message": "Scanned device data",
                    "data": redis_client.hgetall(self._device),
                }
            )

            # also notify device with the qr code.
            await self.channel_layer.send(
                redis_client.hget(self._device, key="channel"),
                {
                    "type": "chat.message",
                    "data": {
                        "event": SCAN_EVENT_TYPES.SCAN_NOTIFY.value,
                        "status": True,
                        "message": "QR code scanned successfully",
                    },
                },
            )

        else:
            # notify the client of the scanned device details, then close connection
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_NOTIFY.value,
                    "status": False,
                    "message": "Channel not found",
                    "data": redis_client.hgetall(self._device),
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
                    did=self._did, alias=alias_name
                )

                if alias_status:
                    # add the device alias to device data and device aliases in redis store
                    redis_client.hset(self._device, key="alias", value=alias_name)
                    redis_client.hset(
                        self._device_aliases, key=str(self._did), value=alias_name
                    )

                    # notify device with the qr code.
                    await self.channel_layer.send(
                        redis_client.hget(self._device, key="channel"),
                        {
                            "type": "chat.message",
                            "data": {
                                "event": SCAN_EVENT_TYPES.SCAN_SETUP.value,
                                "status": True,
                                "message": alias_msg,
                                "data": {
                                    **redis_client.hgetall(self._device),
                                    **{
                                        "groups": list(
                                            redis_client.smembers(self._device_groups)
                                        )
                                    },
                                },
                            },
                        },
                    )

            # notify the client if operation is successfull or not
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_SETUP.value,
                    "status": alias_status,
                    "message": alias_msg,
                    "data": redis_client.hgetall(self._device)
                    if alias_status
                    else {"alias": None},
                }
            )

    async def chat_message(self, event):
        await self.send_json(event["data"])
