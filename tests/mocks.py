class MockRedisClient:
    @staticmethod
    def hset(name: str, mapping: dict) -> int:
        name = name
        name = mapping

        if name and type(mapping) is dict:
            return 1
        return 0


class MockLuaScript:
    @staticmethod
    def set_alias_device(keys: str, client=None) -> int:
        return MockRedisClient.hset(name="alias_device", mapping={"alias": keys})
