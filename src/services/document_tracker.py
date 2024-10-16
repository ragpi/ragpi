import redis

from src.utils.current_datetime import current_datetime


# TODO: Use redis pipeline for bulk operations
class DocumentTracker:
    def __init__(self, repository_name: str, redis_url: str):
        self.namespace = f"document_tracker:{repository_name}"
        self.redis_client = redis.Redis.from_url(redis_url, decode_responses=True)

    def add_documents(self, ids: list[str]) -> None:
        timestamp = current_datetime()

        for id in ids:
            self.redis_client.hset(self.namespace, id, timestamp)

    def delete_documents(self, ids: list[str]) -> None:
        for id in ids:
            self.redis_client.hdel(self.namespace, id)

    def get_all_document_ids(self) -> list[str]:
        return [key[0] for key in self.redis_client.hscan_iter(self.namespace)]

    def repository_exists(self) -> bool:
        return self.redis_client.exists(self.namespace) > 0

    def delete_repository(self) -> None:
        self.redis_client.delete(self.namespace)
