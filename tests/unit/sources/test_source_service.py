import pytest
from datetime import datetime
from pytest_mock import MockerFixture
from uuid import UUID

from src.common.exceptions import (
    ResourceAlreadyExistsException,
    ResourceLockedException,
    ResourceNotFoundException,
    ResourceType,
)
from src.connectors.connector_type import ConnectorType
from src.connectors.sitemap.config import SitemapConfig
from src.sources.metadata.schemas import MetadataUpdate, SourceMetadata
from src.sources.schemas import (
    CreateSourceRequest,
    SourceTask,
    UpdateSourceRequest,
)
from src.sources.service import SourceService
from src.sources.metadata.base import SourceMetadataStore
from src.document_store.base import DocumentStoreBackend
from src.lock.service import LockService


@pytest.fixture
def mock_metadata_store(mocker: MockerFixture) -> SourceMetadataStore:
    return mocker.Mock(spec=SourceMetadataStore)


@pytest.fixture
def mock_document_store(mocker: MockerFixture) -> DocumentStoreBackend:
    return mocker.Mock(spec=DocumentStoreBackend)


@pytest.fixture
def mock_lock_service(mocker: MockerFixture) -> LockService:
    return mocker.Mock(spec=LockService)


@pytest.fixture
def source_service(
    mock_metadata_store: SourceMetadataStore,
    mock_document_store: DocumentStoreBackend,
    mock_lock_service: LockService,
) -> SourceService:
    return SourceService(
        metadata_store=mock_metadata_store,
        document_store=mock_document_store,
        lock_service=mock_lock_service,
    )


@pytest.fixture
def mock_current_datetime() -> str:
    return datetime(2024, 1, 1, 12, 0, 0).isoformat()


@pytest.fixture
def sample_source_metadata() -> SourceMetadata:
    return SourceMetadata(
        id="test-id",
        name="test-source",
        description="Test source description",
        last_task_id="test-task-id",
        connector=SitemapConfig(
            type=ConnectorType.SITEMAP,
            sitemap_url="https://example.com/sitemap.xml",
        ),
        num_docs=0,
        created_at=datetime(2024, 1, 1, 12, 0, 0),
        updated_at=datetime(2024, 1, 1, 12, 0, 0),
    )


@pytest.fixture
def sample_create_request() -> CreateSourceRequest:
    return CreateSourceRequest(
        name="test-source",
        description="Test source description",
        connector=SitemapConfig(
            type=ConnectorType.SITEMAP,
            sitemap_url="https://example.com/sitemap.xml",
        ),
    )


@pytest.fixture
def sample_update_request() -> UpdateSourceRequest:
    return UpdateSourceRequest(
        description="Updated description",
        connector=SitemapConfig(
            type=ConnectorType.SITEMAP,
            sitemap_url="https://example.com/sitemap.xml",
        ),
        sync=True,
    )


async def test_create_source_success(
    source_service: SourceService,
    sample_create_request: CreateSourceRequest,
    sample_source_metadata: SourceMetadata,
    mock_current_datetime: str,
    mocker: MockerFixture,
) -> None:
    # Mock UUID generation
    mock_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mocker.patch("src.sources.service.uuid4", return_value=mock_uuid)

    # Mock current datetime
    mocker.patch(
        "src.sources.service.get_current_datetime",
        return_value=mock_current_datetime,
    )

    # Mock celery task
    mock_task = mocker.Mock()
    mock_task.id = "task-id"
    mocker.patch(
        "src.sources.service.sync_source_documents_task.delay",
        return_value=mock_task,
    )

    # Mock metadata store
    mocker.patch.object(
        source_service.metadata_store, "metadata_exists", return_value=False
    )
    mock_create_metadata = mocker.patch.object(
        source_service.metadata_store,
        "create_metadata",
        return_value=sample_source_metadata,
    )
    mock_update_metadata = mocker.patch.object(
        source_service.metadata_store,
        "update_metadata",
        return_value=sample_source_metadata,
    )

    result = source_service.create_source(sample_create_request)

    assert isinstance(result, SourceTask)
    assert result.task_id == "task-id"
    assert result.source == sample_source_metadata
    assert result.message == "Source created. Syncing documents..."

    mock_create_metadata.assert_called_once_with(
        id=str(mock_uuid),
        source_name=sample_create_request.name,
        description=sample_create_request.description,
        connector=sample_create_request.connector,
        timestamp=mock_current_datetime,
    )

    mock_update_metadata.assert_called_once_with(
        name="test-source",
        updates=MetadataUpdate(
            last_task_id="task-id",
        ),
        timestamp=mock_current_datetime,
    )


async def test_create_source_already_exists(
    source_service: SourceService,
    sample_create_request: CreateSourceRequest,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        source_service.metadata_store, "metadata_exists", return_value=True
    )

    with pytest.raises(ResourceAlreadyExistsException) as exc:
        source_service.create_source(sample_create_request)

    assert exc.value.resource_type == ResourceType.SOURCE
    assert exc.value.identifier == sample_create_request.name


async def test_get_source_success(
    source_service: SourceService,
    sample_source_metadata: SourceMetadata,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        source_service.metadata_store, "metadata_exists", return_value=True
    )
    mock_get_metadata = mocker.patch.object(
        source_service.metadata_store,
        "get_metadata",
        return_value=sample_source_metadata,
    )

    result = source_service.get_source("test-source")

    assert result == sample_source_metadata
    mock_get_metadata.assert_called_once_with("test-source")


async def test_get_source_not_found(
    source_service: SourceService,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        source_service.metadata_store, "metadata_exists", return_value=False
    )

    with pytest.raises(ResourceNotFoundException) as exc:
        source_service.get_source("test-source")

    assert exc.value.resource_type == ResourceType.SOURCE
    assert exc.value.identifier == "test-source"


async def test_update_source_success(
    source_service: SourceService,
    sample_update_request: UpdateSourceRequest,
    sample_source_metadata: SourceMetadata,
    mock_current_datetime: str,
    mocker: MockerFixture,
) -> None:
    # Mock current datetime
    mocker.patch(
        "src.sources.service.get_current_datetime",
        return_value=mock_current_datetime,
    )

    # Mock lock service
    mocker.patch.object(source_service.lock_service, "lock_exists", return_value=False)

    # Mock sync task
    mock_task = mocker.Mock()
    mock_task.id = "task-id"
    mock_sync_source = mocker.patch(
        "src.sources.service.sync_source_documents_task.delay",
        return_value=mock_task,
    )

    # Mock metadata store
    mocker.patch.object(
        source_service.metadata_store, "metadata_exists", return_value=True
    )
    mock_update_metadata = mocker.patch.object(
        source_service.metadata_store,
        "update_metadata",
        return_value=sample_source_metadata,
    )

    result = source_service.update_source("test-source", sample_update_request)

    assert isinstance(result, SourceTask)
    assert result.task_id == "task-id"
    assert result.source == sample_source_metadata
    assert result.message == "Source updated. Syncing documents..."

    assert sample_update_request.connector is not None  # For type checking

    mock_sync_source.assert_called_once_with(
        source_name="test-source",
        connector_config_dict=sample_update_request.connector.model_dump(),
    )

    mock_update_metadata.assert_called_once_with(
        name="test-source",
        updates=MetadataUpdate(
            description=sample_update_request.description,
            last_task_id="task-id",
            connector=sample_update_request.connector,
        ),
        timestamp=mock_current_datetime,
    )


async def test_update_source_locked(
    source_service: SourceService,
    sample_update_request: UpdateSourceRequest,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        source_service.metadata_store, "metadata_exists", return_value=True
    )
    mocker.patch.object(source_service.lock_service, "lock_exists", return_value=True)

    with pytest.raises(ResourceLockedException) as exc:
        source_service.update_source("test-source", sample_update_request)

    assert exc.value.resource_type == ResourceType.SOURCE
    assert exc.value.identifier == "test-source"


async def test_update_source_no_sync(
    source_service: SourceService,
    sample_source_metadata: SourceMetadata,
    mock_current_datetime: str,
    mocker: MockerFixture,
) -> None:
    request_no_sync = UpdateSourceRequest(
        description="Updated description without sync",
        connector=SitemapConfig(
            type=ConnectorType.SITEMAP,
            sitemap_url="https://example.com/sitemap.xml",
        ),
        sync=False,
    )

    # Mock lock service
    mocker.patch.object(source_service.lock_service, "lock_exists", return_value=False)

    # Mock current datetime
    mocker.patch(
        "src.sources.service.get_current_datetime",
        return_value=mock_current_datetime,
    )

    # Mock metadata store
    mocker.patch.object(
        source_service.metadata_store, "metadata_exists", return_value=True
    )
    mock_update_metadata = mocker.patch.object(
        source_service.metadata_store,
        "update_metadata",
        return_value=sample_source_metadata,
    )

    # Mock sync task
    mock_sync_task = mocker.patch(
        "src.sources.service.sync_source_documents_task.delay"
    )

    result = source_service.update_source("test-source", request_no_sync)

    assert isinstance(result, SourceTask)
    # With no sync, the task_id should be None
    assert result.task_id is None
    assert result.source == sample_source_metadata
    assert result.message == "Source updated."

    mock_update_metadata.assert_called_once_with(
        name="test-source",
        updates=MetadataUpdate(
            description="Updated description without sync",
            connector=request_no_sync.connector,
        ),
        timestamp=mock_current_datetime,
    )

    # Ensure the sync task was not called
    mock_sync_task.assert_not_called()


async def test_update_source_no_description_no_config(
    source_service: SourceService,
    sample_source_metadata: SourceMetadata,
    mock_current_datetime: str,
    mocker: MockerFixture,
) -> None:
    request_only_sync = UpdateSourceRequest(sync=True)

    # Mock lock service
    mocker.patch.object(source_service.lock_service, "lock_exists", return_value=False)

    # Mock current datetime
    mocker.patch(
        "src.sources.service.get_current_datetime",
        return_value=mock_current_datetime,
    )

    # Mock metadata store
    mocker.patch.object(
        source_service.metadata_store, "metadata_exists", return_value=True
    )
    mocker.patch.object(
        source_service.metadata_store,
        "get_metadata",
        return_value=sample_source_metadata,
    )
    mocker.patch.object(
        source_service.metadata_store,
        "update_metadata",
        return_value=sample_source_metadata,
    )

    # Mock sync task
    mock_task = mocker.Mock()
    mock_task.id = "task-id"
    mock_sync_task = mocker.patch(
        "src.sources.service.sync_source_documents_task.delay",
        return_value=mock_task,
    )

    result = source_service.update_source("test-source", request_only_sync)

    assert isinstance(result, SourceTask)
    assert result.task_id == "task-id"
    assert result.source == sample_source_metadata
    assert result.message == "Source updated. Syncing documents..."

    mock_sync_task.assert_called_once_with(
        source_name="test-source",
        connector_config_dict=sample_source_metadata.connector.model_dump(),
    )


async def test_search_source_success(
    source_service: SourceService,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        source_service.metadata_store, "metadata_exists", return_value=True
    )
    mock_results = [{"id": "doc1"}, {"id": "doc2"}]
    mock_hybrid_search = mocker.patch.object(
        source_service.document_store, "hybrid_search", return_value=mock_results
    )

    result = source_service.search_source(
        source_name="test-source",
        semantic_query="test semantic query",
        full_text_query="test full text query",
        top_k=2,
    )

    assert result == mock_results
    mock_hybrid_search.assert_called_once_with(
        source_name="test-source",
        semantic_query="test semantic query",
        full_text_query="test full text query",
        top_k=2,
    )


async def test_delete_source_success(
    source_service: SourceService,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        source_service.metadata_store, "metadata_exists", return_value=True
    )
    mocker.patch.object(source_service.lock_service, "lock_exists", return_value=False)
    mock_delete_metadata = mocker.patch.object(
        source_service.metadata_store, "delete_metadata"
    )
    mock_delete_documents = mocker.patch.object(
        source_service.document_store, "delete_all_documents"
    )

    source_service.delete_source("test-source")

    mock_delete_metadata.assert_called_once_with("test-source")
    mock_delete_documents.assert_called_once_with("test-source")
