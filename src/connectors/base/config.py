from pydantic import BaseModel

from src.config import get_settings

settings = get_settings()


class BaseConnectorConfig(BaseModel):
    type: str
