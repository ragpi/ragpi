from slowapi import Limiter
from slowapi.util import get_remote_address


def create_rate_limiter(rate_limit: str, storage_uri: str) -> Limiter:
    return Limiter(
        key_func=get_remote_address,
        application_limits=[rate_limit],
        storage_uri=storage_uri,
    )
