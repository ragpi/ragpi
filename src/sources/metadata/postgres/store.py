from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from src.connectors.registry import ConnectorConfig
from src.common.exceptions import (
    ResourceNotFoundException,
    ResourceAlreadyExistsException,
    ResourceType,
)
from src.sources.metadata.base import SourceMetadataStore
from src.sources.metadata.schemas import MetadataUpdate, SourceMetadata
from src.sources.metadata.postgres.model import Base, SourceMetadataModel
from src.sources.metadata.utils import (
    deserialize_connector_config,
    serialize_connector_config,
)


class PostgresMetadataStore(SourceMetadataStore):
    def __init__(self, database_url: str):
        self.engine = create_engine(database_url)
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    def metadata_exists(self, source_name: str) -> bool:
        with self.Session() as session:
            return session.query(
                session.query(SourceMetadataModel).filter_by(name=source_name).exists()
            ).scalar()

    def create_metadata(
        self,
        id: str,
        source_name: str,
        description: str,
        connector: ConnectorConfig,
        timestamp: datetime,
    ) -> SourceMetadata:
        with self.Session() as session:
            if self.metadata_exists(source_name):
                raise ResourceAlreadyExistsException(ResourceType.SOURCE, source_name)

            connector_json = serialize_connector_config(connector)
            new_metadata = SourceMetadataModel(
                id=id,
                name=source_name,
                description=description,
                connector=connector_json,
                created_at=timestamp,
                updated_at=timestamp,
            )

            try:
                session.add(new_metadata)
                session.commit()
            except IntegrityError as e:
                session.rollback()
                raise ResourceAlreadyExistsException(
                    ResourceType.SOURCE, source_name
                ) from e

            return self.get_metadata(source_name)

    def get_metadata(self, source_name: str) -> SourceMetadata:
        with self.Session() as session:
            metadata = (
                session.query(SourceMetadataModel).filter_by(name=source_name).first()
            )

            if not metadata:
                raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

            connector_config = deserialize_connector_config(metadata.connector)

            return SourceMetadata(
                id=metadata.id,
                name=metadata.name,
                description=metadata.description,
                num_docs=metadata.num_docs,
                connector=connector_config,
                last_task_id=metadata.last_task_id,
                created_at=metadata.created_at,
                updated_at=metadata.updated_at,
            )

    def update_metadata(
        self,
        name: str,
        updates: MetadataUpdate,
        timestamp: datetime,
    ) -> SourceMetadata:
        with self.Session() as session:
            metadata = session.query(SourceMetadataModel).filter_by(name=name).first()

            if not metadata:
                raise ResourceNotFoundException(ResourceType.SOURCE, name)

            if updates.description is not None:
                metadata.description = updates.description
            if updates.last_task_id is not None:
                metadata.last_task_id = updates.last_task_id
            if updates.num_docs is not None:
                metadata.num_docs = updates.num_docs
            if updates.connector is not None:
                metadata.connector = serialize_connector_config(updates.connector)

            metadata.updated_at = timestamp
            session.commit()

            return self.get_metadata(name)

    def delete_metadata(self, source_name: str) -> None:
        with self.Session() as session:
            metadata = (
                session.query(SourceMetadataModel).filter_by(name=source_name).first()
            )

            if not metadata:
                raise ResourceNotFoundException(ResourceType.SOURCE, source_name)

            session.delete(metadata)
            session.commit()

    def list_metadata(self) -> list[SourceMetadata]:
        with self.Session() as session:
            all_metadata = session.query(SourceMetadataModel).all()
            return [
                SourceMetadata(
                    id=metadata.id,
                    name=metadata.name,
                    description=metadata.description,
                    num_docs=metadata.num_docs,
                    connector=deserialize_connector_config(metadata.connector),
                    last_task_id=metadata.last_task_id,
                    created_at=metadata.created_at,
                    updated_at=metadata.updated_at,
                )
                for metadata in all_metadata
            ]
