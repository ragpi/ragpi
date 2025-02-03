import pytest
from pytest_mock import MockerFixture
from unittest.mock import Mock
from datetime import datetime
from openai.types.embedding import Embedding
from openai.types.create_embedding_response import Usage, CreateEmbeddingResponse
from sqlalchemy.orm import Session

from src.document_store.postgres.store import PostgresDocumentStore
from src.document_store.postgres.model import DocumentStoreModel
from src.document_store.schemas import Document

TEST_DATABASE_URL = "postgresql://test:test@localhost:5432/test"
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
def mock_session(mocker: MockerFixture) -> Mock:
    session_mock = mocker.MagicMock(spec=Session)
    session_mock.__enter__.return_value = session_mock
    session_mock.__exit__.return_value = None
    return session_mock


@pytest.fixture
def mock_openai_client(mocker: MockerFixture) -> Mock:
    return mocker.Mock()


@pytest.fixture
def document_store(
    mocker: MockerFixture, mock_session: Mock, mock_openai_client: Mock
) -> PostgresDocumentStore:
    mocker.patch("src.document_store.postgres.store.create_engine")
    mocker.patch(
        "src.document_store.postgres.store.sessionmaker",
        return_value=lambda: mock_session,
    )

    store = PostgresDocumentStore(
        database_url=TEST_DATABASE_URL,
        openai_client=mock_openai_client,
        embedding_model=EMBEDDING_MODEL,
        embedding_dimensions=EMBEDDING_DIMENSIONS,
    )
    return store


def test_add_documents(
    document_store: PostgresDocumentStore,
    sample_documents: list[Document],
    mock_openai_client: Mock,
    mock_session: Mock,
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

    mock_session.bulk_save_objects.assert_called_once()
    saved_objects = mock_session.bulk_save_objects.call_args[0][0]
    assert len(saved_objects) == 2
    assert isinstance(saved_objects[0], DocumentStoreModel)
    assert saved_objects[0].id == "doc1"
    assert saved_objects[0].content == "Test content 1"
    assert saved_objects[1].id == "doc2"
    assert saved_objects[1].content == "Test content 2"
    mock_session.commit.assert_called_once()


def test_get_documents(
    document_store: PostgresDocumentStore,
    sample_documents: list[Document],
    mock_session: Mock,
) -> None:
    mock_docs = [
        DocumentStoreModel(
            id=doc.id,
            source=TEST_SOURCE,
            content=doc.content,
            title=doc.title,
            url=doc.url,
            created_at=doc.created_at,
            embedding=[0.1] * EMBEDDING_DIMENSIONS,
        )
        for doc in sample_documents
    ]
    mock_session.query.return_value.filter_by.return_value.offset.return_value.limit.return_value.all.return_value = mock_docs

    result: list[Document] = document_store.get_documents(
        TEST_SOURCE, limit=10, offset=0
    )

    mock_session.query.assert_called_once_with(document_store.DocumentModel)
    mock_session.query.return_value.filter_by.assert_called_once_with(
        source=TEST_SOURCE
    )
    assert len(result) == 2
    assert all(isinstance(doc, Document) for doc in result)
    assert result[0].id == "doc1"
    assert result[1].id == "doc2"


def test_delete_documents(
    document_store: PostgresDocumentStore,
    mock_session: Mock,
) -> None:
    doc_ids: list[str] = ["doc1", "doc2"]
    document_store.delete_documents(TEST_SOURCE, doc_ids)

    mock_session.query.assert_called_once_with(document_store.DocumentModel)
    mock_session.query.return_value.filter.assert_called_once()
    mock_session.query.return_value.filter.return_value.delete.assert_called_once_with(
        synchronize_session=False
    )
    mock_session.commit.assert_called_once()


def test_delete_all_documents(
    document_store: PostgresDocumentStore,
    mock_session: Mock,
) -> None:
    document_store.delete_all_documents(TEST_SOURCE)

    mock_session.query.assert_called_once_with(document_store.DocumentModel)
    mock_session.query.return_value.filter_by.assert_called_once_with(
        source=TEST_SOURCE
    )
    mock_session.query.return_value.filter_by.return_value.delete.assert_called_once()
    mock_session.commit.assert_called_once()


def test_get_document_ids(
    document_store: PostgresDocumentStore,
    mock_session: Mock,
) -> None:
    mock_session.query.return_value.filter_by.return_value.all.return_value = [
        ("doc1",),
        ("doc2",),
    ]

    ids: list[str] = document_store.get_document_ids(TEST_SOURCE)

    mock_session.query.assert_called_once()
    mock_session.query.return_value.filter_by.assert_called_once_with(
        source=TEST_SOURCE
    )
    assert ids == ["doc1", "doc2"]


def test_semantic_search(
    document_store: PostgresDocumentStore,
    sample_documents: list[Document],
    mock_session: Mock,
    mock_openai_client: Mock,
) -> None:
    mock_embedding: list[float] = [0.1] * EMBEDDING_DIMENSIONS
    mock_docs = [
        DocumentStoreModel(
            id=doc.id,
            source=TEST_SOURCE,
            content=doc.content,
            title=doc.title,
            url=doc.url,
            created_at=doc.created_at,
            embedding=mock_embedding,
        )
        for doc in sample_documents[:TOP_K]
    ]

    mock_openai_client.embeddings.create.return_value = CreateEmbeddingResponse(
        data=[Embedding(embedding=mock_embedding, index=0, object="embedding")],
        model=EMBEDDING_MODEL,
        usage=Usage(prompt_tokens=0, total_tokens=0),
        object="list",
    )

    mock_session.query.return_value.filter_by.return_value.order_by.return_value.limit.return_value.all.return_value = mock_docs

    results: list[Document] = document_store.semantic_search(
        TEST_SOURCE, TEST_SEMANTIC_QUERY, TOP_K
    )

    mock_openai_client.embeddings.create.assert_called_once_with(
        input=TEST_SEMANTIC_QUERY,
        model=EMBEDDING_MODEL,
        dimensions=EMBEDDING_DIMENSIONS,
    )

    assert len(results) == TOP_K
    assert all(isinstance(doc, Document) for doc in results)
    assert results[0].id == "doc1"
    assert results[1].id == "doc2"


def test_full_text_search(
    document_store: PostgresDocumentStore,
    sample_documents: list[Document],
    mock_session: Mock,
) -> None:
    mock_docs = [
        DocumentStoreModel(
            id=doc.id,
            source=TEST_SOURCE,
            content=doc.content,
            title=doc.title,
            url=doc.url,
            created_at=doc.created_at,
            embedding=[0.1] * EMBEDDING_DIMENSIONS,
        )
        for doc in sample_documents[:TOP_K]
    ]

    mock_session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = mock_docs

    results: list[Document] = document_store.full_text_search(
        TEST_SOURCE, TEST_FULL_TEXT_QUERY, TOP_K
    )

    mock_session.query.assert_called_once_with(document_store.DocumentModel)
    assert len(results) == TOP_K
    assert all(isinstance(doc, Document) for doc in results)
    assert results[0].id == "doc1"
    assert results[1].id == "doc2"


def test_hybrid_search(
    mocker: MockerFixture,
    document_store: PostgresDocumentStore,
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

    mock_semantic_search = mocker.patch.object(
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

    mock_semantic_search.assert_called_once_with(
        TEST_SOURCE, TEST_SEMANTIC_QUERY, TOP_K
    )
    mock_text_search.assert_called_once_with(TEST_SOURCE, TEST_FULL_TEXT_QUERY, TOP_K)

    assert len(combined_results) == TOP_K
    # hybrid_search uses a reciprocal rank fusion algorithm to combine results
    # doc2 and doc3 appear in both vector and text results, so they should be ranked highest
    # with doc2 ranked higher than doc3.
    assert combined_results[0].id == "doc2"
    assert combined_results[1].id == "doc3"
