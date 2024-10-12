from fastapi import APIRouter, HTTPException, status


from src.celery import celery_app
from src.schemas.repository import (
    RepositoryTask,
    RepositoryCreate,
    RepositoryUpdate,
    RepositorySearchInput,
)
from src.services import repository as repository_service
from src.tasks import create_repository_task, update_repository_task

router = APIRouter(
    prefix="/repositories",
    tags=[
        "repositories",
    ],
    responses={404: {"description": "Not found"}},
)


@router.get("/status")
def task_status(task_id: str) -> RepositoryTask:
    # TODO: Return 404 if task_id not found
    task = celery_app.AsyncResult(task_id)

    if task.status == "LOCKED":  # type: ignore
        return RepositoryTask(
            task_id=task_id, status="FAILURE", error=task.info["message"]
        )

    return RepositoryTask(
        task_id=task.task_id,
        status=task.status,
        error=str(task.result) if task.failed() else None,
    )


@router.get("/")
def get_all_repositories():
    try:
        repositories = repository_service.get_all_repositories()

        return repositories
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
def create_repository(repository_input: RepositoryCreate):

    try:
        task = create_repository_task.delay(
            repository_input.name, repository_input.model_dump()
        )

        return RepositoryTask(task_id=task.task_id, status=task.status)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{repository_name}")
def get_repository(repository_name: str):
    try:
        results = repository_service.get_repository(repository_name)

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{repository_name}")
def delete_repository(repository_name: str):
    try:
        repository_service.delete_repository(repository_name)

        return {"message": f"Repository '{repository_name}' deleted"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{repository_name}", status_code=status.HTTP_202_ACCEPTED)
async def update_repository(
    repository_name: str, repository_input: RepositoryUpdate | None = None
):
    try:
        task = update_repository_task.delay(
            repository_name, repository_input.model_dump() if repository_input else None
        )

        return RepositoryTask(task_id=task.task_id, status=task.status)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{repository_name}/documents")
def get_repository_documents(repository_name: str):
    try:
        results = repository_service.get_repository_documents(repository_name)

        return results

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{repository_name}/search")
def search_repository(repository_name: str, query_input: RepositorySearchInput):
    try:
        results = repository_service.search_repository(
            repository_name, query_input.query
        )

        return results

    # TODO: Implement custom exception handling. May need to add it in a way that can be applied to all routes
    # except RepositoryNotFoundException:
    #     raise HTTPException(status_code=404, detail=f"Repository '{repository_name}' not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
