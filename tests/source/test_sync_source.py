from unittest.mock import AsyncMock
from openai import OpenAI
import pytest
from datetime import datetime
from pytest_mock import MockerFixture
from typing import AsyncIterator, Set

from src.common.redis import RedisClient
from src.common.schemas import Document
from src.config import Settings
from src.document_extractor.service import DocumentExtractor
from src.document_store.providers.redis.store import RedisDocumentStore
from src.source.exceptions import SyncSourceException
from src.source.config import SourceConfig, SitemapConfig, SourceType
from src.source.metadata import SourceMetadataManager
from src.source.schemas import SourceMetadata, SourceStatus, SyncSourceOutput
from src.source.sync import SourceSyncService


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
def mock_metadata_manager(mocker: MockerFixture) -> SourceMetadataManager:
    return mocker.Mock(spec=SourceMetadataManager)


@pytest.fixture
def mock_document_extractor(mocker: MockerFixture) -> DocumentExtractor:
    return mocker.Mock(spec=DocumentExtractor)


@pytest.fixture
def sample_source_config() -> SourceConfig:
    return SitemapConfig(
        type=SourceType.SITEMAP,
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
        async def _doc_generator(_: SourceConfig) -> AsyncIterator[Document]:
            for doc in documents:
                yield doc

        mocker.patch.object(
            source_sync_service.document_extractor,
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
    mock_metadata_manager: SourceMetadataManager,
    mock_document_extractor: DocumentExtractor,
    mocker: MockerFixture,
) -> SourceSyncService:
    # Mock the OpenAI client creation
    mocker.patch(
        "src.source.sync.get_openai_client",
        return_value=mock_openai_client,
    )

    # Mock RedisDocumentStore creation
    mocker.patch(
        "src.source.sync.RedisDocumentStore",
        return_value=mock_document_store,
    )

    # Mock DocumentExtractor creation
    mocker.patch(
        "src.source.sync.DocumentExtractor",
        return_value=mock_document_extractor,
    )

    # Mock SourceMetadataManager creation
    mocker.patch(
        "src.source.sync.SourceMetadataManager",
        return_value=mock_metadata_manager,
    )

    return SourceSyncService(
        redis_client=mock_redis_client,
        source_name="test-source",
        config_map={"sitemap": SitemapConfig},
        source_config=SitemapConfig(
            type=SourceType.SITEMAP,
            sitemap_url="https://example.com/sitemap.xml",
        ),
        existing_doc_ids=set(),
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
        "src.source.sync.get_current_datetime",
        return_value=mock_current_datetime,
    )

    # Mock document extraction
    await patch_extract_documents(source_sync_service, sample_documents)

    # Mock metadata updates
    mock_metadata = SourceMetadata(
        id="test-id",
        name="test-source",
        description="Test description",
        status=SourceStatus.COMPLETED,
        config=source_sync_service.source_config,
        num_docs=3,
        created_at=mock_current_datetime,
        updated_at=mock_current_datetime,
    )
    mock_update_metadata = mocker.patch.object(
        source_sync_service.metadata_manager,
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
    assert mock_update_metadata.call_count == 2
    mock_update_metadata.assert_any_call(
        name="test-source",
        description=None,
        status=SourceStatus.SYNCING,
        config=None,
        timestamp=mock_current_datetime,
    )
    mock_update_metadata.assert_called_with(
        name="test-source",
        description=None,
        status=SourceStatus.COMPLETED,
        config=None,
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
    source_sync_service.existing_doc_ids = {"doc1", "doc2"}

    # Mock current datetime
    mocker.patch(
        "src.source.sync.get_current_datetime",
        return_value=mock_current_datetime,
    )

    # Mock document extraction
    await patch_extract_documents(source_sync_service, sample_documents)

    # Mock metadata updates
    mock_metadata = SourceMetadata(
        id="test-id",
        name="test-source",
        description="Test description",
        status=SourceStatus.COMPLETED,
        config=source_sync_service.source_config,
        num_docs=3,
        created_at=mock_current_datetime,
        updated_at=mock_current_datetime,
    )
    mocker.patch.object(
        source_sync_service.metadata_manager,
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
    source_sync_service.existing_doc_ids = {"doc1", "doc2", "doc3", "stale-doc"}

    # Mock current datetime
    mocker.patch(
        "src.source.sync.get_current_datetime",
        return_value=mock_current_datetime,
    )

    # Mock document extraction
    await patch_extract_documents(source_sync_service, sample_documents)

    # Mock metadata updates
    mock_metadata = SourceMetadata(
        id="test-id",
        name="test-source",
        description="Test description",
        status=SourceStatus.COMPLETED,
        config=source_sync_service.source_config,
        num_docs=3,
        created_at=mock_current_datetime,
        updated_at=mock_current_datetime,
    )
    mocker.patch.object(
        source_sync_service.metadata_manager,
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
        "src.source.sync.get_current_datetime",
        return_value=mock_current_datetime,
    )

    # Mock document extraction to raise an exception
    mock_extract = AsyncMock()
    mock_extract.__aiter__.side_effect = Exception("Extraction failed")
    mocker.patch.object(
        source_sync_service.document_extractor,
        "extract_documents",
        return_value=mock_extract,
    )

    # Mock metadata updates
    mock_metadata = SourceMetadata(
        id="test-id",
        name="test-source",
        description="Test description",
        status=SourceStatus.FAILED,
        config=source_sync_service.source_config,
        num_docs=0,
        created_at=mock_current_datetime,
        updated_at=mock_current_datetime,
    )
    mock_update_metadata = mocker.patch.object(
        source_sync_service.metadata_manager,
        "update_metadata",
        return_value=mock_metadata,
    )

    with pytest.raises(Exception) as exc:
        await source_sync_service.sync_documents()

    assert str(exc.value) == "Extraction failed"
    mock_update_metadata.assert_called_with(
        name="test-source",
        description=None,
        status=SourceStatus.FAILED,
        config=None,
        timestamp=mock_current_datetime,
    )


async def test_add_documents_batch_failure(
    source_sync_service: SourceSyncService,
    sample_documents: list[Document],
    mock_current_datetime: str,
    mocker: MockerFixture,
) -> None:
    # Mock current datetime
    mocker.patch(
        "src.source.sync.get_current_datetime",
        return_value=mock_current_datetime,
    )

    # Mock document store to raise an exception
    mocker.patch.object(
        source_sync_service.document_store,
        "add_documents",
        side_effect=Exception("Failed to add documents"),
    )

    with pytest.raises(SyncSourceException) as exc:
        await source_sync_service._add_documents_batch(sample_documents)  # type: ignore

    assert str(exc.value) == "Failed to sync documents for source test-source"


async def test_remove_stale_documents_failure(
    source_sync_service: SourceSyncService,
    mock_current_datetime: str,
    mocker: MockerFixture,
) -> None:
    # Mock current datetime
    mocker.patch(
        "src.source.sync.get_current_datetime",
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
        await source_sync_service._remove_stale_documents(doc_ids_to_remove)  # type: ignore

    assert str(exc.value) == "Failed to sync documents for source test-source"
