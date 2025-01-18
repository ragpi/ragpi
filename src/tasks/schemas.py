from typing import Any
from pydantic import BaseModel


class Task(BaseModel):
    id: str | None
    status: str | None
    date_done: str | None
    metadata: dict[str, Any] | str | None
