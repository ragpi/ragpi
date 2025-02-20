from fastapi import Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from src.config import Settings, get_settings


api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


def get_api_key(
    api_key: str = Security(api_key_header), settings: Settings = Depends(get_settings)
):
    if not settings.RAGPI_API_KEY:
        return

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is missing",
        )

    if api_key != settings.RAGPI_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key is invalid",
        )
