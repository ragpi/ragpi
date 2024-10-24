from fastapi import APIRouter, status, Depends

from src.repository.schemas import (
    RepositoryCreateInput,
    RepositorySearchInput,
    RepositoryTaskResponse,
    RepositoryUpdateInput,
)
from src.repository.service import RepositoryService


router = APIRouter(
    prefix="/repositories",
    tags=["repositories"],
)


@router.get("/")
async def get_all_repositories(repository_service: RepositoryService = Depends()):
    repositories = await repository_service.get_all_repositories()
    return repositories


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
async def create_repository(
    repository_input: RepositoryCreateInput,
    repository_service: RepositoryService = Depends(),
):
    repository, task_id = await repository_service.create_repository(repository_input)

    return RepositoryTaskResponse(
        repository=repository,
        task_id=task_id,
        message="Repository has been created and documents are being synced. Check the task status for updates.",
    )


@router.get("/{repository_name}")
async def get_repository(
    repository_name: str, repository_service: RepositoryService = Depends()
):
    results = await repository_service.get_repository(repository_name)
    return results


@router.delete("/{repository_name}")
async def delete_repository(
    repository_name: str, repository_service: RepositoryService = Depends()
):
    await repository_service.delete_repository(repository_name)
    return {"message": f"Repository '{repository_name}' deleted"}


@router.put("/{repository_name}", status_code=status.HTTP_202_ACCEPTED)
async def update_repository(
    repository_name: str,
    repository_input: RepositoryUpdateInput | None = None,
    repository_service: RepositoryService = Depends(),
):
    repository, task_id = await repository_service.update_repository(
        repository_name, repository_input
    )

    return RepositoryTaskResponse(
        repository=repository,
        task_id=task_id,
        message="A task has been created to sync the repository documents. Check the task status for updates.",
    )


@router.get("/{repository_name}/documents")
async def get_repository_documents(
    repository_name: str,
    limit: int | None = None,
    offset: int | None = None,
    repository_service: RepositoryService = Depends(),
):
    results = await repository_service.get_repository_documents(
        repository_name, limit, offset
    )
    return results


@router.get("/{repository_name}/search")
async def search_repository(
    repository_name: str,
    query_input: RepositorySearchInput,
    repository_service: RepositoryService = Depends(),
):
    results = await repository_service.search_repository(
        repository_name, query_input.query, query_input.num_results or 10
    )
    return results
