from fastapi import APIRouter, HTTPException


from src.celery import celery_app
from src.schemas.collections import CollectionTask, CollectionCreate, SearchInput
from src.services import collections as collection_service

router = APIRouter(
    prefix="/collections",
    tags=[
        "collections",
    ],
    responses={404: {"description": "Not found"}},
)


@router.get("/status")
def status(task_id: str) -> CollectionTask:
    task = celery_app.AsyncResult(task_id)  # type: ignore
    return CollectionTask(task_id=task.task_id, status=task.status)  # type: ignore


@router.get("/")
def get_all_collections():
    try:
        collections = collection_service.get_all_collections()

        return collections
    except Exception as e:
        return HTTPException(status_code=500, detail=str(e))


@router.post("/")
def create_collection(collection_input: CollectionCreate):

    try:
        # TODO: Try apply_async instead of delay?
        task = collection_service.create_collection_task.delay(collection_input.model_dump())  # type: ignore

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


@router.put("/{collection_name}")
async def update_collection(collection_name: str):
    try:
        await collection_service.update_collection(collection_name)

        return {"message": f"Collection '{collection_name}' updated"}

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
def query_collection(collection_name: str, query_input: SearchInput):
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
