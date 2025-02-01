from datetime import datetime
from typing import TypedDict

from src.connectors.registry import ConnectorConfig
from src.common.redis import RedisClient
from src.common.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    ResourceType,
)
from src.sources.metadata.base import SourceMetadataStore
from src.sources.metadata.schemas import MetadataUpdate, SourceMetadata
from src.sources.metadata.utils import (
    deserialize_connector_config,
    serialize_connector_config,
)


class UpdateMapping(TypedDict, total=False):
    updated_at: str
    description: str
    last_task_id: str
    num_docs: int
    connector: str


class RedisMetadataStore(SourceMetadataStore):
    def __init__(self, *, redis_client: RedisClient, key_prefix: str):
        self.client = redis_client
        self.key_prefix = key_prefix

    def _get_metadata_key(self, source_name: str, should_exist: bool = True) -> str:
        key_name = f"{self.key_prefix}:{source_name}"

        source_exists = self.client.exists(key_name)

        if should_exist and not source_exists:
            raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

        if not should_exist and source_exists:
            raise ResourceAlreadyExistsException(ResourceType.SOURCE, source_name)

        return key_name

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
        timestamp: datetime,
    ) -> SourceMetadata:
        metadata_key = self._get_metadata_key(source_name, should_exist=False)

        connector_config_json = serialize_connector_config(connector)

        self.client.hset(
            metadata_key,
            mapping={
                "id": id,
                "name": source_name,
                "description": description,
                "num_docs": 0,
                "connector": connector_config_json,
                "last_task_id": "",
                "created_at": timestamp.isoformat(),
                "updated_at": timestamp.isoformat(),
            },
        )

        return self.get_metadata(source_name)

    def get_metadata(self, source_name: str) -> SourceMetadata:
        metadata_key = self._get_metadata_key(source_name)
        metadata = self.client.hgetall(metadata_key)
        connector_config = deserialize_connector_config(metadata["connector"])

        return SourceMetadata(
            id=metadata["id"],
            name=metadata["name"],
            description=metadata["description"],
            last_task_id=metadata["last_task_id"],
            num_docs=int(metadata["num_docs"]),
            created_at=datetime.fromisoformat(metadata["created_at"]),
            updated_at=datetime.fromisoformat(metadata["updated_at"]),
            connector=connector_config,
        )

    def delete_metadata(self, source_name: str) -> None:
        metadata_key = self._get_metadata_key(source_name)
        self.client.delete(metadata_key)

    def list_metadata(self) -> list[SourceMetadata]:
        metadata_keys = self.client.keys(f"{self.key_prefix}:*")
        metadata: list[SourceMetadata] = []
        for key in metadata_keys:
            source_name = key.split(":")[1]
            metadata.append(self.get_metadata(source_name))
        return metadata

    def update_metadata(
        self,
        name: str,
        updates: MetadataUpdate,
        timestamp: datetime,
    ) -> SourceMetadata:
        metadata_key = self._get_metadata_key(name)

        update_mapping: UpdateMapping = {"updated_at": timestamp.isoformat()}

        if updates.description is not None:
            update_mapping["description"] = updates.description

        if updates.last_task_id is not None:
            update_mapping["last_task_id"] = updates.last_task_id

        if updates.num_docs is not None:
            update_mapping["num_docs"] = updates.num_docs

        if updates.connector is not None:
            connector_config_json = serialize_connector_config(updates.connector)
            update_mapping["connector"] = connector_config_json

        self.client.hset(metadata_key, mapping=update_mapping)  # type: ignore

        return self.get_metadata(name)
