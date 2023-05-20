import pytest

from chat.services.consumer_services import ConsumerServices


def test_set_alias_device(mock_luascript_set_alias_device):
    assert ConsumerServices.set_alias_device("device:123") == 1
