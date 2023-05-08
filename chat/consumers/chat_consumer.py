import json
import uuid
from json.decoder import JSONDecodeError

from channels.generic.websocket import AsyncJsonWebsocketConsumer
from django.utils import timezone

from src.utils import redis_client


class ChatOneToOneConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        headers: dict = dict(self.scope["headers"])

        try:
            pid: uuid.UUID = headers[b"pid"].decode()
        except KeyError:
            await self.close()
        else:
            # get user if connected
            user = redis_client.hget(f"user:{pid}")
