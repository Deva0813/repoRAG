import logging
import traceback

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from pymongo.errors import PyMongoError
from starlette.responses import JSONResponse

logger = logging.getLogger("app.error")


class ApiError(Exception):
    """Base class for all expected/handled application errors."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        error_code: str = "BAD_REQUEST",
        details: dict | list | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details
        self.stack = traceback.format_exc()


# ------------------------------ Error SubClass ------------------------------#


class NotFoundError(ApiError):
    def __init__(self, message: str = "Resource not found", details=None):
        super().__init__(message, status.HTTP_404_NOT_FOUND, "NOT_FOUND", details)


class UnauthorizedError(ApiError):
    def __init__(self, message: str = "Unauthorized", details=None):
        super().__init__(message, status.HTTP_401_UNAUTHORIZED, "UNAUTHORIZED", details)


class ForbiddenError(ApiError):
    def __init__(self, message: str = "Forbidden", details=None):
        super().__init__(message, status.HTTP_403_FORBIDDEN, "FORBIDDEN", details)


class ConflictError(ApiError):
    def __init__(self, message: str = "Conflict", details=None):
        super().__init__(message, status.HTTP_409_CONFLICT, "CONFLICT", details)


class ValidationApiError(ApiError):
    def __init__(self, message: str = "Validation failed", details=None):
        super().__init__(
            message, status.HTTP_422_UNPROCESSABLE_CONTENT, "VALIDATION_ERROR", details
        )


# ------------------------------ Error Response ------------------------------#


def _error_response(
    status_code: int, error_code: str, message: str, details=None
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": error_code,
                "message": message,
                "details": details,
            },
        },
    )


# ------------------------------ Error Handler ------------------------------#
def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(req: Request, exc: ApiError):
        logger.warning(f"{exc.error_code} at {req.url.path}: {exc.message}")
        return _error_response(
            exc.status_code, exc.error_code, exc.message, exc.details
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        logger.info(f"Validation error at {request.url.path}: {exc.errors()}")
        return _error_response(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "VALIDATION_ERROR",
            "Request validation failed",
            details=exc.errors(),
        )

    @app.exception_handler(PyMongoError)
    async def db_error_handler(request: Request, exc: PyMongoError):
        logger.error(f"DB error at {request.url.path}: {exc}")
        return _error_response(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "DATABASE_ERROR",
            f"A database error occurred : {exc} ",
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error at {request.url.path}: {exc}")
        return _error_response(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "INTERNAL_ERROR",
            "An unexpected error occurred",
        )
