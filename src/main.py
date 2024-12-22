import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from traceloop.sdk import Traceloop  #  type: ignore

from src.common.api_key import get_api_key
from src.common.exceptions import (
    ResourceAlreadyExistsException,
    ResourceLockedException,
    ResourceNotFoundException,
    rate_limit_exception_handler,
    resource_already_exists_handler,
    resource_locked_handler,
    resource_not_found_handler,
    unexpected_exception_handler,
)
from src.common.rate_limiter import create_rate_limiter
from src.common.redis import create_redis_client
from src.config import get_settings
from src.source.router import router as source_router
from src.chat.router import router as chat_router
from src.task.router import router as task_router

settings = get_settings()

logging.basicConfig(
    level=logging.INFO,
)

Traceloop.init(  #  type: ignore
    disable_batch=True,  # TODO: Disable for prod
    app_name="rag-api",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis_client = create_redis_client(settings.REDIS_URL)
    logging.info("Redis connection established.")

    app.state.limiter = create_rate_limiter(settings.RATE_LIMIT, settings.REDIS_URL)

    yield

    app.state.redis_client.close()
    logging.info("Redis connection closed.")


app = FastAPI(dependencies=[Depends(get_api_key)], lifespan=lifespan)

app.exception_handler(RateLimitExceeded)(rate_limit_exception_handler)
app.exception_handler(ResourceNotFoundException)(resource_not_found_handler)
app.exception_handler(ResourceAlreadyExistsException)(resource_already_exists_handler)
app.exception_handler(ResourceLockedException)(resource_locked_handler)
app.exception_handler(Exception)(unexpected_exception_handler)

app.add_middleware(SlowAPIMiddleware)

app.include_router(source_router)
app.include_router(chat_router)
app.include_router(task_router)
