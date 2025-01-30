from unittest.mock import AsyncMock
from openai import OpenAI
import pytest
from datetime import datetime
from pytest_mock import MockerFixture
from typing import AsyncIterator, Set

from src.common.redis import RedisClient
from src.common.schemas import Document
from src.config import Settings
from src.document_store.providers.redis.store import RedisDocumentStore
from src.sources.exceptions import SyncSourceException
from src.connectors.service import ConnectorService
from src.connectors.connector_type import ConnectorType
from src.connectors.registry import ConnectorConfig
from src.connectors.sitemap.config import SitemapConfig
from src.sources.metadata.store import SourceMetadataStore
from src.sources.metadata.schemas import MetadataUpdate, SourceMetadata
from src.sources.schemas import SyncSourceOutput
from src.sources.sync import SourceSyncService


@pytest.fixture
def mock_redis_client(mocker: MockerFixture) -> RedisClient:
    return mocker.Mock(spec=RedisClient)


@pytest.fixture
def mock_settings(mocker: MockerFixture) -> Settings:
    settings = mocker.Mock(spec=Settings)
    settings.DOCUMENT_STORE_NAMESPACE = "test-namespace"
    settings.EMBEDDING_PROVIDER = "openai"
    settings.EMBEDDING_MODEL = "text-embedding-3-small"
    settings.EMBEDDING_DIMENSIONS = 1536
    settings.DOCUMENT_SYNC_BATCH_SIZE = 2
    settings.OLLAMA_BASE_URL = None
    return settings


@pytest.fixture
def mock_current_datetime() -> str:
    return datetime(2024, 1, 1, 12, 0, 0).isoformat()


@pytest.fixture
def mock_openai_client(mocker: MockerFixture) -> OpenAI:
    return mocker.Mock(spec=OpenAI)


@pytest.fixture
def mock_document_store(mocker: MockerFixture) -> RedisDocumentStore:
    return mocker.Mock(spec=RedisDocumentStore)


@pytest.fixture
def mock_metadata_store(mocker: MockerFixture) -> SourceMetadataStore:
    return mocker.Mock(spec=SourceMetadataStore)


@pytest.fixture
def mock_connector_service(mocker: MockerFixture) -> ConnectorService:
    return mocker.Mock(spec=ConnectorService)


@pytest.fixture
def sample_connector_config() -> ConnectorConfig:
    return SitemapConfig(
        type=ConnectorType.SITEMAP,
        sitemap_url="https://example.com/sitemap.xml",
    )


@pytest.fixture
def sample_documents() -> list[Document]:
    return [
        Document(
            id="doc1",
            title="Test title 1",
            content="Test content 1",
            url="https://example.com/1",
            created_at="2024-01-01T12:00:00",
        ),
        Document(
            id="doc2",
            title="Test title 2",
            content="Test content 2",
            url="https://example.com/2",
            created_at="2024-01-01T12:00:00",
        ),
        Document(
            id="doc3",
            title="Test title 3",
            content="Test content 3",
            url="https://example.com/3",
            created_at="2024-01-01T12:00:00",
        ),
    ]


@pytest.fixture
def patch_extract_documents(mocker: MockerFixture):
    async def _extract_docs(
        source_sync_service: SourceSyncService, documents: list[Document]
    ):
        async def _doc_generator(_: ConnectorConfig) -> AsyncIterator[Document]:
            for doc in documents:
                yield doc

        mocker.patch.object(
            source_sync_service.connector_service,
            "extract_documents",
            side_effect=_doc_generator,
        )

    return _extract_docs


@pytest.fixture
def source_sync_service(
    mock_redis_client: RedisClient,
    mock_settings: Settings,
    mock_openai_client: OpenAI,
    mock_document_store: RedisDocumentStore,
    mock_metadata_store: SourceMetadataStore,
    mock_connector_service: ConnectorService,
    mocker: MockerFixture,
) -> SourceSyncService:
    # Mock the OpenAI client creation
    mocker.patch(
        "src.sources.sync.get_embedding_openai_client",
        return_value=mock_openai_client,
    )

    # Mock RedisDocumentStore creation
    mocker.patch(
        "src.sources.sync.RedisDocumentStore",
        return_value=mock_document_store,
    )

    # Mock ConnectorService creation
    mocker.patch(
        "src.sources.sync.ConnectorService",
        return_value=mock_connector_service,
    )

    # Mock SourceMetadataStore creation
    mocker.patch(
        "src.sources.sync.SourceMetadataStore",
        return_value=mock_metadata_store,
    )

    return SourceSyncService(
        redis_client=mock_redis_client,
        source_name="test-source",
        connector_config=SitemapConfig(
            type=ConnectorType.SITEMAP,
            sitemap_url="https://example.com/sitemap.xml",
        ),
        settings=mock_settings,
    )


async def test_sync_documents_success(
    source_sync_service: SourceSyncService,
    sample_documents: list[Document],
    patch_extract_documents: AsyncMock,
    mock_current_datetime: str,
    mocker: MockerFixture,
) -> None:
    # Mock current datetime
    mocker.patch(
        "src.sources.sync.get_current_datetime",
        return_value=mock_current_datetime,
    )

    mocker.patch.object(
        source_sync_service.document_store,
        "get_document_ids",
        return_value=[],
    )

    # Mock document extraction
    await patch_extract_documents(source_sync_service, sample_documents)

    # Mock metadata updates
    mock_metadata = SourceMetadata(
        id="test-id",
        name="test-source",
        description="Test description",
        last_task_id="test-task-id",
        connector=source_sync_service.connector_config,
        num_docs=3,
        created_at=mock_current_datetime,
        updated_at=mock_current_datetime,
    )
    mock_update_metadata = mocker.patch.object(
        source_sync_service.metadata_store,
        "update_metadata",
        return_value=mock_metadata,
    )

    mock_add_documents_batch = mocker.patch.object(
        source_sync_service, "_add_documents_batch"
    )

    result = await source_sync_service.sync_documents()

    assert isinstance(result, SyncSourceOutput)
    assert result.source == mock_metadata
    assert result.docs_added == 3
    assert result.docs_removed == 0

    # Verify metadata updates
    mock_update_metadata.assert_called_with(
        name="test-source",
        updates=MetadataUpdate(
            num_docs=3,
        ),
        timestamp=mock_current_datetime,
    )

    # Verify document store operations
    assert mock_add_documents_batch.call_count == 2


async def test_sync_documents_with_existing_docs(
    source_sync_service: SourceSyncService,
    sample_documents: list[Document],
    patch_extract_documents: AsyncMock,
    mock_current_datetime: str,
    mocker: MockerFixture,
) -> None:
    # Set existing document IDs
    mocker.patch.object(
        source_sync_service.document_store,
        "get_document_ids",
        return_value=["doc1", "doc2"],
    )

    # Mock current datetime
    mocker.patch(
        "src.sources.sync.get_current_datetime",
        return_value=mock_current_datetime,
    )

    # Mock document extraction
    await patch_extract_documents(source_sync_service, sample_documents)

    # Mock metadata updates
    mock_metadata = SourceMetadata(
        id="test-id",
        name="test-source",
        description="Test description",
        last_task_id="test-task-id",
        connector=source_sync_service.connector_config,
        num_docs=3,
        created_at=mock_current_datetime,
        updated_at=mock_current_datetime,
    )
    mocker.patch.object(
        source_sync_service.metadata_store,
        "update_metadata",
        return_value=mock_metadata,
    )

    # Mock document store operations
    mock_add_documents = mocker.patch.object(
        source_sync_service.document_store, "add_documents"
    )

    result = await source_sync_service.sync_documents()

    assert result.docs_added == 1
    assert result.docs_removed == 0

    mock_add_documents.assert_called_once_with(
        "test-source",
        [sample_documents[2]],  # only doc3 should be added
    )


async def test_sync_documents_with_stale_docs(
    source_sync_service: SourceSyncService,
    sample_documents: list[Document],
    patch_extract_documents: AsyncMock,
    mock_current_datetime: str,
    mocker: MockerFixture,
) -> None:
    # Set existing document IDs including a stale one
    mocker.patch.object(
        source_sync_service.document_store,
        "get_document_ids",
        return_value=["doc1", "doc2", "doc3", "stale-doc"],
    )

    # Mock current datetime
    mocker.patch(
        "src.sources.sync.get_current_datetime",
        return_value=mock_current_datetime,
    )

    # Mock document extraction
    await patch_extract_documents(source_sync_service, sample_documents)

    # Mock metadata updates
    mock_metadata = SourceMetadata(
        id="test-id",
        name="test-source",
        description="Test description",
        last_task_id="test-task-id",
        connector=source_sync_service.connector_config,
        num_docs=3,
        created_at=mock_current_datetime,
        updated_at=mock_current_datetime,
    )
    mocker.patch.object(
        source_sync_service.metadata_store,
        "update_metadata",
        return_value=mock_metadata,
    )

    mock_delete_documents = mocker.patch.object(
        source_sync_service.document_store, "delete_documents"
    )

    result = await source_sync_service.sync_documents()

    assert result.docs_added == 0
    assert result.docs_removed == 1

    mock_delete_documents.assert_called_once_with("test-source", ["stale-doc"])


async def test_sync_documents_failure_handling(
    source_sync_service: SourceSyncService,
    mock_current_datetime: str,
    mocker: MockerFixture,
) -> None:
    # Mock current datetime
    mocker.patch(
        "src.sources.sync.get_current_datetime",
        return_value=mock_current_datetime,
    )

    mocker.patch.object(
        source_sync_service.document_store,
        "get_document_ids",
        return_value=[],
    )

    # Mock document extraction to raise an exception
    mock_extract = AsyncMock()
    mock_extract.__aiter__.side_effect = Exception("Extraction failed")
    mocker.patch.object(
        source_sync_service.connector_service,
        "extract_documents",
        return_value=mock_extract,
    )

    with pytest.raises(Exception) as exc:
        await source_sync_service.sync_documents()

    assert str(exc.value) == "Extraction failed"


async def test_add_documents_batch_failure(
    source_sync_service: SourceSyncService,
    sample_documents: list[Document],
    mock_current_datetime: str,
    mocker: MockerFixture,
) -> None:
    # Mock current datetime
    mocker.patch(
        "src.sources.sync.get_current_datetime",
        return_value=mock_current_datetime,
    )

    # Mock document store to raise an exception
    mocker.patch.object(
        source_sync_service.document_store,
        "add_documents",
        side_effect=Exception("Failed to add documents"),
    )

    with pytest.raises(SyncSourceException) as exc:
        await source_sync_service._add_documents_batch(sample_documents, 0)  # type: ignore

    assert str(exc.value) == "Failed to sync documents for source test-source"


async def test_remove_stale_documents_failure(
    source_sync_service: SourceSyncService,
    mock_current_datetime: str,
    mocker: MockerFixture,
) -> None:
    # Mock current datetime
    mocker.patch(
        "src.sources.sync.get_current_datetime",
        return_value=mock_current_datetime,
    )

    # Mock document store to raise an exception
    mocker.patch.object(
        source_sync_service.document_store,
        "delete_documents",
        side_effect=Exception("Failed to remove documents"),
    )

    doc_ids_to_remove: Set[str] = {"stale1", "stale2"}

    with pytest.raises(SyncSourceException) as exc:
        await source_sync_service._remove_stale_documents(doc_ids_to_remove, 0)  # type: ignore

    assert str(exc.value) == "Failed to sync documents for source test-source"
