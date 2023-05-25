import json
import uuid

import pytest
from channels.testing import WebsocketCommunicator
from django.utils.text import slugify

from chat.consumers.connect_consumer import ConnectConsumer
from chat.events import DEVICE_EVENT_TYPES

pytestmark = pytest.mark.asyncio


class TestConnectConsumerConnect:
    async def test_connection_accepted_but_no_uuid_present_at_index_0_in_subprotocols(
        self,
        mock_redis_hget,
        mock_redis_hdel,
    ):
        """
        Connection is accepted but will later be closed if no uuid is present
        at index 0 in subprotocols. And a data is sent before the connection is closed.
        """
        communicator = WebsocketCommunicator(
            application=ConnectConsumer(),
            path="/test/ws/connect/",
        )

        connected, subprotocols = await communicator.connect()
        response = await communicator.receive_json_from()

        assert connected
        assert not subprotocols
        assert type(response) is dict
        assert response["event"] == DEVICE_EVENT_TYPES.DEVICE_CONNECT.value
        assert response["status"] is False
        assert response["message"] == "A valid uuid should be at index 0 in subprotocols"

        await communicator.disconnect()

    async def test_connection_accepted_but_value_at_index_0_in_subprotocols_not_valid_uuid(
        self,
        mock_redis_hget,
        mock_redis_hdel,
    ):
        """
        Connection is accepted but will later be closed if provided uuid is invalid
        at index 0 in subprotocols. And a data is sent before the connection is closed.
        """
        communicator = WebsocketCommunicator(
            application=ConnectConsumer(),
            path="/test/ws/connect/",
            subprotocols=["not-a-valid-uuid"],
        )

        connected, subprotocols = await communicator.connect()
        response = await communicator.receive_json_from()

        assert connected
        assert subprotocols
        assert type(response) is dict
        assert response["event"] == DEVICE_EVENT_TYPES.DEVICE_CONNECT.value
        assert response["status"] is False
        assert response["message"] == "A valid uuid should be at index 0 in subprotocols"

        await communicator.disconnect()

    async def test_connection_accepted_with_valid_uuid_at_index_0_in_subprotocols(
        self,
        mock_redis_hset,
        mock_redis_hget,
        mock_redis_hdel,
        mock_redis_expireat,
        mock_luascript_set_alias_device,
        mock_luascript_get_device_data,
    ):
        """
        Connection is accepted and kept alive provided uuid is at at index 0 in
        subprotocols and is valid. device data is set in redis store and sent back
        over the network.
        """
        communicator = WebsocketCommunicator(
            application=ConnectConsumer(),
            path="/test/ws/connect/",
            subprotocols=[uuid.uuid4()],
        )

        connected, subprotocols = await communicator.connect()
        response = await communicator.receive_json_from()

        assert connected
        assert type(response) is dict
        assert response["event"] == DEVICE_EVENT_TYPES.DEVICE_CONNECT.value
        assert response["status"] is True
        assert response["message"] == "Current device data"

        assert type(response["data"]) is dict
        assert "did" in response["data"].keys()
        assert "channel" in response["data"].keys()
        assert "ttl" in response["data"].keys()
        assert "alias" in response["data"].keys()

        await communicator.disconnect()


class TestConnectConsumerReceive:
    async def test_received_messages_must_be_in_json_format(
        self,
        mock_redis_hget,
        mock_redis_hset,
        mock_redis_hdel,
        mock_redis_expireat,
        mock_luascript_set_alias_device,
        mock_luascript_get_device_data,
    ):
        communicator = WebsocketCommunicator(
            application=ConnectConsumer(),
            path="/test/ws/connect/",
            subprotocols=[uuid.uuid4()],
        )

        connected, subprotocols = await communicator.connect()

        connected_response = await communicator.receive_json_from()
        set_alias_message = await communicator.send_to(text_data="testuser_001")
        set_alias_response = await communicator.receive_json_from()

        assert connected
        assert set_alias_response["event"] == DEVICE_EVENT_TYPES.DEVICE_SETUP.value
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
        communicator = WebsocketCommunicator(
            application=ConnectConsumer(),
            path="/test/ws/connect/",
            subprotocols=[uuid.uuid4()],
        )

        connected, subprotocols = await communicator.connect()

        connected_response = await communicator.receive_json_from()
        set_alias_message = await communicator.send_to(text_data='{"name": "testuser_001"}')
        set_alias_response = await communicator.receive_json_from()

        assert connected
        assert set_alias_response["event"] == DEVICE_EVENT_TYPES.DEVICE_SETUP.value
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
        communicator = WebsocketCommunicator(
            application=ConnectConsumer(),
            path="/test/ws/connect/",
            subprotocols=[uuid.uuid4()],
        )

        connected, subprotocols = await communicator.connect()

        connected_response = await communicator.receive_json_from()
        set_alias_message = await communicator.send_to(text_data=json.dumps({"alias": test_alias}))
        set_alias_response = await communicator.receive_json_from()

        assert connected
        assert set_alias_response["event"] == DEVICE_EVENT_TYPES.DEVICE_SETUP.value
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
    async def test_received_alias_passed_format_and_verify_alias(
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
        communicator = WebsocketCommunicator(
            application=ConnectConsumer(),
            path="/test/ws/connect/",
            subprotocols=[uuid.uuid4()],
        )

        test_alias: str = slugify(str(test_alias).lower()).replace("-", "_")

        connected, subprotocols = await communicator.connect()

        connected_response = await communicator.receive_json_from()
        set_alias_message = await communicator.send_to(text_data=json.dumps({"alias": test_alias}))
        set_alias_response = await communicator.receive_json_from()

        assert connected
        assert set_alias_response["event"] == DEVICE_EVENT_TYPES.DEVICE_SETUP.value
        assert set_alias_response["status"] is test_status
        assert set_alias_response["message"] == test_message
        assert "did" in set_alias_response["data"].keys()
        assert "channel" in set_alias_response["data"].keys()
        assert "ttl" in set_alias_response["data"].keys()
        assert "alias" in set_alias_response["data"].keys()

        await communicator.disconnect()
