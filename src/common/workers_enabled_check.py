from fastapi import HTTPException, status, Depends
from src.config import Settings, get_settings


def workers_enabled_check(settings: Settings = Depends(get_settings)):
    if not settings.WORKERS_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="This operation requires workers to be enabled. Set WORKERS_ENABLED to True to enable workers.",
        )
