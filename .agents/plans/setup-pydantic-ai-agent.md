# Feature: Pydantic AI Agent Setup

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Transform `fastapi-starter-for-ai-coding/` from a generic FastAPI + PostgreSQL template into the Paddy agent skeleton. Strip all database infrastructure, add Pydantic AI, configure vault/LLM settings, create the core agent instance with `VaultDependencies`, and wire up a smoke-test tool to validate the decorator-based registration pattern.

No real tools, no OpenAI-compatible endpoint, no Docker changes. Just the agent wiring.

## User Story

As a developer building the Paddy agent
I want a working Pydantic AI agent instance with proper configuration and one registered tool
So that I have a proven foundation to build the 3 real vault tools on top of

## Problem Statement

The starter template is a generic FastAPI + PostgreSQL project. Paddy is a file-system-based AI agent using Pydantic AI. The database layer must be removed and replaced with agent infrastructure, vault configuration, and the tool registration pattern from the project rules.

## Solution Statement

Adapt the starter in-place: delete database files, rewrite config for LLM/vault, create `core/agent.py` with a single `Agent` instance, create `core/dependencies.py` with `VaultDependencies`, add a trivial `features/ping/tools.py` to validate tool registration, and update all affected tests.

## Feature Metadata

**Feature Type**: Refactor + New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: `app/core/`, `app/shared/`, `app/main.py`, `pyproject.toml`, `.env.example`
**Dependencies**: `pydantic-ai` (latest, currently v0.0.24+)

---

## CONTEXT REFERENCES

### Relevant Codebase Files — READ BEFORE IMPLEMENTING

**Files to modify:**
- `app/main.py` (lines 1-108) — Remove DB imports/engine disposal, add tool side-effect imports
- `app/core/config.py` (lines 1-61) — Replace `database_url` with LLM/vault settings
- `app/core/health.py` (lines 1-106) — Remove DB endpoints (lines 30-106), keep basic `/health`
- `app/core/exceptions.py` (lines 1-88) — Replace `DatabaseError` hierarchy with `PaddyError`/`VaultError`
- `app/shared/schemas.py` (lines 1-89) — Remove `PaginationParams`/`PaginatedResponse`, keep `ErrorResponse`
- `pyproject.toml` (lines 1-125) — Remove DB deps, add `pydantic-ai`
- `.env.example` (lines 1-45) — Replace database block with LLM/vault vars
- `docker-compose.yml` (lines 1-77) — Remove `db` service

**Files to keep as-is:** `app/core/middleware.py`, `app/core/logging.py`, `app/shared/utils.py`

### Files to DELETE

- `alembic.ini` and `alembic/` (entire directory)
- `app/core/database.py`
- `app/core/tests/test_database.py`
- `app/tests/conftest.py` (DB fixtures)
- `app/tests/test_database_integration.py`
- `app/shared/tests/conftest.py` (DB fixtures)
- `app/shared/tests/test_models.py` (SQLAlchemy model tests)
- `app/shared/models.py` (SQLAlchemy `TimestampMixin`)

### New Files to Create

- `app/core/agent.py` — Single Pydantic AI agent instance
- `app/core/dependencies.py` — `VaultDependencies` dataclass
- `app/features/__init__.py` — Package init
- `app/features/ping/__init__.py` — Package init
- `app/features/ping/tools.py` — Smoke-test tool
- `app/core/tests/test_agent.py` — Agent instantiation tests

### Test Files to Update

- `app/core/tests/test_config.py` — Rewrite for LLM/vault settings
- `app/core/tests/test_health.py` — Remove DB health tests
- `app/core/tests/test_exceptions.py` — Rewrite for `PaddyError` hierarchy
- `app/shared/tests/test_schemas.py` — Remove pagination tests
- `app/tests/test_main.py` — Update `app_name` assertions to `"Paddy"`

### External Documentation — READ BEFORE IMPLEMENTING

- [Pydantic AI Agents](https://ai.pydantic.dev/agents/) — `Agent()` constructor, `deps_type`, `instructions`
- [Pydantic AI Tools](https://ai.pydantic.dev/tools/) — `@agent.tool` decorator, `RunContext[Deps]`
- [Pydantic AI Dependencies](https://ai.pydantic.dev/dependencies/) — Dataclass deps pattern

### Patterns to Follow

**Agent/Tool Registration** (from `.cursor/rules/OBSIDIAN_AGENT.md` lines 76-89):
```python
# core/agent.py — define agent once
vault_agent = Agent('anthropic:claude-sonnet-4-0', deps_type=VaultDependencies)

# features/*/tools.py — register tool via decorator
@vault_agent.tool
async def some_tool(ctx: RunContext[VaultDependencies], ...) -> str: ...

# main.py — import for side-effect registration
import app.features.ping.tools  # noqa: F401
```

**Naming:** `vault_agent` (module-level), `VaultDependencies` dataclass, logging events as `{domain}.{component}.{action}_{state}`

**Config:** `BaseSettings` + `SettingsConfigDict` + `@lru_cache` + `# type: ignore[call-arg]`

**Errors:** Keyword args to structlog (not `extra={}` dict — match `middleware.py` lines 56-60)

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### 1. REMOVE database files

Delete all files listed in "Files to DELETE" section above.

- **VALIDATE**: Confirm deleted files no longer exist

### 2. UPDATE `pyproject.toml` — swap dependencies and clean lint config

- **REMOVE** from dependencies: `alembic>=1.17.1`, `asyncpg>=0.30.0`, `sqlalchemy[asyncio]>=2.0.44`
- **ADD** to dependencies: `pydantic-ai` (latest version)
- **REMOVE** per-file-ignore: `"app/core/health.py" = ["B008"]` (line 68) — `Depends()` is no longer used in health.py
- **VALIDATE**: `cd fastapi-starter-for-ai-coding && uv sync`

### 3. UPDATE `app/core/config.py` — vault and LLM settings

Replace `database_url: str` and update defaults. Add `from pathlib import Path`.

```python
class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8",
        case_sensitive=False, extra="ignore",
    )

    # Application metadata
    app_name: str = "Paddy"
    version: str = "0.1.0"
    environment: str = "development"
    log_level: str = "INFO"

    # LLM configuration
    llm_provider: str = "anthropic"
    llm_model: str = "claude-sonnet-4-0"
    llm_api_key: str = ""

    # Vault configuration
    obsidian_vault_path: Path = Path("/vault")

    # API authentication
    api_key: str = ""

    # CORS settings
    allowed_origins: list[str] = ["app://obsidian.md", "capacitor://localhost"]

    @property
    def model_name(self) -> str:
        """Build full model string for Pydantic AI (e.g. 'anthropic:claude-sonnet-4-0')."""
        return f"{self.llm_provider}:{self.llm_model}"
```

- **GOTCHA**: Keep `@lru_cache` + `# type: ignore[call-arg]` on `get_settings()`
- **GOTCHA**: All fields have defaults so `Settings()` works without env vars in tests

### 4. UPDATE `.env.example`

Replace entire content with:

```env
# Application
APP_NAME=Paddy
VERSION=0.1.0
ENVIRONMENT=development
LOG_LEVEL=INFO

# LLM
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-0
LLM_API_KEY=sk-ant-...

# Vault
OBSIDIAN_VAULT_PATH=/Users/yourname/Documents/MyVault

# API
API_KEY=your-secret-api-key

# CORS
ALLOWED_ORIGINS=["app://obsidian.md","capacitor://localhost"]
```

### 5. UPDATE `app/core/health.py` — remove DB endpoints

Remove everything below the basic `/health` endpoint (lines 30-106). Remove all DB imports. Add version to response:

```python
"""Health check endpoints for monitoring application status."""

from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Basic health check endpoint."""
    settings = get_settings()
    return {"status": "healthy", "service": "paddy", "version": settings.version}
```

### 6. UPDATE `app/core/exceptions.py` — vault exception hierarchy

Replace `DatabaseError`/`NotFoundError`/`ValidationError` with `PaddyError`/`VaultError`/`NoteNotFoundError`/`VaultPathError`. Keep the `setup_exception_handlers` structure and `cast(Any, ...)` pattern.

**Exception hierarchy:**
- `PaddyError` (base) -> 500
- `VaultError(PaddyError)` -> 500
- `NoteNotFoundError(VaultError)` -> 404
- `VaultPathError(VaultError)` -> 400

**Handler:** Rename `database_exception_handler` to `paddy_exception_handler`. Use keyword args for structlog (not `extra={}` dict). Register all 4 exception types.

### 7. UPDATE `app/shared/schemas.py` — remove DB pagination

Remove `PaginationParams`, `PaginatedResponse`, `import math`, and `TypeVar`. Keep only `ErrorResponse`.

### 8. CREATE `app/core/dependencies.py`

```python
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
```

### 9. CREATE `app/core/agent.py`

```python
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
    instructions=(
        "You are Paddy, an AI assistant for managing Obsidian vaults. "
        "You help users find, read, and organize their notes using natural language. "
        "Always use the available tools to interact with the vault — "
        "do not guess file contents or paths."
    ),
)
```

- **GOTCHA**: `instructions` is the current Pydantic AI parameter (not `system_prompt`)
- **GOTCHA**: Uses `settings.model_name` property for dynamic `"provider:model"` string

### 10. CREATE `app/features/` package structure

Create empty `__init__.py` files:
- `app/features/__init__.py`
- `app/features/ping/__init__.py`

### 11. CREATE `app/features/ping/tools.py`

```python
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
```

### 12. UPDATE `app/main.py` — remove DB, wire agent

- **REMOVE**: `from app.core.database import engine` (line 21)
- **REMOVE**: `await engine.dispose()` (line 58), DB log lines (lines 53, 59)
- **ADD**: `import app.features.ping.tools  # noqa: F401` (side-effect tool registration)
- **ADD**: `logger.info("vault.config_validated", vault_path=str(settings.obsidian_vault_path))` in startup
- **UPDATE**: Module docstring — remove database references, add agent tool registration
- **UPDATE**: Port from 8123 to 8000 in `__main__` block (per PRD)
- **KEEP**: Everything else (lifespan structure, middleware, health router, root endpoint)

### 13. UPDATE `docker-compose.yml` — remove DB service

- **REMOVE**: Entire `db:` service block, `depends_on`, `DATABASE_URL` env var, `postgres_data` volume
- **KEEP**: `app` service structure (full Docker rewrite comes later)

### 14. UPDATE `app/core/tests/test_config.py`

Rewrite all tests for new settings fields. Remove all `DATABASE_URL` references.

**Tests to implement:**
- `test_settings_defaults` — `app_name="Paddy"`, `llm_provider="anthropic"`, `obsidian_vault_path=Path("/vault")`
- `test_settings_from_environment` — override `LLM_PROVIDER`, `LLM_MODEL`, `OBSIDIAN_VAULT_PATH`
- `test_model_name_property` — returns `"anthropic:claude-sonnet-4-0"`
- `test_allowed_origins_parsing` — update expected to `"app://obsidian.md"`
- `test_get_settings_caching` — keep as-is
- `test_settings_case_insensitive` — update env vars to new fields

**PATTERN**: Keep existing `patch.dict(os.environ, {...})` + `create_settings()` structure

### 15. UPDATE `app/core/tests/test_health.py`

Remove all DB health tests (lines 20-133). Keep/update `test_health_check_returns_healthy` to verify `"service": "paddy"` and `"version"` key.

### 16. UPDATE `app/core/tests/test_exceptions.py`

Rewrite for `PaddyError`/`VaultError`/`NoteNotFoundError`/`VaultPathError`:
- Exception instantiation and inheritance tests
- Handler returns 404 for `NoteNotFoundError`, 400 for `VaultPathError`, 500 for base
- `setup_exception_handlers` registers 4 handlers

**PATTERN**: Mirror existing structure — `MagicMock(spec=Request)`, `patch("app.core.exceptions.logger.error")`

### 17. UPDATE `app/shared/tests/test_schemas.py`

Remove all `PaginationParams`/`PaginatedResponse` tests and `ProductSchema`. Keep `test_error_response_structure` and `test_error_response_optional_detail`.

### 18. UPDATE `app/tests/test_main.py`

- Change expected `message`/`title` from `"Obsidian Agent Project"` to `"Paddy"` in all assertions
- Update `test_lifespan_startup_logging` — expected `app_name="Paddy"`, remove DB log assertions
- Update CORS test origin to `"app://obsidian.md"`
- Keep: `test_docs_endpoint_accessible`, `test_request_id_in_response_headers`, `test_custom_request_id_preserved`

### 19. CREATE `app/core/tests/test_agent.py`

```python
"""Tests for Pydantic AI agent setup."""

from app.core.agent import vault_agent
from app.core.dependencies import VaultDependencies


def test_vault_agent_exists():
    """Test that vault_agent is instantiated."""
    assert vault_agent is not None


def test_vault_agent_has_deps_type():
    """Test that vault_agent has VaultDependencies as deps type."""
    assert vault_agent.deps_type is VaultDependencies


def test_vault_agent_has_tools():
    """Test that at least the ping tool is registered."""
    import app.features.ping.tools  # noqa: F401

    tool_names = [t.name for t in vault_agent._function_tools.values()]
    assert "ping" in tool_names
```

- **GOTCHA**: Check actual Pydantic AI API for listing registered tools — `_function_tools` may differ by version

### 20. RUN full validation suite

```bash
cd fastapi-starter-for-ai-coding
uv run ruff check .
uv run ruff format .
uv run mypy app/
uv run pyright app/
uv run pytest -v
```

- **GOTCHA**: Pydantic AI may lack full mypy/pyright stubs. Add targeted `# type: ignore` with rationale if needed. Minimize suppressions.

---

## TESTING STRATEGY

### Unit Tests

- **Config**: All new fields load from env, `model_name` property, defaults work without env vars
- **Exceptions**: Hierarchy, handler status codes (404/400/500)
- **Health**: `/health` returns `{"status": "healthy", "service": "paddy", ...}`
- **Agent**: Exists, correct `deps_type`, ping tool registered
- **Main**: Root endpoint, CORS, request ID, lifespan logging with `"Paddy"`

### Edge Cases

- Empty `llm_api_key` — should not crash at import (fails only on actual LLM calls)
- Non-existent `obsidian_vault_path` — should not crash at import (validated at tool runtime)
- Multiple imports of tool modules — side-effect registration must be idempotent

---

## VALIDATION COMMANDS

```bash
cd fastapi-starter-for-ai-coding

# Syntax & style
uv run ruff check .
uv run ruff format --check .

# Type checking
uv run mypy app/
uv run pyright app/

# Tests
uv run pytest -v

# Manual smoke test
uv run uvicorn app.main:app --port 8000 &
sleep 2
curl http://localhost:8000/health
curl http://localhost:8000/
kill %1
```

---

## ACCEPTANCE CRITERIA

- [ ] All PostgreSQL/SQLAlchemy/Alembic code is removed
- [ ] `pydantic-ai` is installed and importable
- [ ] `Settings` class has LLM, vault, and API key fields (no `database_url`)
- [ ] `vault_agent` is a valid Pydantic AI `Agent` instance with `VaultDependencies`
- [ ] `ping` tool is registered on `vault_agent` via `@vault_agent.tool`
- [ ] `main.py` imports `app.features.ping.tools` for side-effect registration
- [ ] `app.main:app` starts without errors
- [ ] `/health` returns `{"status": "healthy", "service": "paddy", ...}`
- [ ] All validation commands pass: ruff, mypy, pyright, pytest
- [ ] No regressions in middleware, logging, CORS, or request ID handling

---

## COMPLETION CHECKLIST

- [ ] All 20 tasks completed in order
- [ ] All validation commands pass
- [ ] Full test suite green
- [ ] No linting or type errors (minimal justified suppressions OK for pydantic-ai)
- [ ] Manual smoke test confirms app starts and `/health` works

---

## NOTES

- **Why keep `shared/utils.py`?** `utcnow()`/`format_iso()` useful for frontmatter timestamps later.
- **Why keep `shared/schemas.py`?** `ErrorResponse` used by exception handlers, will grow with API schemas.
- **Why `ping` tool?** Validates the full registration chain before adding real tools. Deleted when `obsidian_query_vault` lands.
- **Docker changes minimal.** Full rewrite (vault volume mount) happens in a dedicated Docker step.
- **Port 8123 -> 8000.** PRD specifies 8000 for Paddy. Changed in `__main__` block only.

<!-- EOF -->
