---
description: Consolidated project rules for the Paddy Obsidian AI Agent
alwaysApply: true
---

# Paddy — Obsidian AI Agent

**Paddy** is a self-hosted, Dockerized FastAPI backend that lets Obsidian users interact with their vaults using natural language. It uses Pydantic AI for tool orchestration and integrates with Obsidian via the Copilot plugin, exposing an OpenAI-compatible API endpoint.

## Core Principles

1. **Self-hosted & Simple** — easy to set up and run locally via Docker.
2. **Provider-agnostic** — works with Anthropic, OpenAI, Google, or local models (Ollama).
3. **Transparent** — clear reasoning, visible tool calls, actionable errors.
4. **Workflow-oriented** — tools match how users think, not just CRUD operations.
5. **Type-safe** — leverages Pydantic AI for reliable, maintainable agent development.

---

## 1. Architecture — Vertical Slice Architecture (VSA)

### Directory Layout

```
app/
├── core/                   # Universal infrastructure (exists before features)
│   ├── agent.py            # Single Pydantic AI agent instance
│   ├── config.py           # Settings via pydantic-settings
│   ├── dependencies.py     # Agent dependencies (VaultDependencies)
│   ├── logging.py          # Structured logging + correlation IDs
│   ├── middleware.py        # Request/response middleware
│   ├── exceptions.py       # Base exception classes
│   └── lifespan.py         # FastAPI startup/shutdown
├── shared/                 # Cross-feature utilities (3-feature rule)
│   ├── vault/
│   │   ├── manager.py      # VaultManager class (file I/O)
│   │   └── models.py       # Vault domain models
│   └── openai_adapter.py   # OpenAI ↔ Pydantic AI format conversion
├── features/               # Vertical slices — self-contained per feature
│   ├── chat/
│   │   ├── routes.py       # POST /v1/chat/completions
│   │   └── models.py       # ChatRequest, ChatResponse
│   ├── vault_query/
│   │   ├── tools.py        # obsidian_query_vault
│   │   └── models.py       # QueryResult, NoteInfo
│   ├── vault_context/
│   │   ├── tools.py        # obsidian_get_context
│   │   └── models.py       # ContextResult, NoteContent, BacklinkInfo
│   └── vault_management/
│       ├── tools.py        # obsidian_vault_manager
│       └── models.py       # OperationResult
├── main.py                 # FastAPI app entry point
tests/
├── conftest.py             # Shared fixtures (test client, mock vault)
└── integration/            # Cross-feature tests
```

### Decision Framework — What Goes Where

| Location | Rule | Examples |
|---|---|---|
| `core/` | Exists *before* features; universal across the app. | config, database, logging, middleware, agent instance |
| `shared/` | Used by **3+ features** with identical logic. Duplicate until the 3rd use. | VaultManager, pagination, OpenAI adapter |
| `features/<name>/` | Feature-specific logic, routes, models. Self-contained. | vault_query, vault_context, vault_management, chat |

**Key VSA rules:**

- `core/` is for universal infrastructure only — never put feature logic here.
- Code moves to `shared/` only when **3+ features** need it with identical logic. Before that, duplicate.
- Each feature slice owns its routes, models, tools, and (optional) tests.
- Cross-feature data access: read from another feature's repo is OK; **never write** to another feature's tables/files directly.
- When features must coordinate, use an orchestrating service pattern within the calling feature.

### Agent / Tool Registration Pattern

```python
# core/agent.py — define agent once
vault_agent = Agent('openai:gpt-4.1-nano', deps_type=VaultDependencies)

# features/vault_query/tools.py — register tool via decorator
from app.core.agent import vault_agent

@vault_agent.tool
async def obsidian_query_vault(...):
    ...

# main.py — import for side-effect registration
import app.features.vault_query.tools  # noqa: F401
```

---

## 2. The Three-Tool Architecture

Paddy exposes **3 consolidated, workflow-oriented tools** following Anthropic's "fewer, smarter tools" principle.

### Mental Model

| Need to… | Tool |
|---|---|
| **Find** something | `obsidian_query_vault` |
| **Read** content with context | `obsidian_get_context` |
| **Change** something | `obsidian_vault_manager` |

### Tool 1 — `obsidian_query_vault` (read-only discovery)

**Operations:** `semantic_search`, `list_structure`, `find_related`, `search_by_metadata`, `recent_changes`

Key parameters: `query_type`, `query`, `path`, `reference_note`, `filters`, `limit`, `response_format` (detailed/concise).

Response model: `QueryResult` containing `list[NoteInfo]`, `total_found`, `truncated`, `suggestion`.

Token efficiency: concise ≈ 50 tokens/result, detailed ≈ 200 tokens/result.

### Tool 2 — `obsidian_vault_manager` (all modifications)

**Operations (notes):** `create_note`, `update_note`, `append_note`, `delete_note`, `move_note`
**Operations (folders):** `create_folder`, `delete_folder`, `move_folder`
**Operations (bulk):** `bulk_tag`, `bulk_move`, `bulk_update_metadata`

Key parameters: `operation`, `target`/`targets`, `content`, `destination`, `metadata`, `metadata_changes`, `confirm_destructive`, `create_folders`.

Response model: `OperationResult` with `success`, `affected_count`, `affected_paths`, `message`, `warnings`, `partial_success`, `failures`.

Safety: destructive ops require `confirm_destructive=True`; bulk ops report partial success/failures.

### Tool 3 — `obsidian_get_context` (workflow-oriented reading)

**Operations:** `read_note`, `read_multiple`, `gather_related`, `daily_note`, `note_with_backlinks`

Key parameters: `context_type`, `target`/`targets`, `date`, `include_metadata`, `include_backlinks`, `max_related`, `response_format`.

Response model: `ContextResult` with `primary_note` (`NoteContent`), `related_notes`, `backlinks` (`BacklinkInfo`), `metadata_summary`, `token_estimate`.

### Why 3 Tools

- Cleanest separation: discover → read → modify.
- Minimal agent confusion about tool selection.
- Bulk operations are a parameter variation, not a separate workflow.
- Folder operations belong in vault management (vault organization).

### Typical Workflows

```python
# "Find my notes about Python and summarize them"
results = obsidian_query_vault(query_type="semantic_search", query="Python programming")
context = obsidian_get_context(context_type="read_multiple", targets=[r.path for r in results.results[:3]])
# Agent synthesizes summary from context

# "Create a new project note"
obsidian_vault_manager(
    operation="create_note",
    target="Projects/2025/New Project.md",
    content="# New Project\n...",
    metadata={"tags": ["project", "2025"], "status": "planning"},
    create_folders=True,
)

# "Tag all meeting notes from last week as reviewed"
results = obsidian_query_vault(query_type="search_by_metadata", filters={"folder": "Meetings", "date_range": {"days": 7}})
obsidian_vault_manager(operation="bulk_tag", targets=[r.path for r in results.results], metadata={"tags": ["reviewed"]})
```

---

## 3. Tool Docstring Requirements

Tool docstrings are read by the LLM during tool selection. They must guide the agent to choose the **right** tool, use it **efficiently**, and compose tools into workflows.

Every agent tool docstring **must** include, in order:

1. **One-line summary** — clear statement of purpose.
2. **Use this when** — 3-5 bullet points of specific scenarios.
3. **Do NOT use this for** — redirect to the correct alternative tool.
4. **Args** — each param with type, description, *and guidance on when/why to vary it*. For enums, describe each option's use case. For optional params, say when to include vs omit.
5. **Returns** — structure and format details that help the agent parse.
6. **Performance Notes** — token usage per response_format, execution time, resource limits.
7. **Examples** — 2-4 realistic examples (no "foo"/"bar"). Simple case, complex case, edge case.

### Anti-patterns to avoid

- Vague guidance ("use this when you need to work with notes").
- Missing negative guidance (agent won't know when to pick another tool).
- Toy/unrealistic example paths.
- No token/performance info.

### Consolidation principle

Prefer consolidated tools (single call handles multiple sub-operations via `operation` parameter) over fragmented single-purpose tools. Document the consolidation in the tool description.

---

## 4. Technology Stack

| Layer | Technology | Notes |
|---|---|---|
| Language | Python 3.12+ | |
| Framework | FastAPI 0.115+ | OpenAI-compatible `/v1/chat/completions` endpoint |
| Agent | Pydantic AI 0.0.14+ | Tool orchestration, `@agent.tool` decorators |
| Validation | Pydantic 2.9+ | Request/response models, settings |
| Server | Uvicorn | ASGI |
| Package manager | UV | `uv sync`, `uv run` |
| Containerization | Docker + Docker Compose | Volume-mount vault at `/vault` |
| Frontmatter | python-frontmatter 1.1+ | YAML frontmatter parsing |
| Env management | python-dotenv 1.0+ | `.env` support |
| Linting/formatting | Ruff | `uv run ruff check .` / `uv run ruff format .` |
| Type checking | MyPy + Pyright (strict) | `uv run mypy app/` / `uv run pyright app/` |
| Testing | pytest | `uv run pytest -v` |
| Logging | structlog | JSON structured, correlation IDs |

### LLM Providers (any via Pydantic AI)

Anthropic Claude, OpenAI GPT-4, Google Gemini, local models via Ollama.

### Frontend Integration

Obsidian Copilot plugin → connects to Paddy's `/v1/chat/completions` endpoint.

---

## 5. Code Quality Standards

### Type Annotations

- Require **explicit type annotations** on all production functions, methods, and important variables.
- Strict typing: `mypy` + `pyright` with zero unnecessary suppressions.
- Avoid `Any` unless justified with a concise rationale.

### Docstrings

- Google-style docstrings for public modules, classes, and functions.
- Agent tool docstrings follow the extended format in Section 3.

### Validation Commands

Before finalizing any work, ensure all of these pass:

```bash
uv run mypy app/
uv run pyright app/
uv run ruff check .
uv run pytest -v
```

### Testing

- Keep tests green with `uv run pytest -v`.
- Use `@pytest.mark.integration` for tests that require real external resources.
- **Unit tests** are colocated with the feature they test (e.g., `features/vault_query/test_tools.py`).
- **Integration tests** that span features go in `tests/integration/`.
- Feature-specific fixtures live in the feature's `conftest.py`; shared fixtures in `tests/conftest.py`.

### Linting & Formatting

Ruff configuration in `pyproject.toml`:

```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "W", "F", "I", "B", "C4", "UP", "ANN", "S", "RUF"]
ignore = ["B008", "ANN101", "S311"]

[tool.ruff.lint.per-file-ignores]
"tests/**/*.py" = ["S101", "ANN"]
"__init__.py" = ["F401"]

[tool.mypy]
python_version = "3.12"
strict = true
plugins = ["pydantic.mypy"]
```

---

## 6. Logging Conventions

- Use structured logs via `get_logger` (wraps structlog).
- Follow event format: `{domain}.{component}.{action}_{state}`.
- Preferred states: `_started`, `_completed`, `_failed`, `_validated`, `_rejected`, `_retrying`.
- Include `exc_info=True` on failure logs and include actionable context fields.
- All logs emit JSON with a `request_id` correlation field from middleware.

```python
from app.core.logging import get_logger

logger = get_logger(__name__)

logger.info("vault.query.search_started", query=query, query_type=query_type)
logger.error("vault.manager.create_failed", target=path, exc_info=True)
```

---

## 7. API & Integration

### OpenAI-Compatible Endpoint

**`POST /v1/chat/completions`**

Request:
```json
{
  "model": "paddy",
  "messages": [{"role": "user", "content": "Find my notes about ML"}],
  "stream": false
}
```

Response follows the standard OpenAI chat completion format (`id`, `object`, `created`, `model`, `choices`, `usage`).

### Authentication

- Single API key in `.env` → validated via `Authorization: Bearer <API_KEY>` on every `/v1/chat/completions` request.

### CORS

```
Access-Control-Allow-Origin: app://obsidian.md
Access-Control-Allow-Methods: POST, OPTIONS
Access-Control-Allow-Headers: Content-Type, Authorization
```

### OpenAI Adapter (`shared/openai_adapter.py`)

Converts between OpenAI chat completion format and Pydantic AI's internal format so Obsidian Copilot works transparently.

---

## 8. Configuration & Deployment

### Environment Variables (`.env`)

```bash
# LLM
LLM_PROVIDER=openai                 # anthropic | openai | google | ollama
LLM_MODEL=gpt-4.1-nano
LLM_API_KEY=sk-proj-...             # Provider key (OpenAI in this setup)

# Vault
OBSIDIAN_VAULT_PATH=/Users/name/Documents/MyVault   # host path

# API
API_KEY=your-secret-api-key         # App auth token for Authorization: Bearer <API_KEY>
API_HOST=0.0.0.0
API_PORT=8000

# CORS
ALLOWED_ORIGINS=app://obsidian.md,capacitor://localhost
```

### Settings Class

```python
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    llm_provider: str
    llm_model: str
    llm_api_key: str
    obsidian_vault_path: Path          # /vault inside container
    api_key: str
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    allowed_origins: list[str]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", case_sensitive=False)
```

### Docker

```yaml
services:
  paddy:
    build: .
    container_name: paddy-agent
    ports:
      - "8000:8000"
    volumes:
      - ${OBSIDIAN_VAULT_PATH}:/vault:rw    # bidirectional sync
    environment:
      - OBSIDIAN_VAULT_PATH=/vault          # container path
    env_file:
      - .env
```

- Volume mount gives sandboxed read-write access to the vault only.
- Changes by Paddy are immediately visible to Obsidian and vice versa.
- Container cannot access files outside the mounted vault directory.

---

## 9. Error Handling & Safety

### Error Message Philosophy

Always provide **specific, actionable** guidance:

```python
# Good
"Cannot create note at 'Projects/Q1/note.md': folder 'Projects/Q1' doesn't exist. "
"Set create_folders=True to automatically create missing folders, or use operation='create_folder' first."

# Bad
"Error: ENOENT"
```

### Safety Mechanisms

1. **Destructive operations require `confirm_destructive=True`** — prevents accidental deletes.
2. **Partial success reporting** — bulk operations report which items succeeded/failed.
3. **Automatic folder creation** — `create_folders=True` avoids multi-step folder setup.
4. **Path validation** — all file operations validate paths stay within the vault.
5. **Atomic writes** — file operations use atomic writes to prevent corruption.

### Vault Corruption Mitigation

- File operations use atomic writes.
- Delete operations require explicit confirmation.
- Validation runs before destructive operations.
- Users are expected to maintain their own backups (standard Obsidian practice).

---

## 10. Anthropic Tool Design Principles Applied

These principles from [Anthropic's best practices](https://www.anthropic.com/engineering/writing-tools-for-agents) are embedded throughout:

1. **Token efficiency** — `response_format` parameter on query/context tools (concise ≈ 67% reduction).
2. **Natural language over IDs** — human-readable paths (`"Projects/ML Project.md"`), not UUIDs.
3. **Helpful error messages** — specific cause + suggested fix in every error.
4. **Clear parameter naming** — `target` not `file`, `confirm_destructive` not `force`, `max_related` not `limit`.
5. **Workflow consolidation** — `gather_related` combines read + find-related + read-related in one call.
6. **Clear namespacing** — all tools prefixed with `obsidian_`.

---

## 11. AI-Friendliness Checklist

When writing or reviewing code, ensure:

- [ ] Files stay under 300 lines.
- [ ] All dependencies are explicit (no hidden globals).
- [ ] Minimal magic and metaprogramming.
- [ ] Feature code is self-contained and discoverable within its slice.
- [ ] Structured JSON logging with correlation IDs everywhere.
- [ ] Consistent event naming (`domain.component.action_state`).
- [ ] Exception tracebacks included via `exc_info=True`.
- [ ] Type hints on every function signature.
- [ ] Each feature directory could be loaded in isolation to understand the feature.

---

## 12. MVP Scope Summary

### In Scope

- Natural language querying, reading, creating, updating, appending notes.
- Folder management and organization.
- Bulk operations (tagging, moving, metadata updates).
- OpenAI-compatible `/v1/chat/completions` for Obsidian Copilot.
- Provider-agnostic LLM support.
- Docker volume mounting for vault access.
- Simple API key authentication.

### Out of Scope (Future)

- Cloud/SaaS deployment, multi-user, advanced auth.
- Conversation history persistence (database).
- Embeddings, semantic indexing, RAG.
- Streaming responses (SSE).
- Support for other note apps.
- Mobile, real-time collaboration.

---

## 13. Implementation Phases

| Phase | Goal | Key Deliverables |
|---|---|---|
| 1 — Foundation | Basic agent + one working tool | Project scaffolding, Dockerfile, volume mount, FastAPI + OpenAI endpoint, `obsidian_query_vault`, Copilot integration, provider config |
| 2 — Reading & Basic Ops | Enable reading + simple modifications | `obsidian_get_context`, `obsidian_vault_manager` (create/append/update), VaultManager, frontmatter parsing |
| 3 — Advanced Ops | Complete tool functionality | Bulk operations, folder management, related notes, backlinks, error handling |
| 4 — Polish | Production-ready MVP | README, `.env.example`, error message improvements, performance testing, edge cases |

---

## 14. Quick Reference Commands

```bash
# Development
uv run uvicorn app.main:app --reload --port 8000

# Validation (run all before finalizing)
uv run mypy app/
uv run pyright app/
uv run ruff check .
uv run ruff format .
uv run pytest -v

# Docker
docker compose up -d
docker compose logs -f paddy
docker compose down
```
