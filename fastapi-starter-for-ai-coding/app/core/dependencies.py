"""Agent dependencies for Pydantic AI tool context."""

from dataclasses import dataclass
from pathlib import Path


@dataclass
class VaultDependencies:
    """Dependencies injected into agent tools via RunContext.

    Tools access these via ctx.deps.vault_path to locate the Obsidian vault.
    Extended in later phases with VaultManager and other shared services.
    """

    vault_path: Path
