from fastapi import APIRouter, status, Depends

from src.source.dependencies import get_source_service
from src.source.schemas import (
    SearchSourceInput,
    CreateSourceRequest,
    SearchSourceRequest,
    UpdateSourceRequest,
)
from src.source.service import SourceService


router = APIRouter(
    prefix="/sources",
    tags=["sources"],
)


@router.get("/")
def get_all_sources(source_service: SourceService = Depends(get_source_service)):
    sources = source_service.get_all_sources()
    return sources


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
def create_source(
    source_input: CreateSourceRequest,
    source_service: SourceService = Depends(get_source_service),
):
    return source_service.create_source(source_input)


@router.get("/{source_name}")
def get_source(
    source_name: str, source_service: SourceService = Depends(get_source_service)
):
    results = source_service.get_source(source_name)
    return results


@router.delete("/{source_name}")
def delete_source(
    source_name: str, source_service: SourceService = Depends(get_source_service)
):
    source_service.delete_source(source_name)
    return {"message": f"Source '{source_name}' deleted"}


@router.put("/{source_name}", status_code=status.HTTP_202_ACCEPTED)
def update_source(
    source_name: str,
    source_input: UpdateSourceRequest,
    source_service: SourceService = Depends(get_source_service),
):
    return source_service.update_source(source_name, source_input)


@router.get("/{source_name}/documents")
def get_source_documents(
    source_name: str,
    limit: int | None = None,
    offset: int | None = None,
    source_service: SourceService = Depends(get_source_service),
):
    results = source_service.get_source_documents(source_name, limit, offset)
    return results


@router.get("/{source_name}/search")
def search_source(
    source_name: str,
    query_input: SearchSourceRequest,
    source_service: SourceService = Depends(get_source_service),
):
    results = source_service.search_source(
        SearchSourceInput(
            name=source_name, query=query_input.query, top_k=query_input.top_k
        )
    )
    return results
