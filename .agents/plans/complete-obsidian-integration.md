# Feature: Complete Obsidian Copilot Integration

The following plan should be complete, but its important that you validate documentation and codebase patterns and task sanity before you start implementing.

Pay special attention to naming of existing utils types and models. Import from the right files etc.

## Feature Description

Complete the Obsidian Copilot integration by implementing the OpenAI-compatible `/v1/chat/completions` endpoint, the OpenAI adapter for message format conversion, API key authentication, and CORS validation. This enables end-to-end communication between the Obsidian Copilot plugin and the Paddy agent.

The implementation uses `agent.iter()` for agent execution, converts full OpenAI message history to Pydantic AI's `ModelMessage` format for multi-turn context, and reuses the system prompt already defined in `core/agent.py` — no custom system prompts are written in the adapter layer.

## User Story

As an Obsidian vault user
I want to connect the Obsidian Copilot plugin to my self-hosted Paddy agent
So that I can interact with my vault using natural language from within Obsidian

## Problem Statement

The Paddy agent has a working Pydantic AI agent with tool registration and core infrastructure (logging, middleware, CORS, config), but lacks the HTTP endpoint that Obsidian Copilot needs to communicate with it. Without the `/v1/chat/completions` endpoint, the OpenAI message adapter, and proper authentication, the Copilot plugin cannot send requests to or receive responses from Paddy.

## Solution Statement

Implement a vertical slice `features/chat/` containing the OpenAI-compatible endpoint and request/response models. Create `shared/openai_adapter.py` to convert between OpenAI and Pydantic AI message formats. Add API key authentication as a FastAPI dependency. Validate CORS is properly configured for `app://obsidian.md`. Use `agent.iter()` for agent execution with full message history support.

## Feature Metadata

**Feature Type**: New Capability
**Estimated Complexity**: Medium
**Primary Systems Affected**: `features/chat/`, `shared/openai_adapter.py`, `core/middleware.py`
**Dependencies**: `pydantic-ai`, `fastapi`, existing `core/agent.py`, existing `core/config.py`

---

## CONTEXT REFERENCES

### Relevant Codebase Files — IMPORTANT: YOU MUST READ THESE FILES BEFORE IMPLEMENTING!

- `fastapi-starter-for-ai-coding/app/core/agent.py` (lines 1-25) — **Why:** Contains the `vault_agent` instance and system prompt. The system prompt here is THE system prompt — the OpenAI adapter must NOT create a separate one. The agent's `system_prompt` parameter is what Pydantic AI sends to the LLM.
- `fastapi-starter-for-ai-coding/app/core/config.py` (lines 1-68) — **Why:** Contains `Settings` class with `api_key`, `allowed_origins`, and `model_name` property. Authentication and CORS config come from here.
- `fastapi-starter-for-ai-coding/app/core/dependencies.py` (lines 1-15) — **Why:** Contains `VaultDependencies` dataclass passed to agent runs.
- `fastapi-starter-for-ai-coding/app/core/middleware.py` (lines 91-113) — **Why:** Contains `setup_middleware()` with CORS already configured. Verify `allow_origins` uses `settings.allowed_origins`.
- `fastapi-starter-for-ai-coding/app/core/logging.py` (lines 1-146) — **Why:** `get_logger(__name__)` pattern and structured event naming convention.
- `fastapi-starter-for-ai-coding/app/core/exceptions.py` (lines 1-62) — **Why:** Base `PaddyError` hierarchy and exception handler pattern.
- `fastapi-starter-for-ai-coding/app/main.py` (lines 1-108) — **Why:** Application entry point. New chat router and tool imports must be wired here.
- `fastapi-starter-for-ai-coding/app/features/ping/tools.py` (lines 1-24) — **Why:** Example tool registration pattern to follow.
- `fastapi-starter-for-ai-coding/app/shared/schemas.py` (lines 1-28) — **Why:** Existing shared Pydantic schema pattern (`ErrorResponse`).
- `fastapi-starter-for-ai-coding/app/shared/utils.py` (lines 1-36) — **Why:** Existing shared utilities pattern (`utcnow()`, `format_iso()`).
- `fastapi-starter-for-ai-coding/app/core/tests/test_middleware.py` (lines 1-128) — **Why:** Test patterns for middleware (fixtures, mock patching, assertions).
- `fastapi-starter-for-ai-coding/app/core/tests/test_agent.py` (lines 1-22) — **Why:** Test pattern for agent assertions (tool registration, deps type).
- `fastapi-starter-for-ai-coding/app/tests/test_main.py` (lines 1-96) — **Why:** Integration test patterns (TestClient, CORS headers, lifespan).
- `fastapi-starter-for-ai-coding/pyproject.toml` (lines 1-122) — **Why:** Ruff, mypy, pyright, pytest config. All code must pass these checks.

### Research Findings — READ BEFORE IMPLEMENTING!

- `.agents/report/research-report-copilot-openai-api-integration.md` — **Critical research findings:**
  - **Section 1.2:** Copilot sends `content: string` (99% of cases) or `content: array` (vision). Accept both, normalize to string.
  - **Section 2.4:** Endpoint MUST be `POST /v1/chat/completions`. Users enter `http://localhost:8000/v1` as Base URL.
  - **Section 3.1:** Copilot defaults to `stream: true`. MVP supports non-streaming; streaming is future.
  - **Section 5.4:** Use `vault_agent.run()` (or `agent.iter()`) with `user_prompt` + `deps`. Convert result back to OpenAI format.
  - **Section 5.5:** Copilot manages history client-side. Full history in `messages` array each request. Convert prior messages to `message_history` for Pydantic AI.
  - **Section 5.6:** CORS needed for `app://obsidian.md`. Already in middleware config.
  - **Section 6:** Step-by-step Copilot configuration guide for users.

### New Files to Create

- `fastapi-starter-for-ai-coding/app/features/chat/__init__.py` — Package init
- `fastapi-starter-for-ai-coding/app/features/chat/models.py` — OpenAI-compatible request/response Pydantic models
- `fastapi-starter-for-ai-coding/app/features/chat/routes.py` — POST `/v1/chat/completions` endpoint with auth
- `fastapi-starter-for-ai-coding/app/shared/openai_adapter.py` — OpenAI ↔ Pydantic AI message conversion
- `.cursor/reference/obsidian-copilot-setup-guide.md` — User-facing setup guide for Copilot plugin
- `fastapi-starter-for-ai-coding/app/features/chat/test_models.py` — Unit tests for models
- `fastapi-starter-for-ai-coding/app/features/chat/test_routes.py` — Unit tests for routes
- `fastapi-starter-for-ai-coding/app/shared/tests/test_openai_adapter.py` — Unit tests for adapter

### Relevant Documentation — YOU SHOULD READ THESE BEFORE IMPLEMENTING!

- [Pydantic AI Agents — agent.iter()](https://ai.pydantic.dev/agents/)
  - Specific section: "Iterating over an agent's graph" and "async for iteration"
  - Why: `agent.iter()` is how we execute the agent run, accessing nodes and the final result
- [Pydantic AI Message History](https://ai.pydantic.dev/message-history/)
  - Specific section: "Using Messages as Input for Further Agent Runs"
  - Why: Shows how `message_history` parameter works with `ModelRequest`/`ModelResponse`
  - Key detail: When `message_history` is set and not empty, agent uses `instructions` (not `system_prompt`) — instructions are always re-evaluated. Our `system_prompt` in agent.py is set at construction time and always included.
- [Pydantic AI Messages API](https://ai.pydantic.dev/api/messages/)
  - Specific section: `ModelRequest`, `ModelResponse`, `UserPromptPart`, `TextPart`
  - Why: These are the exact types needed for the adapter conversion
- [Obsidian Copilot Research Report](.agents/report/research-report-copilot-openai-api-integration.md)
  - Why: Contains all findings about what Copilot sends and expects

### Patterns to Follow

**VSA Pattern (from `.cursor/reference/vsa-patterns.md`):**
- `features/chat/` is a self-contained vertical slice owning routes + models
- `shared/openai_adapter.py` is shared because it will be used by chat feature AND future streaming feature (anticipating 3+ features)
- `core/` is not touched for feature logic — only universal infrastructure

**Naming Conventions:**
- Event names: `{domain}.{component}.{action}_{state}` — e.g., `chat.completions.request_received`, `chat.completions.response_completed`
- File names: lowercase with underscores — `openai_adapter.py`, not `OpenAIAdapter.py`
- Models: PascalCase — `ChatCompletionRequest`, `ChatCompletionResponse`

**Logging Pattern (from `core/logging.py` and `core/middleware.py`):**
```python
from app.core.logging import get_logger
logger = get_logger(__name__)
logger.info("chat.completions.request_received", model=request.model, message_count=len(request.messages))
logger.error("chat.completions.agent_run_failed", error=str(e), exc_info=True)
```

**Error Handling (from `core/exceptions.py`):**
- Feature exceptions inherit from `PaddyError`
- 401 for missing/invalid API key
- 400 for malformed requests (no messages, no user message)
- 500 for agent execution failures

**Type Annotations:**
- All functions have explicit return types
- Pydantic models with strict field types
- `from __future__ import annotations` not used (project doesn't use it)

**Testing Pattern (from existing tests):**
- `pytest` fixtures for test app/client
- `unittest.mock.patch` for mocking logger
- `TestClient` from `fastapi.testclient`
- Tests colocated with feature: `features/chat/test_routes.py`

---

## IMPLEMENTATION PLAN

### Phase 1: Foundation — Chat Models & OpenAI Adapter

Create the Pydantic models for OpenAI chat completion request/response, and the adapter that converts between OpenAI and Pydantic AI message formats.

**Tasks:**
- Define `ChatCompletionRequest`, `ChatCompletionResponse`, and supporting models in `features/chat/models.py`
- Create `shared/openai_adapter.py` with functions to convert OpenAI messages to Pydantic AI `ModelMessage` list and to build OpenAI response from agent result

### Phase 2: Core Implementation — Chat Route & Authentication

Build the `/v1/chat/completions` endpoint using `agent.iter()`, with API key validation.

**Tasks:**
- Implement the chat completions route in `features/chat/routes.py`
- Add API key authentication as a FastAPI dependency
- Wire the chat router into `main.py`

### Phase 3: Integration — CORS Validation & End-to-End

Validate CORS configuration works with Obsidian, create user setup guide.

**Tasks:**
- Verify CORS middleware allows `app://obsidian.md` origin
- Create `.cursor/reference/obsidian-copilot-setup-guide.md`
- Test end-to-end with Obsidian Copilot plugin

### Phase 4: Testing & Validation

Comprehensive unit and integration tests.

**Tasks:**
- Unit tests for chat models (serialization, validation, content normalization)
- Unit tests for OpenAI adapter (message conversion, edge cases)
- Unit tests for chat route (auth, request handling, error cases)
- Integration tests for full request → agent → response flow

---

## STEP-BY-STEP TASKS

IMPORTANT: Execute every task in order, top to bottom. Each task is atomic and independently testable.

### Task 1: CREATE `features/chat/__init__.py`

- **IMPLEMENT**: Empty `__init__.py` for the chat feature package.
- **VALIDATE**: File exists at `fastapi-starter-for-ai-coding/app/features/chat/__init__.py`

### Task 2: CREATE `features/chat/models.py`

- **IMPLEMENT**: OpenAI-compatible Pydantic models for the chat completions API.
- **PATTERN**: Follow `shared/schemas.py` for Pydantic model style (BaseModel, Field, docstrings).
- **IMPORTS**: `from pydantic import BaseModel, Field`
- **MODELS TO CREATE**:
  - `ContentPart`: `type: str`, `text: str | None = None`, `image_url: dict[str, Any] | None = None`
  - `ChatMessage`: `role: Literal["system", "user", "assistant"]`, `content: str | list[ContentPart]` with a `text_content` property that normalizes array content to string
  - `ChatCompletionRequest`: `model: str`, `messages: list[ChatMessage]`, `stream: bool = False`, `temperature: float | None = None`, `max_tokens: int | None = None`, `top_p: float | None = None`, `frequency_penalty: float | None = None`
  - `ResponseMessage`: `role: Literal["assistant"] = "assistant"`, `content: str`
  - `Choice`: `index: int = 0`, `message: ResponseMessage`, `finish_reason: Literal["stop", "length"] = "stop"`
  - `Usage`: `prompt_tokens: int = 0`, `completion_tokens: int = 0`, `total_tokens: int = 0`
  - `ChatCompletionResponse`: `id: str`, `object: Literal["chat.completion"] = "chat.completion"`, `created: int`, `model: str`, `choices: list[Choice]`, `usage: Usage`
- **GOTCHA**: `content` in `ChatMessage` must accept BOTH `str` and `list[ContentPart]` (Copilot sends string 99% of the time, array for vision). The `text_content` property extracts plain text from either format.
- **GOTCHA**: All models need Google-style docstrings per code quality standards.
- **VALIDATE**: `uv run ruff check app/features/chat/models.py` and `uv run mypy app/features/chat/models.py`

### Task 3: CREATE `shared/openai_adapter.py`

- **IMPLEMENT**: Two main functions for converting between OpenAI and Pydantic AI message formats.
- **PATTERN**: Follow `shared/utils.py` for shared utility module style.
- **IMPORTS**: `from pydantic_ai import ModelMessage`, `from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart`
- **FUNCTIONS TO CREATE**:

  **`openai_messages_to_pydantic(messages: list[ChatMessage]) -> tuple[str, list[ModelMessage]]`**
  - Takes the full OpenAI `messages` array from the request.
  - Returns a tuple of `(user_prompt, message_history)`.
  - The last user message becomes `user_prompt` (string).
  - All prior user/assistant messages (excluding system messages and the last user message) are converted to `ModelRequest`/`ModelResponse` pairs for `message_history`.
  - **System messages are IGNORED** — Paddy's system prompt lives in `core/agent.py` and Pydantic AI handles it. Copilot sends its own system message (L1+L2 context layers) which we discard because our agent has its own system prompt.
  - User messages → `ModelRequest(parts=[UserPromptPart(content=text)])`
  - Assistant messages → `ModelResponse(parts=[TextPart(content=text)])`
  - Content normalization: use `ChatMessage.text_content` property.

  **`build_chat_response(output: str, model: str, usage_info: ...) -> ChatCompletionResponse`**
  - Takes the agent's output string, model name, and usage info.
  - Builds a complete `ChatCompletionResponse` with unique ID, timestamp, choices, and usage.
  - ID format: `chatcmpl-{uuid_hex[:29]}` (OpenAI uses a similar format).
  - Uses `app.shared.utils.utcnow()` for the timestamp (reuse existing utility).

- **LOGGING**: Use `get_logger(__name__)` for structured logging.
  - `adapter.openai.messages_converted` with `total_messages`, `history_messages`, `system_messages_skipped`
- **GOTCHA**: Empty messages list or no user message should raise a clear error.
- **GOTCHA**: The message history conversion must maintain alternating user/assistant order for Pydantic AI.
- **VALIDATE**: `uv run ruff check app/shared/openai_adapter.py` and `uv run mypy app/shared/openai_adapter.py`

### Task 4: CREATE `features/chat/routes.py`

- **IMPLEMENT**: The `POST /v1/chat/completions` endpoint.
- **PATTERN**: Follow `core/health.py` for router creation (`APIRouter(prefix="/v1", tags=["chat"])`).
- **IMPORTS**: `from app.core.agent import vault_agent`, `from app.core.config import get_settings`, `from app.core.dependencies import VaultDependencies`, `from app.shared.openai_adapter import openai_messages_to_pydantic, build_chat_response`, `from app.features.chat.models import ChatCompletionRequest, ChatCompletionResponse`
- **ROUTE IMPLEMENTATION**:
  1. Define `verify_api_key` as a FastAPI dependency using `fastapi.Security` with `HTTPAuthorizationCredentials` from `fastapi.security`. Compare `credentials.credentials` against `settings.api_key`. Return 401 if mismatch.
  2. Route: `@router.post("/chat/completions", response_model=ChatCompletionResponse)`
  3. Extract `(user_prompt, message_history)` from request using `openai_messages_to_pydantic()`.
  4. Create `VaultDependencies(vault_path=settings.obsidian_vault_path)`.
  5. Run agent using `agent.iter()`:
     ```python
     async with vault_agent.iter(
         user_prompt=user_prompt,
         message_history=message_history,
         deps=deps,
     ) as agent_run:
         async for node in agent_run:
             pass  # Let the agent complete its execution
     result = agent_run.result
     ```
  6. Build response using `build_chat_response(result.output, request.model, result.usage())`.
  7. Return the `ChatCompletionResponse`.
- **ERROR HANDLING**:
  - 401 if API key is missing or invalid (`HTTPException(status_code=401, detail="Invalid API key")`)
  - 400 if request has no messages or no user message
  - 500 if agent execution fails (catch `Exception`, log with `exc_info=True`)
- **LOGGING**:
  - `chat.completions.request_received` — model, message_count, stream
  - `chat.completions.agent_run_started` — user_prompt_length, history_length
  - `chat.completions.response_completed` — total_tokens, duration
  - `chat.completions.request_failed` — error, exc_info=True
- **GOTCHA**: If `request.stream` is `True`, return a 400 error with message "Streaming not yet supported. Set stream to false in Copilot settings or enable CORS bypass." (MVP does not support streaming.)
- **GOTCHA**: The `verify_api_key` dependency must be applied to the route, not globally, so health/root endpoints remain unprotected.
- **VALIDATE**: `uv run ruff check app/features/chat/routes.py` and `uv run mypy app/features/chat/routes.py`

### Task 5: UPDATE `main.py` — Wire Chat Route & Registration

- **IMPLEMENT**: Import and register the chat router.
- **PATTERN**: Follow existing `health_router` inclusion and `ping.tools` side-effect import.
- **ADD** after the ping tools import:
  ```python
  from app.features.chat.routes import router as chat_router
  application.include_router(chat_router)
  ```
- **GOTCHA**: The chat router import must come AFTER `setup_middleware()` and `setup_exception_handlers()` calls.
- **VALIDATE**: `uv run ruff check app/main.py` and `uv run pytest app/tests/test_main.py -v`

### Task 6: VALIDATE CORS Configuration

- **IMPLEMENT**: Verify the existing CORS middleware in `core/middleware.py` already supports Obsidian.
- **CHECK**: `settings.allowed_origins` defaults to `["app://obsidian.md", "capacitor://localhost"]` (confirmed in `config.py` line 50).
- **CHECK**: `CORSMiddleware` in `setup_middleware()` uses `allow_origins=settings.allowed_origins`, `allow_credentials=True`, `allow_methods=["*"]`, `allow_headers=["*"]` (confirmed in `middleware.py` lines 107-113).
- **VALIDATE**: Write a test that sends a request with `Origin: app://obsidian.md` header to `/v1/chat/completions` and verifies `Access-Control-Allow-Origin` is present in response.
- **GOTCHA**: The CORS middleware should also handle OPTIONS preflight requests. `allow_methods=["*"]` covers POST and OPTIONS.

### Task 7: CREATE `features/chat/test_models.py`

- **IMPLEMENT**: Unit tests for chat models.
- **PATTERN**: Follow `shared/tests/test_schemas.py` for model test style.
- **TESTS**:
  - `test_chat_message_string_content`: Create `ChatMessage` with string content, verify `text_content` returns it.
  - `test_chat_message_array_content`: Create `ChatMessage` with `list[ContentPart]`, verify `text_content` extracts text.
  - `test_chat_message_mixed_array_content`: Array with text + image_url parts, verify only text is extracted.
  - `test_chat_completion_request_defaults`: Verify `stream=False` default and optional fields.
  - `test_chat_completion_response_structure`: Build a complete response, verify JSON serialization matches OpenAI format.
  - `test_content_part_text_only`: Verify ContentPart with just text type.
  - `test_usage_defaults`: Verify all usage fields default to 0.
- **VALIDATE**: `uv run pytest app/features/chat/test_models.py -v`

### Task 8: CREATE `shared/tests/test_openai_adapter.py`

- **IMPLEMENT**: Unit tests for the OpenAI adapter.
- **PATTERN**: Follow `shared/tests/test_schemas.py` and `core/tests/test_agent.py`.
- **TESTS**:
  - `test_single_user_message`: One user message → `user_prompt` is message text, `message_history` is empty.
  - `test_multi_turn_conversation`: user → assistant → user → extracts last user as prompt, prior two as history.
  - `test_system_messages_ignored`: system + user messages → system is skipped, user becomes prompt.
  - `test_array_content_normalized`: User message with array content → text extracted correctly.
  - `test_empty_messages_raises`: Empty messages list raises `ValueError`.
  - `test_no_user_message_raises`: Only system/assistant messages raises `ValueError`.
  - `test_build_chat_response_structure`: Verify response has correct `id`, `object`, `created`, `model`, `choices`, `usage`.
  - `test_build_chat_response_id_format`: Verify `id` starts with `chatcmpl-`.
  - `test_message_history_alternating_order`: Verify converted history maintains proper ModelRequest/ModelResponse order.
- **VALIDATE**: `uv run pytest app/shared/tests/test_openai_adapter.py -v`

### Task 9: CREATE `features/chat/test_routes.py`

- **IMPLEMENT**: Unit tests for the chat routes.
- **PATTERN**: Follow `tests/test_main.py` for route test style with `TestClient`.
- **TESTS**:
  - `test_chat_completions_requires_auth`: Request without `Authorization` header returns 401.
  - `test_chat_completions_rejects_bad_key`: Request with wrong Bearer token returns 401.
  - `test_chat_completions_accepts_valid_key`: Request with correct key (mock agent run) returns 200.
  - `test_chat_completions_returns_openai_format`: Verify response JSON has `id`, `object`, `choices`, `usage`.
  - `test_chat_completions_rejects_streaming`: Request with `stream: true` returns 400 with helpful message.
  - `test_chat_completions_empty_messages_returns_400`: Request with empty messages array returns 400.
  - `test_cors_headers_for_obsidian_origin`: Request with `Origin: app://obsidian.md` includes CORS headers.
- **GOTCHA**: Mock `vault_agent.iter()` in tests to avoid real LLM calls. Use `unittest.mock.patch` or `unittest.mock.AsyncMock`.
- **VALIDATE**: `uv run pytest app/features/chat/test_routes.py -v`

### Task 10: CREATE `.cursor/reference/obsidian-copilot-setup-guide.md`

- **IMPLEMENT**: User-facing guide for setting up Obsidian Copilot to work with Paddy.
- **CONTENT**:
  - Prerequisites (Paddy running, API key configured)
  - Step-by-step Copilot plugin configuration
  - Screenshots/descriptions of each settings field
  - Troubleshooting common issues (connection refused, 401 errors, CORS)
  - Verification steps (send a test message)
- **PATTERN**: Follow existing reference doc style in `.cursor/reference/`.
- **VALIDATE**: File exists and is well-structured markdown.

### Task 11: RUN Full Validation Suite

- **IMPLEMENT**: Run all validation commands and fix any issues.
- **VALIDATE**:
  ```bash
  uv run ruff check .
  uv run ruff format .
  uv run mypy app/
  uv run pyright app/
  uv run pytest -v
  ```

---

## TESTING STRATEGY

### Unit Tests

Unit tests are colocated with their feature per project convention.

**`features/chat/test_models.py`**: Tests Pydantic model validation, serialization, and the `text_content` property for content normalization. No mocks needed — pure data validation.

**`shared/tests/test_openai_adapter.py`**: Tests message conversion functions with various input shapes:
- Single message, multi-turn, system messages, array content, empty/invalid inputs.
- Tests `build_chat_response` output structure.
- No mocks needed — pure conversion logic.

**`features/chat/test_routes.py`**: Tests the HTTP endpoint behavior:
- Auth validation (missing, wrong, correct key).
- Request validation (empty messages, streaming rejection).
- Response format (OpenAI-compatible JSON structure).
- Requires mocking `vault_agent.iter()` to avoid real LLM calls.

### Integration Tests

**`tests/integration/test_chat_flow.py`** (optional, if time permits):
- Full request → adapter → agent → response flow with a mock LLM model.
- CORS preflight request handling.
- Multiple sequential requests simulating a conversation.

### Edge Cases

- Content as array with mixed text/image parts
- Empty content string in user message
- Very long message history (token limits)
- Missing fields in request (optional params)
- Concurrent requests (basic thread safety)
- Unicode content in messages
- Messages with only system role (no user)

---

## VALIDATION COMMANDS

Execute every command to ensure zero regressions and 100% feature correctness.

### Level 1: Syntax & Style

```bash
uv run ruff check .
uv run ruff format --check .
```

### Level 2: Type Checking

```bash
uv run mypy app/
uv run pyright app/
```

### Level 3: Unit Tests

```bash
uv run pytest -v
uv run pytest app/features/chat/ -v
uv run pytest app/shared/tests/test_openai_adapter.py -v
```

### Level 4: Manual Validation

```bash
# Start the server
uv run uvicorn app.main:application --reload --port 8000

# Test health endpoint (no auth required)
curl http://localhost:8000/health

# Test chat endpoint without auth (expect 401)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"paddy","messages":[{"role":"user","content":"ping"}]}'

# Test chat endpoint with auth (expect 200)
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"model":"paddy","messages":[{"role":"user","content":"What notes do I have?"}],"stream":false}'

# Test CORS preflight
curl -X OPTIONS http://localhost:8000/v1/chat/completions \
  -H "Origin: app://obsidian.md" \
  -H "Access-Control-Request-Method: POST" \
  -H "Access-Control-Request-Headers: Content-Type, Authorization" \
  -v
```

### Level 5: Obsidian Copilot Validation

Follow the steps in `.cursor/reference/obsidian-copilot-setup-guide.md`:
1. Open Obsidian with Copilot plugin installed
2. Configure custom model with Base URL `http://localhost:8000/v1`
3. Enter API key from `.env` file
4. Send a test message: "Hello, are you connected?"
5. Verify response appears in Copilot chat
6. Test multi-turn conversation (follow-up questions reference earlier context)

---

## ACCEPTANCE CRITERIA

- [x] `POST /v1/chat/completions` endpoint exists and accepts OpenAI-format requests
- [x] API key authentication via `Authorization: Bearer <API_KEY>` header
- [x] Request models accept both `string` and `array` content formats
- [x] OpenAI adapter converts messages to Pydantic AI `ModelMessage` format
- [x] System messages from Copilot are ignored — agent uses its own system prompt from `core/agent.py`
- [x] `agent.iter()` is used for agent execution with full message history
- [x] Response follows OpenAI chat completion format (id, object, created, model, choices, usage)
- [x] CORS allows `app://obsidian.md` origin
- [x] Streaming requests return 400 with helpful error message
- [x] All validation commands pass with zero errors
- [x] Unit test coverage for models, adapter, and routes
- [x] User setup guide created at `.cursor/reference/obsidian-copilot-setup-guide.md`
- [x] No regressions in existing tests
- [x] Structured logging follows `{domain}.{component}.{action}_{state}` convention
- [x] All code follows project typing and docstring standards

---

## COMPLETION CHECKLIST

- [ ] All tasks completed in order (Tasks 1-11)
- [ ] Each task validation passed immediately
- [ ] All validation commands executed successfully
- [ ] Full test suite passes (unit + integration)
- [ ] No linting or type checking errors
- [ ] Manual testing confirms feature works (curl commands)
- [ ] Obsidian Copilot plugin connects and communicates successfully
- [ ] Acceptance criteria all met
- [ ] Code reviewed for quality and maintainability

---

## NOTES

### Design Decisions

**Why `agent.iter()` instead of `agent.run()`:** `agent.iter()` provides fine-grained control over the agent execution graph. While for MVP non-streaming we iterate fully, this pattern directly supports future streaming implementation where we'll need to yield SSE chunks as `ModelRequestNode` and `CallToolsNode` events occur. Using `agent.iter()` from the start avoids a future refactor.

**Why system messages are discarded:** Obsidian Copilot sends its own system prompt (containing L1 system prompt + L2 context library from the plugin's configuration). Paddy has its own carefully crafted system prompt in `core/agent.py` that instructs the agent how to use vault tools. Using Copilot's system prompt would override Paddy's tool-usage instructions, breaking the agent's behavior. Pydantic AI's `system_prompt` parameter on the Agent constructor is always included regardless of `message_history`.

**Why non-streaming MVP:** The research report (Section 3.1) notes that when CORS bypass is enabled in Copilot, streaming is disabled anyway. For local development, non-streaming works reliably. Streaming support (SSE) is a natural Phase 2 enhancement that `agent.iter()` will enable.

**Why `shared/openai_adapter.py` instead of in `features/chat/`:** The adapter will be needed by both the current non-streaming chat route and the future streaming chat route. Per VSA's three-feature rule, we anticipate this. However, if in doubt, it can start in `features/chat/` and move to `shared/` when the third consumer arrives.

**Content normalization strategy:** We accept both `string` and `array` content formats in the request model but normalize everything to strings before passing to Pydantic AI. The `ChatMessage.text_content` property handles this cleanly. Image content parts are silently ignored for MVP (no vision support).

### Key Implementation Details from Research

- OpenAI SDK auto-appends `/chat/completions` to base URL, so Paddy's route is `POST /v1/chat/completions` and users configure `http://localhost:8000/v1`
- Copilot sends `temperature`, `max_tokens`, `top_p`, `frequency_penalty` — these are accepted in the request model but not passed to the agent for MVP (Pydantic AI uses its own model settings)
- The `model` field in the request is passed through to the response but Paddy ignores it for model selection (agent uses `settings.model_name`)
- Response `usage` comes from `result.usage()` which returns `Usage(request_tokens, response_tokens, total_tokens)`

### Future Enhancements (Post-MVP)

- SSE streaming support using `agent.iter()` node-by-node with `StreamingResponse`
- Pass `temperature`/`max_tokens` from request to agent via `model_settings`
- Conversation history persistence (database)
- Rate limiting
- `/v1/models` endpoint for Copilot model listing

<!-- EOF -->
