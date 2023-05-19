import json
from json.decoder import JSONDecodeError

from chat.events import DEVICE_EVENT_TYPES, SCAN_EVENT_TYPES
from chat.services.consumers import ConsumerServices
from src.utils import BaseAsyncJsonWebsocketConsumer, is_valid_uuid, redis_client


class ConnectConsumer(BaseAsyncJsonWebsocketConsumer):
    """
    Connect Consumer will:

    1. Accept connections, checks if to keep or discard connection.
    2. Receive data to set device alias.
    3. Then Disconnect, when successfully completed.
    """

    async def connect(self):
        """
        Accept all connections at first.

        But only keep connection if the value at index 0 in the request subprotocol
        is a valid uuid4. If not, notify device and close connection.

        Because we need the uuid4 to keep track of connected devices.
        """

        try:
            self.did = self.scope["subprotocols"][0]
            await self.accept(subprotocol=self.did)
        except IndexError:
            await self.accept()
            await self.send_json(
                {
                    "event": DEVICE_EVENT_TYPES.DEVICE_CONNECT.value,
                    "status": False,
                    "message": "A valid uuid should be at index 0 in subprotocols",
                }
            )
            await self.close()
        else:
            if is_valid_uuid(self.did):
                # set instance variables device & device_groups values
                self.device = f"device:{self.did}"
                self.device_groups = f"{self.device}:groups"

                ConsumerServices.set_device_data(
                    device=self.device,
                    did=self.did,
                    channel=self.channel_name,
                )

                # send device data back to client
                await self.send_json(
                    {
                        "event": DEVICE_EVENT_TYPES.DEVICE_CONNECT.value,
                        "status": True,
                        "message": "Current device data",
                        "data": ConsumerServices.get_device_data(self.device),
                    }
                )

            else:  # uuid is not valid
                await self.send_json(
                    {
                        "event": DEVICE_EVENT_TYPES.DEVICE_CONNECT.value,
                        "status": False,
                        "message": "A valid uuid should be at index 0 in subprotocols",
                    }
                )
                await self.close()

    async def receive(self, text_data=None):
        """Receive device alias and store in redis"""

        try:  # get device alias
            alias: str = json.loads(text_data)["alias"]
        except (TypeError, JSONDecodeError):
            await self.send_json(
                {
                    "event": DEVICE_EVENT_TYPES.DEVICE_SETUP.value,
                    "status": False,
                    "message": "Message(s) must be in json format",
                }
            )
        except KeyError as e:
            await self.send_json(
                {
                    "event": DEVICE_EVENT_TYPES.DEVICE_SETUP.value,
                    "status": False,
                    "message": f"Missing key {str(e)}",
                }
            )
        else:
            message, alias, status = ConsumerServices.format_and_verify_alias(
                device=self.device, alias=alias
            )

            if status:  # SUCCESS: save and notify client.
                ConsumerServices.set_device_alias(
                    device=self.device,
                    alias=alias,
                    device_alias=self.device_alias,
                    alias_device=self.alias_device,
                )

                await self.send_json(
                    {
                        "event": DEVICE_EVENT_TYPES.DEVICE_SETUP.value,
                        "status": status,
                        "message": message,
                        "data": ConsumerServices.get_device_data(self.device),
                    }
                )

            else:  # FAILURE: notify client
                await self.send_json(
                    {
                        "event": DEVICE_EVENT_TYPES.DEVICE_SETUP.value,
                        "status": status,
                        "message": message,
                        "data": {"alias": alias},
                    }
                )

    async def chat_message(self, event):
        await self.send_json(event["data"])

    async def disconnect(self, code):
        redis_client.hdel(f"{self.device}", "channel")
        redis_client.hdel(
            self.alias_device,
            f"{redis_client.hget(f'{self.device_alias}', f'{self.device}')}",
        )


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

        Also checks if a device with such uuid has a channel and and only keep
        connection if device alias is not set.
        """
        self.did = self.scope["url_route"]["kwargs"]["did"]
        self.device = f"device:{self.did}"
        self.device_groups = f"{self.device}:groups"

        await self.accept()

        if (
            redis_client.hget(self.device, key="channel")
            and redis_client.hget(self.device_alias, key=self.device) == None
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
        except KeyError as e:
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_SETUP.value,
                    "status": False,
                    "message": f"Missing value {str(e)}",
                }
            )
        except (TypeError, JSONDecodeError):
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_SETUP.value,
                    "status": False,
                    "message": "Message(s) must be in json format",
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
