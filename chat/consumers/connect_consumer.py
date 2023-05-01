# Note: the words user & device are used interchangeably
# pid: Persistent identification

import json
import uuid
from json.decoder import JSONDecodeError

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from chat.events import CONNECT_EVENT_TYPES, SCAN_EVENT_TYPES
from src.helpers import format_alias, is_valid_alias
from src.utils import is_valid_uuid, redis_client


class ConnectConsumer(AsyncJsonWebsocketConsumer):
    groups = ["broadcast"]

    _pid: uuid.UUID | None = None
    _device: str | None = None
    _device_groups: str | None = None
    _device_aliases: str = "device:aliases"

    async def connect(self):
        headers: dict = dict(self.scope["headers"])

        try:
            # get device pid
            pid: str | uuid.UUID = headers[b"pid"].decode()
        except KeyError:
            await self.close()
        else:
            if is_valid_uuid(pid):
                await self.channel_layer.group_add("broadcast", self.channel_name)

                # set _pid,  _device & _device_groups values
                self._pid = pid
                self._device = f"device:{self._pid}"
                self._device_groups = f"{self._device}:groups"

                # store data in redis
                redis_client.hset(
                    name=self._device,
                    mapping={
                        "pid": f"{self._pid}",
                        "channel": f"{self.channel_name}",
                        "last_seen": f"{timezone.now()}",
                    },
                )

                # store users groups in redis also
                redis_client.sadd(self._device_groups, *self.groups)

                # accept connection and send device data back to client
                await self.accept()
                await self.send_json(
                    {
                        "event": CONNECT_EVENT_TYPES.CONNECT_USER.value,
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
        await self.channel_layer.group_discard("group", self.channel_name)
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
                    pid=self._pid, alias=alias_name
                )

                if alias_status:
                    # add the device alias to device data and device aliases in redis store
                    redis_client.hset(self._device, key="alias", value=alias_name)
                    redis_client.hset(
                        self._device_aliases, key=self._pid, value=alias_name
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


class ScanConnectConsumer(AsyncJsonWebsocketConsumer):
    """Implements a scan to connect feature via QR Code scanning"""

    async def connect(self):
        pid = self.scope["url_route"]["kwargs"]["pid"]

        await self.accept()

        if redis_client.hget(f"user:{pid}", key="channel"):
            # notify the client of the scanned device details
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_NOTIFY.value,
                    "status": True,
                    "message": "Scanned device data",
                    "data": redis_client.hgetall(f"user:{pid}"),
                }
            )

            # notify device with the qr code.
            await self.channel_layer.send(
                redis_client.hget(f"user:{pid}", key="channel"),
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
            # notify the client of the scanned device details
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_NOTIFY.value,
                    "status": False,
                    "message": "Channel not found",
                    "data": redis_client.hgetall(f"user:{pid}"),
                }
            )

    async def chat_message(self, event):
        await self.send_json(event["data"])
