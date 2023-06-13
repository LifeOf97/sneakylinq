import uuid
from datetime import datetime, timedelta


class MockRedisClient:
    redis_store: dict = {
        "device:001": {
            "did": str(uuid.uuid4()),
            "channel": "channel_name",
            "alias": "testalias_001",
            "ttl": (datetime.now() + timedelta(hours=2)).timestamp(),
        },
        "device:alias": {
            "device:001": "testalias_001.linq",
            "device:002": "testalias_002.linq",
            "device:003": "testalias_003.linq",
        },
        "alias:device": {
            "testalias_001.linq": "device:001",
            "testalias_002.linq": "device:001",
            "testalias_003.linq": "device:001",
        },
    }

    @staticmethod
    def reset() -> None:
        MockRedisClient.redis_store = {
            "device:001": {
                "did": str(uuid.uuid4()),
                "channel": "specific_uniqu_str_by_channels",
                "alias": "testalias_001",
                "ttl": (datetime.now() + timedelta(hours=2)).timestamp(),
            },
            "device:alias": {
                "device:001": "testalias_001.linq",
                "device:002": "testalias_002.linq",
                "device:003": "testalias_003.linq",
            },
            "alias:device": {
                "testalias_001.linq": "device:001",
                "testalias_002.linq": "device:001",
                "testalias_003.linq": "device:001",
            },
        }

    @staticmethod
    def hset(name: str, mapping: dict) -> int:
        if type(mapping) is dict:
            if name in MockRedisClient.redis_store.keys():
                MockRedisClient.redis_store[name].update(mapping)
            else:
                MockRedisClient.redis_store[name] = mapping
            return 1
        return 0

    @staticmethod
    def hget(name: str, key: str | None = None) -> dict | str | None:
        try:
            if key:
                return MockRedisClient.redis_store[name][key]
            else:
                return MockRedisClient.redis_store[name]
        except KeyError:
            return None

    @staticmethod
    def hvals(name: str) -> list | None:
        try:
            return MockRedisClient.redis_store[name].values()
        except KeyError:
            return None

    @staticmethod
    def hdel(name: str, key: str) -> int:
        try:
            MockRedisClient.redis_store[name][key] = None
            return 1
        except KeyError:
            return 0

    @staticmethod
    def delete(name: str) -> int:
        try:
            MockRedisClient.redis_store[name] = None
            return 1
        except KeyError:
            return 0

    @staticmethod
    def expireat(name: str, ttl: datetime) -> None:
        MockRedisClient.redis_store[name]["expireat"] = str(ttl)


class MockLuaScript:
    """
    Here, redis methods to execute a lua script gets it's keys as list
    so we need to index the values we need, when calling certain redis
    methods.
    """

    @staticmethod
    def set_alias_device(keys: list, client=None) -> int:
        device = MockRedisClient.hget(name="device:alias", key=keys[0]) or keys[0]

        return MockRedisClient.hset(name="alias:device", mapping={"testalias": device})

    @staticmethod
    def get_device_data(keys: list, client=None) -> dict:
        return MockRedisClient.hget(name=keys[0])
