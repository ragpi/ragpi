from datetime import datetime
import pytest
from pytest_mock import MockerFixture
from typing import Any

from src.common.exceptions import (
    ResourceAlreadyExistsException,
    ResourceNotFoundException,
    ResourceType,
)
from src.common.redis import RedisClient
from src.document_store.base import DocumentStoreBackend
from src.connectors.connector_type import ConnectorType
from src.connectors.sitemap.config import SitemapConfig
from src.sources.metadata.redis.store import RedisMetadataStore
from src.sources.metadata.schemas import SourceMetadata, MetadataUpdate


@pytest.fixture
def mock_redis_client(mocker: MockerFixture) -> RedisClient:
    return mocker.Mock(spec=RedisClient)


@pytest.fixture
def mock_document_store(mocker: MockerFixture) -> DocumentStoreBackend:
    return mocker.Mock(spec=DocumentStoreBackend)


@pytest.fixture
def metadata_store(
    mock_redis_client: RedisClient,
) -> RedisMetadataStore:
    return RedisMetadataStore(
        redis_client=mock_redis_client,
        key_prefix="metadata",
    )


@pytest.fixture
def sample_connector_config() -> SitemapConfig:
    return SitemapConfig(
        type=ConnectorType.SITEMAP, sitemap_url="https://example.com/sitemap.xml"
    )


@pytest.fixture
def sample_metadata_dict(
    sample_connector_config: SitemapConfig,
) -> dict[str, Any]:
    return {
        "id": "test-id",
        "name": "test-source",
        "description": "Test description",
        "num_docs": 0,
        "last_task_id": "",
        "connector": sample_connector_config.model_dump_json(),
        "created_at": "2024-01-01T12:00:00",
        "updated_at": "2024-01-01T12:00:00",
    }


def test_metadata_exists_true(
    metadata_store: RedisMetadataStore,
    mocker: MockerFixture,
) -> None:
    mock_redis_client_exists = mocker.patch.object(
        metadata_store.client, "exists", return_value=True
    )

    assert metadata_store.metadata_exists("test-source") is True
    mock_redis_client_exists.assert_called_once_with("metadata:test-source")


def test_metadata_exists_false(
    metadata_store: RedisMetadataStore,
    mocker: MockerFixture,
) -> None:
    mock_redis_client_exists = mocker.patch.object(
        metadata_store.client, "exists", return_value=False
    )
    assert metadata_store.metadata_exists("test-source") is False
    mock_redis_client_exists.assert_called_once_with("metadata:test-source")


def test_create_metadata_success(
    metadata_store: RedisMetadataStore,
    sample_connector_config: SitemapConfig,
    sample_metadata_dict: dict[str, Any],
    mocker: MockerFixture,
) -> None:
    # Mock redis client
    mocker.patch.object(metadata_store.client, "exists", side_effect=[False, True])
    mocker.patch.object(
        metadata_store.client,
        "hgetall",
        return_value=sample_metadata_dict,
    )
    mock_redis_client_hset = mocker.patch.object(metadata_store.client, "hset")

    result = metadata_store.create_metadata(
        source_name="test-source",
        description="Test description",
        connector=sample_connector_config,
        id="test-id",
        timestamp=datetime.fromisoformat("2024-01-01T12:00:00"),
    )

    expected_mapping: dict[str, Any] = {
        "id": "test-id",
        "name": "test-source",
        "description": "Test description",
        "num_docs": 0,
        "last_task_id": "",
        "connector": sample_connector_config.model_dump_json(),
        "created_at": "2024-01-01T12:00:00",
        "updated_at": "2024-01-01T12:00:00",
    }

    mock_redis_client_hset.assert_called_once_with(
        "metadata:test-source",
        mapping=expected_mapping,
    )

    assert isinstance(result, SourceMetadata)
    assert result.id == "test-id"
    assert result.name == "test-source"
    assert result.description == "Test description"
    assert result.last_task_id == ""
    assert result.connector == sample_connector_config
    assert result.num_docs == 0
    assert result.created_at == datetime.fromisoformat("2024-01-01T12:00:00")
    assert result.updated_at == datetime.fromisoformat("2024-01-01T12:00:00")


def test_create_metadata_already_exists(
    metadata_store: RedisMetadataStore,
    sample_connector_config: SitemapConfig,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(metadata_store.client, "exists", return_value=True)

    with pytest.raises(ResourceAlreadyExistsException) as exc:
        metadata_store.create_metadata(
            source_name="test-source",
            description="Test description",
            connector=sample_connector_config,
            id="test-id",
            timestamp=datetime.fromisoformat("2024-01-01T12:00:00"),
        )

    assert exc.value.resource_type == ResourceType.SOURCE
    assert exc.value.identifier == "test-source"


def test_get_metadata_success(
    metadata_store: RedisMetadataStore,
    sample_metadata_dict: dict[str, Any],
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(metadata_store.client, "exists", return_value=True)
    mocker.patch.object(
        metadata_store.client, "hgetall", return_value=sample_metadata_dict
    )

    result = metadata_store.get_metadata("test-source")

    assert isinstance(result, SourceMetadata)
    assert result.id == sample_metadata_dict["id"]
    assert result.name == sample_metadata_dict["name"]
    assert result.description == sample_metadata_dict["description"]
    assert result.last_task_id == ""
    assert result.num_docs == 0
    assert result.created_at == datetime.fromisoformat(
        sample_metadata_dict["created_at"]
    )
    assert result.updated_at == datetime.fromisoformat(
        sample_metadata_dict["updated_at"]
    )


def test_get_metadata_not_found(
    metadata_store: RedisMetadataStore,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(metadata_store.client, "exists", return_value=False)

    with pytest.raises(ResourceNotFoundException) as exc:
        metadata_store.get_metadata("test-source")

    assert exc.value.resource_type == ResourceType.SOURCE
    assert exc.value.identifier == "test-source"


def test_delete_metadata_success(
    metadata_store: RedisMetadataStore,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(metadata_store.client, "exists", return_value=True)

    mock_delete = mocker.patch.object(metadata_store.client, "delete")

    metadata_store.delete_metadata("test-source")

    mock_delete.assert_called_once_with("metadata:test-source")


def test_list_metadata_success(
    metadata_store: RedisMetadataStore,
    sample_metadata_dict: dict[str, Any],
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(
        metadata_store.client,
        "keys",
        return_value=["metadata:source1", "metadata:source2"],
    )

    mocker.patch.object(metadata_store.client, "exists", return_value=True)
    mock_hgetall = mocker.patch.object(
        metadata_store.client, "hgetall", return_value=sample_metadata_dict
    )

    result = metadata_store.list_metadata()

    assert len(result) == 2
    assert all(isinstance(metadata, SourceMetadata) for metadata in result)
    assert mock_hgetall.call_count == 2
    assert result[0].name == "test-source"
    assert result[0].last_task_id == ""


def test_update_metadata_success(
    metadata_store: RedisMetadataStore,
    sample_connector_config: SitemapConfig,
    sample_metadata_dict: dict[str, Any],
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(metadata_store.client, "exists", return_value=True)
    mocker.patch.object(
        metadata_store.client, "hgetall", return_value=sample_metadata_dict
    )

    mock_hset = mocker.patch.object(metadata_store.client, "hset")

    updates = MetadataUpdate(
        description="Updated description",
        last_task_id="task-123",
        num_docs=10,
        connector=sample_connector_config,
    )

    result = metadata_store.update_metadata(
        name="test-source",
        updates=updates,
        timestamp=datetime.fromisoformat("2024-01-01T13:00:00"),
    )

    assert isinstance(result, SourceMetadata)
    mock_hset.assert_called_once_with(
        "metadata:test-source",
        mapping={
            "description": "Updated description",
            "last_task_id": "task-123",
            "num_docs": 10,
            "connector": sample_connector_config.model_dump_json(),
            "updated_at": "2024-01-01T13:00:00",
        },
    )
