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
from src.source.config import SitemapConfig, SourceType
from src.source.schemas import (
    CreateSourceRequest,
    SearchSourceInput,
    SourceMetadata,
    SourceStatus,
    SourceTask,
    UpdateSourceRequest,
)
from src.source.service import SourceService
from src.source.metadata import SourceMetadataManager
from src.document_store.base import DocumentStoreService
from src.lock.service import LockService


@pytest.fixture
def mock_metadata_manager(mocker: MockerFixture) -> SourceMetadataManager:
    return mocker.Mock(spec=SourceMetadataManager)


@pytest.fixture
def mock_document_store(mocker: MockerFixture) -> DocumentStoreService:
    return mocker.Mock(spec=DocumentStoreService)


@pytest.fixture
def mock_lock_service(mocker: MockerFixture) -> LockService:
    return mocker.Mock(spec=LockService)


@pytest.fixture
def source_service(
    mock_metadata_manager: SourceMetadataManager,
    mock_document_store: DocumentStoreService,
    mock_lock_service: LockService,
) -> SourceService:
    return SourceService(
        metadata_manager=mock_metadata_manager,
        document_store=mock_document_store,
        lock_service=mock_lock_service,
    )


@pytest.fixture
def mock_current_time() -> str:
    return datetime(2024, 1, 1, 12, 0, 0).isoformat()


@pytest.fixture
def sample_source_metadata() -> SourceMetadata:
    return SourceMetadata(
        id="test-id",
        name="test-source",
        description="Test source description",
        status=SourceStatus.PENDING,
        config=SitemapConfig(
            type=SourceType.SITEMAP,
            sitemap_url="https://example.com/sitemap.xml",
        ),
        num_docs=0,
        created_at="2024-01-01T12:00:00",
        updated_at="2024-01-01T12:00:00",
    )


@pytest.fixture
def sample_create_request() -> CreateSourceRequest:
    return CreateSourceRequest(
        name="test-source",
        description="Test source description",
        config=SitemapConfig(
            type=SourceType.SITEMAP,
            sitemap_url="https://example.com/sitemap.xml",
        ),
    )


@pytest.fixture
def sample_update_request() -> UpdateSourceRequest:
    return UpdateSourceRequest(
        description="Updated description",
        config=SitemapConfig(
            type=SourceType.SITEMAP,
            sitemap_url="https://example.com/sitemap.xml",
        ),
        sync=True,
    )


async def test_create_source_success(
    source_service: SourceService,
    sample_create_request: CreateSourceRequest,
    sample_source_metadata: SourceMetadata,
    mock_current_time: str,
    mocker: MockerFixture,
) -> None:
    # Mock UUID generation
    mock_uuid = UUID("12345678-1234-5678-1234-567812345678")
    mocker.patch("src.source.service.uuid4", return_value=mock_uuid)

    # Mock current datetime
    mocker.patch(
        "src.source.service.get_current_datetime",
        return_value=mock_current_time,
    )

    # Mock celery task
    mock_task = mocker.Mock()
    mock_task.id = "task-id"
    mocker.patch(
        "src.source.service.sync_source_documents_task.delay",
        return_value=mock_task,
    )

    # Mock metadata manager
    mocker.patch.object(
        source_service.metadata_manager, "metadata_exists", return_value=False
    )
    mock_create_metadata = mocker.patch.object(
        source_service.metadata_manager,
        "create_metadata",
        return_value=sample_source_metadata,
    )

    result = source_service.create_source(sample_create_request)

    assert isinstance(result, SourceTask)
    assert result.task_id == "task-id"
    assert result.source == sample_source_metadata
    assert result.message == "Source created. Syncing documents..."

    mock_create_metadata.assert_called_once_with(
        source_name=sample_create_request.name,
        description=sample_create_request.description,
        status=SourceStatus.PENDING,
        config=sample_create_request.config,
        id=str(mock_uuid),
        created_at=mock_current_time,
        updated_at=mock_current_time,
    )


async def test_create_source_already_exists(
    source_service: SourceService,
    sample_create_request: CreateSourceRequest,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        source_service.metadata_manager, "metadata_exists", return_value=True
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
        source_service.metadata_manager, "metadata_exists", return_value=True
    )
    mock_get_metadata = mocker.patch.object(
        source_service.metadata_manager,
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
        source_service.metadata_manager, "metadata_exists", return_value=False
    )

    with pytest.raises(ResourceNotFoundException) as exc:
        source_service.get_source("test-source")

    assert exc.value.resource_type == ResourceType.SOURCE
    assert exc.value.identifier == "test-source"


async def test_update_source_success(
    source_service: SourceService,
    sample_update_request: UpdateSourceRequest,
    sample_source_metadata: SourceMetadata,
    mock_current_time: str,
    mocker: MockerFixture,
) -> None:
    # Mock existing document IDs
    existing_doc_ids = ["doc1", "doc2"]
    mocker.patch.object(
        source_service.document_store, "get_document_ids", return_value=existing_doc_ids
    )

    # Mock current datetime
    mocker.patch(
        "src.source.service.get_current_datetime",
        return_value=mock_current_time,
    )

    # Mock lock service
    mocker.patch.object(source_service.lock_service, "lock_exists", return_value=False)

    # Mock sync task
    mock_task = mocker.Mock()
    mock_task.id = "task-id"
    mock_sync_source = mocker.patch(
        "src.source.service.sync_source_documents_task.delay",
        return_value=mock_task,
    )

    # Mock metadata manager
    mocker.patch.object(
        source_service.metadata_manager, "metadata_exists", return_value=True
    )
    mock_update_metadata = mocker.patch.object(
        source_service.metadata_manager,
        "update_metadata",
        return_value=sample_source_metadata,
    )

    result = source_service.update_source("test-source", sample_update_request)

    assert isinstance(result, SourceTask)
    assert result.task_id == "task-id"
    assert result.source == sample_source_metadata
    assert result.message == "Source updated. Syncing documents..."

    assert sample_update_request.config is not None  # For type checking

    mock_sync_source.assert_called_once_with(
        source_name="test-source",
        source_config_dict=sample_update_request.config.model_dump(),
        existing_doc_ids=existing_doc_ids,
    )

    mock_update_metadata.assert_called_once_with(
        name="test-source",
        description=sample_update_request.description,
        status=SourceStatus.PENDING,
        config=sample_update_request.config,
        timestamp=mock_current_time,
    )


async def test_update_source_locked(
    source_service: SourceService,
    sample_update_request: UpdateSourceRequest,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        source_service.metadata_manager, "metadata_exists", return_value=True
    )
    mocker.patch.object(source_service.lock_service, "lock_exists", return_value=True)

    with pytest.raises(ResourceLockedException) as exc:
        source_service.update_source("test-source", sample_update_request)

    assert exc.value.resource_type == ResourceType.SOURCE
    assert exc.value.identifier == "test-source"


async def test_update_source_no_sync(
    source_service: SourceService,
    sample_source_metadata: SourceMetadata,
    mock_current_time: str,
    mocker: MockerFixture,
) -> None:
    request_no_sync = UpdateSourceRequest(
        description="Updated description without sync",
        config=SitemapConfig(
            type=SourceType.SITEMAP,
            sitemap_url="https://example.com/sitemap.xml",
        ),
        sync=False,
    )

    # Mock lock service
    mocker.patch.object(source_service.lock_service, "lock_exists", return_value=False)

    # Mock current datetime
    mocker.patch(
        "src.source.service.get_current_datetime",
        return_value=mock_current_time,
    )

    # Mock metadata manager
    mocker.patch.object(
        source_service.metadata_manager, "metadata_exists", return_value=True
    )
    mock_update_metadata = mocker.patch.object(
        source_service.metadata_manager,
        "update_metadata",
        return_value=sample_source_metadata,
    )

    # Mock sync task
    mock_sync_task = mocker.patch("src.source.service.sync_source_documents_task.delay")

    result = source_service.update_source("test-source", request_no_sync)

    assert isinstance(result, SourceTask)
    # With no sync, the task_id should be None
    assert result.task_id is None
    assert result.source == sample_source_metadata
    assert result.message == "Source updated."

    mock_update_metadata.assert_called_once_with(
        name="test-source",
        description="Updated description without sync",
        status=None,
        config=request_no_sync.config,
        timestamp=mock_current_time,
    )

    # Ensure the sync task was not called
    mock_sync_task.assert_not_called()


async def test_update_source_no_description_no_config(
    source_service: SourceService,
    sample_source_metadata: SourceMetadata,
    mock_current_time: str,
    mocker: MockerFixture,
) -> None:
    request_only_sync = UpdateSourceRequest(sync=True)

    # Mock lock service
    mocker.patch.object(source_service.lock_service, "lock_exists", return_value=False)

    # Mock existing document IDs
    existing_doc_ids = ["doc1", "doc2"]
    mocker.patch.object(
        source_service.document_store, "get_document_ids", return_value=existing_doc_ids
    )

    # Mock current datetime
    mocker.patch(
        "src.source.service.get_current_datetime",
        return_value=mock_current_time,
    )

    # Mock metadata manager
    mocker.patch.object(
        source_service.metadata_manager, "metadata_exists", return_value=True
    )
    mock_update_metadata = mocker.patch.object(
        source_service.metadata_manager,
        "update_metadata",
        return_value=sample_source_metadata,
    )

    # Mock sync task
    mock_task = mocker.Mock()
    mock_task.id = "task-id"
    mock_sync_task = mocker.patch(
        "src.source.service.sync_source_documents_task.delay",
        return_value=mock_task,
    )

    result = source_service.update_source("test-source", request_only_sync)

    assert isinstance(result, SourceTask)
    assert result.task_id == "task-id"
    assert result.source == sample_source_metadata
    assert result.message == "Source updated. Syncing documents..."

    mock_update_metadata.assert_called_once_with(
        name="test-source",
        description=None,  # Because request_only_sync has no description
        status=SourceStatus.PENDING,  # Because sync=True => set to PENDING
        config=None,  # Because request_only_sync has no config
        timestamp=mock_current_time,
    )
    mock_sync_task.assert_called_once_with(
        source_name="test-source",
        source_config_dict=sample_source_metadata.config.model_dump(),
        existing_doc_ids=existing_doc_ids,
    )


async def test_search_source_success(
    source_service: SourceService,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        source_service.metadata_manager, "metadata_exists", return_value=True
    )
    mock_results = [{"id": "doc1"}, {"id": "doc2"}]
    mock_search_documents = mocker.patch.object(
        source_service.document_store, "search_documents", return_value=mock_results
    )

    search_input = SearchSourceInput(name="test-source", query="test query", top_k=2)
    result = source_service.search_source(search_input)

    assert result == mock_results
    mock_search_documents.assert_called_once_with("test-source", "test query", 2)


async def test_delete_source_success(
    source_service: SourceService,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        source_service.metadata_manager, "metadata_exists", return_value=True
    )
    mock_delete_metadata = mocker.patch.object(
        source_service.metadata_manager, "delete_metadata"
    )
    mock_delete_documents = mocker.patch.object(
        source_service.document_store, "delete_all_documents"
    )

    source_service.delete_source("test-source")

    mock_delete_metadata.assert_called_once_with("test-source")
    mock_delete_documents.assert_called_once_with("test-source")
