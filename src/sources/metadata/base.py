from abc import ABC, abstractmethod
from datetime import datetime

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
        timestamp: datetime,
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
        timestamp: datetime,
    ) -> SourceMetadata:
        pass

    @abstractmethod
    def delete_metadata(self, source_name: str) -> None:
        pass

    @abstractmethod
    def list_metadata(self) -> list[SourceMetadata]:
        pass
