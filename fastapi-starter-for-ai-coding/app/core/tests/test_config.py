"""Tests for app.core.config module."""

import os
from pathlib import Path
from unittest.mock import patch

from app.core.config import Settings, get_settings


def create_settings() -> Settings:
    """Create Settings instance for testing.

    Helper function for creating Settings in tests. pydantic-settings loads
    required fields from environment variables at runtime. Mypy's static analysis
    doesn't understand this and expects constructor arguments. This is a known
    limitation with pydantic-settings, so we suppress the call-arg error.

    Returns:
        Settings instance loaded from environment variables.
    """
    return Settings()


def test_settings_defaults() -> None:
    """Test Settings instantiation with default values.

    We explicitly override env vars that may come from .env to verify
    that the Settings class declares correct defaults.
    """
    env_overrides = {
        "LOG_LEVEL": "INFO",
        "OBSIDIAN_VAULT_PATH": "/vault",
        "LLM_API_KEY": "",
        "API_KEY": "",
    }
    with patch.dict(os.environ, env_overrides, clear=False):
        settings = create_settings()

        assert settings.app_name == "Paddy"
        assert settings.version == "0.1.0"
        assert settings.environment == "development"
        assert settings.log_level == "INFO"
        assert settings.llm_provider == "openai"
        assert settings.obsidian_vault_path == Path("/vault")
        assert "app://obsidian.md" in settings.allowed_origins
        assert "capacitor://localhost" in settings.allowed_origins


def test_settings_from_environment() -> None:
    """Test Settings can be overridden by environment variables."""
    with patch.dict(
        os.environ,
        {
            "APP_NAME": "Test App",
            "VERSION": "1.0.0",
            "ENVIRONMENT": "production",
            "LOG_LEVEL": "DEBUG",
            "LLM_PROVIDER": "anthropic",
            "LLM_MODEL": "claude-3-5-sonnet-latest",
            "OBSIDIAN_VAULT_PATH": "/Users/test-vault",
        },
    ):
        settings = create_settings()

        assert settings.app_name == "Test App"
        assert settings.version == "1.0.0"
        assert settings.environment == "production"
        assert settings.log_level == "DEBUG"
        assert settings.llm_provider == "anthropic"
        assert settings.llm_model == "claude-3-5-sonnet-latest"
        assert settings.obsidian_vault_path == Path("/Users/test-vault")


def test_model_name_property() -> None:
    """Test model_name builds provider:model value."""
    with patch.dict(os.environ, {"LLM_PROVIDER": "openai", "LLM_MODEL": "gpt-4.1-nano"}):
        settings = create_settings()
        assert settings.model_name == "openai:gpt-4.1-nano"


def test_allowed_origins_parsing() -> None:
    """Test allowed_origins parsing from environment variable.

    Note: pydantic-settings expects JSON array format for list fields.
    """
    with patch.dict(
        os.environ,
        {
            "ALLOWED_ORIGINS": '["app://obsidian.md","capacitor://localhost","http://test.com"]',
        },
    ):
        settings = create_settings()

        assert len(settings.allowed_origins) == 3
        assert "app://obsidian.md" in settings.allowed_origins
        assert "capacitor://localhost" in settings.allowed_origins
        assert "http://test.com" in settings.allowed_origins


def test_get_settings_caching() -> None:
    """Test get_settings() returns cached instance."""
    # Clear the cache first
    get_settings.cache_clear()

    settings1 = get_settings()
    settings2 = get_settings()

    # Should return the same instance (cached)
    assert settings1 is settings2


def test_settings_case_insensitive() -> None:
    """Test settings are case-insensitive."""
    with patch.dict(
        os.environ,
        {
            "app_name": "Lower Case App",
            "ENVIRONMENT": "PRODUCTION",
            "llm_provider": "google-gla",
        },
    ):
        settings = create_settings()

        assert settings.app_name == "Lower Case App"
        assert settings.environment == "PRODUCTION"
        assert settings.llm_provider == "google-gla"
