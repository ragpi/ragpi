import asyncio
from typing import Any
from celery import current_task

from src.celery import celery_app
from src.schemas.collections import (
    CollectionCreate,
    CollectionDocument,
    CollectionResponse,
    CollectionUpdate,
)
from src.services.vector_store import VectorStoreService
from src.utils.text_splitter import split_markdown_content
from src.utils.web_scraper import extract_docs_from_website, scrape_website
from src.services.document_tracker import DocumentTracker


async def create_collection(collection_input: CollectionCreate):
    collection_start_url = collection_input.start_url.rstrip("/")

    print(f"Extracting documents from {collection_start_url}")

    docs, num_pages = await extract_docs_from_website(
        start_url=collection_start_url,
        max_pages=collection_input.max_pages,
        include_pattern=collection_input.include_pattern,
        exclude_pattern=collection_input.exclude_pattern,
        proxy_urls=collection_input.proxy_urls,
    )

    print(f"Successfully extracted {len(docs)} documents from {num_pages} pages")

    vector_store_service = VectorStoreService()

    collection_id = vector_store_service.create_collection(
        name=collection_input.name,
        source=collection_input.source,
        start_url=collection_start_url,
        num_pages=num_pages,
        include_pattern=collection_input.include_pattern,
        exclude_pattern=collection_input.exclude_pattern,
    )

    print(f"Adding {len(docs)} documents to collection {collection_input.name}")

    doc_ids = vector_store_service.add_documents(collection_input.name, docs)

    print(
        f"Successfully added {len(doc_ids)} documents to collection {collection_input.name}"
    )

    return CollectionResponse(
        id=collection_id,
        name=collection_input.name,
        source=collection_input.source,
        start_url=collection_start_url,
        num_pages=num_pages,
        num_documents=len(doc_ids),
        include_pattern=collection_input.include_pattern,
        exclude_pattern=collection_input.exclude_pattern,
    )


def search_collection(collection_name: str, query: str):
    vector_store_service = VectorStoreService()
    return vector_store_service.search_collection(collection_name, query)


def get_collection(collection_name: str):
    vector_store_service = VectorStoreService()
    return vector_store_service.get_collection(collection_name)


def get_collection_documents(collection_name: str):
    vector_store_service = VectorStoreService()
    return vector_store_service.get_collection_documents(collection_name)


def get_all_collections():
    vector_store_service = VectorStoreService()
    return vector_store_service.get_all_collections()


def delete_collection(collection_name: str):
    vector_store_service = VectorStoreService()
    vector_store_service.delete_collection(collection_name)


async def update_collection(
    collection_name: str, collection_input: CollectionUpdate | None = None
):
    vector_store_service = VectorStoreService()
    existing_collection = vector_store_service.get_collection(collection_name)

    docs, num_pages = await extract_docs_from_website(
        start_url=existing_collection.start_url,
        max_pages=existing_collection.num_pages,
        include_pattern=existing_collection.include_pattern,
        exclude_pattern=existing_collection.exclude_pattern,
        proxy_urls=collection_input.proxy_urls if collection_input else None,
    )

    vector_store_service.delete_collection_documents(collection_name)

    doc_ids = vector_store_service.add_documents(collection_name, docs)

    return CollectionResponse(
        id=existing_collection.id,
        name=collection_name,
        source=existing_collection.source,
        start_url=existing_collection.start_url,
        num_pages=num_pages,
        num_documents=len(doc_ids),
        include_pattern=existing_collection.include_pattern,
        exclude_pattern=existing_collection.exclude_pattern,
    )


async def test_collection(collection_name: str):
    vector_store_service = VectorStoreService()
    existing_collection = vector_store_service.get_collection(collection_name)

    pages = await scrape_website(
        start_url=existing_collection.start_url,
        max_pages=existing_collection.num_pages,
        include_pattern=existing_collection.include_pattern,
        exclude_pattern=existing_collection.exclude_pattern,
        proxy_urls=None,
    )

    new_docs: list[CollectionDocument] = []
    for page in pages:
        chunks = split_markdown_content(page)
        new_docs.extend(chunks)

    new_doc_ids = [doc.id for doc in new_docs]

    docs_to_add: list[CollectionDocument] = []

    document_tracker = DocumentTracker(
        namespace=collection_name, redis_url="redis://localhost:6379"
    )

    for doc in new_docs:
        if not document_tracker.exists(doc.id):
            docs_to_add.append(doc)
            document_tracker.add(doc.id)

    doc_ids_to_add = [doc.id for doc in docs_to_add]

    existing_doc_ids = document_tracker.get_all_ids()

    doc_ids_to_remove = list(set(existing_doc_ids) - set(new_doc_ids))

    for doc_id in doc_ids_to_remove:
        document_tracker.remove(doc_id)

    return {
        "doc_ids_to_remove": doc_ids_to_remove,
        "doc_ids_to_add": doc_ids_to_add,
    }


# Tasks
@celery_app.task
def create_collection_task(collection_input_dict: dict[str, Any]):
    collection_input = CollectionCreate(**collection_input_dict)

    current_task.update_state(state="PROCESSING")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(create_collection(collection_input))
    finally:
        loop.close()

    return result.model_dump()


@celery_app.task
def update_collection_task(
    collection_name: str, collection_input_dict: dict[str, Any] | None = None
):
    collection_input = (
        CollectionUpdate(**collection_input_dict) if collection_input_dict else None
    )

    current_task.update_state(state="PROCESSING")

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            update_collection(collection_name, collection_input)
        )
    finally:
        loop.close()

    return result.model_dump()
