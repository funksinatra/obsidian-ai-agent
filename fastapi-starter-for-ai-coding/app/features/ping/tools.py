"""Smoke-test tool for validating agent wiring.

This tool exists to prove the Pydantic AI tool registration pattern works.
Remove once the real vault tools are implemented.
"""

from pydantic_ai import RunContext

from app.core.agent import vault_agent
from app.core.dependencies import VaultDependencies


@vault_agent.tool
async def ping(ctx: RunContext[VaultDependencies]) -> str:
    """Check that the agent is connected and can access vault configuration.

    Use this when you need to:
    - Verify the agent is running and responsive
    - Confirm the vault path is configured

    Returns:
        A confirmation message with the configured vault path.
    """
    return f"Paddy is connected. Vault path: {ctx.deps.vault_path}"
