from pydantic import BaseModel, Field


class ToolDefinition(BaseModel):
    model: type[BaseModel]
    name: str
    description: str


class RetrieveDocuments(BaseModel):
    source_name: str = Field(description="Source name")
    semantic_query: str = Field(description="Semantic query")
    full_text_query: str = Field(description="Full text query")
