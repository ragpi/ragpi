from fastapi import APIRouter, HTTPException, status


from src.celery import celery_app
from src.schemas.collections import (
    CollectionTask,
    CollectionCreate,
    CollectionUpdate,
    SearchInput,
)
from src.services import collections as collection_service

router = APIRouter(
    prefix="/collections",
    tags=[
        "collections",
    ],
    responses={404: {"description": "Not found"}},
)


@router.get("/status")
def task_status(task_id: str) -> CollectionTask:
    task = celery_app.AsyncResult(task_id)
    return CollectionTask(
        task_id=task.task_id,
        status=task.status,
        error=str(task.result) if task.failed() else None,
    )


@router.get("/")
def get_all_collections():
    try:
        collections = collection_service.get_all_collections()

        return collections
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
def create_collection(collection_input: CollectionCreate):

    try:
        task = collection_service.create_collection_task.delay(
            collection_input.model_dump()
        )

        return CollectionTask(task_id=task.task_id, status=task.status)

    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))


@router.get("/{collection_name}")
def get_collection(collection_name: str):
    try:
        results = collection_service.get_collection(collection_name)

        return results

    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))


@router.delete("/{collection_name}")
def delete_collection(collection_name: str):
    try:
        collection_service.delete_collection(collection_name)

        return {"message": f"Collection '{collection_name}' deleted"}

    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))


@router.put("/{collection_name}", status_code=status.HTTP_202_ACCEPTED)
async def update_collection(
    collection_name: str, collection_input: CollectionUpdate | None = None
):
    try:
        task = collection_service.update_collection_task.delay(
            collection_name, collection_input.model_dump() if collection_input else None
        )

        return CollectionTask(task_id=task.task_id, status=task.status)

    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))


@router.get("/{collection_name}/documents")
def get_collection_documents(collection_name: str):
    try:
        results = collection_service.get_collection_documents(collection_name)

        return results

    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))


@router.get("/{collection_name}/search")
def search_collection(collection_name: str, query_input: SearchInput):
    try:
        results = collection_service.search_collection(
            collection_name, query_input.query
        )

        return results

    # TODO: Implement custom exception handling. May need to add it in a way that can be applied to all routes
    # except CollectionNotFoundException:
    #     raise HTTPException(status_code=404, detail=f"Collection '{collection_name}' not found")
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))


@router.put("/{collection_name}/test")
async def test_collection(collection_name: str):
    try:
        response = await collection_service.test_collection(collection_name)

        return response
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))
