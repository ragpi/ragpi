import json
import logging
from typing import Any

from src.connectors.connector_type import ConnectorType
from src.connectors.registry import ConnectorConfig, get_connector_config_schema
from src.common.redis import RedisClient
from src.common.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    ResourceType,
)
from src.sources.schemas import SourceMetadata

logger = logging.getLogger(__name__)


class SourceMetadataStore:
    def __init__(
        self,
        redis_client: RedisClient,
    ):
        self.client = redis_client

    def _get_metadata_key(self, source_name: str, should_exist: bool = True) -> str:
        key_name = f"metadata:{source_name}"

        source_exists = self.client.exists(key_name)

        if should_exist and not source_exists:
            raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

        if not should_exist and source_exists:
            raise ResourceAlreadyExistsException(ResourceType.SOURCE, source_name)

        return key_name

    def _serialize_connector_config(self, config: ConnectorConfig) -> str:
        return config.model_dump_json()

    def _deserialize_connector_config(self, config: str) -> ConnectorConfig:
        config_dict = json.loads(config)

        connector_type = config_dict.get("type")
        if not connector_type:
            raise ValueError("Connector type not found in config")

        ConnectorConfigSchema = get_connector_config_schema(
            ConnectorType(connector_type)
        )

        return ConnectorConfigSchema(**config_dict)

    def metadata_exists(self, source_name: str) -> bool:
        try:
            self._get_metadata_key(source_name)
            return True
        except ResourceNotFoundException:
            return False

    def create_metadata(
        self,
        id: str,
        source_name: str,
        description: str,
        connector: ConnectorConfig,
        created_at: str,
        updated_at: str,
    ) -> SourceMetadata:
        metadata_key = self._get_metadata_key(source_name, should_exist=False)

        connector_config_json = self._serialize_connector_config(connector)

        self.client.hset(
            metadata_key,
            mapping={
                "id": id,
                "name": source_name,
                "description": description,
                "num_docs": 0,
                "connector": connector_config_json,
                "last_task_id": "",
                "created_at": created_at,
                "updated_at": updated_at,
            },
        )

        return self.get_metadata(source_name)

    def get_metadata(self, source_name: str) -> SourceMetadata:
        metadata_key = self._get_metadata_key(source_name)
        metadata = self.client.hgetall(metadata_key)
        connector_config = self._deserialize_connector_config(metadata["connector"])

        return SourceMetadata(
            id=metadata["id"],
            name=metadata["name"],
            description=metadata["description"],
            last_task_id=metadata["last_task_id"],
            num_docs=int(metadata["num_docs"]),
            created_at=metadata["created_at"],
            updated_at=metadata["updated_at"],
            connector=connector_config,
        )

    def delete_metadata(self, source_name: str) -> None:
        metadata_key = self._get_metadata_key(source_name)
        self.client.delete(metadata_key)

    def list_metadata(self) -> list[SourceMetadata]:
        metadata_keys = self.client.keys("metadata:*")
        metadata: list[SourceMetadata] = []
        for key in metadata_keys:
            source_name = key.split(":")[1]
            metadata.append(self.get_metadata(source_name))
        return metadata

    def update_metadata(
        self,
        name: str,
        description: str | None,
        last_task_id: str | None,
        num_docs: int | None,
        connector: ConnectorConfig | None,
        timestamp: str,
    ) -> SourceMetadata:
        metadata_key = self._get_metadata_key(name)

        update_mapping: dict[str, Any] = {"updated_at": timestamp}

        if description is not None:
            update_mapping["description"] = description

        if last_task_id is not None:
            update_mapping["last_task_id"] = last_task_id

        if num_docs is not None:
            update_mapping["num_docs"] = num_docs

        if connector is not None:
            connector_config_json = self._serialize_connector_config(connector)
            update_mapping["connector"] = connector_config_json

        self.client.hset(metadata_key, mapping=update_mapping)  # type: ignore

        return self.get_metadata(name)
