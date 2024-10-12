from src.schemas.repository import (
    RepositoryCreateInput,
    RepositoryResponse,
    RepositoryUpdateInput,
)
from src.services.vector_store.service import VectorStoreService
from src.utils.current_datetime import current_datetime
from src.utils.web_scraper import extract_docs_from_website
from src.services.document_tracker import DocumentTracker


class RepositoryService:
    def __init__(self):
        self.vector_store_service = VectorStoreService()
        self.redis_url = "redis://localhost:6379"

    async def create_repository(self, repository_input: RepositoryCreateInput):
        repository_start_url = repository_input.start_url.rstrip("/")
        print(f"Extracting documents from {repository_start_url}")

        docs, num_pages = await extract_docs_from_website(
            start_url=repository_start_url,
            max_pages=repository_input.max_pages,
            include_pattern=repository_input.include_pattern,
            exclude_pattern=repository_input.exclude_pattern,
            proxy_urls=repository_input.proxy_urls,
        )

        print(f"Successfully extracted {len(docs)} documents from {num_pages} pages")
        timestamp = current_datetime()

        repository_id = self.vector_store_service.create_repository(
            name=repository_input.name,
            source=repository_input.source,
            start_url=repository_start_url,
            num_pages=num_pages,
            include_pattern=repository_input.include_pattern,
            exclude_pattern=repository_input.exclude_pattern,
            timestamp=timestamp,
        )

        print(f"Adding {len(docs)} documents to repository {repository_input.name}")

        # TODO: If this fails, delete the repository. Probably need to add a try/except block around entire function
        doc_ids = self.vector_store_service.add_documents(
            repository_input.name, docs, timestamp
        )
        print(
            f"Successfully added {len(doc_ids)} documents to repository {repository_input.name}"
        )

        document_tracker = DocumentTracker(
            repository_name=repository_input.name, redis_url=self.redis_url
        )

        if document_tracker.repository_exists():
            document_tracker.delete_repository()

        document_tracker.add_document(doc_ids)

        return RepositoryResponse(
            id=repository_id,
            name=repository_input.name,
            source=repository_input.source,
            start_url=repository_start_url,
            num_pages=num_pages,
            num_documents=len(doc_ids),
            include_pattern=repository_input.include_pattern,
            exclude_pattern=repository_input.exclude_pattern,
            created_at=timestamp,
            updated_at=timestamp,
        )

    def search_repository(self, repository_name: str, query: str):
        return self.vector_store_service.search_repository(repository_name, query)

    def get_repository(self, repository_name: str):
        return self.vector_store_service.get_repository(repository_name)

    def get_repository_documents(self, repository_name: str):
        return self.vector_store_service.get_repository_documents(repository_name)

    def get_all_repositories(self):
        return self.vector_store_service.get_all_repositories()

    def delete_repository(self, repository_name: str):
        self.vector_store_service.delete_repository(repository_name)

        document_tracker = DocumentTracker(
            repository_name=repository_name, redis_url=self.redis_url
        )
        document_tracker.delete_repository()

    async def update_repository(
        self,
        repository_name: str,
        repository_input: RepositoryUpdateInput | None = None,
    ):
        existing_repository = self.vector_store_service.get_repository(repository_name)

        document_tracker = DocumentTracker(
            repository_name=repository_name, redis_url=self.redis_url
        )
        existing_doc_ids = document_tracker.get_all_document_ids()

        extracted_docs, num_pages = await extract_docs_from_website(
            start_url=existing_repository.start_url,
            max_pages=existing_repository.num_pages,
            include_pattern=existing_repository.include_pattern,
            exclude_pattern=existing_repository.exclude_pattern,
            proxy_urls=repository_input.proxy_urls if repository_input else None,
        )

        extracted_doc_ids = [doc.id for doc in extracted_docs]

        docs_to_add = [
            doc
            for doc in extracted_docs
            if not document_tracker.document_exists(doc.id)
        ]
        timestamp = current_datetime()

        doc_ids_added = self.vector_store_service.add_documents(
            repository_name, docs_to_add, timestamp
        )
        document_tracker.add_document(doc_ids_added)

        print(
            f"Successfully added {len(doc_ids_added)} documents to repository {repository_name}"
        )

        doc_ids_to_remove = list(set(existing_doc_ids) - set(extracted_doc_ids))
        self.vector_store_service.delete_documents(repository_name, doc_ids_to_remove)
        document_tracker.delete_document(doc_ids_to_remove)

        print(
            f"Successfully removed {len(doc_ids_to_remove)} documents from repository {repository_name}"
        )

        if len(doc_ids_added) > 0 or len(doc_ids_to_remove) > 0:
            self.vector_store_service.update_repository_timestamp(
                repository_name, timestamp
            )

        return RepositoryResponse(
            id=existing_repository.id,
            name=repository_name,
            source=existing_repository.source,
            start_url=existing_repository.start_url,
            num_pages=num_pages,
            num_documents=len(extracted_doc_ids),
            include_pattern=existing_repository.include_pattern,
            exclude_pattern=existing_repository.exclude_pattern,
            created_at=existing_repository.created_at,
            updated_at=timestamp,
        )
