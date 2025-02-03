from src.chat.tools.schamas import RetrieveDocuments, ToolDefinition


TOOL_DEFINITIONS: list[ToolDefinition] = [
    ToolDefinition(
        model=RetrieveDocuments,
        name="retrieve_documents",
        description=(
            """Retrieves relevant documents from source 'source_name' based on the 'semantic_query' and 'full_text_query'.
            It combines semantic vector-based search with keyword-based full-text search and results are merged using reciprocal rank fusion. 
            The semantic_query should be a natural language query and optimized for semantic search.
            The full_text_query should be a keyword-based query and optimized for full-text search.
            The output includes a list of documents with their URLs and content."""
        ),
    )
]
