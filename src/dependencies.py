from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address

from src.config import settings


api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


def get_api_key(api_key: str = Security(api_key_header)):
    if not settings.API_KEY:
        return

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing",
        )

    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is invalid",
        )


def create_rate_limiter() -> Limiter:
    return Limiter(
        key_func=get_remote_address,
        application_limits=["60/minute"],  # TODO: Make this configurable
        storage_uri=settings.REDIS_URL,
    )
