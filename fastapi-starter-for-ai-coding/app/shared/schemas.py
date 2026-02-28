"""Shared Pydantic schemas for common patterns."""

from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Standard error response format.

    Used by exception handlers to provide consistent error responses
    across the API.

    Example:
        @app.exception_handler(ValueError)
        def value_error_handler(request: Request, exc: ValueError):
            return JSONResponse(
                status_code=400,
                content=ErrorResponse(
                    error=str(exc),
                    type="validation_error",
                    detail="Invalid input provided"
                ).model_dump()
            )
    """

    error: str
    type: str
    detail: str | None = None
