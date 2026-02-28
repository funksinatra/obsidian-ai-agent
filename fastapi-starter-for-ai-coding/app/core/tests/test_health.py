"""Unit tests for health check endpoints."""

import pytest

from app.core.health import health_check


@pytest.mark.asyncio
async def test_health_check_returns_healthy() -> None:
    """Test that basic health check returns healthy status."""
    response = await health_check()

    assert response["status"] == "healthy"
    assert response["service"] == "paddy"
    assert "version" in response
