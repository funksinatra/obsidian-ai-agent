"""Health check endpoints for monitoring application status."""

from fastapi import APIRouter

from app.core.config import get_settings

# Health check endpoints are typically at root (no prefix)
router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Basic health check endpoint.

    Returns:
        dict: Health status of the API service.

    Example response:
        {"status": "healthy", "service": "api"}
    """
    settings = get_settings()
    return {"status": "healthy", "service": "paddy", "version": settings.version}
