import redis

from src.utils.current_datetime import current_datetime


class DocumentTracker:
    def __init__(self, repository_name: str, redis_url: str):
        self.namespace = f"document_tracker:{repository_name}"
        self.redis_client = redis.Redis.from_url(redis_url)  # TODO: decode responses

    def add_document(self, ids: list[str]) -> None:  # TODO: Change to add_documents
        timestamp = current_datetime()

        for id in ids:
            self.redis_client.hset(self.namespace, id, timestamp)

    def document_exists(self, id: str) -> bool:
        return self.redis_client.hexists(self.namespace, id)

    def delete_document(
        self, ids: list[str]
    ) -> None:  # TODO: Change to delete_documents
        for id in ids:
            self.redis_client.hdel(self.namespace, id)

    def get_all_document_ids(self) -> list[str]:
        return [key.decode() for key in self.redis_client.hkeys(self.namespace)]

    def repository_exists(self) -> bool:
        return self.redis_client.exists(self.namespace) > 0

    def delete_repository(self) -> None:
        self.redis_client.delete(self.namespace)
