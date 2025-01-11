from enum import Enum
import logging
from typing import Any, Sequence
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from redis.exceptions import ConnectionError

logger = logging.getLogger(__name__)


class ResourceType(str, Enum):
    SOURCE = "Source"
    TASK = "Task"
    MODEL = "Model"


# Exceptions
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


# Exception handlers
def resource_not_found_handler(request: Request, exc: ResourceNotFoundException):
    logger.error(exc)
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)},
    )


def resource_already_exists_handler(
    request: Request, exc: ResourceAlreadyExistsException
):
    logger.error(exc)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={"detail": str(exc)},
    )


def resource_locked_handler(request: Request, exc: ResourceLockedException):
    logger.error(exc)
    return JSONResponse(
        status_code=status.HTTP_423_LOCKED,
        content={"detail": str(exc)},
    )


def known_exception_handler(request: Request, exc: KnownException):
    logger.error(exc)
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"detail": str(exc)},
    )


def unexpected_exception_handler(request: Request, exc: Exception):
    logger.error(exc)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An unexpected error occurred"},
    )


def redis_connection_error(request: Request, exc: ConnectionError):
    logger.error(f"Failed to connect to Redis: {exc}")
    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"detail": "Service unavailable"},
    )


def validation_exception_handler(request: Request, exc: RequestValidationError):
    def loc_to_dot_sep(loc: tuple[Any, ...]) -> str:
        path = ""
        for i, x in enumerate(loc):
            if isinstance(x, str):
                if i > 0:
                    path += "."
                path += x
            elif isinstance(x, int):
                path += f"[{x}]"
            else:
                raise TypeError("Unexpected type")
        return path

    def convert_errors(e: RequestValidationError) -> Sequence[Any]:
        new_errors: Sequence[Any] = e.errors()
        for error in new_errors:
            error["loc"] = loc_to_dot_sep(error["loc"])
        return new_errors

    errors = convert_errors(exc)

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "Validation error", "errors": errors},
    )


ResponseDict = dict[int | str, dict[str, Any]]


def resource_not_found_response(
    resource_type: ResourceType,
) -> ResponseDict:
    return {
        404: {
            "description": f"{resource_type.value} not found",
            "content": {
                "application/json": {
                    "example": {"detail": f"{resource_type.value} 'example' not found"}
                }
            },
        }
    }


def resource_already_exists_response(
    resource_type: ResourceType,
) -> ResponseDict:
    return {
        409: {
            "description": f"{resource_type.value} already exists",
            "content": {
                "application/json": {
                    "example": {
                        "detail": f"{resource_type.value} 'example' already exists"
                    }
                }
            },
        }
    }


def resource_locked_response(resource_type: ResourceType) -> ResponseDict:
    return {
        423: {
            "description": f"{resource_type.value} locked",
            "content": {
                "application/json": {
                    "example": {"detail": f"{resource_type.value} 'example' is locked"}
                }
            },
        }
    }


service_unavailable_response: ResponseDict = {
    503: {
        "description": "Service unavailable",
        "content": {"application/json": {"example": {"detail": "Service unavailable"}}},
    }
}

internal_error_response: ResponseDict = {
    500: {
        "description": "Internal server error",
        "content": {
            "application/json": {"example": {"detail": "An unexpected error occurred"}}
        },
    }
}

validation_error_response: ResponseDict = {
    422: {
        "description": "Validation error",
        "content": {
            "application/json": {
                "example": {
                    "detail": "Validation error",
                    "errors": [
                        {
                            "loc": "field",
                            "msg": "error message",
                            "type": "type",
                        }
                    ],
                }
            }
        },
    }
}
