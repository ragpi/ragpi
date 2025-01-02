import logging

from src.common.openai import get_embedding_openai_client
from src.common.redis import RedisClient
from src.config import Settings
from src.document_extractor.service import DocumentExtractor
from src.document_store.providers.redis.store import RedisDocumentStore
from src.source.exceptions import SyncSourceException
from src.common.schemas import Document
from src.source.config import (
    SourceConfig,
)
from src.source.metadata import SourceMetadataManager
from src.source.schemas import SourceStatus, SyncSourceOutput
from src.common.current_datetime import get_current_datetime

logger = logging.getLogger(__name__)


class SourceSyncService:
    """Class to handle the syncing of documents for a particular source."""

    def __init__(
        self,
        *,
        redis_client: RedisClient,
        source_name: str,
        config_map: dict[str, type[SourceConfig]],
        source_config: SourceConfig,
        existing_doc_ids: set[str],
        settings: Settings,
    ):
        self.redis_client = redis_client
        self.source_name = source_name
        self.config_map = config_map
        self.source_config = source_config
        self.existing_doc_ids = existing_doc_ids
        self.settings = settings

        self.openai_client = get_embedding_openai_client(settings=self.settings)
        self.document_store = RedisDocumentStore(
            index_name=self.settings.DOCUMENT_STORE_NAMESPACE,
            redis_client=self.redis_client,
            openai_client=self.openai_client,
            embedding_model=self.settings.EMBEDDING_MODEL,
            embedding_dimensions=self.settings.EMBEDDING_DIMENSIONS,
        )
        self.metadata_manager = SourceMetadataManager(
            redis_client=self.redis_client,
            document_store=self.document_store,
            config_map=self.config_map,
        )
        self.document_extractor = DocumentExtractor(self.settings)
        self.batch_size = self.settings.DOCUMENT_SYNC_BATCH_SIZE

    async def sync_documents(self) -> SyncSourceOutput:
        """Main entry point for syncing documents for a source."""
        logger.info(f"Syncing documents for source {self.source_name}")

        current_doc_ids: set[str] = set()
        docs_to_add: list[Document] = []
        added_doc_ids: set[str] = set()

        try:
            # Mark source as SYNCING
            self.metadata_manager.update_metadata(
                name=self.source_name,
                description=None,
                status=SourceStatus.SYNCING,
                config=None,
                timestamp=get_current_datetime(),
            )

            # Extract and sync documents
            async for doc in self.document_extractor.extract_documents(
                self.source_config
            ):
                if doc.id in current_doc_ids:
                    continue

                current_doc_ids.add(doc.id)

                # Only add if it's actually new and not already queued
                if doc.id not in self.existing_doc_ids and doc.id not in added_doc_ids:
                    docs_to_add.append(doc)
                    added_doc_ids.add(doc.id)

                    # If we have reached batch size, add the batch
                    if len(docs_to_add) >= self.batch_size:
                        self._add_documents_batch(docs_to_add)
                        docs_to_add = []

            # Add any remaining documents in the last batch
            if docs_to_add:
                self._add_documents_batch(docs_to_add)

            # Remove documents that exist in the store but not in the current sync
            doc_ids_to_remove = self.existing_doc_ids - current_doc_ids
            if doc_ids_to_remove:
                self._remove_stale_documents(doc_ids_to_remove)

            # If no documents were added in the entire sync
            if not added_doc_ids:
                logger.info(f"No new documents added to source {self.source_name}")

            # Mark source as COMPLETED
            updated_source = self.metadata_manager.update_metadata(
                name=self.source_name,
                description=None,
                status=SourceStatus.COMPLETED,
                config=None,
                timestamp=get_current_datetime(),
            )

            return SyncSourceOutput(
                source=updated_source,
                docs_added=len(added_doc_ids),
                docs_removed=len(doc_ids_to_remove),
            )

        except Exception as e:
            self.metadata_manager.update_metadata(
                name=self.source_name,
                description=None,
                status=SourceStatus.FAILED,
                config=None,
                timestamp=get_current_datetime(),
            )
            raise e

    def _add_documents_batch(self, docs: list[Document]) -> None:
        """Helper method to add a batch of documents to the document store."""
        try:
            self.document_store.add_documents(self.source_name, docs)
            logger.info(
                f"Added a batch of {len(docs)} documents to source {self.source_name}"
            )
        except Exception:
            logger.exception(
                f"Failed to add batch of documents to source {self.source_name}"
            )
            raise SyncSourceException(
                f"Failed to sync documents for source {self.source_name}"
            )

    def _remove_stale_documents(self, doc_ids_to_remove: set[str]) -> None:
        """Helper method to remove stale documents from the document store."""
        try:
            self.document_store.delete_documents(
                self.source_name, list(doc_ids_to_remove)
            )
            logger.info(
                f"Removed {len(doc_ids_to_remove)} documents from source {self.source_name}"
            )
        except Exception:
            logger.exception(
                f"Failed to remove documents from source {self.source_name}"
            )
            raise SyncSourceException(
                f"Failed to sync documents for source {self.source_name}"
            )
