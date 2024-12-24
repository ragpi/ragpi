from enum import Enum
import logging
from fastapi import Request, status
from fastapi.responses import JSONResponse


class ResourceType(str, Enum):
    SOURCE = "Source"
    TASK = "Task"
    MODEL = "Model"


class ResourceNotFoundException(Exception):
    def __init__(self, resource_type: ResourceType, identifier: str):
        self.resource_type = resource_type.value
        self.identifier = identifier
        super().__init__(f"{self.resource_type} '{identifier}' not found")


class ResourceAlreadyExistsException(Exception):
    def __init__(self, resource_type: ResourceType, identifier: str):
        self.resource_type = resource_type.value
        self.identifier = identifier
        super().__init__(f"{self.resource_type} '{identifier}' already exists")


class ResourceLockedException(Exception):
    def __init__(self, resource_type: ResourceType | None, identifier: str):
        self.resource_type = resource_type.value if resource_type else "Resource"
        self.identifier = identifier
        if resource_type == ResourceType.SOURCE:
            message = f"There is already a task running for source '{identifier}'"
        else:
            message = f"{self.resource_type} '{identifier}' is locked"
        super().__init__(message)


class KnownException(Exception):
    def __init__(self, message: str):
        super().__init__(message)


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


def resource_locked_handler(request: Request, exc: ResourceLockedException):
    logging.error(exc)
    return JSONResponse(
        status_code=status.HTTP_423_LOCKED,
        content={"detail": str(exc)},
    )


def known_exception_handler(request: Request, exc: KnownException):
    logging.error(exc)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


def unexpected_exception_handler(request: Request, exc: Exception):
    logging.error(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred"},
    )
