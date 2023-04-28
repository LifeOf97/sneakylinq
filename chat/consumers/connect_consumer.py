# Note: the words user & device are used interchangeably
# pid: Persistent identification

import json
import uuid
from json.decoder import JSONDecodeError

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.layers import get_channel_layer
from django.utils import timezone

from chat.events import CONNECT_EVENT_TYPES, SCAN_EVENT_TYPES
from src.helpers import format_alias, is_valid_alias
from src.utils import is_valid_uuid, redis_client

CHANNEL_LAYER = get_channel_layer()


class ConnectConsumer(AsyncJsonWebsocketConsumer):
    groups = ["broadcast"]
    _user: str | None = None
    _user_groups: str | None = None

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

                # update  _user & _user_groups values
                self._user = f"user:{pid}"
                self._user_groups = f"{self._user}:groups"

                # store data in redis
                redis_client.hset(
                    name=self._user,
                    mapping={
                        "pid": f"{pid}",
                        "channel": f"{self.channel_name}",
                        "last_seen": f"{timezone.now()}",
                    },
                )

                # store users groups in redis also
                redis_client.sadd(self._user_groups, *self.groups)

                # accept connection and send device data if any, back to client
                await self.accept()
                await self.send_json(
                    {
                        "event": CONNECT_EVENT_TYPES.CONNECT_USER.value,
                        "status": True,
                        "message": "Current device data",
                        "data": {
                            **redis_client.hgetall(self._user),
                            **{
                                "groups": list(redis_client.smembers(self._user_groups))
                            },
                        },
                    }
                )

            else:
                await self.close()

    async def disconnect(self, code):
        await self.channel_layer.group_discard("group", self.channel_name)
        redis_client.hdel(self._user, "channel")

    async def receive(self, text_data=None, bytes_data=None):
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
            alias_msg, alias_status = is_valid_alias(alias)

            await self.send_json(
                {
                    "event": CONNECT_EVENT_TYPES.CONNECT_SETUP.value,
                    "status": alias_status,
                    "message": alias_msg,
                }
            )

            if alias_status:
                # update _users data, to add the users/device alias
                redis_client.hset(self._user, key="alias", value=format_alias(alias))

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
