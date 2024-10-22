from typing import Any
from pydantic import BaseModel


class TaskOverview(BaseModel):
    id: str
    status: str
    error: str | None = None
    result: dict[str, Any] | None = None
