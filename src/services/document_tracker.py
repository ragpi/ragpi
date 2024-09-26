from datetime import datetime, timezone
import redis


class DocumentTracker:
    def __init__(self, collection_name: str, redis_url: str):
        self.namespace = f"document_tracker:{collection_name}"
        self.redis_client = redis.Redis.from_url(redis_url)

    def add_document(self, ids: list[str]) -> None:
        timestamp = datetime.now(timezone.utc).isoformat()

        for id in ids:
            self.redis_client.hset(self.namespace, id, timestamp)

    def document_exists(self, id: str) -> bool:
        return self.redis_client.hexists(self.namespace, id)

    def delete_document(self, ids: list[str]) -> None:
        for id in ids:
            self.redis_client.hdel(self.namespace, id)

    def get_all_document_ids(self) -> list[str]:
        return [key.decode() for key in self.redis_client.hkeys(self.namespace)]

    def collection_exists(self) -> bool:
        return self.redis_client.exists(self.namespace) > 0

    def delete_collection(self) -> None:
        self.redis_client.delete(self.namespace)
