from fastapi import APIRouter

from src.task.service import get_task_status


router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


@router.get("/{task_id}")
def get_task(task_id: str):
    return get_task_status(task_id)
