from fastapi import FastAPI

from src.exceptions import (
    ResourceAlreadyExistsException,
    ResourceNotFoundException,
    resource_already_exists_handler,
    resource_not_found_handler,
    unexpected_exception_handler,
)
from src.routers.repository import router as repository_router
from src.routers.chat import router as chat_router
from src.routers.task import router as tasks_router

app = FastAPI()

app.exception_handler(ResourceNotFoundException)(resource_not_found_handler)
app.exception_handler(ResourceAlreadyExistsException)(resource_already_exists_handler)
app.exception_handler(Exception)(unexpected_exception_handler)

app.include_router(repository_router)
app.include_router(chat_router)
app.include_router(tasks_router)
