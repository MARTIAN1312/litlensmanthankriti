"""Error envelope (DESIGN §4.5) and global exception handlers (SECURITY L-1, L-3).

Clients only ever see `{"error": {"code", "message"}}`: no stack traces,
file paths or upstream bodies.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.models.schemas import ErrorCode, ErrorDetail, ErrorResponse

log = logging.getLogger("litlens.api")

_STATUS_TO_CODE: dict[int, ErrorCode] = {
    400: "VALIDATION_ERROR",
    404: "NOT_FOUND",
    405: "NOT_FOUND",
    409: "NOT_READY",
    422: "VALIDATION_ERROR",
    429: "RATE_LIMITED",
    502: "UPSTREAM_ERROR",
    503: "UPSTREAM_ERROR",
    504: "UPSTREAM_ERROR",
}


class AppError(Exception):
    """Raise from routes/services to return a specific error envelope."""

    def __init__(self, status_code: int, code: ErrorCode, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def error_response(status_code: int, code: ErrorCode, message: str) -> JSONResponse:
    body = ErrorResponse(error=ErrorDetail(code=code, message=message))
    return JSONResponse(status_code=status_code, content=body.model_dump())


def _validation_message(exc: RequestValidationError) -> str:
    """Short, human-readable summary of the first validation problem."""
    errors = exc.errors()
    if not errors:
        return "Invalid request."
    first = errors[0]
    field = ".".join(str(p) for p in first.get("loc", ()) if p != "body")
    msg = str(first.get("msg", "invalid value"))
    return f"{field}: {msg}" if field else msg


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError) -> JSONResponse:
        return error_response(exc.status_code, exc.code, exc.message)

    @app.exception_handler(RequestValidationError)
    async def _validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return error_response(422, "VALIDATION_ERROR", _validation_message(exc))

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = _STATUS_TO_CODE.get(exc.status_code, "INTERNAL")
        message = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return error_response(exc.status_code, code, message)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:
        # Full trace stays in the server log only (L-3).
        log.exception(
            "unhandled error on %s %s: %s",
            request.method,
            request.url.path,
            type(exc).__name__,
        )
        return error_response(500, "INTERNAL", "Something went wrong on the server.")
