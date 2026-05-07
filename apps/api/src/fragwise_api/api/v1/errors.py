"""Error envelope + FastAPI exception handlers."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Closed taxonomy of error codes used in the envelope.
# Mapped from HTTP status by `_code_for_status`.
ERROR_CODES = {
    "not_found",  # 404 — slug or resource missing
    "method_not_allowed",  # 405 — HTTP method not supported on route
    "conflict",  # 409 — state conflict
    "invalid_params",  # 422 — Pydantic / Query validation failure
    "http_error",  # any other 4xx
    "internal_error",  # 500 — unhandled exception
}


class ApiError(HTTPException):
    """Application-typed HTTP error; maps to the error envelope."""

    def __init__(
        self,
        *,
        status_code: int,
        code: str,
        message: str,
        detail: Any = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=message)
        self.code = code
        self.message = message
        self.envelope_detail = detail


def errors_envelope(code: str, message: str, detail: Any = None) -> dict[str, Any]:
    return {"error": {"code": code, "message": message, "detail": detail}}


async def _api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    return JSONResponse(
        status_code=exc.status_code,
        content=errors_envelope(exc.code, exc.message, exc.envelope_detail),
    )


def _code_for_status(status: int) -> str:
    """Map HTTP status to closed-taxonomy error code (W1)."""
    if status == 404:
        return "not_found"
    if status == 405:
        return "method_not_allowed"
    if status == 409:
        return "conflict"
    if status == 422:
        return "invalid_params"
    if status >= 500:
        return "internal_error"
    if 400 <= status < 500:
        return "http_error"
    return "http_error"


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    return JSONResponse(
        status_code=exc.status_code,
        content=errors_envelope(_code_for_status(exc.status_code), str(exc.detail), None),
    )


async def _validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    # W7: filter Pydantic error dicts to drop `input` and `ctx` (these reflect
    # user-supplied data and are a reflected-input surface). Keep only the
    # safe trio: `loc`, `msg`, `type`.
    cleaned_errors = [
        {"loc": list(e["loc"]), "msg": e["msg"], "type": e["type"]} for e in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=errors_envelope("invalid_params", "Invalid request parameters", cleaned_errors),
    )


async def _unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(
        status_code=500,
        content=errors_envelope("internal_error", "Internal server error", None),
    )


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error_handler)
    app.add_exception_handler(HTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(Exception, _unhandled_exception_handler)


def not_found(resource: str, slug: str) -> ApiError:
    return ApiError(
        status_code=404,
        code="not_found",
        message=f"{resource} with slug '{slug}' not found",
        detail={"slug": slug},
    )
