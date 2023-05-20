import pytest
from channels.testing import WebsocketCommunicator

from chat.consumers.connect_consumer import ConnectConsumer


class TestConnectConsumer:
    # @pytest.mark.asyncio
    def test_cannot_connect_if_no_valid_uuid4_present(self):
        # communicator = WebsocketCommunicator()
        assert True
