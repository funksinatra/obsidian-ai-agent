"""Custom exception classes and global exception handlers."""

from typing import Any, cast

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


class PaddyError(Exception):
    """Base exception for Paddy application errors."""


class VaultError(PaddyError):
    """Base exception for vault-related errors."""


class NoteNotFoundError(VaultError):
    """Exception raised when a note is not found."""


class VaultPathError(VaultError):
    """Exception raised when a vault path is invalid."""


async def paddy_exception_handler(request: Request, exc: PaddyError) -> JSONResponse:
    """Handle Paddy exceptions globally."""
    logger.error(
        "vault.exception_raised",
        error_type=type(exc).__name__,
        error_message=str(exc),
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    if isinstance(exc, NoteNotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    elif isinstance(exc, VaultPathError):
        status_code = status.HTTP_400_BAD_REQUEST

    return JSONResponse(
        status_code=status_code,
        content={"error": str(exc), "type": type(exc).__name__},
    )


def setup_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers with the FastAPI application."""
    # FastAPI expects handler signatures that match the registered exception type.
    # We intentionally reuse one polymorphic handler across related exception classes.
    handler: Any = cast(Any, paddy_exception_handler)

    app.add_exception_handler(PaddyError, handler)
    app.add_exception_handler(VaultError, handler)
    app.add_exception_handler(NoteNotFoundError, handler)
    app.add_exception_handler(VaultPathError, handler)
