"""Application configuration using pydantic-settings.

This module provides centralized configuration management:
- Environment variable loading from .env file
- Type-safe settings with validation
- Cached settings instance with @lru_cache
- Settings for application, CORS, and future database configuration
"""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide configuration.

    All settings can be overridden via environment variables.
    Environment variables are case-insensitive.
    Settings are loaded from .env file if present.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        # Don't fail if .env file doesn't exist
        extra="ignore",
    )

    # Application metadata
    app_name: str = "Paddy"
    version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"

    # LLM configuration
    llm_provider: str = "openai"
    llm_model: str = "gpt-4.1-nano"
    llm_api_key: str = ""

    # Vault configuration
    obsidian_vault_path: Path = Path("/vault")

    # API authentication
    api_key: str = ""

    # CORS settings
    allowed_origins: list[str] = ["app://obsidian.md", "capacitor://localhost"]

    @property
    def model_name(self) -> str:
        """Build provider:model string used by Pydantic AI."""
        return f"{self.llm_provider}:{self.llm_model}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    The @lru_cache decorator ensures settings are only loaded once
    and reused across the application lifecycle.

    Returns:
        The application settings instance.
    """
    return Settings()
