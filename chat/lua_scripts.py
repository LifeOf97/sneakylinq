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
    local device_alias = redis.call('HGET', 'device:alias', device)
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

    _set_alias_device = """
    redis.setresp(3)

    local device = KEYS[1]
    local device_alias = redis.call('HGET', 'device:alias', device)

    -- add alias:device to alias_device hash
    if device_alias then
        redis.call('HSET', 'alias:device', device_alias, device)
    end

    return true
    """

    get_device_data = redis_client.register_script(_get_device_data)
    """
    Redis lua script to get complete device info
    """

    set_alias_device = redis_client.register_script(_set_alias_device)
    """
    Redis lua script to set/update the alias:device hash. Where key is device alias
    and value is device:did. We use this to store each alias/device:did to easily
    retreive device:did when needed.
    """
