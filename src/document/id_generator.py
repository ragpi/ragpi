import hashlib


def generate_stable_id(url: str, content: str) -> str:
    return hashlib.md5(f"{url}:{content}".encode()).hexdigest()
