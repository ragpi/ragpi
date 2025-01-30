from abc import ABC, abstractmethod

from src.sources.metadata.schemas import MetadataUpdate, SourceMetadata
from src.connectors.registry import ConnectorConfig


class SourceMetadataStore(ABC):
    @abstractmethod
    def metadata_exists(self, source_name: str) -> bool:
        pass

    @abstractmethod
    def create_metadata(
        self,
        id: str,
        source_name: str,
        description: str,
        connector: ConnectorConfig,
        created_at: str,
        updated_at: str,
    ) -> SourceMetadata:
        pass

    @abstractmethod
    def get_metadata(self, source_name: str) -> SourceMetadata:
        pass

    @abstractmethod
    def update_metadata(
        self,
        name: str,
        updates: MetadataUpdate,
        timestamp: str,
    ) -> SourceMetadata:
        pass

    @abstractmethod
    def delete_metadata(self, source_name: str) -> None:
        pass

    @abstractmethod
    def list_metadata(self) -> list[SourceMetadata]:
        pass
