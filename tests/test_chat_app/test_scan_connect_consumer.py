import json
import uuid

import pytest
from channels.routing import URLRouter
from channels.testing import WebsocketCommunicator
from django.urls import path
from django.utils.text import slugify

from chat.consumers.scan_consumer import ScanConnectConsumer
from chat.events import SCAN_EVENT_TYPES
from tests.mocks import MockRedisClient

pytestmark = pytest.mark.asyncio


class TestScanConsumerConnect:
    async def test_drop_connection_if_scanned_device_has_no_channel(
        self,
        mock_redis_hget,
        mock_redis_hdel,
    ):
        did: uuid.UUID = uuid.uuid4()

        # Set device data in mock redis store
        MockRedisClient.redis_store[f"device:{did}"] = {
            "channel": None,
        }

        application = URLRouter(
            [path("test/ws/scan/connect/<uuid:did>/", ScanConnectConsumer.as_asgi())]
        )

        communicator = WebsocketCommunicator(
            application=application,
            path=f"/test/ws/scan/connect/{did}/",
        )

        connected, _ = await communicator.connect()
        received = await communicator.receive_json_from()

        assert connected
        assert received["event"] == SCAN_EVENT_TYPES.SCAN_CONNECT.value
        assert received["status"] is False
        assert received["message"] == "Invalid channel or device already setup"

        await communicator.disconnect()

    async def test_drop_connection_if_scanned_device_has_channel_and_alias(
        self,
        mock_redis_hget,
        mock_redis_hdel,
    ):
        did: uuid.UUID = uuid.uuid4()

        # Set device data in mock redis store
        MockRedisClient.redis_store[f"device:{did}"] = {
            "channel": "specific.c908693bb",
        }
        MockRedisClient.redis_store["device:alias"] = {
            f"device:{did}": "testalias_001",
        }

        application = URLRouter(
            [path("test/ws/scan/connect/<uuid:did>/", ScanConnectConsumer.as_asgi())]
        )

        communicator = WebsocketCommunicator(
            application=application,
            path=f"/test/ws/scan/connect/{did}/",
        )

        connected, _ = await communicator.connect()
        received = await communicator.receive_json_from()

        assert connected
        assert received["event"] == SCAN_EVENT_TYPES.SCAN_CONNECT.value
        assert received["status"] is False
        assert received["message"] == "Invalid channel or device already setup"

        await communicator.disconnect()

    async def test_keep_connection_if_scanned_device_has_channel_but_no_alias(
        self,
        mock_redis_hget,
        mock_redis_hdel,
        mock_luascript_get_device_data,
    ):
        did: uuid.UUID = uuid.uuid4()

        # Set device data in mock redis store
        MockRedisClient.redis_store[f"device:{did}"] = {
            "channel": "specific.c908693bb",
        }
        MockRedisClient.redis_store["device:alias"] = {
            f"device:{did}": None,
        }

        application = URLRouter(
            [path("test/ws/scan/connect/<uuid:did>/", ScanConnectConsumer.as_asgi())]
        )

        communicator = WebsocketCommunicator(
            application=application,
            path=f"/test/ws/scan/connect/{did}/",
        )

        connected, _ = await communicator.connect()
        received = await communicator.receive_json_from()

        assert connected
        assert received["event"] == SCAN_EVENT_TYPES.SCAN_CONNECT.value
        assert received["status"] is True
        assert received["message"] == "Scanned succeccfully"

        assert "did" in received["data"]
        assert "channel" in received["data"]
        assert "alias" in received["data"]
        assert "ttl" in received["data"]

        await communicator.disconnect()


class TestScanConsumerReceive:
    async def test_received_messages_must_be_in_json_format(
        self,
        mock_redis_hget,
        mock_redis_hset,
        mock_redis_hdel,
        mock_redis_expireat,
        mock_luascript_set_alias_device,
        mock_luascript_get_device_data,
    ):
        did: uuid.UUID = uuid.uuid4()

        # Set device data in mock redis store
        MockRedisClient.redis_store[f"device:{did}"] = {
            "channel": "specific.c908693bb",
        }
        MockRedisClient.redis_store["device:alias"] = {
            f"device:{did}": None,
        }

        application = URLRouter(
            [path("test/ws/scan/connect/<uuid:did>/", ScanConnectConsumer.as_asgi())]
        )

        communicator = WebsocketCommunicator(
            application=application,
            path=f"/test/ws/scan/connect/{did}/",
        )

        connected, _ = await communicator.connect()

        connected_response = await communicator.receive_json_from()
        set_alias_message = await communicator.send_to(text_data="testuser_001")
        set_alias_response = await communicator.receive_json_from()

        assert connected
        assert set_alias_response["event"] == SCAN_EVENT_TYPES.SCAN_SETUP.value
        assert set_alias_response["status"] is False
        assert set_alias_response["message"] == "Message(s) must be in json format"

        await communicator.disconnect()

    async def test_received_messages_must_have_key_alias_in_received_json_data(
        self,
        mock_redis_hget,
        mock_redis_hset,
        mock_redis_hdel,
        mock_redis_expireat,
        mock_luascript_set_alias_device,
        mock_luascript_get_device_data,
    ):
        did: uuid.UUID = uuid.uuid4()

        # Set device data in mock redis store
        MockRedisClient.redis_store[f"device:{did}"] = {
            "channel": "specific.c908693bb",
        }
        MockRedisClient.redis_store["device:alias"] = {
            f"device:{did}": None,
        }

        application = URLRouter(
            [path("test/ws/scan/connect/<uuid:did>/", ScanConnectConsumer.as_asgi())]
        )

        communicator = WebsocketCommunicator(
            application=application,
            path=f"/test/ws/scan/connect/{did}/",
        )

        connected, _ = await communicator.connect()

        connected_response = await communicator.receive_json_from()
        set_alias_message = await communicator.send_to(text_data='{"name": "testuser_001"}')
        set_alias_response = await communicator.receive_json_from()

        assert connected
        assert set_alias_response["event"] == SCAN_EVENT_TYPES.SCAN_SETUP.value
        assert set_alias_response["status"] is False
        assert set_alias_response["message"] == "Missing key 'alias'"

        await communicator.disconnect()

    @pytest.mark.parametrize(
        "test_alias, test_message, test_status",
        [
            ("12345", "Alias must be a mix of alphanumeric characters", False),
            ("tes", "Alias must be between 4 to 15 characters long", False),
            ("linq", "linq is not allowed", False),
        ],
    )
    async def test_received_alias_failed_format_and_verify_alias(
        self,
        test_alias,
        test_message,
        test_status,
        mock_redis_hget,
        mock_redis_hset,
        mock_redis_hdel,
        mock_redis_expireat,
        mock_luascript_set_alias_device,
        mock_luascript_get_device_data,
    ):
        did: uuid.UUID = uuid.uuid4()

        # Set device data in mock redis store
        MockRedisClient.redis_store[f"device:{did}"] = {
            "channel": "specific.c908693bb",
        }
        MockRedisClient.redis_store["device:alias"] = {
            f"device:{did}": None,
        }

        application = URLRouter(
            [path("test/ws/scan/connect/<uuid:did>/", ScanConnectConsumer.as_asgi())]
        )

        communicator = WebsocketCommunicator(
            application=application,
            path=f"/test/ws/scan/connect/{did}/",
        )

        connected, _ = await communicator.connect()

        connected_response = await communicator.receive_json_from()
        set_alias_message = await communicator.send_to(text_data=json.dumps({"alias": test_alias}))
        set_alias_response = await communicator.receive_json_from()

        assert connected
        assert set_alias_response["event"] == SCAN_EVENT_TYPES.SCAN_SETUP.value
        assert set_alias_response["status"] is test_status
        assert set_alias_response["message"] == test_message
        assert set_alias_response["data"]["alias"] == test_alias

        await communicator.disconnect()

    @pytest.mark.parametrize(
        "test_alias, test_message, test_status",
        [
            ("test_alias_001", "Alias accepted", True),
            ("kelly_pc_HOME", "Alias accepted", True),
            ("Luke.Shaw", "Alias accepted", True),
        ],
    )
    async def test_received_alias_passed_format_and_verify_alias_but_raises_typeerror(
        self,
        test_alias,
        test_message,
        test_status,
        mock_redis_hset,
        mock_redis_hget,
        mock_redis_hdel,
        mock_redis_hvals,
        mock_redis_expireat,
        mock_luascript_set_alias_device,
        mock_luascript_get_device_data,
    ):
        """
        Because channelnames are dynamically assigned on connect, we check that a
        TypeError is raised when it get to the self.channel_layer.send() method
        which requires the channel name to send a message to.
        """
        did: uuid.UUID = uuid.uuid4()

        # Set device data in mock redis store
        MockRedisClient.redis_store[f"device:{did}"] = {
            "channel": "specific.c908693bb04d4a1cb62b86577532ddec!",
        }
        MockRedisClient.redis_store["device:alias"] = {
            f"device:{did}": None,
        }

        application = URLRouter(
            [path("test/ws/scan/connect/<uuid:did>/", ScanConnectConsumer.as_asgi())]
        )

        communicator = WebsocketCommunicator(
            application=application,
            path=f"/test/ws/scan/connect/{did}/",
        )

        test_alias: str = slugify(str(test_alias).lower()).replace("-", "_")

        connected, _ = await communicator.connect()

        connected_response = await communicator.receive_json_from()

        with pytest.raises(TypeError):
            set_alias_message = await communicator.send_to(
                text_data=json.dumps({"alias": test_alias})
            )
            set_alias_response = await communicator.receive_json_from()

            await communicator.disconnect()
