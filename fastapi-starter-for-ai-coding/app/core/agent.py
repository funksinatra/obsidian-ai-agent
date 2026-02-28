"""Single Pydantic AI agent instance for the Paddy application.

This module defines the vault_agent at module level. Tools register themselves
by importing vault_agent and using the @vault_agent.tool decorator.
Tool modules are imported in main.py for side-effect registration.
"""

from pydantic_ai import Agent

from app.core.config import get_settings
from app.core.dependencies import VaultDependencies

settings = get_settings()

vault_agent = Agent(
    settings.model_name,
    deps_type=VaultDependencies,
    defer_model_check=True,
    system_prompt=(
        "You are Paddy, an AI assistant for managing Obsidian vaults. "
        "You help users find, read, and organize their notes using natural language. "
        "Always use the available tools to interact with the vault - "
        "do not guess file contents or paths."
    ),
)
