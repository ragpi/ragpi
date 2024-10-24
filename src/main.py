from fastapi import FastAPI

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

app = FastAPI()

app.exception_handler(ResourceNotFoundException)(resource_not_found_handler)
app.exception_handler(ResourceAlreadyExistsException)(resource_already_exists_handler)
app.exception_handler(Exception)(unexpected_exception_handler)

app.include_router(repository_router)
app.include_router(chat_router)
app.include_router(task_router)
