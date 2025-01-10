from fastapi import HTTPException, status, Depends
from src.config import Settings, get_settings


def api_only_check(settings: Settings = Depends(get_settings)):
    if settings.API_ONLY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="This operation is disabled in API_ONLY mode.",
        )
