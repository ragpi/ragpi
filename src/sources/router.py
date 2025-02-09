from fastapi import APIRouter, status, Depends

from src.common.exceptions import (
    ResourceType,
    resource_already_exists_response,
    resource_locked_response,
    resource_not_found_response,
)
from src.document_store.schemas import Document
from src.common.workers_enabled_check import workers_enabled_check
from src.sources.dependencies import get_source_service
from src.sources.metadata.schemas import SourceMetadata
from src.sources.schemas import (
    CreateSourceRequest,
    SourceTask,
    UpdateSourceRequest,
)
from src.sources.service import SourceService


router = APIRouter(
    prefix="/sources",
    tags=["Sources"],
)


@router.get("")
def list_sources(
    source_service: SourceService = Depends(get_source_service),
) -> list[SourceMetadata]:
    return source_service.list_sources()


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(workers_enabled_check)],
    responses={**resource_already_exists_response(ResourceType.SOURCE)},
)
def create_source(
    source_input: CreateSourceRequest,
    source_service: SourceService = Depends(get_source_service),
) -> SourceTask:
    return source_service.create_source(source_input)


@router.get(
    "/{source_name}", responses={**resource_not_found_response(ResourceType.SOURCE)}
)
def get_source(
    source_name: str, source_service: SourceService = Depends(get_source_service)
) -> SourceMetadata:
    return source_service.get_source(source_name)


@router.put(
    "/{source_name}",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(workers_enabled_check)],
    responses={
        **resource_not_found_response(ResourceType.SOURCE),
        **resource_locked_response(ResourceType.SOURCE),
    },
)
def update_source(
    source_name: str,
    source_input: UpdateSourceRequest,
    source_service: SourceService = Depends(get_source_service),
) -> SourceTask:
    return source_service.update_source(source_name, source_input)


@router.delete(
    "/{source_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **resource_not_found_response(ResourceType.SOURCE),
        **resource_locked_response(ResourceType.SOURCE),
    },
)
def delete_source(
    source_name: str, source_service: SourceService = Depends(get_source_service)
):
    source_service.delete_source(source_name)


@router.get(
    "/{source_name}/documents",
    responses={**resource_not_found_response(ResourceType.SOURCE)},
)
def get_source_documents(
    source_name: str,
    limit: int = 100,
    offset: int = 0,
    source_service: SourceService = Depends(get_source_service),
) -> list[Document]:
    return source_service.get_source_documents(source_name, limit, offset)


# TODO: Update search endpoint querying
@router.get(
    "/{source_name}/search",
    responses={**resource_not_found_response(ResourceType.SOURCE)},
)
def search_source(
    source_name: str,
    query: str,
    top_k: int = 10,
    source_service: SourceService = Depends(get_source_service),
) -> list[Document]:
    return source_service.search_source(
        source_name=source_name,
        semantic_query=query,
        full_text_query=query,
        top_k=top_k,
    )
