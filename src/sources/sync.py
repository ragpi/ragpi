import logging

from src.common.openai import get_embedding_openai_client
from src.common.redis import RedisClient
from src.config import Settings
from src.extractors.service import ExtractorService
from src.document_store.providers.redis.store import RedisDocumentStore
from src.sources.exceptions import SyncSourceException
from src.common.schemas import Document
from src.extractors.registry import ExtractorConfig
from src.sources.metadata import SourceMetadataStore
from src.sources.schemas import SourceStatus, SyncSourceOutput
from src.common.current_datetime import get_current_datetime

logger = logging.getLogger(__name__)


class SourceSyncService:
    """Class to handle the syncing of documents for a particular source."""

    def __init__(
        self,
        *,
        redis_client: RedisClient,
        source_name: str,
        extractor_config: ExtractorConfig,
        settings: Settings,
    ):
        self.redis_client = redis_client
        self.source_name = source_name
        self.extractor_config = extractor_config
        self.settings = settings

        self.openai_client = get_embedding_openai_client(settings=self.settings)
        self.document_store = RedisDocumentStore(
            index_name=self.settings.DOCUMENT_STORE_NAMESPACE,
            redis_client=self.redis_client,
            openai_client=self.openai_client,
            embedding_model=self.settings.EMBEDDING_MODEL,
            embedding_dimensions=self.settings.EMBEDDING_DIMENSIONS,
        )
        self.metadata_store = SourceMetadataStore(
            redis_client=self.redis_client,
        )
        self.extractor_service = ExtractorService(self.settings)
        self.batch_size = self.settings.DOCUMENT_SYNC_BATCH_SIZE

    async def sync_documents(self) -> SyncSourceOutput:
        """Main entry point for syncing documents for a source."""
        logger.info(f"Syncing documents for source {self.source_name}")

        existing_doc_ids: set[str] = set(
            self.document_store.get_document_ids(self.source_name)
        )
        current_doc_ids: set[str] = set()
        docs_to_add: list[Document] = []
        added_doc_ids: set[str] = set()

        try:
            # Mark source as SYNCING
            self.metadata_store.update_metadata(
                name=self.source_name,
                description=None,
                status=SourceStatus.SYNCING,
                num_docs=len(existing_doc_ids),
                extractor=None,
                timestamp=get_current_datetime(),
            )

            # Extract and sync documents
            async for doc in self.extractor_service.extract_documents(
                self.extractor_config
            ):
                if doc.id in current_doc_ids:
                    continue

                current_doc_ids.add(doc.id)

                # Only add if it's actually new and not already queued
                if doc.id not in existing_doc_ids and doc.id not in added_doc_ids:
                    docs_to_add.append(doc)
                    added_doc_ids.add(doc.id)

                    # If we have reached batch size, add the batch
                    if len(docs_to_add) >= self.batch_size:
                        self._add_documents_batch(docs_to_add, len(current_doc_ids))
                        docs_to_add = []

            # Add any remaining documents in the last batch
            if docs_to_add:
                self._add_documents_batch(docs_to_add, len(current_doc_ids))

            # Remove documents that exist in the store but not in the current sync
            doc_ids_to_remove = existing_doc_ids - current_doc_ids
            if doc_ids_to_remove:
                self._remove_stale_documents(doc_ids_to_remove, len(current_doc_ids))

            # Mark source as COMPLETED
            updated_source = self.metadata_store.update_metadata(
                name=self.source_name,
                description=None,
                status=SourceStatus.COMPLETED,
                num_docs=len(current_doc_ids),
                extractor=None,
                timestamp=get_current_datetime(),
            )

            return SyncSourceOutput(
                source=updated_source,
                docs_added=len(added_doc_ids),
                docs_removed=len(doc_ids_to_remove),
            )

        except Exception as e:
            self.metadata_store.update_metadata(
                name=self.source_name,
                description=None,
                status=SourceStatus.FAILED,
                num_docs=None,
                extractor=None,
                timestamp=get_current_datetime(),
            )
            raise e

    def _add_documents_batch(
        self, docs: list[Document], current_doc_count: int
    ) -> None:
        """Helper method to add a batch of documents to the document store."""
        try:
            self.document_store.add_documents(self.source_name, docs)

            self.metadata_store.update_metadata(
                name=self.source_name,
                description=None,
                status=SourceStatus.SYNCING,
                num_docs=current_doc_count,
                extractor=None,
                timestamp=get_current_datetime(),
            )

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

    def _remove_stale_documents(
        self, doc_ids_to_remove: set[str], current_doc_count: int
    ) -> None:
        """Helper method to remove stale documents from the document store."""
        try:
            self.document_store.delete_documents(
                self.source_name, list(doc_ids_to_remove)
            )

            self.metadata_store.update_metadata(
                name=self.source_name,
                description=None,
                status=SourceStatus.SYNCING,
                num_docs=current_doc_count,
                extractor=None,
                timestamp=get_current_datetime(),
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
