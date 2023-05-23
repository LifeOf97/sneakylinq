import pytest
from pytest import MonkeyPatch

from chat.lua_scripts import LuaScripts
from src.utils import redis_client
from tests.mocks import MockLuaScript, MockRedisClient


@pytest.fixture
def mock_redis_hset(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(redis_client, "hset", MockRedisClient.hset)


@pytest.fixture
def mock_redis_hget(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(redis_client, "hget", MockRedisClient.hget)


@pytest.fixture
def mock_redis_hvals(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(redis_client, "hvals", MockRedisClient.hvals)


@pytest.fixture
def mock_redis_expireat(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(redis_client, "expireat", MockRedisClient.expireat)


@pytest.fixture
def mock_luascript_set_alias_device(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(LuaScripts, "set_alias_device", MockLuaScript.set_alias_device)


@pytest.fixture
def mock_luascript_get_device_data(monkeypatch: MonkeyPatch):
    monkeypatch.setattr(LuaScripts, "get_device_data", MockLuaScript.get_device_data)
