from datetime import datetime


class MockRedisClient:
    redis_store: dict = {
        "device_alias": {},
        "alias_device": {},
    }

    @staticmethod
    def hset(name: str, mapping: dict) -> int:
        if type(mapping) is dict:
            MockRedisClient.redis_store[name] = mapping
            return 1
        return 0

    @staticmethod
    def hget(name: str, key: str) -> str | None:
        try:
            return MockRedisClient.redis_store[name][key]
        except KeyError:
            return None

    @staticmethod
    def expireat(name: str, ttl: datetime) -> None:
        MockRedisClient.redis_store[name]["expireat"] = ttl


class MockLuaScript:
    @staticmethod
    def set_alias_device(keys: str, client=None) -> int:
        """
        Here redis method to execute a lua script gets it's keys as list
        so we need to index the values we need, when calling certain redis
        methods.
        """
        device = MockRedisClient.hget(name="device_alias", key=keys[0]) or keys[0]

        return MockRedisClient.hset(name="alias_device", mapping={"tester": device})
