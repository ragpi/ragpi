from uuid import UUID, uuid5

from src.config import get_settings


def generate_stable_id(url: str, content: str) -> str:
    settings = get_settings()  # TODO: add namespace as a parameter
    namespace = UUID(settings.DOCUMENT_UUID_NAMESPACE)

    return str(uuid5(namespace, f"{url}:{content}"))
