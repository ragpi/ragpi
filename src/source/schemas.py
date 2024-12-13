from pydantic import BaseModel, Field, field_validator
import re

from src.source.config import SourceConfig


# Inputs
class SearchSourceInput(BaseModel):
    name: str = Field(description="Source name")
    query: str = Field(description="Search query")
    top_k: int = Field(description="Number of results to return")


# Outputs
class SourceOverview(BaseModel):
    id: str
    name: str
    description: str
    num_docs: int
    created_at: str
    updated_at: str
    config: SourceConfig


# Requests
class CreateSourceRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=50)
    description: str
    config: SourceConfig

    @field_validator("name")
    def validate_name(cls, value: str):
        if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$", value):
            raise ValueError(
                "'name' must start and end with an alphanumeric character and contain only alphanumeric characters, underscores, or hyphens"
            )
        return value


class UpdateSourceRequest(BaseModel):
    sync: bool = False
    description: str | None = None
    config: SourceConfig | None = None


class SearchSourceRequest(BaseModel):
    query: str
    top_k: int = 10


# Responses
class SourceTaskResponse(BaseModel):
    task_id: str | None
    source: SourceOverview
    message: str | None = None
