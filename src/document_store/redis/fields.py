from typing import Any


def get_index_schema_fields(embedding_dimensions: int) -> dict[str, Any]:
    return {
        "fields": [
            {"name": "id", "type": "tag"},
            {"name": "source", "type": "tag"},
            {"name": "content", "type": "text"},
            {"name": "url", "type": "tag"},
            {"name": "created_at", "type": "tag"},
            {"name": "title", "type": "text"},
            {
                "name": "embedding",
                "type": "vector",
                "attrs": {
                    "dims": embedding_dimensions,
                    "distance_metric": "cosine",
                    "algorithm": "hnsw",
                    "datatype": "float32",
                },
            },
        ],
    }


DOCUMENT_FIELDS = [
    "source",
    "id",
    "content",
    "url",
    "title",
    "created_at",
]
