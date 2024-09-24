from datetime import datetime, timezone
import redis


class DocumentTracker:
    def __init__(self, namespace: str, redis_url: str):
        self.namespace = namespace
        self.redis_client = redis.Redis.from_url(redis_url)

    def add(self, id: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()
        self.redis_client.hset(self.namespace, id, timestamp)

    def exists(self, id: str) -> bool:
        return self.redis_client.hexists(self.namespace, id)

    def remove(self, id: str) -> None:
        self.redis_client.hdel(self.namespace, id)

    def get_all_ids(self) -> list[str]:
        return [key.decode() for key in self.redis_client.hkeys(self.namespace)]
