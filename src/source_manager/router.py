from fastapi import APIRouter, status, Depends

from src.common.exceptions import (
    ResourceType,
    resource_already_exists_response,
    resource_locked_response,
    resource_not_found_response,
)
from src.common.schemas import Document
from src.common.workers_enabled_check import workers_enabled_check
from src.source_manager.dependencies import get_source_manager
from src.source_manager.schemas import (
    SearchSourceInput,
    CreateSourceRequest,
    SourceMetadata,
    SourceTask,
    UpdateSourceRequest,
)
from src.source_manager.service import SourceManagerService


router = APIRouter(
    prefix="/sources",
    tags=["sources"],
)


@router.get("")
def list_sources(
    source_manager: SourceManagerService = Depends(get_source_manager),
) -> list[SourceMetadata]:
    return source_manager.list_sources()


@router.post(
    "",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(workers_enabled_check)],
    responses={**resource_already_exists_response(ResourceType.SOURCE)},
)
def create_source(
    source_input: CreateSourceRequest,
    source_manager: SourceManagerService = Depends(get_source_manager),
) -> SourceTask:
    return source_manager.create_source(source_input)


@router.get(
    "/{source_name}", responses={**resource_not_found_response(ResourceType.SOURCE)}
)
def get_source(
    source_name: str, source_manager: SourceManagerService = Depends(get_source_manager)
) -> SourceMetadata:
    return source_manager.get_source(source_name)


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
    source_manager: SourceManagerService = Depends(get_source_manager),
) -> SourceTask:
    return source_manager.update_source(source_name, source_input)


@router.delete(
    "/{source_name}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        **resource_not_found_response(ResourceType.SOURCE),
        **resource_locked_response(ResourceType.SOURCE),
    },
)
def delete_source(
    source_name: str, source_manager: SourceManagerService = Depends(get_source_manager)
):
    source_manager.delete_source(source_name)


@router.get(
    "/{source_name}/documents",
    responses={**resource_not_found_response(ResourceType.SOURCE)},
)
def get_source_documents(
    source_name: str,
    limit: int = 100,
    offset: int = 0,
    source_manager: SourceManagerService = Depends(get_source_manager),
) -> list[Document]:
    return source_manager.get_source_documents(source_name, limit, offset)


@router.get(
    "/{source_name}/search",
    responses={**resource_not_found_response(ResourceType.SOURCE)},
)
def search_source(
    source_name: str,
    query: str,
    top_k: int = 10,
    source_manager: SourceManagerService = Depends(get_source_manager),
) -> list[Document]:
    return source_manager.search_source(
        SearchSourceInput(name=source_name, query=query, top_k=top_k)
    )
