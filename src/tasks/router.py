from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from src.common.exceptions import ResourceType, resource_not_found_response
from src.common.workers_enabled_check import workers_enabled_check
from src.tasks.dependencies import get_task_service
from src.tasks.schemas import Task
from src.tasks.service import TaskService


router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"],
)


@router.get("")
def list_tasks(task_service: TaskService = Depends(get_task_service)) -> list[Task]:
    return task_service.list_tasks()


@router.get("/{task_id}", responses={**resource_not_found_response(ResourceType.TASK)})
def get_task(
    task_id: str, task_service: TaskService = Depends(get_task_service)
) -> Task:
    return task_service.get_task(task_id)


@router.post(
    "/{task_id}/terminate",
    dependencies=[Depends(workers_enabled_check)],
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {
            "description": "Task termination initiated",
            "content": {
                "application/json": {
                    "example": {"message": "Terminating task 'example'"}
                }
            },
        },
        **resource_not_found_response(ResourceType.TASK),
    },
)
def terminate_task(
    task_id: str, task_service: TaskService = Depends(get_task_service)
) -> JSONResponse:
    task_service.terminate_task(task_id)

    return JSONResponse(
        content={"message": f"Terminating task {task_id}"},
        status_code=status.HTTP_202_ACCEPTED,
    )
