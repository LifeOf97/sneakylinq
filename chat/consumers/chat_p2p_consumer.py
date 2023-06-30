import json
from json.decoder import JSONDecodeError

from redis import exceptions as redis_exceptions

from chat.events import CHAT_EVENT_TYPES
from chat.services.consumer_services import ConsumerServices
from src.utils import BaseAsyncJsonWebsocketConsumer, is_valid_uuid, redis_client


class P2PChatConsumer(BaseAsyncJsonWebsocketConsumer):
    """
    P2P Chat consumer will:

    1. Accept connections, checks device if to keep or discard connection.
    2. Receive data to send as chat messages.
    3. Then Disconnect, when explicitly requested.
    """

    async def connect(self):
        """
        Accept all connections at first.

        But only keep connection if the value at index 0 in the request subprotocol
        is a valid uuid and device setup is complete else close connection.
        """
        try:
            self.did = self.scope["subprotocols"][0]
            await self.accept(subprotocol=self.did)
        except IndexError:
            await self.accept()
            await self.send_json(
                {
                    "event": CHAT_EVENT_TYPES.CHAT_CONNECT.value,
                    "status": False,
                    "message": "A valid uuid should be at index 0 in subprotocols",
                }
            )
            await self.close()
        else:
            if is_valid_uuid(self.did):
                # set instance variables did, device & device_groups values
                self.device = f"device:{self.did}"
                self.device_groups = f"{self.device}:groups"

                # add device channel to broadcast group
                await self.channel_layer.group_add("broadcast", self.channel_name)

                ConsumerServices.set_device_data(
                    device=self.device,
                    did=self.did,
                    channel=self.channel_name,
                )

                # get device data
                device_data: dict = ConsumerServices.get_device_data(device=self.device)

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

                else:
                    await self.send_json(
                        {
                            "event": CHAT_EVENT_TYPES.CHAT_CONNECT.value,
                            "status": True,
                            "message": "Current device data",
                            "data": device_data,
                        }
                    )

            else:  # close if uuid is not valid
                await self.send_json(
                    {
                        "event": CHAT_EVENT_TYPES.CHAT_CONNECT.value,
                        "status": False,
                        "message": "A valid uuid should be at index 0 in subprotocols",
                    }
                )
                await self.close()

    async def receive(self, text_data=None):
        """Receive chat messages and send to reciepient"""
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
                # send chat to receipient
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
                            "message": "received",
                            "data": {
                                "alias": redis_client.hget(self.device_alias, self.device),
                                "did": redis_client.hget(self.device, "did"),
                                "message": message,
                            },
                        },
                    },
                )

                # send chat to sender
                await self.send_json(
                    {
                        "event": CHAT_EVENT_TYPES.CHAT_MESSAGE.value,
                        "status": True,
                        "message": "send",
                        "data": {
                            "alias": to_alias,
                            "did": redis_client.hget(
                                redis_client.hget(self.alias_device, to_alias), "did"
                            ),
                            "message": message,
                        },
                    }
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
        """
        Discard device channel from broadcast group. And delete/reset device
        data in redis store.

        Notice we provide values in redis_client in f-string format, this is
        because redis sometimes raises a ValueError when values are passed as-is.
        """
        await self.channel_layer.group_discard("broadcast", self.channel_name)

        redis_client.hdel(f"{self.device}", "channel")
        redis_client.hdel(
            f"{self.alias_device}",
            f"{redis_client.hget(f'{self.device_alias}', f'{self.device}')}",
        )
