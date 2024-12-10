from pydantic import BaseModel

from src.source.schemas import SearchSourceInput


class FunctionTool(BaseModel):
    model: type[BaseModel]
    name: str
    description: str


FUNCTION_TOOLS: list[FunctionTool] = [
    FunctionTool(
        model=SearchSourceInput,
        name="search_source",
        description=(
            """Retrieves 'top_k' relevant documents from source 'name' based on the search 'query'.
            It combines semantic vector-based search with keyword-based full-text search and results are merged using reciprocal rank fusion. 
            The output includes a list of documents with their URLs and content."""
        ),
    )
]
