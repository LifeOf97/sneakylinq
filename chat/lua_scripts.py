"""
Lua scripts used for redis programmability
"""
from src.utils import redis_client


class LuaScripts:
    """
    Lua scripts
    """


    _get_device_data = """
    redis.setresp(3)

    local device = KEYS[1]
    local device_data = redis.call('HGETALL', device)
    local device_alias = redis.call('HGET', 'device:aliases', device)
    local device_groups = redis.call('SMEMBERS', device .. ':groups')

    -- add device alias to device data if present
    if device_alias then
        device_data['map']['alias'] = device_alias
    end

    -- add device groups to device data if present
    if device_groups then
        device_data['map']['groups'] = device_groups
    end

    return device_data
    """

    get_device_data = redis_client.register_script(_get_device_data)
