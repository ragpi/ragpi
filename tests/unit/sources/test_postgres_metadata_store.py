from datetime import datetime
from pathlib import Path
import pytest

from src.common.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    ResourceType,
)
from src.connectors.registry import ConnectorConfig
from src.connectors.connector_type import ConnectorType
from src.sources.metadata.postgres.store import PostgresMetadataStore
from src.sources.metadata.schemas import SourceMetadata, MetadataUpdate
from src.connectors.sitemap.config import SitemapConfig

TEST_TIMESTAMP = datetime.fromisoformat("2024-01-01T12:00:00")
UPDATED_TIMESTAMP = datetime.fromisoformat("2024-01-01T13:00:00")


@pytest.fixture
def test_database_url(tmp_path: Path) -> str:
    db_path: Path = tmp_path / "test_postgres_metadata.db"
    return f"sqlite:///{db_path}"


@pytest.fixture
def metadata_store(test_database_url: str) -> PostgresMetadataStore:
    return PostgresMetadataStore(database_url=test_database_url)


@pytest.fixture
def sample_connector_config() -> SitemapConfig:
    return SitemapConfig(
        type=ConnectorType.SITEMAP,
        sitemap_url="https://example.com/sitemap.xml",
    )


def test_metadata_exists_false(metadata_store: PostgresMetadataStore) -> None:
    assert metadata_store.metadata_exists("nonexistent") is False


def test_create_metadata_success(
    metadata_store: PostgresMetadataStore,
    sample_connector_config: ConnectorConfig,
) -> None:
    result = metadata_store.create_metadata(
        id="test-id",
        source_name="test-source",
        description="Test description",
        connector=sample_connector_config,
        timestamp=TEST_TIMESTAMP,
    )

    assert result.id == "test-id"
    assert result.name == "test-source"
    assert result.description == "Test description"
    assert result.last_task_id == ""
    assert result.num_docs == 0
    assert result.connector == sample_connector_config
    assert result.created_at == TEST_TIMESTAMP
    assert result.updated_at == TEST_TIMESTAMP


def test_create_metadata_already_exists(
    metadata_store: PostgresMetadataStore,
    sample_connector_config: ConnectorConfig,
) -> None:
    metadata_store.create_metadata(
        id="test-id",
        source_name="test-source",
        description="Test description",
        connector=sample_connector_config,
        timestamp=TEST_TIMESTAMP,
    )

    with pytest.raises(ResourceAlreadyExistsException) as exc_info:
        metadata_store.create_metadata(
            id="another-id",
            source_name="test-source",
            description="Another description",
            connector=sample_connector_config,
            timestamp=TEST_TIMESTAMP,
        )

    assert exc_info.value.resource_type == ResourceType.SOURCE
    assert exc_info.value.identifier == "test-source"


def test_get_metadata_success(
    metadata_store: PostgresMetadataStore,
    sample_connector_config: ConnectorConfig,
) -> None:
    metadata_store.create_metadata(
        id="test-id",
        source_name="test-source",
        description="Test description",
        connector=sample_connector_config,
        timestamp=TEST_TIMESTAMP,
    )
    result = metadata_store.get_metadata("test-source")

    assert result.id == "test-id"
    assert result.name == "test-source"
    assert result.description == "Test description"
    assert result.last_task_id == ""
    assert result.num_docs == 0
    assert result.connector == sample_connector_config
    assert result.created_at == TEST_TIMESTAMP
    assert result.updated_at == TEST_TIMESTAMP


def test_get_metadata_not_found(metadata_store: PostgresMetadataStore) -> None:
    with pytest.raises(ResourceNotFoundException) as exc_info:
        metadata_store.get_metadata("nonexistent")
    assert exc_info.value.resource_type == ResourceType.SOURCE
    assert exc_info.value.identifier == "nonexistent"


def test_update_metadata_success(
    metadata_store: PostgresMetadataStore,
    sample_connector_config: ConnectorConfig,
) -> None:
    metadata_store.create_metadata(
        id="test-id",
        source_name="test-source",
        description="Test description",
        connector=sample_connector_config,
        timestamp=TEST_TIMESTAMP,
    )

    updates = MetadataUpdate(
        description="Updated description",
        last_task_id="task-123",
        num_docs=10,
        connector=sample_connector_config,
    )
    updated_metadata = metadata_store.update_metadata(
        name="test-source",
        updates=updates,
        timestamp=UPDATED_TIMESTAMP,
    )

    assert updated_metadata.description == "Updated description"
    assert updated_metadata.last_task_id == "task-123"
    assert updated_metadata.num_docs == 10
    assert updated_metadata.connector == sample_connector_config
    assert updated_metadata.updated_at == UPDATED_TIMESTAMP


def test_update_metadata_not_found(metadata_store: PostgresMetadataStore) -> None:
    updates = MetadataUpdate(
        description="Updated description",
    )
    with pytest.raises(ResourceNotFoundException) as exc_info:
        metadata_store.update_metadata(
            name="nonexistent",
            updates=updates,
            timestamp=TEST_TIMESTAMP,
        )
    assert exc_info.value.resource_type == ResourceType.SOURCE
    assert exc_info.value.identifier == "nonexistent"


def test_delete_metadata_success(
    metadata_store: PostgresMetadataStore,
    sample_connector_config: ConnectorConfig,
) -> None:
    metadata_store.create_metadata(
        id="test-id",
        source_name="test-source",
        description="Test description",
        connector=sample_connector_config,
        timestamp=TEST_TIMESTAMP,
    )

    metadata_store.delete_metadata("test-source")

    with pytest.raises(ResourceNotFoundException):
        metadata_store.get_metadata("test-source")


def test_delete_metadata_not_found(metadata_store: PostgresMetadataStore) -> None:
    with pytest.raises(ResourceNotFoundException) as exc_info:
        metadata_store.delete_metadata("nonexistent")
    assert exc_info.value.resource_type == ResourceType.SOURCE
    assert exc_info.value.identifier == "nonexistent"


def test_list_metadata(
    metadata_store: PostgresMetadataStore,
    sample_connector_config: ConnectorConfig,
) -> None:
    initial_list: list[SourceMetadata] = metadata_store.list_metadata()
    assert len(initial_list) == 0

    metadata_store.create_metadata(
        id="id1",
        source_name="source1",
        description="Description 1",
        connector=sample_connector_config,
        timestamp=TEST_TIMESTAMP,
    )
    metadata_store.create_metadata(
        id="id2",
        source_name="source2",
        description="Description 2",
        connector=sample_connector_config,
        timestamp=TEST_TIMESTAMP,
    )
    metadata_list: list[SourceMetadata] = metadata_store.list_metadata()
    assert len(metadata_list) == 2

    names: set[str] = {metadata.name for metadata in metadata_list}
    assert names == {"source1", "source2"}
