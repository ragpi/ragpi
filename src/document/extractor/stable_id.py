from uuid import UUID, uuid5

from src.config import settings


def generate_stable_id(url: str, content: str) -> str:
    namespace = UUID(settings.DOCUMENT_UUID_NAMESPACE)

    return str(uuid5(namespace, f"{url}:{content}"))
