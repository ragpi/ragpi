from enum import Enum
import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded


class ResourceType(str, Enum):
    REPOSITORY = "repository"
    TASK = "task"


class ResourceNotFoundException(Exception):
    def __init__(self, resource_type: ResourceType, identifier: str):
        self.resource_type = resource_type
        self.identifier = identifier
        super().__init__(f"{resource_type.capitalize()} '{identifier}' not found")


class ResourceAlreadyExistsException(Exception):
    def __init__(self, resource_type: ResourceType, identifier: str):
        self.resource_type = resource_type
        self.identifier = identifier
        super().__init__(f"{resource_type.capitalize()} '{identifier}' already exists")


class ResourceLockedException(Exception):
    def __init__(self, resource_name: str):
        self.resource_name = resource_name
        super().__init__(f"Resource '{resource_name}' is locked")


class SiteMapCrawlerException(Exception):
    pass


class RepositorySyncException(Exception):
    pass


def resource_not_found_handler(request: Request, exc: ResourceNotFoundException):
    logging.error(exc)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


def resource_already_exists_handler(
    request: Request, exc: ResourceAlreadyExistsException
):
    logging.error(exc)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


def unexpected_exception_handler(request: Request, exc: Exception):
    logging.error(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred"},
    )


def rate_limit_exception_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={"detail": "Too many requests. Please try again later."},
    )
