import uuid

from chat.events import DEVICE_EVENT_TYPES
from chat.lua_scripts import LuaScripts
from src.utils import (
    BaseAsyncJsonWebsocketConsumer,
    convert_array_to_dict,
    is_valid_uuid,
    redis_client,
)


class P2PChatConsumer(BaseAsyncJsonWebsocketConsumer):
    async def connect(self):
        headers: dict = dict(self.scope["headers"])

        try:  # get device did
            self.did = headers[b"did"].decode()
        except KeyError:
            await self.close()
        else:
            if is_valid_uuid(self.did):
                # set instance variables did, device & device_groups values
                self.device = f"device:{self.did}"
                self.device_groups = f"{self.device}:groups"

                await self.accept()
            else:
                await self.close()

    async def receive_json(self, content, **kwargs):
        data = content[data]

        await self.channel_layer.send(redis_client.hget())

    async def chat_message(self, event):
        raise NotImplementedError

    async def disconnect(self, code):
        await self.channel_layer.group_discard("broadcast", self.channel_name)

        redis_client.hdel(
            self.alias_device,
            redis_client.hget(self.device_alias, self.device),
        )
        redis_client.hdel(self.device_aliases, self.device)
        redis_client.delete(self.device)
