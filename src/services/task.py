import logging

from redis import Redis

from src.celery import celery_app
from src.config import settings
from src.decorators import lock_and_execute_repository_task
from src.exceptions import ResourceNotFoundException, ResourceType
from src.schemas.repository import (
    RepositoryMetadata,
)
from src.schemas.task import TaskStatus
from src.services.vector_store.service import get_vector_store_service
from src.utils.datetime import get_current_datetime
from src.utils.web_scraper import extract_docs_from_website


def task_exists(task_id: str) -> bool:
    redis_client = Redis.from_url(settings.REDIS_URL)

    key = f"celery-task-meta-{task_id}"

    return redis_client.exists(key) == 1


def get_task_status(task_id: str) -> TaskStatus:
    if not task_exists(task_id):
        raise ResourceNotFoundException(ResourceType.TASK, task_id)

    task = celery_app.AsyncResult(task_id)

    if task.status == "LOCKED":  # type: ignore
        return TaskStatus(id=task_id, status="FAILURE", error=task.info["message"])

    return TaskStatus(
        id=task.task_id,
        status=task.status,
        error=(
            "An error occurred, please check the task logs for more information"
            if task.failed()
            else None
        ),
        result=task.result if task.successful() else None,  # type: ignore
    )


@celery_app.task
@lock_and_execute_repository_task()
async def sync_repository_documents_task(
    repository_name: str,
    start_url: str,
    max_pages: int | None,
    include_pattern: str | None,
    exclude_pattern: str | None,
    proxy_urls: list[str] | None,
    chunk_size: int,
    chunk_overlap: int,
    existing_doc_ids: list[str],
):
    logging.info(f"Extracting documents from {start_url}")

    vector_store_service = get_vector_store_service(settings.VECTOR_STORE_PROVIDER)

    docs, num_pages = await extract_docs_from_website(
        start_url=start_url,
        max_pages=max_pages,
        include_pattern=include_pattern,
        exclude_pattern=exclude_pattern,
        proxy_urls=proxy_urls,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    logging.info(f"Successfully extracted {len(docs)} documents from {num_pages} pages")

    extracted_doc_ids = {doc.id for doc in docs}
    existing_doc_ids_set = set(existing_doc_ids)

    docs_to_add = [doc for doc in docs if doc.id not in existing_doc_ids_set]
    doc_ids_to_remove = existing_doc_ids_set - extracted_doc_ids

    if docs_to_add:
        logging.info(
            f"Adding {len(docs_to_add)} documents to repository {repository_name}"
        )
        await vector_store_service.add_repository_documents(
            repository_name, docs_to_add, timestamp=get_current_datetime()
        )
        logging.info(
            f"Successfully added {len(docs_to_add)} documents to repository {repository_name}"
        )

    if doc_ids_to_remove:
        logging.info(
            f"Removing {len(doc_ids_to_remove)} documents from repository {repository_name}"
        )
        await vector_store_service.delete_repository_documents(
            repository_name, list(doc_ids_to_remove)
        )
        logging.info(
            f"Successfully removed {len(doc_ids_to_remove)} documents from repository {repository_name}"
        )

    if not docs_to_add and not doc_ids_to_remove:
        logging.info("No changes detected in repository")
        existing_repository = await vector_store_service.get_repository(repository_name)
        return existing_repository.model_dump()

    updated_repository = await vector_store_service.update_repository_metadata(
        repository_name,
        RepositoryMetadata(
            start_url=start_url,
            num_pages=num_pages,
            include_pattern=include_pattern,
            exclude_pattern=exclude_pattern,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        ),
        get_current_datetime(),
    )

    return updated_repository.model_dump()
