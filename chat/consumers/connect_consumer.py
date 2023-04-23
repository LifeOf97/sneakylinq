import json
import uuid
from json.decoder import JSONDecodeError

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from src.utils import redis_client


class ConnectConsumer(AsyncJsonWebsocketConsumer):
    groups = ["broadcast"]
    _user: str | None = None
    _user_groups: str | None = None

    async def connect(self):
        headers: dict = dict(self.scope["headers"])

        try:
            pid: uuid.UUID = headers[b"pid"].decode()
        except KeyError:
            await self.close()
        else:
            await self.channel_layer.group_add("broadcast", self.channel_name)

            # set instance _user & _user_groups
            self._user = f"user:{pid}"
            self._user_groups = f"{self._user}:groups"

            redis_client.hset(
                name=self._user,
                mapping={
                    "id": f"{self.channel_name}",
                    "pid": f"{pid}",
                    "last_seen": f"{timezone.now()}",
                },
            )

            redis_client.sadd(self._user_groups, *self.groups)

            await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard("broadcast", self.channel_name)
        redis_client.delete(self._user, self._user_groups)

    async def receive(self, text_data=None, bytes_data=None):
        try:
            received = json.loads(text_data)
        except JSONDecodeError:
            await self.send_json(
                {
                    "event": "message.receive",
                    "status": "error",
                    "data": {"detail": "Message not valid json"},
                }
            )
        else:
            await self.send_json(
                {
                    "event": "message.receive",
                    "status": "success",
                    "data": received,
                }
            )
