import json
import uuid
from json.decoder import JSONDecodeError

from django.utils import timezone

from chat.events import DEVICE_EVENT_TYPES, SCAN_EVENT_TYPES
from chat.lua_scripts import LuaScripts
from src.helpers import format_alias, is_valid_alias
from src.utils import (
    BaseAsyncJsonWebsocketConsumer,
    convert_array_to_dict,
    is_valid_uuid,
    redis_client,
)


class ConnectConsumer(BaseAsyncJsonWebsocketConsumer):
    """Connect client to websocket server and carry out setup"""

    async def connect(self):
        headers: dict = dict(self.scope["headers"])

        try:  # get device did
            self.did = headers[b"did"].decode()
        except KeyError:
            await self.close()
        else:
            if is_valid_uuid(self.did):
                # set instance variables device & device_groups values
                self.device = f"device:{self.did}"
                self.device_groups = f"{self.device}:groups"

                # accept connection
                await self.accept()

                # connection time-to-live date object
                ttl = timezone.now() + timezone.timedelta(hours=2)

                # store data as hash type in redis store, also set an expire
                # option to the device data in redis store using
                # the ttl as the value.
                redis_client.hset(
                    name=self.device,
                    mapping={
                        "did": f"{self.did}",
                        "channel": f"{self.channel_name}",
                        "ttl": ttl.timestamp(),
                    },
                )
                redis_client.expireat(self.device, ttl)

                # send device data back to client
                await self.send_json(
                    {
                        "event": DEVICE_EVENT_TYPES.DEVICE_CONNECT.value,
                        "status": True,
                        "message": "Current device data",
                        "data": convert_array_to_dict(
                            LuaScripts.get_device_data(
                                keys=[self.device],
                                client=redis_client,
                            )
                        ),
                    }
                )

                # call lua script
                LuaScripts.set_alias_device(keys=[self.device], client=redis_client)

            else: # uuid is not valid
                await self.close()

    async def receive_json(self, content, **kwargs):
        """Receive device alias and store in redis"""

        try: # get device alias
            alias: str = content["alias"]
        except (TypeError, JSONDecodeError):
            await self.send_json(
                {
                    "event": DEVICE_EVENT_TYPES.DEVICE_SETUP.value,
                    "status": False,
                    "message": "Message(s) must be in json format",
                }
            )
        except KeyError:
            await self.send_json(
                {
                    "event": DEVICE_EVENT_TYPES.DEVICE_SETUP.value,
                    "status": False,
                    "message": "Please provide your alias",
                }
            )
        else:
            alias_msg, alias_name, alias_status = is_valid_alias(alias=alias)

            if alias_status:
                alias_msg, alias_name, alias_status = format_alias(
                    device=self.device, alias=alias_name
                )

                if alias_status:
                    # add the device alias to device:alias & alias:device hash
                    # in redis store
                    redis_client.hset(
                        self.device_alias, key=self.device, value=alias_name
                    )
                    redis_client.hset(
                        self.alias_device, key=alias_name, value=self.device
                    )

                    # connection time-to-live date object
                    ttl = timezone.now() + timezone.timedelta(hours=2)

                    # in redis store, update device data ttl value. And also set an expire
                    # option to the device data in redis store using the ttl as the value.
                    redis_client.hset(self.device, key="ttl", value=ttl.timestamp())
                    redis_client.expireat(self.device, ttl)

                    # SUCCESS: notify client.
                    await self.send_json(
                        {
                            "event": DEVICE_EVENT_TYPES.DEVICE_SETUP.value,
                            "status": True,
                            "message": alias_msg,
                            "data": convert_array_to_dict(
                                LuaScripts.get_device_data(
                                    keys=[self.device], client=redis_client
                                )
                            ),
                        }
                    )

                    return

            # FAILURE: notify client
            await self.send_json(
                {
                    "event": DEVICE_EVENT_TYPES.DEVICE_SETUP.value,
                    "status": alias_status,
                    "message": alias_msg,
                    "data": {"alias": alias_name},
                }
            )

    async def chat_message(self, event):
        await self.send_json(event["data"])

    async def disconnect(self, code):
        redis_client.hdel(self.device, "channel")
        redis_client.hdel(
            self.alias_device,
            redis_client.hget(self.device_alias, self.device),
        )


class ScanConnectConsumer(BaseAsyncJsonWebsocketConsumer):
    """
    Implements a scan to connect feature via QR Code scanning
    and carries out device setup.
    """

    async def connect(self):
        self.did = self.scope["url_route"]["kwargs"]["did"]
        self.device = f"device:{self.did}"
        self.device_groups = f"{self.device}:groups"

        await self.accept()

        if (
            redis_client.hget(self.device, key="channel")
            and redis_client.hget(self.device_alias, key=self.device) == None
        ):
            # notify the client of the scanned device details
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_CONNECT.value,
                    "status": True,
                    "message": "Scanned device data",
                    "data": convert_array_to_dict(
                        LuaScripts.get_device_data(
                            keys=[self.device],
                            client=redis_client,
                        )
                    ),
                }
            )

            # also notify device with the qr code.
            await self.channel_layer.send(
                redis_client.hget(self.device, key="channel"),
                {
                    "type": "chat.message",
                    "data": {
                        "event": SCAN_EVENT_TYPES.SCAN_CONNECT.value,
                        "status": True,
                        "message": "QR code scanned successfully",
                    },
                },
            )

        else: 
            # if device with channel already has an alias or channel not present
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_CONNECT.value,
                    "status": False,
                    "message": "Invalid channel or device already setup",
                }
            )
            await self.close()

    async def receive_json(self, content=None):
        """Receive device alias and store in redis"""

        try:
            alias: str = content["alias"]
        except (TypeError, JSONDecodeError):
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_SETUP.value,
                    "status": False,
                    "message": "Message(s) must be in json format",
                }
            )
        except KeyError:
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_SETUP.value,
                    "status": False,
                    "message": "Please provide your alias",
                }
            )
        else:
            alias_msg, alias_name, alias_status = is_valid_alias(alias=alias)

            if alias_status:
                alias_msg, alias_name, alias_status = format_alias(
                    device=self.device, alias=alias_name
                )

                if alias_status:
                    # add the device alias to device:alias & alias:device hash
                    # in redis store
                    redis_client.hset(
                        self.device_alias, key=self.device, value=alias_name
                    )
                    redis_client.hset(
                        self.alias_device, key=alias_name, value=self.device
                    )

                    # connection time-to-live date object
                    ttl = timezone.now() + timezone.timedelta(hours=2)

                    # in redis store, update device data ttl value. And also set an expire
                    # option to the device data in redis store using the ttl as the value.
                    redis_client.hset(self.device, key="ttl", value=ttl.timestamp())
                    redis_client.expireat(self.device, ttl)

                    # SUCCESS: notify device with the qr code.
                    await self.channel_layer.send(
                        redis_client.hget(self.device, key="channel"),
                        {
                            "type": "chat.message",
                            "data": {
                                "event": SCAN_EVENT_TYPES.SCAN_SETUP.value,
                                "status": True,
                                "message": alias_msg,
                                "data": convert_array_to_dict(
                                    LuaScripts.get_device_data(
                                        keys=[self.device],
                                        client=redis_client,
                                    )
                                ),
                            },
                        },
                    )

            # SUCCESS | FAILURE: notify the client only
            await self.send_json(
                {
                    "event": SCAN_EVENT_TYPES.SCAN_SETUP.value,
                    "status": alias_status,
                    "message": alias_msg,
                    "data": {"alias": alias_name},
                }
            )

            if alias_status:  # gracefully disconnect the scanning device
                await self.close(code=1000)

    async def chat_message(self, event):
        await self.send_json(event["data"])
