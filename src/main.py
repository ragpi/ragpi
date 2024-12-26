import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends

from src.common.api_key import get_api_key
from src.common.exceptions import (
    KnownException,
    ResourceAlreadyExistsException,
    ResourceLockedException,
    ResourceNotFoundException,
    known_exception_handler,
    resource_already_exists_handler,
    resource_locked_handler,
    resource_not_found_handler,
    unexpected_exception_handler,
)
from src.common.opentelemetry import setup_opentelemetry
from src.common.redis import create_redis_client
from src.config import get_settings
from src.source.router import router as source_router
from src.chat.router import router as chat_router
from src.task.router import router as tasks_router

settings = get_settings()

logging.basicConfig(
    level=settings.LOG_LEVEL,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis_client = create_redis_client(settings.REDIS_URL)
    logger.info("Redis connection established.")

    yield

    app.state.redis_client.close()
    logger.info("Redis connection closed.")


app = FastAPI(dependencies=[Depends(get_api_key)], lifespan=lifespan)

if settings.ENABLE_OTEL:
    setup_opentelemetry(settings.OTEL_SERVICE_NAME, app)

app.exception_handler(ResourceNotFoundException)(resource_not_found_handler)
app.exception_handler(ResourceAlreadyExistsException)(resource_already_exists_handler)
app.exception_handler(ResourceLockedException)(resource_locked_handler)
app.exception_handler(KnownException)(known_exception_handler)
app.exception_handler(Exception)(unexpected_exception_handler)

app.include_router(source_router)
app.include_router(chat_router)
app.include_router(tasks_router)
