import pytest
from unittest.mock import MagicMock
from openai import OpenAI
from redis import Redis
from src.common.schemas import Document
from src.document_store.providers.redis.store import RedisDocumentStore


@pytest.fixture
def redis_client() -> Redis:
    return MagicMock(spec=Redis)


@pytest.fixture
def openai_client() -> OpenAI:
    return MagicMock(spec=OpenAI)


@pytest.fixture
def document_store(redis_client: Redis, openai_client: OpenAI) -> RedisDocumentStore:
    return RedisDocumentStore(
        index_name="test_index",
        redis_client=redis_client,
        openai_client=openai_client,
        embedding_model="test_model",
        embedding_dimensions=1536,
    )


def test_add_documents(document_store: RedisDocumentStore, redis_client: Redis, openai_client: OpenAI) -> None:
    documents = [
        Document(id="1", content="test content 1", title="title 1", url="url 1", created_at="2023-01-01"),
        Document(id="2", content="test content 2", title="title 2", url="url 2", created_at="2023-01-02"),
    ]

    openai_client.embeddings.create.return_value = MagicMock(data=[
        MagicMock(embedding=[0.1] * 1536),
        MagicMock(embedding=[0.2] * 1536),
    ])

    document_store.add_documents("test_source", documents)

    assert redis_client.pipeline().execute.called


def test_get_documents(document_store: RedisDocumentStore, redis_client: Redis) -> None:
    redis_client.scan_iter.return_value = [f"test_index:sources:test_source:{i}" for i in range(3)]
    redis_client.pipeline().execute.return_value = [
        ["1", "test content 1", "url 1", "title 1", "2023-01-01"],
        ["2", "test content 2", "url 2", "title 2", "2023-01-02"],
        ["3", "test content 3", "url 3", "title 3", "2023-01-03"],
    ]

    documents = document_store.get_documents("test_source", limit=2, offset=1)

    assert len(documents) == 2
    assert documents[0].id == "2"
    assert documents[1].id == "3"


def test_delete_all_documents(document_store: RedisDocumentStore, redis_client: Redis) -> None:
    redis_client.scan_iter.return_value = [f"test_index:sources:test_source:{i}" for i in range(3)]

    document_store.delete_all_documents("test_source")

    assert redis_client.delete.called


def test_search_documents(document_store: RedisDocumentStore, redis_client: Redis, openai_client: OpenAI) -> None:
    openai_client.embeddings.create.return_value = MagicMock(data=[MagicMock(embedding=[0.1] * 1536)])
    redis_client.ft().search.return_value = MagicMock(docs=[
        {"id": "1", "content": "test content 1", "title": "title 1", "url": "url 1", "created_at": "2023-01-01"},
        {"id": "2", "content": "test content 2", "title": "title 2", "url": "url 2", "created_at": "2023-01-02"},
    ])

    documents = document_store.search_documents("test_source", "test query", top_k=2)

    assert len(documents) == 2
    assert documents[0].id == "1"
    assert documents[1].id == "2"
