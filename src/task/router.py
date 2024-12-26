from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from src.task.dependencies import get_task_service
from src.task.service import TaskService


router = APIRouter(
    prefix="/tasks",
    tags=["tasks"],
)


@router.get("")
def get_all_tasks(task_service: TaskService = Depends(get_task_service)):
    return task_service.get_all_tasks()


@router.get("/{task_id}")
def get_task(task_id: str, task_service: TaskService = Depends(get_task_service)):
    return task_service.get_task(task_id)


@router.post("/{task_id}/terminate")
def terminate_task(task_id: str, task_service: TaskService = Depends(get_task_service)):
    task_service.terminate_task(task_id)

    return JSONResponse(
        content={"message": f"Terminating task {task_id}"},
        status_code=200,
    )
