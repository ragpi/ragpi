import pytest
from pytest_mock import MockerFixture
from typing import Any

from src.common.exceptions import ResourceAlreadyExistsException, ResourceType
from src.common.redis import RedisClient
from src.document_store.base import DocumentStoreService
from src.source_connectors.source_type import SourceType
from src.source_connectors.registry import SourceRegistryType
from src.source_connectors.sitemap.config import SitemapConfig
from src.source_manager.metadata import SourceMetadataStore
from src.source_manager.schemas import SourceMetadata, SourceStatus


@pytest.fixture
def mock_redis_client(mocker: MockerFixture) -> RedisClient:
    return mocker.Mock(spec=RedisClient)


@pytest.fixture
def mock_document_store(mocker: MockerFixture) -> DocumentStoreService:
    return mocker.Mock(spec=DocumentStoreService)


@pytest.fixture
def source_registry() -> SourceRegistryType:
    return {SourceType.SITEMAP: SitemapConfig}


@pytest.fixture
def metadata_store(
    mock_redis_client: RedisClient,
    mock_document_store: DocumentStoreService,
    source_registry: SourceRegistryType,
) -> SourceMetadataStore:
    return SourceMetadataStore(
        redis_client=mock_redis_client,
        document_store=mock_document_store,
        source_registry=source_registry,
    )


@pytest.fixture
def sample_config() -> SitemapConfig:
    return SitemapConfig(
        type=SourceType.SITEMAP, sitemap_url="https://example.com/sitemap.xml"
    )


@pytest.fixture
def sample_metadata_dict(
    sample_config: SitemapConfig,
) -> dict[str, Any]:
    return {
        "id": "test-id",
        "name": "test-source",
        "description": "Test description",
        "status": SourceStatus.PENDING,
        "num_docs": 0,
        "config": sample_config.model_dump_json(),
        "created_at": "2024-01-01T12:00:00",
        "updated_at": "2024-01-01T12:00:00",
    }


def test_metadata_exists_true(
    metadata_store: SourceMetadataStore,
    mocker: MockerFixture,
) -> None:
    mock_redis_client_exists = mocker.patch.object(
        metadata_store.client, "exists", return_value=True
    )

    assert metadata_store.metadata_exists("test-source") is True
    mock_redis_client_exists.assert_called_once_with("metadata:test-source")


def test_metadata_exists_false(
    metadata_store: SourceMetadataStore,
    mocker: MockerFixture,
) -> None:
    mock_redis_client_exists = mocker.patch.object(
        metadata_store.client, "exists", return_value=False
    )
    assert metadata_store.metadata_exists("test-source") is False
    mock_redis_client_exists.assert_called_once_with("metadata:test-source")


def test_create_metadata_success(
    metadata_store: SourceMetadataStore,
    sample_config: SitemapConfig,
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
        status=SourceStatus.PENDING,
        config=sample_config,
        id="test-id",
        created_at="2024-01-01T12:00:00",
        updated_at="2024-01-01T12:00:00",
    )

    mock_redis_client_hset.assert_called_once_with(
        "metadata:test-source",
        mapping=sample_metadata_dict,
    )

    assert isinstance(result, SourceMetadata)
    assert result.id == "test-id"
    assert result.name == "test-source"
    assert result.description == "Test description"
    assert result.status == SourceStatus.PENDING
    assert result.config == sample_config
    assert result.num_docs == 0


def test_create_metadata_already_exists(
    metadata_store: SourceMetadataStore,
    sample_config: SitemapConfig,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(metadata_store.client, "exists", return_value=True)

    with pytest.raises(ResourceAlreadyExistsException) as exc:
        metadata_store.create_metadata(
            source_name="test-source",
            description="Test description",
            status=SourceStatus.PENDING,
            config=sample_config,
            id="test-id",
            created_at="2024-01-01T12:00:00",
            updated_at="2024-01-01T12:00:00",
        )

    assert exc.value.resource_type == ResourceType.SOURCE
    assert exc.value.identifier == "test-source"


def test_get_metadata_success(
    metadata_store: SourceMetadataStore,
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
    assert result.status == SourceStatus.PENDING
    assert result.num_docs == 0


def test_delete_metadata_success(
    metadata_store: SourceMetadataStore,
    mocker: MockerFixture,
) -> None:
    mocker.patch.object(metadata_store.client, "exists", return_value=True)

    mock_delete = mocker.patch.object(metadata_store.client, "delete")

    metadata_store.delete_metadata("test-source")

    mock_delete.assert_called_once_with("metadata:test-source")


def test_list_metadata_success(
    metadata_store: SourceMetadataStore,
    sample_metadata_dict: dict[str, Any],
    mocker: MockerFixture,
) -> None:
    # Mock self.client.keys
    mocker.patch.object(
        metadata_store.client,
        "keys",
        return_value=["metadata:source1", "metadata:source2"],
    )

    # Mock calls in self.get_metadata
    mocker.patch.object(metadata_store.client, "exists", return_value=True)
    mock_hgetall = mocker.patch.object(
        metadata_store.client, "hgetall", return_value=sample_metadata_dict
    )

    result = metadata_store.list_metadata()

    assert len(result) == 2
    assert all(isinstance(metadata, SourceMetadata) for metadata in result)
    assert mock_hgetall.call_count == 2
    assert result[0].name == "test-source"


def test_update_metadata_success(
    metadata_store: SourceMetadataStore,
    sample_config: SitemapConfig,
    sample_metadata_dict: dict[str, Any],
    mocker: MockerFixture,
) -> None:
    # Mock calls in self.get_metadata
    mocker.patch.object(metadata_store.client, "exists", return_value=True)
    mocker.patch.object(
        metadata_store.client, "hgetall", return_value=sample_metadata_dict
    )

    mock_hset = mocker.patch.object(metadata_store.client, "hset")

    result = metadata_store.update_metadata(
        name="test-source",
        description="Updated description",
        status=SourceStatus.COMPLETED,
        num_docs=10,
        config=sample_config,
        timestamp="2024-01-01T13:00:00",
    )

    assert isinstance(result, SourceMetadata)
    mock_hset.assert_called_once_with(
        "metadata:test-source",
        mapping={
            "description": "Updated description",
            "status": SourceStatus.COMPLETED,
            "num_docs": 10,
            "config": sample_config.model_dump_json(),
            "updated_at": "2024-01-01T13:00:00",
        },
    )
