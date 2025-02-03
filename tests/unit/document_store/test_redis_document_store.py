import pytest
from pytest_mock import MockerFixture
from unittest.mock import Mock
from datetime import datetime
from openai.types.embedding import Embedding
from openai.types.create_embedding_response import Usage, CreateEmbeddingResponse
from redis.commands.search.document import Document as RedisDocument

from src.document_store.redis.store import RedisDocumentStore
from src.document_store.schemas import Document

TEST_INDEX_NAME = "test_index"
TEST_SOURCE = "test_source"
EMBEDDING_MODEL = "test-embedding-model"
EMBEDDING_DIMENSIONS = 1536
TEST_SEMANTIC_QUERY = "Test semantic query"
TEST_FULL_TEXT_QUERY = "Test full text query"
TOP_K = 2


@pytest.fixture
def sample_documents() -> list[Document]:
    return [
        Document(
            id="doc1",
            content="Test content 1",
            title="Test title 1",
            url="http://test1.com",
            created_at=datetime.now(),
        ),
        Document(
            id="doc2",
            content="Test content 2",
            title="Test title 2",
            url="http://test2.com",
            created_at=datetime.now(),
        ),
    ]


@pytest.fixture
def mock_redis_client(mocker: MockerFixture) -> Mock:
    return mocker.Mock()


@pytest.fixture
def mock_openai_client(mocker: MockerFixture) -> Mock:
    return mocker.Mock()


@pytest.fixture
def mock_index(mocker: MockerFixture) -> Mock:
    return mocker.Mock()


@pytest.fixture
def document_store(
    mocker: MockerFixture,
    mock_redis_client: Mock,
    mock_openai_client: Mock,
    mock_index: Mock,
) -> RedisDocumentStore:
    mocker.patch("src.document_store.redis.store.SearchIndex", return_value=mock_index)
    return RedisDocumentStore(
        index_name=TEST_INDEX_NAME,
        redis_client=mock_redis_client,
        openai_client=mock_openai_client,
        embedding_model=EMBEDDING_MODEL,
        embedding_dimensions=EMBEDDING_DIMENSIONS,
    )


def test_add_documents(
    document_store: RedisDocumentStore,
    sample_documents: list[Document],
    mock_openai_client: Mock,
) -> None:
    mock_embeddings: list[Embedding] = [
        Embedding(embedding=[0.1] * EMBEDDING_DIMENSIONS, index=0, object="embedding"),
        Embedding(embedding=[0.2] * EMBEDDING_DIMENSIONS, index=1, object="embedding"),
    ]
    mock_openai_client.embeddings.create.return_value = CreateEmbeddingResponse(
        data=mock_embeddings,
        model=EMBEDDING_MODEL,
        usage=Usage(prompt_tokens=0, total_tokens=0),
        object="list",
    )

    document_store.add_documents(TEST_SOURCE, sample_documents)

    mock_openai_client.embeddings.create.assert_called_once_with(
        input=[doc.content for doc in sample_documents],
        model=EMBEDDING_MODEL,
        dimensions=EMBEDDING_DIMENSIONS,
    )

    document_store.index.load.assert_called_once()  # type: ignore
    call_args = document_store.index.load.call_args[1]  # type: ignore
    assert call_args["id_field"] == "id"
    data = call_args["data"]
    assert len(data) == 2
    assert data[0]["id"] == f"{TEST_SOURCE}:doc1"
    assert data[0]["content"] == "Test content 1"
    assert data[1]["id"] == f"{TEST_SOURCE}:doc2"
    assert data[1]["content"] == "Test content 2"


def test_get_documents(
    mocker: MockerFixture,
    document_store: RedisDocumentStore,
    sample_documents: list[Document],
) -> None:
    mock_keys: list[str] = [
        f"{TEST_INDEX_NAME}:sources:{TEST_SOURCE}:doc1",
        f"{TEST_INDEX_NAME}:sources:{TEST_SOURCE}:doc2",
    ]

    pipeline_mock: Mock = mocker.Mock()
    pipeline_mock.execute.return_value = [
        [
            TEST_SOURCE,
            f"{TEST_SOURCE}:doc1",
            "Test content 1",
            "http://test1.com",
            "Test title 1",
            sample_documents[0].created_at.isoformat(),
        ],
        [
            TEST_SOURCE,
            f"{TEST_SOURCE}:doc2",
            "Test content 2",
            "http://test2.com",
            "Test title 2",
            sample_documents[1].created_at.isoformat(),
        ],
    ]

    mocker.patch.object(document_store.client, "scan_iter", return_value=mock_keys)
    mocker.patch.object(document_store.client, "pipeline", return_value=pipeline_mock)

    result: list[Document] = document_store.get_documents(
        TEST_SOURCE, limit=10, offset=0
    )
    assert len(result) == 2
    assert result[0] == sample_documents[0]
    assert result[1] == sample_documents[1]


def test_delete_documents(
    mocker: MockerFixture, document_store: RedisDocumentStore
) -> None:
    doc_ids: list[str] = ["doc1", "doc2"]
    mock_drop_keys = mocker.patch.object(document_store.index, "drop_keys")

    document_store.delete_documents(TEST_SOURCE, doc_ids)

    expected_keys: list[str] = [
        f"{TEST_INDEX_NAME}:sources:{TEST_SOURCE}:doc1",
        f"{TEST_INDEX_NAME}:sources:{TEST_SOURCE}:doc2",
    ]
    mock_drop_keys.assert_called_once_with(expected_keys)


def test_delete_all_documents(
    mocker: MockerFixture, document_store: RedisDocumentStore
) -> None:
    mock_keys: list[str] = [
        f"{TEST_INDEX_NAME}:sources:{TEST_SOURCE}:doc1",
        f"{TEST_INDEX_NAME}:sources:{TEST_SOURCE}:doc2",
        f"{TEST_INDEX_NAME}:sources:{TEST_SOURCE}:doc3",
    ]

    mock_scan_iter = mocker.patch.object(
        document_store.client, "scan_iter", return_value=mock_keys
    )
    mock_drop_keys = mocker.patch.object(document_store.index, "drop_keys")

    document_store.delete_all_documents(TEST_SOURCE)
    mock_scan_iter.assert_called_once_with(f"{TEST_INDEX_NAME}:sources:{TEST_SOURCE}:*")
    mock_drop_keys.assert_called_once_with(mock_keys)


def test_get_document_ids(
    mocker: MockerFixture, document_store: RedisDocumentStore
) -> None:
    mock_keys: list[str] = [
        f"{TEST_INDEX_NAME}:sources:{TEST_SOURCE}:doc1",
        f"{TEST_INDEX_NAME}:sources:{TEST_SOURCE}:doc2",
    ]

    mock_scan_iter = mocker.patch.object(
        document_store.client, "scan_iter", return_value=mock_keys
    )

    ids: list[str] = document_store.get_document_ids(TEST_SOURCE)
    mock_scan_iter.assert_called_once_with(f"{TEST_INDEX_NAME}:sources:{TEST_SOURCE}:*")
    assert ids == ["doc1", "doc2"]


def test_semantic_search(
    mocker: MockerFixture, document_store: RedisDocumentStore
) -> None:
    mock_embedding: list[float] = [0.1] * EMBEDDING_DIMENSIONS

    mock_create = mocker.patch.object(
        document_store.embedding_client,
        "create",
        return_value=CreateEmbeddingResponse(
            data=[Embedding(embedding=mock_embedding, index=0, object="embedding")],
            model=EMBEDDING_MODEL,
            usage=Usage(prompt_tokens=0, total_tokens=0),
            object="list",
        ),
    )

    mock_search_results = [
        {
            "id": f"{TEST_SOURCE}:doc1",
            "content": "Test content 1",
            "title": "Test title 1",
            "url": "http://test1.com",
            "created_at": "2024-01-01T00:00:00",
        },
        {
            "id": f"{TEST_SOURCE}:doc2",
            "content": "Test content 2",
            "title": "Test title 2",
            "url": "http://test2.com",
            "created_at": "2024-01-02T00:00:00",
        },
    ]
    mocker.patch.object(document_store.index, "query", return_value=mock_search_results)

    results: list[Document] = document_store.semantic_search(
        TEST_SOURCE, TEST_SEMANTIC_QUERY, TOP_K
    )

    mock_create.assert_called_once_with(
        input=TEST_SEMANTIC_QUERY,
        model=EMBEDDING_MODEL,
        dimensions=EMBEDDING_DIMENSIONS,
    )

    assert len(results) == TOP_K
    assert results[0].id == "doc1"
    assert results[0].content == "Test content 1"
    assert results[1].id == "doc2"
    assert results[1].content == "Test content 2"


def test_full_text_search(
    mocker: MockerFixture, document_store: RedisDocumentStore
) -> None:
    mock_search_results: list[RedisDocument] = [
        RedisDocument(
            id=f"{TEST_INDEX_NAME}:sources:{TEST_SOURCE}:doc1",
            payload=None,
            **{
                "content": "Test content 1",
                "title": "Test title 1",
                "url": "http://test1.com",
                "created_at": "2024-01-01T00:00:00",
            },
        ),
        RedisDocument(
            id=f"{TEST_INDEX_NAME}:sources:{TEST_SOURCE}:doc2",
            payload=None,
            **{
                "content": "Test content 2",
                "title": "Test title 2",
                "url": "http://test2.com",
                "created_at": "2024-01-02T00:00:00",
            },
        ),
    ]

    ft_mock: Mock = mocker.Mock()
    ft_mock.search.return_value.docs = mock_search_results
    mocker.patch.object(document_store.client, "ft", return_value=ft_mock)

    results: list[Document] = document_store.full_text_search(
        TEST_SOURCE, TEST_FULL_TEXT_QUERY, TOP_K
    )
    assert len(results) == TOP_K
    assert results[0].id == "doc1"
    assert results[0].content == "Test content 1"
    assert results[1].id == "doc2"
    assert results[1].content == "Test content 2"


def test_hybrid_search(
    mocker: MockerFixture, document_store: RedisDocumentStore
) -> None:
    vector_results: list[Document] = [
        Document(
            id="doc1",
            content="Test content 1",
            title="Title 1",
            url="http://test1.com",
            created_at=datetime.fromisoformat("2024-01-01T00:00:00"),
        ),
        Document(
            id="doc2",
            content="Test content 2",
            title="Title 2",
            url="http://test2.com",
            created_at=datetime.fromisoformat("2024-01-02T00:00:00"),
        ),
        Document(
            id="doc3",
            content="Test content 3",
            title="Title 3",
            url="http://test3.com",
            created_at=datetime.fromisoformat("2024-01-03T00:00:00"),
        ),
    ]

    text_results: list[Document] = [
        Document(
            id="doc2",
            content="Test content 2",
            title="Title 2",
            url="http://test2.com",
            created_at=datetime.fromisoformat("2024-01-02T00:00:00"),
        ),
        Document(
            id="doc3",
            content="Test content 3",
            title="Title 3",
            url="http://test3.com",
            created_at=datetime.fromisoformat("2024-01-03T00:00:00"),
        ),
        Document(
            id="doc4",
            content="Test content 4",
            title="Title 4",
            url="http://test4.com",
            created_at=datetime.fromisoformat("2024-01-04T00:00:00"),
        ),
    ]

    mock_vector_search = mocker.patch.object(
        document_store, "semantic_search", return_value=vector_results
    )
    mock_text_search = mocker.patch.object(
        document_store, "full_text_search", return_value=text_results
    )

    combined_results: list[Document] = document_store.hybrid_search(
        source_name=TEST_SOURCE,
        semantic_query=TEST_SEMANTIC_QUERY,
        full_text_query=TEST_FULL_TEXT_QUERY,
        top_k=TOP_K,
    )

    mock_vector_search.assert_called_once_with(TEST_SOURCE, TEST_SEMANTIC_QUERY, TOP_K)
    mock_text_search.assert_called_once_with(TEST_SOURCE, TEST_FULL_TEXT_QUERY, TOP_K)

    assert len(combined_results) == TOP_K
    # hybrid_search uses a reciprocal rank fusion algorithm to combine results
    # doc2 and doc3 appear in both vector and text results, so they should be ranked highest
    # with doc2 ranked higher than doc3.
    assert combined_results[0].id == "doc2"
    assert combined_results[1].id == "doc3"
