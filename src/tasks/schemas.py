from typing import Any
from pydantic import BaseModel


class Task(BaseModel):
    id: str | None
    status: str | None
    completed_at: str | None
    metadata: dict[str, Any] | str | None
