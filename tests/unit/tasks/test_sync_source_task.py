from unittest.mock import AsyncMock, Mock
import pytest
from pytest_mock import MockerFixture
from redis.lock import Lock
import asyncio
from celery import Task
from celery.exceptions import Ignore

from src.config import Settings
from src.common.redis import RedisClient
from src.sources.metadata.schemas import SourceMetadata
from src.sources.sync.service import SourceSyncService
from src.sources.schemas import SyncSourceOutput
from src.tasks.sync_source import sync_source_documents_task


@pytest.fixture
def mock_settings(mocker: MockerFixture) -> Settings:
    settings = mocker.Mock(spec=Settings)
    settings.REDIS_URL = "redis://localhost:6379"
    return settings


@pytest.fixture
def mock_redis_client(mocker: MockerFixture) -> Mock:
    return mocker.Mock(spec=RedisClient)


@pytest.fixture
def mock_lock(mocker: MockerFixture) -> Lock:
    return mocker.Mock(spec=Lock)


@pytest.fixture
def mock_lock_service(mocker: MockerFixture) -> Mock:
    lock_service = mocker.Mock()
    lock_service.acquire_lock.return_value = mocker.Mock(spec=Lock)
    lock_service.renew_lock = AsyncMock()
    return lock_service


@pytest.fixture
def mock_sync_service(mocker: MockerFixture) -> Mock:
    sync_service = mocker.Mock(spec=SourceSyncService)
    sync_service.sync_documents = AsyncMock()
    return sync_service


@pytest.fixture
def mock_current_task(mocker: MockerFixture) -> Mock:
    task = mocker.Mock(spec=Task)
    task.update_state = mocker.Mock()
    return task


@pytest.fixture
def common_setup(
    mocker: MockerFixture,
    mock_settings: Settings,
    mock_redis_client: Mock,
    mock_lock_service: Mock,
    mock_sync_service: Mock,
    mock_current_task: Mock,
) -> None:
    mocker.patch("src.tasks.sync_source.get_settings", return_value=mock_settings)
    mocker.patch("src.tasks.sync_source.Redis.from_url", return_value=mock_redis_client)
    mocker.patch("src.tasks.sync_source.LockService", return_value=mock_lock_service)
    mocker.patch(
        "src.tasks.sync_source.SourceSyncService", return_value=mock_sync_service
    )
    mocker.patch("src.tasks.sync_source.current_task", mock_current_task)


def test_sync_source_documents_success(
    common_setup: None,
    mock_redis_client: Mock,
    mock_lock_service: Mock,
    mock_sync_service: Mock,
    mock_current_task: Mock,
    mocker: MockerFixture,
) -> None:
    mock_loop = mocker.Mock(spec=asyncio.AbstractEventLoop)
    mocker.patch("asyncio.new_event_loop", return_value=mock_loop)

    # Setup test data
    source_name = "test-source"
    connector_config = {
        "type": "sitemap",
        "sitemap_url": "https://example.com/sitemap.xml",
    }

    # Mock sync result
    mock_sync_result = SyncSourceOutput(
        source=mocker.Mock(spec=SourceMetadata), docs_added=2, docs_removed=1
    )
    mock_sync_service.sync_documents.return_value = mock_sync_result
    mock_loop.run_until_complete.return_value = {
        "source": source_name,
        "message": "Documents synced successfully.",
        "docs_added": 2,
        "docs_removed": 1,
    }

    # Execute task
    result = sync_source_documents_task(source_name, connector_config)

    # Verify results
    assert result == {
        "source": source_name,
        "message": "Documents synced successfully.",
        "docs_added": 2,
        "docs_removed": 1,
    }

    # Verify state updates
    mock_current_task.update_state.assert_called_with(
        state="SYNCING",
        meta={
            "source": source_name,
            "message": "Syncing documents...",
        },
    )

    # Verify cleanup
    mock_loop.close.assert_called_once()
    mock_lock_service.release_lock.assert_called_once()
    mock_redis_client.close.assert_called_once()


def test_sync_source_documents_invalid_source_type(
    common_setup: None,
    mock_current_task: Mock,
) -> None:
    source_name = "test-source"
    invalid_config = {"type": "invalid_type"}

    with pytest.raises(Ignore):
        sync_source_documents_task(source_name, invalid_config)

    mock_current_task.update_state.assert_called_with(
        state="FAILURE",
        meta={
            "source": source_name,
            "message": "Failed to sync documents.",
            "error": "Invalid connector config: 'invalid_type' is not a valid ConnectorType",
            "exc_type": "SyncSourceException",
        },
    )


def test_sync_source_documents_invalid_config(
    common_setup: None,
    mock_current_task: Mock,
) -> None:
    source_name = "test-source"
    invalid_config = {"type": "sitemap"}

    with pytest.raises(Ignore):
        sync_source_documents_task(source_name, invalid_config)

    mock_current_task.update_state.assert_called()

    _, kwargs = mock_current_task.update_state.call_args
    assert kwargs["state"] == "FAILURE"
    assert "Invalid connector config" in kwargs["meta"]["error"]
    assert kwargs["meta"]["source"] == source_name
    assert kwargs["meta"]["message"] == "Failed to sync documents."
    assert kwargs["meta"]["exc_type"] == "SyncSourceException"


def test_sync_source_documents_lock_failure(
    common_setup: None,
    mock_lock_service: Mock,
    mock_current_task: Mock,
) -> None:
    # Mock lock acquisition failure
    mock_lock_service.acquire_lock.side_effect = Exception("Lock acquisition failed")

    source_name = "test-source"
    connector_config = {
        "type": "sitemap",
        "sitemap_url": "https://example.com/sitemap.xml",
    }

    with pytest.raises(Ignore):
        sync_source_documents_task(source_name, connector_config)

    mock_current_task.update_state.assert_called_with(
        state="FAILURE",
        meta={
            "source": source_name,
            "message": "Failed to sync documents.",
            "error": "Lock acquisition failed",
            "exc_type": "Exception",
        },
    )


def test_sync_source_documents_sync_failure(
    common_setup: None,
    mock_redis_client: Mock,
    mock_lock_service: Mock,
    mock_current_task: Mock,
    mocker: MockerFixture,
) -> None:
    # Mock sync failure
    mock_loop = mocker.Mock(spec=asyncio.AbstractEventLoop)
    mock_loop.run_until_complete.side_effect = Exception("Sync failed")
    mocker.patch("asyncio.new_event_loop", return_value=mock_loop)

    source_name = "test-source"
    connector_config = {
        "type": "sitemap",
        "sitemap_url": "https://example.com/sitemap.xml",
    }

    with pytest.raises(Ignore):
        sync_source_documents_task(source_name, connector_config)

    mock_current_task.update_state.assert_called_with(
        state="FAILURE",
        meta={
            "source": source_name,
            "message": "Failed to sync documents.",
            "error": "Sync failed",
            "exc_type": "Exception",
        },
    )

    # Verify cleanup still occurs
    mock_loop.close.assert_called_once()
    mock_lock_service.release_lock.assert_called_once()
    mock_redis_client.close.assert_called_once()
