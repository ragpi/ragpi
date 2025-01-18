from pydantic import BaseModel

from src.config import get_settings

settings = get_settings()


class BaseConnectorConfig(BaseModel):
    type: str
    chunk_size: int = settings.DEFAULT_CHUNK_SIZE
    chunk_overlap: int = settings.DEFAULT_CHUNK_OVERLAP
