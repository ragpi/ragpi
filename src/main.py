from fastapi import FastAPI

from src.routers.repository import router as repository_router
from src.routers.chat import router as chat_router

app = FastAPI()

app.include_router(repository_router)
app.include_router(chat_router)
