from typing import Any
from celery import Celery
from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import create_engine, text

from src.config import Settings, get_settings
from src.common.redis import RedisClient, get_redis_client
from src.celery import get_celery_app

router = APIRouter()


@router.get(
    "/healthcheck",
    tags=["Healthcheck"],
    status_code=status.HTTP_200_OK,
    responses={
        200: {
            "description": "Healthcheck status",
            "content": {
                "application/json": {
                    "example": {
                        "api": {"status": "ok"},
                        "redis": {"status": "ok"},
                        "postgres": {"status": "ok"},
                        "workers": {"status": "ok", "active_workers": 2},
                    }
                }
            },
        },
        503: {
            "description": "Service unavailable",
            "content": {
                "application/json": {
                    "example": {
                        "api": {"status": "ok"},
                        "redis": {"status": "error", "message": "Connection error"},
                        "postgres": {
                            "status": "error",
                            "message": "Connection error or unexpected result",
                        },
                        "workers": {
                            "status": "error",
                            "message": "No active workers found",
                        },
                    }
                }
            },
        },
    },
)
def healthcheck(
    settings: Settings = Depends(get_settings),
    redis_client: RedisClient = Depends(get_redis_client),
    celery_app: Celery = Depends(get_celery_app),
) -> JSONResponse:
    health_status: dict[str, Any] = {
        "api": {"status": "ok"},
        "redis": {"status": "ok"},
        "postgres": {"status": "ok"},
        "workers": {"status": "ok"},
    }
    has_error = False

    # Check Redis connection
    try:
        redis_client.ping()
    except Exception as e:
        health_status["redis"].update({"status": "error", "message": str(e)})
        has_error = True

    # Check PostgreSQL connection
    if (
        settings.SOURCE_METADATA_BACKEND == "postgres"
        or settings.DOCUMENT_STORE_BACKEND == "postgres"
    ):
        try:
            engine = create_engine(settings.POSTGRES_URL)
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1")).scalar()
                if result != 1:
                    raise Exception("Postgres health check failed")
        except Exception as e:
            health_status["postgres"].update({"status": "error", "message": str(e)})
            has_error = True
    else:
        del health_status["postgres"]

    # Check Celery Worker status
    if not settings.WORKERS_ENABLED:
        health_status["workers"].update(
            {
                "status": "skipped",
                "message": "Workers are disabled. Set WORKERS_ENABLED to True to enable workers.",
            }
        )
    else:
        try:
            inspect = celery_app.control.inspect()
            active_workers = inspect.active()
            if not active_workers:
                raise Exception("No active workers found")
            worker_count = len(active_workers.keys())
            health_status["workers"].update(
                {"status": "ok", "active_workers": worker_count}
            )
        except Exception as e:
            health_status["workers"].update({"status": "error", "message": str(e)})
            has_error = True

    if has_error:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content=health_status
        )

    return JSONResponse(status_code=status.HTTP_200_OK, content=health_status)
