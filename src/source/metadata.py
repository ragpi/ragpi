import json
import logging
from typing import Any

from src.document_store.base import DocumentStoreService
from src.source.config import SourceConfig
from src.common.redis import RedisClient
from src.common.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    ResourceType,
)
from src.source.schemas import SourceMetadata, SourceStatus

logger = logging.getLogger(__name__)


class SourceMetadataManager:
    def __init__(
        self,
        redis_client: RedisClient,
        document_store: DocumentStoreService,
        config_map: dict[str, type[SourceConfig]],
    ):
        self.client = redis_client
        self.document_store = document_store
        self.config_map = config_map

    def _get_metadata_key(self, source_name: str, should_exist: bool = True) -> str:
        key_name = f"metadata:{source_name}"

        if not self.client.exists(key_name) and should_exist:
            raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

        if self.client.exists(key_name) and not should_exist:
            raise ResourceAlreadyExistsException(ResourceType.SOURCE, source_name)

        return key_name

    def _serialize_config(self, config: SourceConfig) -> str:
        return config.model_dump_json()

    def _deserialize_config(self, config: str) -> SourceConfig:
        config_dict = json.loads(config)

        source_type = config_dict.get("type")
        if not source_type:
            raise ValueError(f"Unknown source type: {source_type}")

        ConfigModel = self.config_map[source_type]

        return ConfigModel(**config_dict)

    def metadata_exists(self, source_name: str) -> bool:
        try:
            self._get_metadata_key(source_name)
            return True
        except ResourceNotFoundException:
            return False

    def create_metadata(
        self,
        source_name: str,
        description: str,
        status: SourceStatus,
        config: SourceConfig,
        id: str,
        created_at: str,
        updated_at: str,
    ) -> SourceMetadata:
        metadata_key = self._get_metadata_key(source_name, should_exist=False)

        config_json = self._serialize_config(config)

        self.client.hset(
            metadata_key,
            mapping={
                "id": id,
                "name": source_name,
                "description": description,
                "status": status,
                "config": config_json,
                "created_at": created_at,
                "updated_at": updated_at,
            },
        )

        return self.get_metadata(source_name)

    def get_metadata(self, source_name: str) -> SourceMetadata:
        metadata_key = self._get_metadata_key(source_name)
        metadata = self.client.hgetall(metadata_key)
        num_docs = self.document_store.get_document_count(source_name)
        source_config = self._deserialize_config(metadata["config"])
        status = SourceStatus(metadata["status"])

        return SourceMetadata(
            id=metadata["id"],
            name=metadata["name"],
            description=metadata["description"],
            status=status,
            num_docs=num_docs,
            created_at=metadata["created_at"],
            updated_at=metadata["updated_at"],
            config=source_config,
        )

    def delete_metadata(self, source_name: str) -> None:
        metadata_key = self._get_metadata_key(source_name)
        self.client.delete(metadata_key)

    def get_all_metadata(self) -> list[SourceMetadata]:
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
        status: SourceStatus | None,
        config: SourceConfig | None,
        timestamp: str,
    ) -> SourceMetadata:
        metadata_key = self._get_metadata_key(name)

        update_mapping: dict[str, Any] = {"updated_at": timestamp}

        if status is not None:
            update_mapping["status"] = status

        if description is not None:
            update_mapping["description"] = description

        if config is not None:
            config_dict = self._serialize_config(config)
            update_mapping["config"] = config_dict

        self.client.hset(metadata_key, mapping=update_mapping)  # type: ignore

        return self.get_metadata(name)
