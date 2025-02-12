from unittest.mock import AsyncMock
from openai import OpenAI
import pytest
from datetime import datetime
from pytest_mock import MockerFixture
from typing import AsyncIterator, Set

from src.common.redis import RedisClient
from src.document_store.schemas import Document
from src.config import Settings
from src.connectors.common.schemas import ExtractedDocument
from src.document_store.base import DocumentStoreBackend
from src.sources.exceptions import SyncSourceException
from src.connectors.service import ConnectorService
from src.connectors.connector_type import ConnectorType
from src.connectors.registry import ConnectorConfig
from src.connectors.sitemap.config import SitemapConfig
from src.sources.metadata.base import SourceMetadataStore
from src.sources.metadata.schemas import MetadataUpdate, SourceMetadata
from src.sources.schemas import SyncSourceOutput
from src.sources.sync.service import SourceSyncService


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
    settings.DOCUMENT_UUID_NAMESPACE = "ee747eb2-fd0f-4650-9785-a2e9ae036ff2"
    return settings


@pytest.fixture
def mock_current_datetime() -> datetime:
    return datetime(2024, 1, 1, 12, 0, 0)


@pytest.fixture
def mock_openai_client(mocker: MockerFixture) -> OpenAI:
    return mocker.Mock(spec=OpenAI)


@pytest.fixture
def mock_document_store(mocker: MockerFixture) -> DocumentStoreBackend:
    return mocker.Mock(spec=DocumentStoreBackend)


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
    mock_document_store: DocumentStoreBackend,
    mock_metadata_store: SourceMetadataStore,
    mock_connector_service: ConnectorService,
    mocker: MockerFixture,
) -> SourceSyncService:
    # Mock the OpenAI client creation
    mocker.patch(
        "src.sources.sync.service.get_embedding_openai_client",
        return_value=mock_openai_client,
    )

    # Mock DocumentStoreBackend creation
    mocker.patch(
        "src.sources.sync.service.get_document_store_backend",
        return_value=mock_document_store,
    )

    # Mock ConnectorService creation
    mocker.patch(
        "src.sources.sync.service.ConnectorService",
        return_value=mock_connector_service,
    )

    # Mock SourceMetadataStore creation
    mocker.patch(
        "src.sources.sync.service.get_metadata_store_backend",
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


@pytest.fixture
def sample_extracted_documents() -> list[ExtractedDocument]:
    return [
        ExtractedDocument(
            title="Test title 1",
            content="Test content 1",
            url="https://example.com/1",
        ),
        ExtractedDocument(
            title="Test title 2",
            content="Test content 2",
            url="https://example.com/2",
        ),
        ExtractedDocument(
            title="Test title 3",
            content="Test content 3",
            url="https://example.com/3",
        ),
    ]


@pytest.fixture
def sample_documents(
    source_sync_service: SourceSyncService,
    mock_current_datetime: datetime,
    sample_extracted_documents: list[ExtractedDocument],
) -> list[Document]:
    return [
        Document(
            **sample_extracted_documents[0].model_dump(),
            created_at=mock_current_datetime,
            id=source_sync_service._generate_stable_id(  # type: ignore
                sample_extracted_documents[0].title,
                sample_extracted_documents[0].content,
            ),
        ),
        Document(
            **sample_extracted_documents[1].model_dump(),
            created_at=mock_current_datetime,
            id=source_sync_service._generate_stable_id(  # type: ignore
                sample_extracted_documents[1].title,
                sample_extracted_documents[1].content,
            ),
        ),
        Document(
            **sample_extracted_documents[2].model_dump(),
            created_at=mock_current_datetime,
            id=source_sync_service._generate_stable_id(  # type: ignore
                sample_extracted_documents[2].title,
                sample_extracted_documents[2].content,
            ),
        ),
    ]


async def test_sync_documents_success(
    source_sync_service: SourceSyncService,
    sample_extracted_documents: list[ExtractedDocument],
    patch_extract_documents: AsyncMock,
    mock_current_datetime: datetime,
    mocker: MockerFixture,
) -> None:
    # Mock current datetime
    mocker.patch(
        "src.sources.sync.service.get_current_datetime",
        return_value=mock_current_datetime,
    )

    mocker.patch.object(
        source_sync_service.document_store,
        "get_document_ids",
        return_value=[],
    )

    # Mock document extraction
    await patch_extract_documents(source_sync_service, sample_extracted_documents)

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
    sample_extracted_documents: list[ExtractedDocument],
    sample_documents: list[Document],
    patch_extract_documents: AsyncMock,
    mock_current_datetime: datetime,
    mocker: MockerFixture,
) -> None:
    # Set existing document IDs
    mocker.patch.object(
        source_sync_service.document_store,
        "get_document_ids",
        # Only doc1 and doc2 are in the store
        return_value=[sample_documents[0].id, sample_documents[1].id],
    )

    # Mock current datetime
    mocker.patch(
        "src.sources.sync.service.get_current_datetime",
        return_value=mock_current_datetime,
    )

    # Mock document extraction
    await patch_extract_documents(source_sync_service, sample_extracted_documents)

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
        [sample_documents[2]],  # Only doc3 should be added
    )


async def test_sync_documents_with_stale_docs(
    source_sync_service: SourceSyncService,
    sample_extracted_documents: list[ExtractedDocument],
    sample_documents: list[Document],
    patch_extract_documents: AsyncMock,
    mock_current_datetime: datetime,
    mocker: MockerFixture,
) -> None:
    # Set existing document IDs including a stale one
    mocker.patch.object(
        source_sync_service.document_store,
        "get_document_ids",
        return_value=[doc.id for doc in sample_documents] + ["stale-doc"],
    )

    # Mock current datetime
    mocker.patch(
        "src.sources.sync.service.get_current_datetime",
        return_value=mock_current_datetime,
    )

    # Mock document extraction
    await patch_extract_documents(source_sync_service, sample_extracted_documents)

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
    mock_current_datetime: datetime,
    mocker: MockerFixture,
) -> None:
    # Mock current datetime
    mocker.patch(
        "src.sources.sync.service.get_current_datetime",
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
    sample_extracted_documents: list[ExtractedDocument],
    mock_current_datetime: datetime,
    mocker: MockerFixture,
) -> None:
    # Mock current datetime
    mocker.patch(
        "src.sources.sync.service.get_current_datetime",
        return_value=mock_current_datetime,
    )

    # Mock document store to raise an exception
    mocker.patch.object(
        source_sync_service.document_store,
        "add_documents",
        side_effect=Exception("Failed to add documents"),
    )

    with pytest.raises(SyncSourceException) as exc:
        await source_sync_service._add_documents_batch(sample_extracted_documents, 0)  # type: ignore

    assert str(exc.value) == "Failed to add batch of documents to source test-source"


async def test_remove_stale_documents_failure(
    source_sync_service: SourceSyncService,
    mock_current_datetime: datetime,
    mocker: MockerFixture,
) -> None:
    # Mock current datetime
    mocker.patch(
        "src.sources.sync.service.get_current_datetime",
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

    assert str(exc.value) == "Failed to remove documents from source test-source"
