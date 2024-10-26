from uuid import UUID, uuid5


def generate_stable_id(source: str, content: str) -> str:
    namespace = UUID("ee747eb2-fd0f-4650-9785-a2e9ae036ff2")

    return str(uuid5(namespace, f"{source}:{content}"))
