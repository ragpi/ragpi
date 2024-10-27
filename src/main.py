from fastapi import FastAPI, Depends, HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from src.config import settings
from src.exceptions import (
    ResourceAlreadyExistsException,
    ResourceNotFoundException,
    resource_already_exists_handler,
    resource_not_found_handler,
    unexpected_exception_handler,
)
from src.repository.router import router as repository_router
from src.chat.router import router as chat_router
from src.task.router import router as task_router


api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


async def get_api_key(api_key: str = Security(api_key_header)):
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


app = FastAPI(dependencies=[Depends(get_api_key)])

app.exception_handler(ResourceNotFoundException)(resource_not_found_handler)
app.exception_handler(ResourceAlreadyExistsException)(resource_already_exists_handler)
app.exception_handler(Exception)(unexpected_exception_handler)

app.include_router(repository_router)
app.include_router(chat_router)
app.include_router(task_router)
