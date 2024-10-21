import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse


class RepositoryNotFoundException(Exception):
    def __init__(self, repository_name: str):
        self.repository_name = repository_name
        super().__init__(f"Repository '{repository_name}' not found")


class RepositoryAlreadyExistsException(Exception):
    def __init__(self, repository_name: str):
        self.repository_name = repository_name
        super().__init__(f"Repository '{repository_name}' already exists")


# TODO: add init method with repository_name
class LockedRepositoryException(Exception):
    pass


async def repository_not_found_handler(
    request: Request, exc: RepositoryNotFoundException
):
    logging.error(exc)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


async def unexpected_exception_handler(request: Request, exc: Exception):
    logging.error(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred"},
    )
