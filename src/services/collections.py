import asyncio
from typing import Any
from celery import current_task

from src.celery import celery_app
from src.schemas.collections import CollectionCreate, CollectionResponse
from src.services.vector_store import VectorStoreService
from src.utils.web_scraper import extract_docs_from_website


async def create_collection(collection_input: CollectionCreate):
    collection_start_url = collection_input.start_url.rstrip("/")

    print(f"Extracting documents from {collection_start_url}")

    docs, num_pages = await extract_docs_from_website(
        start_url=collection_start_url,
        max_pages=collection_input.max_pages,
        include_pattern=collection_input.include_pattern,
        exclude_pattern=collection_input.exclude_pattern,
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

    doc_ids = await vector_store_service.add_documents(collection_input.name, docs)

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


# update
async def update_collection(collection_name: str):
    vector_store_service = VectorStoreService()
    existing_collection = vector_store_service.get_collection(collection_name)

    docs, num_pages = await extract_docs_from_website(
        start_url=existing_collection.start_url,
        max_pages=existing_collection.num_pages,
        include_pattern=existing_collection.include_pattern,
        exclude_pattern=existing_collection.exclude_pattern,
    )

    vector_store_service.delete_collection_documents(collection_name)

    doc_ids = await vector_store_service.add_documents(collection_name, docs)

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

    # Return the result
    return result.model_dump()
