"""Tests for Pydantic AI agent setup."""

import importlib

from app.core.agent import vault_agent
from app.core.dependencies import VaultDependencies

importlib.import_module("app.features.ping.tools")


def test_vault_agent_exists():
    assert vault_agent is not None


def test_vault_agent_has_deps_type():
    assert vault_agent._deps_type == VaultDependencies  # pyright: ignore[reportPrivateUsage]


def test_vault_agent_has_tools():
    tool_names = list(vault_agent._function_tools.keys())  # pyright: ignore[reportPrivateUsage]
    assert "ping" in tool_names
