import pytest
from unittest.mock import patch, MagicMock
from src.task.sync_source import sync_source_documents_task
from src.source.exceptions import SyncSourceException

@pytest.fixture
def mock_settings():
    with patch("src.task.sync_source.get_settings") as mock_get_settings:
        mock_settings = MagicMock()
        mock_get_settings.return_value = mock_settings
        yield mock_settings

@pytest.fixture
def mock_redis_client():
    with patch("src.task.sync_source.Redis.from_url") as mock_redis:
        mock_redis_client = MagicMock()
        mock_redis.return_value = mock_redis_client
        yield mock_redis_client

@pytest.fixture
def mock_lock_service():
    with patch("src.task.sync_source.LockService") as mock_lock_service:
        mock_lock_service_instance = MagicMock()
        mock_lock_service.return_value = mock_lock_service_instance
        yield mock_lock_service_instance

@pytest.fixture
def mock_source_sync_service():
    with patch("src.task.sync_source.SourceSyncService") as mock_source_sync_service:
        mock_source_sync_service_instance = MagicMock()
        mock_source_sync_service.return_value = mock_source_sync_service_instance
        yield mock_source_sync_service_instance

def test_sync_source_documents_task_success(
    mock_settings, mock_redis_client, mock_lock_service, mock_source_sync_service
):
    source_name = "test_source"
    source_config_dict = {"type": "SITEMAP"}
    existing_doc_ids = []

    mock_source_sync_service_instance = mock_source_sync_service.return_value
    mock_source_sync_service_instance.sync_documents.return_value = MagicMock(
        docs_added=10, docs_removed=5
    )

    result = sync_source_documents_task(source_name, source_config_dict, existing_doc_ids)

    assert result == {
        "source": source_name,
        "message": "Documents synced successfully.",
        "docs_added": 10,
        "docs_removed": 5,
    }

def test_sync_source_documents_task_failure(
    mock_settings, mock_redis_client, mock_lock_service, mock_source_sync_service
):
    source_name = "test_source"
    source_config_dict = {"type": "SITEMAP"}
    existing_doc_ids = []

    mock_source_sync_service_instance = mock_source_sync_service.return_value
    mock_source_sync_service_instance.sync_documents.side_effect = SyncSourceException("Sync failed")

    with pytest.raises(SyncSourceException):
        sync_source_documents_task(source_name, source_config_dict, existing_doc_ids)
