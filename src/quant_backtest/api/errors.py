"""Unified RFC 7807-style error envelope for the API."""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


def _envelope(code: str, message: str, status_code: int, details: dict | None = None) -> JSONResponse:
    body: dict = {"error": {"code": code, "message": message}}
    if details:
        body["error"]["details"] = details
    return JSONResponse(status_code=status_code, content=body)


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def _http_exc(request: Request, exc: StarletteHTTPException):
        return _envelope(
            code=f"http_{exc.status_code}",
            message=str(exc.detail) if exc.detail else "HTTP error",
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def _validation_exc(request: Request, exc: RequestValidationError):
        return _envelope(
            code="validation_error",
            message="Request validation failed",
            status_code=422,
            details={"errors": exc.errors()},
        )

    @app.exception_handler(Exception)
    async def _internal_exc(request: Request, exc: Exception):
        return _envelope(
            code="internal_error",
            message=f"{type(exc).__name__}: {exc}",
            status_code=500,
        )
