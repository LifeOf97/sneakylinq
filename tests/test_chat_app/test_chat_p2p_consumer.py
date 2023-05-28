import uuid

import pytest
from channels.testing import WebsocketCommunicator

from chat.consumers.chat_p2p_consumer import P2PChatConsumer
from chat.events import CHAT_EVENT_TYPES
from tests.mocks import MockRedisClient

pytestmark = pytest.mark.asyncio


class TestConsumerConnect:
    async def test_connection_accepted_but_no_uuid_present_at_index_0_in_subprotocols(
        self,
        mock_redis_hget,
        mock_redis_hdel,
        mock_redis_delete,
    ):
        """
        Connection is accepted but will later be closed if no uuid is present
        at index 0 in subprotocols. And a data is sent before the connection is closed.
        """
        communicator = WebsocketCommunicator(
            application=P2PChatConsumer(),
            path="/test/ws/chat/p2p/",
        )

        connected, subprotocols = await communicator.connect()
        response = await communicator.receive_json_from()

        assert connected
        assert not subprotocols
        assert type(response) is dict
        assert response["event"] == CHAT_EVENT_TYPES.CHAT_CONNECT.value
        assert response["status"] is False
        assert response["message"] == "A valid uuid should be at index 0 in subprotocols"

        await communicator.disconnect()

    async def test_connection_accepted_but_value_at_index_0_in_subprotocols_not_valid_uuid(
        self,
        mock_redis_hget,
        mock_redis_hdel,
        mock_redis_delete,
    ):
        """
        Connection is accepted but will later be closed if provided uuid is invalid
        at index 0 in subprotocols. And a data is sent before the connection is closed.
        """
        communicator = WebsocketCommunicator(
            application=P2PChatConsumer(),
            path="/test/ws/chat/p2p/",
            subprotocols=["not-a-valid-uuid"],
        )

        connected, subprotocols = await communicator.connect()
        response = await communicator.receive_json_from()

        assert connected
        assert subprotocols
        assert type(response) is dict
        assert response["event"] == CHAT_EVENT_TYPES.CHAT_CONNECT.value
        assert response["status"] is False
        assert response["message"] == "A valid uuid should be at index 0 in subprotocols"

        await communicator.disconnect()

    async def test_connection_accepted_with_valid_uuid_and_device_setup_not_complete(
        self,
        mock_redis_hset,
        mock_redis_hget,
        mock_redis_hdel,
        mock_redis_delete,
        mock_redis_expireat,
        mock_luascript_set_alias_device,
        mock_luascript_get_device_data,
    ):
        did: uuid.UUID = uuid.uuid4()

        communicator = WebsocketCommunicator(
            application=P2PChatConsumer(),
            path="/test/ws/chat/p2p/",
            subprotocols=[did],
        )

        connected, _ = await communicator.connect()
        response = await communicator.receive_json_from()

        assert connected
        assert response["event"] == CHAT_EVENT_TYPES.CHAT_CONNECT.value
        assert response["status"] is False
        assert response["message"] == "Device setup not complete"

        await communicator.disconnect()
