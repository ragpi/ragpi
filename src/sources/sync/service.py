import logging
from uuid import UUID, uuid5

from src.llm_providers.client import get_embedding_openai_client
from src.common.redis import RedisClient
from src.config import Settings
from src.connectors.service import ConnectorService
from src.document_store.backend import get_document_store_backend
from src.sources.exceptions import SyncSourceException
from src.document_store.schemas import Document
from src.connectors.registry import ConnectorConfig
from src.sources.metadata.schemas import MetadataUpdate
from src.sources.metadata.backend import get_metadata_store_backend
from src.sources.schemas import SyncSourceOutput
from src.common.current_datetime import get_current_datetime

logger = logging.getLogger(__name__)


class SourceSyncService:
    """Class to handle the syncing of documents for a particular source."""

    def __init__(
        self,
        *,
        redis_client: RedisClient,
        source_name: str,
        connector_config: ConnectorConfig,
        settings: Settings,
    ):
        self.redis_client = redis_client
        self.source_name = source_name
        self.connector_config = connector_config
        self.settings = settings

        self.openai_client = get_embedding_openai_client(settings=self.settings)
        self.document_store = get_document_store_backend(
            redis_client=self.redis_client,
            openai_client=self.openai_client,
            settings=self.settings,
        )
        self.metadata_store = get_metadata_store_backend(
            redis_client=self.redis_client,
            settings=self.settings,
        )
        self.connector_service = ConnectorService(self.settings)
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
            # Extract and sync documents
            async for extracted_doc in self.connector_service.extract_documents(
                self.connector_config
            ):
                stable_id = self._generate_stable_id(
                    title=extracted_doc.title,
                    content=extracted_doc.content,
                )
                doc = Document(
                    id=stable_id,
                    url=extracted_doc.url,
                    title=extracted_doc.title,
                    content=extracted_doc.content,
                    created_at=get_current_datetime(),
                )
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
                updates=MetadataUpdate(
                    num_docs=len(current_doc_ids),
                ),
                timestamp=get_current_datetime(),
            )

            return SyncSourceOutput(
                source=updated_source,
                docs_added=len(added_doc_ids),
                docs_removed=len(doc_ids_to_remove),
            )

        except Exception as e:
            logger.exception(f"Failed to sync documents for source {self.source_name}")
            raise e

    def _generate_stable_id(self, title: str, content: str) -> str:
        """Generates a stable ID for a document."""
        namespace = UUID(self.settings.DOCUMENT_UUID_NAMESPACE)
        return str(uuid5(namespace, f"{self.source_name}:{title}:{content}"))

    def _add_documents_batch(
        self, docs: list[Document], current_doc_count: int
    ) -> None:
        """Helper method to add a batch of documents to the document store."""
        try:
            self.document_store.add_documents(self.source_name, docs)

            self.metadata_store.update_metadata(
                name=self.source_name,
                updates=MetadataUpdate(
                    num_docs=current_doc_count,
                ),
                timestamp=get_current_datetime(),
            )

            logger.info(
                f"Added a batch of {len(docs)} documents to source {self.source_name}"
            )
        except Exception:
            message = f"Failed to add batch of documents to source {self.source_name}"
            logger.exception(message)
            raise SyncSourceException(message)

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
                updates=MetadataUpdate(
                    num_docs=current_doc_count,
                ),
                timestamp=get_current_datetime(),
            )

            logger.info(
                f"Removed {len(doc_ids_to_remove)} documents from source {self.source_name}"
            )
        except Exception:
            message = f"Failed to remove documents from source {self.source_name}"
            logger.exception(message)
            raise SyncSourceException(message)
