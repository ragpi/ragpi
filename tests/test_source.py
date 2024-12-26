import pytest
from unittest.mock import Mock, patch
from src.source.service import SourceService
from src.source.metadata import SourceMetadataManager
from src.document_store.base import DocumentStoreService
from src.lock.service import LockService
from src.common.exceptions import ResourceAlreadyExistsException, ResourceNotFoundException, ResourceLockedException
from src.source.schemas import CreateSourceRequest, UpdateSourceRequest, SourceStatus, SourceTask
from src.task.sync_source import sync_source_documents_task
from src.source.utils import get_current_datetime
from uuid import uuid4

@pytest.fixture
def mock_metadata_manager():
    return Mock(spec=SourceMetadataManager)

@pytest.fixture
def mock_document_store():
    return Mock(spec=DocumentStoreService)

@pytest.fixture
def mock_lock_service():
    return Mock(spec=LockService)

@pytest.fixture
def source_service(mock_metadata_manager, mock_document_store, mock_lock_service):
    return SourceService(
        metadata_manager=mock_metadata_manager,
        document_store=mock_document_store,
        lock_service=mock_lock_service,
    )

def test_create_source(source_service, mock_metadata_manager):
    source_input = CreateSourceRequest(
        name="test_source",
        description="Test description",
        config=Mock()
    )

    mock_metadata_manager.metadata_exists.return_value = False
    mock_metadata_manager.create_metadata.return_value = Mock()

    with patch("src.task.sync_source.sync_source_documents_task.delay") as mock_task:
        mock_task.return_value.id = "task_id"
        result = source_service.create_source(source_input)

    assert isinstance(result, SourceTask)
    assert result.task_id == "task_id"
    mock_metadata_manager.create_metadata.assert_called_once()

def test_create_source_already_exists(source_service, mock_metadata_manager):
    source_input = CreateSourceRequest(
        name="test_source",
        description="Test description",
        config=Mock()
    )

    mock_metadata_manager.metadata_exists.return_value = True

    with pytest.raises(ResourceAlreadyExistsException):
        source_service.create_source(source_input)

def test_get_source(source_service, mock_metadata_manager):
    mock_metadata_manager.metadata_exists.return_value = True
    mock_metadata_manager.get_metadata.return_value = Mock()

    result = source_service.get_source("test_source")

    assert result is not None
    mock_metadata_manager.get_metadata.assert_called_once_with("test_source")

def test_get_source_not_found(source_service, mock_metadata_manager):
    mock_metadata_manager.metadata_exists.return_value = False

    with pytest.raises(ResourceNotFoundException):
        source_service.get_source("test_source")

def test_update_source(source_service, mock_metadata_manager, mock_document_store, mock_lock_service):
    source_input = UpdateSourceRequest(
        sync=True,
        description="Updated description",
        config=Mock()
    )

    mock_metadata_manager.metadata_exists.return_value = True
    mock_lock_service.lock_exists.return_value = False
    mock_document_store.get_document_ids.return_value = []
    mock_metadata_manager.update_metadata.return_value = Mock()

    with patch("src.task.sync_source.sync_source_documents_task.delay") as mock_task:
        mock_task.return_value.id = "task_id"
        result = source_service.update_source("test_source", source_input)

    assert isinstance(result, SourceTask)
    assert result.task_id == "task_id"
    mock_metadata_manager.update_metadata.assert_called_once()

def test_update_source_not_found(source_service, mock_metadata_manager):
    source_input = UpdateSourceRequest(
        sync=True,
        description="Updated description",
        config=Mock()
    )

    mock_metadata_manager.metadata_exists.return_value = False

    with pytest.raises(ResourceNotFoundException):
        source_service.update_source("test_source", source_input)

def test_update_source_locked(source_service, mock_metadata_manager, mock_lock_service):
    source_input = UpdateSourceRequest(
        sync=True,
        description="Updated description",
        config=Mock()
    )

    mock_metadata_manager.metadata_exists.return_value = True
    mock_lock_service.lock_exists.return_value = True

    with pytest.raises(ResourceLockedException):
        source_service.update_source("test_source", source_input)

def test_get_source_documents(source_service, mock_metadata_manager, mock_document_store):
    mock_metadata_manager.metadata_exists.return_value = True
    mock_document_store.get_documents.return_value = []

    result = source_service.get_source_documents("test_source", limit=10, offset=0)

    assert result == []
    mock_document_store.get_documents.assert_called_once_with("test_source", 10, 0)

def test_get_source_documents_not_found(source_service, mock_metadata_manager):
    mock_metadata_manager.metadata_exists.return_value = False

    with pytest.raises(ResourceNotFoundException):
        source_service.get_source_documents("test_source", limit=10, offset=0)

def test_get_all_sources(source_service, mock_metadata_manager):
    mock_metadata_manager.get_all_metadata.return_value = []

    result = source_service.get_all_sources()

    assert result == []
    mock_metadata_manager.get_all_metadata.assert_called_once()

def test_delete_source(source_service, mock_metadata_manager, mock_document_store):
    mock_metadata_manager.metadata_exists.return_value = True

    source_service.delete_source("test_source")

    mock_document_store.delete_all_documents.assert_called_once_with("test_source")
    mock_metadata_manager.delete_metadata.assert_called_once_with("test_source")

def test_delete_source_not_found(source_service, mock_metadata_manager):
    mock_metadata_manager.metadata_exists.return_value = False

    with pytest.raises(ResourceNotFoundException):
        source_service.delete_source("test_source")

def test_search_source(source_service, mock_metadata_manager, mock_document_store):
    mock_metadata_manager.metadata_exists.return_value = True
    mock_document_store.search_documents.return_value = []

    result = source_service.search_source(Mock(name="test_source", query="test_query", top_k=10))

    assert result == []
    mock_document_store.search_documents.assert_called_once_with("test_source", "test_query", 10)

def test_search_source_not_found(source_service, mock_metadata_manager):
    mock_metadata_manager.metadata_exists.return_value = False

    with pytest.raises(ResourceNotFoundException):
        source_service.search_source(Mock(name="test_source", query="test_query", top_k=10))
