import json
from typing import Any
from src.config import settings
from src.common.redis import get_redis_client
from src.source.config import SOURCE_CONFIG_REGISTRY, SourceConfig
from src.common.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    ResourceType,
)
from src.source.schemas import SourceOverview, SourceStatus
from src.document.store.service import get_document_store


class SourceMetadataManager:
    def __init__(self):
        self.client = get_redis_client()
        self.document_store = get_document_store(settings.VECTOR_STORE_PROVIDER)
        self.config_prefix = "config__"
        self.source_config_classes = SOURCE_CONFIG_REGISTRY

    def _get_metadata_key(self, source_name: str, should_exist: bool = True) -> str:
        key_name = f"metadata:{source_name}"

        if not self.client.exists(key_name) and should_exist:
            raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

        if self.client.exists(key_name) and not should_exist:
            raise ResourceAlreadyExistsException(ResourceType.SOURCE, source_name)

        return key_name

    # TODO: Rename to serialize and deserialize?
    def _create_config_dict(self, config: SourceConfig) -> dict[str, Any]:
        config_dict: dict[str, Any] = {}
        for key, value in config.model_dump().items():
            if isinstance(value, list):
                value = json.dumps(value)
            elif isinstance(value, bool):
                value = int(value)
            elif value is None:
                value = ""
            config_dict[f"{self.config_prefix}{key}"] = value
        return config_dict

    def _parse_config_from_metadata(self, metadata: dict[str, Any]) -> SourceConfig:
        source_type = metadata.get(f"{self.config_prefix}type")
        if source_type not in self.source_config_classes:
            raise ValueError(f"Unknown source type: {source_type}")

        config_dict: dict[str, Any] = {}
        for key, value in metadata.items():
            if key.startswith(self.config_prefix):
                config_key = key.split(self.config_prefix)[1]
                if value and (value.startswith("[") or value.startswith("{")):
                    try:
                        value = json.loads(value)
                    except json.JSONDecodeError:
                        pass
                if value in ("0", "1"):
                    value = bool(int(value))
                if value == "":
                    value = None
                config_dict[config_key] = value

        return self.source_config_classes[source_type](**config_dict)

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
    ) -> SourceOverview:
        metadata_key = self._get_metadata_key(source_name, should_exist=False)

        config_dict = self._create_config_dict(config)

        self.client.hset(
            metadata_key,
            mapping={
                "id": id,
                "name": source_name,
                "description": description,
                "status": status,
                **config_dict,
                "created_at": created_at,
                "updated_at": updated_at,
            },
        )

        return self.get_metadata(source_name)

    def get_metadata(self, source_name: str) -> SourceOverview:
        metadata_key = self._get_metadata_key(source_name)
        metadata = self.client.hgetall(metadata_key)
        num_docs = self.document_store.get_document_count(source_name)
        source_config = self._parse_config_from_metadata(metadata)
        status = SourceStatus(metadata["status"])

        return SourceOverview(
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

    def get_all_metadata(self) -> list[SourceOverview]:
        metadata_keys = self.client.keys("metadata:*")
        metadata: list[SourceOverview] = []
        for key in metadata_keys:
            source_name = key.split(":")[1]
            metadata.append(self.get_metadata(source_name))
        return metadata

    def update_metadata(
        self,
        name: str,
        description: str | None,
        status: SourceStatus,
        config: SourceConfig | None,
        timestamp: str,
    ) -> SourceOverview:
        metadata_key = self._get_metadata_key(name)

        if description is not None:
            self.client.hset(metadata_key, "description", description)

        config_dict: dict[str, Any] = {}

        if config is not None:
            config_dict = self._create_config_dict(config)

        self.client.hset(
            metadata_key,
            mapping={
                **config_dict,
                "status": status,
                "updated_at": timestamp,
            },
        )

        return self.get_metadata(name)
