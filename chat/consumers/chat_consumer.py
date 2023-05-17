import json
from json.decoder import JSONDecodeError

from redis import exceptions as redis_exceptions

from chat.events import CHAT_EVENT_TYPES
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

                # accept connection, add device channel to broadcast group
                await self.accept()
                await self.channel_layer.group_add("broadcast", self.channel_name)

                # execute this lua script
                LuaScripts.set_alias_device(keys=[self.device], client=redis_client)

                # store data as hash type in redis store
                redis_client.hset(
                    name=self.device,
                    mapping={
                        "did": f"{self.did}",
                        "channel": f"{self.channel_name}",
                    },
                )

                # get device data
                device_data: dict = convert_array_to_dict(
                    LuaScripts.get_device_data(
                        keys=[self.device],
                        client=redis_client,
                    )
                )

                # if device setup is not complete, notify device and
                # close connection
                if "alias" not in list(device_data.keys()):
                    await self.send_json(
                        {
                            "event": CHAT_EVENT_TYPES.CHAT_CONNECT.value,
                            "status": False,
                            "message": "Device setup not complete",
                        }
                    )
                    await self.close(code=1000)
                    return

                # if device setup is complete, notify device and
                # keep connection
                await self.send_json(
                    {
                        "event": CHAT_EVENT_TYPES.CHAT_CONNECT.value,
                        "status": True,
                        "message": "Current device data",
                        "data": device_data,
                    }
                )

            else:  # close if uuid is not valis
                await self.close()

    async def receive(self, text_data=None, byte_data=None):
        try:
            to_alias: str = json.loads(text_data)["to"]
            message: str = json.loads(text_data)["message"]
        except (TypeError, JSONDecodeError):
            await self.send_json(
                {
                    "event": CHAT_EVENT_TYPES.CHAT_MESSAGE.value,
                    "status": False,
                    "message": "Message(s) must be in json format",
                }
            )
        except KeyError as e:
            await self.send_json(
                {
                    "event": CHAT_EVENT_TYPES.CHAT_MESSAGE.value,
                    "status": False,
                    "message": f"Missing key {str(e)}",
                }
            )
        else:
            try:
                await self.channel_layer.send(
                    redis_client.hget(
                        redis_client.hget(self.alias_device, to_alias),
                        "channel",
                    ),
                    {
                        "type": "chat.message",
                        "data": {
                            "event": CHAT_EVENT_TYPES.CHAT_MESSAGE.value,
                            "status": True,
                            "message": "Message",
                            "data": {
                                "from": redis_client.hget(self.device_alias, self.device),
                                "message": message,
                            },
                        },
                    },
                )
            except redis_exceptions.DataError:
                await self.send_json(
                    {
                        "event": CHAT_EVENT_TYPES.CHAT_MESSAGE.value,
                        "status": False,
                        "message": f"{to_alias} is offline or not available",
                    }
                )

    async def chat_message(self, event):
        await self.send_json(event["data"])

    async def disconnect(self, code):
        await self.channel_layer.group_discard("broadcast", self.channel_name)

        redis_client.hdel(
            self.alias_device,
            f"{redis_client.hget(self.device_alias, self.device)}",
        )
        # redis_client.hdel(self.device_alias, self.device)
        redis_client.delete(self.device)
