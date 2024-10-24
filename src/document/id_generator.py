import hashlib


def generate_stable_id(source: str, content: str) -> str:
    return hashlib.md5(f"{source}:{content}".encode()).hexdigest()
