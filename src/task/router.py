from fastapi import APIRouter, Depends

from src.task.service import TaskService


router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


@router.get("/{task_id}")
def get_task(task_id: str, task_service: TaskService = Depends()):
    return task_service.get_task_status(task_id)
