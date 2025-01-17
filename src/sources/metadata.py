import json
import logging
from typing import Any

from src.document_store.base import DocumentStoreService
from src.extractors.extractor_type import ExtractorType
from src.extractors.registry import ExtractorConfig, get_extractor_config_schema
from src.common.redis import RedisClient
from src.common.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    ResourceType,
)
from src.sources.schemas import SourceMetadata, SourceStatus

logger = logging.getLogger(__name__)


class SourceMetadataStore:
    def __init__(
        self,
        redis_client: RedisClient,
        document_store: DocumentStoreService,
    ):
        self.client = redis_client
        self.document_store = document_store

    def _get_metadata_key(self, source_name: str, should_exist: bool = True) -> str:
        key_name = f"metadata:{source_name}"

        source_exists = self.client.exists(key_name)

        if should_exist and not source_exists:
            raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

        if not should_exist and source_exists:
            raise ResourceAlreadyExistsException(ResourceType.SOURCE, source_name)

        return key_name

    def _serialize_extractor_config(self, config: ExtractorConfig) -> str:
        return config.model_dump_json()

    def _deserialize_extractor_config(self, config: str) -> ExtractorConfig:
        config_dict = json.loads(config)

        extractor_type = config_dict.get("type")
        if not extractor_type:
            raise ValueError("Extractor type not found in config")

        ExtractorConfigSchema = get_extractor_config_schema(
            ExtractorType(extractor_type)
        )

        return ExtractorConfigSchema(**config_dict)

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
        extractor: ExtractorConfig,
        id: str,
        created_at: str,
        updated_at: str,
    ) -> SourceMetadata:
        metadata_key = self._get_metadata_key(source_name, should_exist=False)

        extractor_config_json = self._serialize_extractor_config(extractor)

        self.client.hset(
            metadata_key,
            mapping={
                "id": id,
                "name": source_name,
                "description": description,
                "status": status,
                "num_docs": 0,
                "extractor": extractor_config_json,
                "created_at": created_at,
                "updated_at": updated_at,
            },
        )

        return self.get_metadata(source_name)

    def get_metadata(self, source_name: str) -> SourceMetadata:
        metadata_key = self._get_metadata_key(source_name)
        metadata = self.client.hgetall(metadata_key)
        extractor_config = self._deserialize_extractor_config(metadata["extractor"])
        status = SourceStatus(metadata["status"])

        return SourceMetadata(
            id=metadata["id"],
            name=metadata["name"],
            description=metadata["description"],
            status=status,
            num_docs=int(metadata["num_docs"]),
            created_at=metadata["created_at"],
            updated_at=metadata["updated_at"],
            extractor=extractor_config,
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
        status: SourceStatus | None,
        num_docs: int | None,
        extractor: ExtractorConfig | None,
        timestamp: str,
    ) -> SourceMetadata:
        metadata_key = self._get_metadata_key(name)

        update_mapping: dict[str, Any] = {"updated_at": timestamp}

        if description is not None:
            update_mapping["description"] = description

        if status is not None:
            update_mapping["status"] = status

        if num_docs is not None:
            update_mapping["num_docs"] = num_docs

        if extractor is not None:
            extractor_config_json = self._serialize_extractor_config(extractor)
            update_mapping["extractor"] = extractor_config_json

        self.client.hset(metadata_key, mapping=update_mapping)  # type: ignore

        return self.get_metadata(name)
