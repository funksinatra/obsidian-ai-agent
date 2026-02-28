"""FastAPI application entry point.

This module creates and configures the FastAPI application with:
- Lifespan event management for startup/shutdown
- Structured logging setup
- Request/response middleware
- CORS support
- Agent tool registration
- Health check endpoints
- Global exception handlers
- Root API endpoint
"""

import importlib
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.core.config import get_settings
from app.core.exceptions import setup_exception_handlers
from app.core.health import router as health_router
from app.core.logging import get_logger, setup_logging
from app.core.middleware import setup_middleware
from app.features.chat.routes import router as chat_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
    """Application lifespan event handler.

    Handles startup and shutdown logic:
    - Startup: Configure logging, validate vault configuration, log application start
    - Shutdown: Log application shutdown

    Args:
        _application: The FastAPI application instance (unused, required by protocol).

    Yields:
        None: Control returns to the application.
    """
    # Startup
    setup_logging(log_level=settings.log_level)
    logger = get_logger(__name__)
    logger.info(
        "application.lifecycle_started",
        app_name=settings.app_name,
        version=settings.version,
        environment=settings.environment,
    )
    logger.info(
        "vault.config_validated",
        vault_path=str(settings.obsidian_vault_path),
    )

    yield

    # Shutdown
    logger.info("application.lifecycle_stopped", app_name=settings.app_name)


application = FastAPI(
    title=settings.app_name,
    version=settings.version,
    lifespan=lifespan,
)

setup_middleware(application)

setup_exception_handlers(application)

# Side-effect import: registers ping tool on vault_agent via @vault_agent.tool decorator
importlib.import_module("app.features.ping.tools")

application.include_router(health_router)
application.include_router(chat_router)


@application.get("/")
def read_root() -> dict[str, str]:
    """Root endpoint providing API information.

    Returns:
        Dict containing application name, version, and docs URL.
    """
    return {
        "message": settings.app_name,
        "version": settings.version,
        "docs": "/docs",
    }


if __name__ == "__main__":
    # S104: Binding to 0.0.0.0 is intentional for development/container environments.
    # This code path is ONLY used for:
    # 1. Local development (note reload=True)
    # 2. Docker containers where binding to all interfaces is required
    #
    # PRODUCTION DEPLOYMENT: Always use uvicorn CLI or gunicorn with explicit
    # host configuration (e.g., --host 127.0.0.1) instead of running this file directly.
    uvicorn.run(
        "app.main:application",
        host="0.0.0.0",  # noqa: S104
        port=8000,
        reload=True,
    )
