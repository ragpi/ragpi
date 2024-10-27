from fastapi import FastAPI, Depends
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from src.dependencies import create_rate_limiter, get_api_key
from src.exceptions import (
    ResourceAlreadyExistsException,
    ResourceNotFoundException,
    rate_limit_exception_handler,
    resource_already_exists_handler,
    resource_not_found_handler,
    unexpected_exception_handler,
)
from src.repository.router import router as repository_router
from src.chat.router import router as chat_router
from src.task.router import router as task_router


limiter = create_rate_limiter()

app = FastAPI(dependencies=[Depends(get_api_key)])

app.state.limiter = limiter

app.exception_handler(RateLimitExceeded)(rate_limit_exception_handler)
app.exception_handler(ResourceNotFoundException)(resource_not_found_handler)
app.exception_handler(ResourceAlreadyExistsException)(resource_already_exists_handler)
app.exception_handler(Exception)(unexpected_exception_handler)

app.add_middleware(SlowAPIMiddleware)

app.include_router(repository_router)
app.include_router(chat_router)
app.include_router(task_router)
