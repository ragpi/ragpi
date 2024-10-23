from fastapi import APIRouter
from src.celery import celery_app
from src.schemas.task import TaskOverview


router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


@router.get("/{task_id}")
async def task_status(task_id: str) -> TaskOverview:
    # TODO: Return 404 if task_id not found
    task = celery_app.AsyncResult(task_id)

    if task.status == "LOCKED":  # type: ignore
        return TaskOverview(id=task_id, status="FAILURE", error=task.info["message"])

    return TaskOverview(
        id=task.task_id,
        status=task.status,
        error=str(task.result) if task.failed() else None,
        result=task.result if task.successful() else None,  # type: ignore
    )
