import pytest
from pytest import MonkeyPatch

from chat.lua_scripts import LuaScripts
from src.utils import redis_client
from tests.mocks import MockLuaScript, MockRedisClient


@pytest.fixture
def mock_redis_hset(monkeypatch: MonkeyPatch, name: str, mapping: dict):
    monkeypatch.setattr(
        redis_client,
        "hset",
        MockRedisClient.hset(name=name, mapping=mapping),
    )


@pytest.fixture
def mock_luascript_set_alias_device(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(
        LuaScripts,
        "set_alias_device",
        MockLuaScript.set_alias_device,
    )
