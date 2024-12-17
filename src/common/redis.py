from redis import Redis

from src.config import settings

redis_client = None


def get_redis_client():
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client
