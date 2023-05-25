import json
from json.decoder import JSONDecodeError

from chat.events import SCAN_EVENT_TYPES
from chat.services.consumer_services import ConsumerServices
from src.utils import BaseAsyncJsonWebsocketConsumer, redis_client


class ScanConnectConsumer(BaseAsyncJsonWebsocketConsumer):
    """
    Implements a scan to connect feature via QR Code scanning. It

    1. Accept connections.
    2. Receive data to set device alias.
    3. Then Disconnect, when successfully completed.
    """

    async def connect(self):
        """
        Since the path() function in the routers url file automatically confirms
        if a valid uuid was provided as the required url kwarg 'did'. We can
        be rest assured that 'self.did' is assigned a valid uuid.

        Also checks if a device with such uuid has a channel and only keep
        connection if device alias is not set.
        """
        self.did = self.scope["url_route"]["kwargs"]["did"]
        self.device = f"device:{self.did}"
        self.device_groups = f"{self.device}:groups"

        await self.accept()

        if (
            redis_client.hget(self.device, key="channel")
            and redis_client.hget(self.device_alias, key=self.device) is None
        ):
            # SUCCESS: notify the client of the scanned device details
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_CONNECT.value,
                    "status": True,
                    "message": "Scanned succeccfully",
                    "data": ConsumerServices.get_device_data(device=self.device),
                }
            )

            # SUCCESS: notify the scanned device.
            await self.channel_layer.send(
                redis_client.hget(self.device, key="channel"),
                {
                    "type": "chat.message",
                    "data": {
                        "event": SCAN_EVENT_TYPES.SCAN_CONNECT.value,
                        "status": True,
                        "message": "Scanned successfully",
                    },
                },
            )

        else:  # device with channel already has an alias or channel not present
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_CONNECT.value,
                    "status": False,
                    "message": "Invalid channel or device already setup",
                }
            )
            await self.close()

    async def receive(self, text_data=None, byte_data=None):
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
        except KeyError as e:
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_SETUP.value,
                    "status": False,
                    "message": f"Missing key {str(e)}",
                }
            )
        else:
            message, alias, status = ConsumerServices.format_and_verify_alias(
                device=self.device, alias=alias
            )

            if status:  # SUCCESS: save and notify the scanned device.
                ConsumerServices.set_device_alias(
                    device=self.device,
                    alias=alias,
                    device_alias=self.device_alias,
                    alias_device=self.alias_device,
                )

                await self.channel_layer.send(
                    redis_client.hget(self.device, key="channel"),
                    {
                        "type": "chat.message",
                        "data": {
                            "event": SCAN_EVENT_TYPES.SCAN_SETUP.value,
                            "status": status,
                            "message": message,
                            "data": ConsumerServices.get_device_data(device=self.device),
                        },
                    },
                )

            # SUCCESS | FAILURE: notify scanning device
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_SETUP.value,
                    "status": status,
                    "message": message,
                    "data": {"alias": alias},
                }
            )

            if status:  # gracefully disconnect the scanning device
                await self.close(code=1000)

    async def chat_message(self, event):
        await self.send_json(event["data"])
