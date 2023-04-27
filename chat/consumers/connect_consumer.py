# Note: the words user & device are used interchangeably
# pid: Persistent identification

import json
import uuid
from json.decoder import JSONDecodeError

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from chat.events import CONNECT_EVENT_TYPES
from src.utils import is_valid_uuid, redis_client


class ConnectConsumer(AsyncJsonWebsocketConsumer):
    groups = ["broadcast"]
    _user: str | None = None
    _user_groups: str | None = None

    async def connect(self):
        headers: dict = dict(self.scope["headers"])

        # get device pid
        try:
            pid: uuid.UUID = headers[b"pid"].decode()
        except KeyError:
            await self.close()
        else:
            if is_valid_uuid(pid):
                await self.channel_layer.group_add("broadcast", self.channel_name)

                # set consumer's _user & _user_groups
                self._user = f"user:{pid}"
                self._user_groups = f"{self._user}:groups"

                # save device data in redis
                redis_client.hset(
                    name=self._user,
                    mapping={
                        "id": f"{self.channel_name}",
                        "pid": f"{pid}",
                        "last_seen": f"{timezone.now()}",
                    },
                )
                redis_client.sadd(self._user_groups, *self.groups)

                # accept connection and send current user's data if any, back to client
                await self.accept()
                await self.send_json(
                    {
                        "event": CONNECT_EVENT_TYPES.CONNECT_USER.value,
                        "status": "success",
                        "message": "Current device data",
                        "data": redis_client.hgetall(self._user),
                    }
                )

            else:
                await self.close()

    async def receive(self, text_data=None, bytes_data=None):
        try:
            alias: str = json.loads(text_data)["alias"]
        except (TypeError, JSONDecodeError):
            await self.send_json(
                {
                    "event": "connect.setup",
                    "status": "error",
                    "message": "Message(s) must be in json format",
                }
            )
        except KeyError:
            await self.send_json(
                {
                    "event": "connect.setup",
                    "status": "error",
                    "message": "Please provide your alias",
                }
            )
        else:
            if str(alias).isnumeric() or len(str(alias)) < 4:
                await self.send_json(
                    {
                        "event": "connect.setup",
                        "status": "error",
                        "message": "Alias must be a mix of letters & numbers, and cannot be less than 4 characters",
                    }
                )
            else:
                # update _users data, to add the users alias
                redis_client.hset(self._user, key="alias", value=alias)

                await self.send_json(
                    {
                        "event": "connect.setup",
                        "status": "success",
                        "message": "Alias saved successfully",
                    }
                )


class ScanConnectConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        ...
