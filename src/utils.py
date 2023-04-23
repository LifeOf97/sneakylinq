import redis

from src import env

redis_client = redis.Redis(
    host=env.REDIS_SERVER, port=env.REDIS_PORT, decode_responses=True
)
