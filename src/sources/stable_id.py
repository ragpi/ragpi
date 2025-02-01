from uuid import UUID, uuid5


def generate_stable_id(
    uuid_namespace: str, source: str, title: str, content: str
) -> str:
    namespace = UUID(uuid_namespace)

    return str(uuid5(namespace, f"{source}:{title}:{content}"))
