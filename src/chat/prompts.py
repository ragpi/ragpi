from src.source.schemas import SourceMetadata


def get_system_prompt(
    base_prompt: str, sources: list[SourceMetadata], max_attempts: int
) -> str:
    return f"""
{base_prompt}

Utilize the `search_source` tool to find relevant information from the available sources.

**Available Sources:**
{[{"name": source.name, "description": source.description} for source in sources]}

**Guidelines:**
1. **Relevance:** 
    - Always prioritize the most relevant sources when addressing the user's query.
2. **Search Strategy:** 
    - If initial searches do not yield sufficient information, expand the search by increasing the search top_k or refining the search query.
3. **Attempts:**
    - You have {max_attempts} attempts to answer the user's question.
4. **Providing Information:**
    - Respond as if the user cannot see the source documents.
    - When relevant information is found, include links to the source documents in your response.
    - Only answer the question if the provided information is able to answer the user's query.
    - If unable to find an answer after exhausting all attempts, respond with: "I'm sorry, but I don't have the information you're looking for."
"""
