# Research Report: OpenAI-Compatible Streaming with Pydantic AI and FastAPI

**Date:** 2026-02-28
**Sources analyzed:**
- Pydantic AI docs (ai.pydantic.dev) — agents, run API, result API, messages API
- OpenAI streaming spec (developers.openai.com)
- Obsidian Copilot source (github.com/logancyang/obsidian-copilot)
- OpenAI cookbook: how_to_stream_completions

---

## Part 1: Pydantic AI Streaming Deep Dive

### 1.1 Three Streaming Approaches

Pydantic AI provides three ways to stream agent output, ranked from simplest to most powerful:

| Method | Returns | Best for |
|---|---|---|
| `agent.run_stream()` | `StreamedRunResult` with `.stream_text(delta=True)` | Simple text streaming, easiest to use |
| `agent.run_stream_events()` | `AsyncIterator[AgentStreamEvent \| AgentRunResultEvent]` | Event-level access without manual node iteration |
| `agent.iter()` | `AgentRun` (async iterable over graph nodes) | Full control, streaming + tool call visibility |

### 1.2 Recommended Approach: `run_stream()` with `stream_text(delta=True)`

For an OpenAI-compatible streaming endpoint, **`run_stream()`** is the best fit because:
- It returns text deltas directly — maps cleanly to OpenAI `delta.content`
- It handles tool execution internally (agent keeps running until final text)
- It's the simplest approach with the least boilerplate

#### Core Pattern

```python
from pydantic_ai import Agent

agent = Agent('openai:gpt-4.1-nano', deps_type=VaultDependencies)

async def stream_agent_response(user_prompt: str, deps: VaultDependencies):
    async with agent.run_stream(user_prompt, deps=deps) as response:
        async for text in response.stream_text(delta=True):
            yield text  # Each yield is a text delta (e.g., "The ", "capital ", "of ")
        # After stream completes, access usage:
        usage = response.usage()
        # usage.request_tokens, usage.response_tokens, usage.total_tokens
```

**Critical: `delta=True`**
- `delta=True` → yields incremental text chunks (what we need for SSE)
- `delta=False` (default) → yields the accumulated text so far (not useful for SSE)

### 1.3 Alternative: `agent.iter()` with `node.stream()`

The `iter()` approach gives full visibility into the agent graph execution, including tool calls. Each iteration yields a **node** representing a step in the agent's execution.

#### Node Types (Graph Execution Flow)

```
UserPromptNode → ModelRequestNode → CallToolsNode → [loop back to ModelRequestNode if tools called]
                                                   → End(FinalResult)
```

| Node | Purpose | Contains streamable text? |
|---|---|---|
| `UserPromptNode` | User input was received | No |
| `ModelRequestNode` | Model is being called | **Yes** — stream via `node.stream(ctx)` |
| `CallToolsNode` | Model response arrived, tools may execute | Only tool call events |
| `End(FinalResult)` | Agent run complete | Final output in `node.data.output` |

#### Full Streaming with `iter()` Example

```python
from pydantic_ai import (
    Agent, FinalResultEvent, PartDeltaEvent,
    PartStartEvent, TextPartDelta,
)
from pydantic_graph import End

async def stream_with_iter(user_prompt: str, deps: VaultDependencies):
    async with agent.iter(user_prompt, deps=deps) as run:
        async for node in run:
            if Agent.is_model_request_node(node):
                # Stream tokens from the model's response
                async with node.stream(run.ctx) as request_stream:
                    async for event in request_stream:
                        if isinstance(event, PartStartEvent):
                            if hasattr(event.part, 'content'):
                                yield event.part.content  # Initial text chunk
                        elif isinstance(event, PartDeltaEvent):
                            if isinstance(event.delta, TextPartDelta):
                                yield event.delta.content_delta  # Text delta
                        elif isinstance(event, FinalResultEvent):
                            # Model is producing final result, switch to text streaming
                            async for text in request_stream.stream_text():
                                yield text
                            break
            elif Agent.is_call_tools_node(node):
                # Tools are executing — no text to stream
                # (Agent loops back to ModelRequestNode after tools run)
                pass
            elif Agent.is_end_node(node):
                # Run complete
                pass
    # Usage available via run.usage()
```

### 1.4 Conversation History (message_history)

Both `run_stream()` and `iter()` accept a `message_history` parameter:

```python
async with agent.run_stream(
    user_prompt,
    deps=deps,
    message_history=history,  # Sequence[ModelMessage]
) as response:
    ...
```

**Pydantic AI's `ModelMessage` type** is a union of:
- `ModelRequest` — contains `UserPromptPart`, `SystemPromptPart`, `ToolReturnPart`, `RetryPromptPart`
- `ModelResponse` — contains `TextPart`, `ToolCallPart`, `ThinkingPart`

**Converting OpenAI messages to Pydantic AI format:**

Pydantic AI does NOT accept raw OpenAI format messages. You must convert them:

```python
from pydantic_ai.messages import (
    ModelRequest, ModelResponse, UserPromptPart, TextPart,
)

def openai_messages_to_pydantic(messages: list[dict]) -> list[ModelRequest | ModelResponse]:
    """Convert OpenAI-format messages to Pydantic AI message history."""
    history = []
    for msg in messages:
        role = msg["role"]
        content = msg["content"] if isinstance(msg["content"], str) else extract_text(msg["content"])

        if role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=content)]))
        elif role == "assistant":
            history.append(ModelResponse(parts=[TextPart(content=content)]))
        # "system" messages are handled via agent system_prompt, not message_history
    return history
```

**However, for MVP:** Since Copilot sends the full conversation history each request, and Paddy is a tool-calling agent (not a simple passthrough), the simplest approach is to:
1. Extract only the **latest user message** as the prompt
2. Let the agent handle each request independently (no `message_history`)
3. Optionally pass prior turns as `message_history` for multi-turn context

---

## Part 2: OpenAI Streaming Chunk Format Spec

### 2.1 SSE Wire Format

Each chunk is sent as an SSE event:

```
data: {JSON chunk}\n\n
```

The stream terminates with:

```
data: [DONE]\n\n
```

### 2.2 Chunk Object Structure

From the OpenAI API reference:

```typescript
interface ChatCompletionChunk {
  id: string;                          // Same ID across all chunks
  object: "chat.completion.chunk";     // Always this value
  created: number;                     // Unix timestamp (same across all chunks)
  model: string;                       // Model identifier
  choices: Array<{
    index: number;                     // Always 0 for single-choice
    delta: {
      role?: string;                   // Only in first chunk: "assistant"
      content?: string;                // Text content delta (null when done)
      tool_calls?: Array<{...}>;       // Tool calls (not needed for MVP)
    };
    finish_reason: string | null;      // null during streaming, "stop" at end
  }>;
  usage?: {                            // Only present if stream_options.include_usage=true
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
}
```

### 2.3 Chunk Progression Example

**First chunk** (role announcement):
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion.chunk",
  "created": 1709000000,
  "model": "paddy",
  "choices": [{
    "index": 0,
    "delta": {"role": "assistant", "content": ""},
    "finish_reason": null
  }]
}
```

**Middle chunks** (content deltas):
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion.chunk",
  "created": 1709000000,
  "model": "paddy",
  "choices": [{
    "index": 0,
    "delta": {"content": "I found"},
    "finish_reason": null
  }]
}
```

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion.chunk",
  "created": 1709000000,
  "model": "paddy",
  "choices": [{
    "index": 0,
    "delta": {"content": " 3 notes"},
    "finish_reason": null
  }]
}
```

**Final chunk** (finish signal):
```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion.chunk",
  "created": 1709000000,
  "model": "paddy",
  "choices": [{
    "index": 0,
    "delta": {},
    "finish_reason": "stop"
  }]
}
```

**Terminator:**
```
data: [DONE]
```

### 2.4 Required vs Optional Fields

| Field | Required | Notes |
|---|---|---|
| `id` | Yes | Same across all chunks. Use `f"chatcmpl-{uuid}"` |
| `object` | Yes | Always `"chat.completion.chunk"` |
| `created` | Yes | Unix timestamp, same across all chunks |
| `model` | Yes | Model identifier string |
| `choices[0].index` | Yes | Always `0` |
| `choices[0].delta` | Yes | Object with optional `role`, `content`, `tool_calls` |
| `choices[0].finish_reason` | Yes | `null` during stream, `"stop"` at end |
| `usage` | No | Only if `stream_options.include_usage` is set |
| `system_fingerprint` | No | Deprecated |
| `service_tier` | No | Not needed |

### 2.5 How Copilot Handles Streaming Chunks

From `ChatOpenRouter.ts`, the plugin processes chunks as follows:

```typescript
// src/LLMProviders/ChatOpenRouter.ts (simplified)
for await (const rawChunk of stream) {
  const choice = rawChunk.choices?.[0];
  const delta = choice?.delta;
  if (!choice || !delta) continue;

  // Extract text content (handles both string and array)
  const content = this.extractDeltaContent(delta.content);

  // Build LangChain message chunk
  const messageChunk = new AIMessageChunk({
    content,
    tool_call_chunks: this.extractToolCallChunks(delta.tool_calls),
    // ...
  });

  yield new ChatGenerationChunk({ message: messageChunk, text: content });
}
```

Key observations:
- It iterates `rawChunk.choices[0].delta`
- It extracts `delta.content` (handles string or array)
- It checks for `finish_reason` to detect completion
- Usage data is captured from the final chunk with `rawChunk.usage`

---

## Part 3: FastAPI SSE Implementation Blueprint

### 3.1 Approach A: `run_stream()` — Recommended for MVP

```python
import json
import time
from collections.abc import AsyncIterator
from uuid import uuid4

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from app.core.agent import vault_agent
from app.core.config import get_settings
from app.core.dependencies import VaultDependencies

router = APIRouter(prefix="/v1")


def _make_chunk(
    chunk_id: str,
    created: int,
    model: str,
    content: str | None = None,
    role: str | None = None,
    finish_reason: str | None = None,
) -> str:
    """Format a single SSE chunk in OpenAI chat.completion.chunk format."""
    delta: dict[str, str] = {}
    if role is not None:
        delta["role"] = role
    if content is not None:
        delta["content"] = content

    chunk = {
        "id": chunk_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": delta,
                "finish_reason": finish_reason,
            }
        ],
    }
    return f"data: {json.dumps(chunk)}\n\n"


async def _stream_agent(
    user_prompt: str,
    model: str,
    deps: VaultDependencies,
) -> AsyncIterator[str]:
    """Async generator that yields SSE-formatted chunks from the Pydantic AI agent."""
    chunk_id = f"chatcmpl-{uuid4().hex[:12]}"
    created = int(time.time())

    # First chunk: role announcement
    yield _make_chunk(chunk_id, created, model, content="", role="assistant")

    # Stream text deltas from the agent
    async with vault_agent.run_stream(user_prompt, deps=deps) as response:
        async for delta_text in response.stream_text(delta=True):
            yield _make_chunk(chunk_id, created, model, content=delta_text)

    # Final chunk: finish signal
    yield _make_chunk(chunk_id, created, model, finish_reason="stop")

    # Terminator
    yield "data: [DONE]\n\n"


@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest) -> StreamingResponse:
    settings = get_settings()
    deps = VaultDependencies(vault_path=settings.obsidian_vault_path)
    user_prompt = extract_latest_user_message(request.messages)

    if request.stream:
        return StreamingResponse(
            _stream_agent(user_prompt, request.model, deps),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        # Non-streaming: run agent to completion
        result = await vault_agent.run(user_prompt, deps=deps)
        return build_completion_response(request.model, result)
```

### 3.2 Approach B: `agent.iter()` — Full Control (Future Enhancement)

This approach is more complex but gives visibility into tool execution, useful for future streaming of tool call status to the client.

```python
async def _stream_agent_with_iter(
    user_prompt: str,
    model: str,
    deps: VaultDependencies,
) -> AsyncIterator[str]:
    """Stream using agent.iter() for full tool-call visibility."""
    chunk_id = f"chatcmpl-{uuid4().hex[:12]}"
    created = int(time.time())

    yield _make_chunk(chunk_id, created, model, content="", role="assistant")

    async with vault_agent.iter(user_prompt, deps=deps) as run:
        async for node in run:
            if Agent.is_model_request_node(node):
                async with node.stream(run.ctx) as request_stream:
                    async for event in request_stream:
                        if isinstance(event, PartDeltaEvent):
                            if isinstance(event.delta, TextPartDelta):
                                yield _make_chunk(
                                    chunk_id, created, model,
                                    content=event.delta.content_delta,
                                )
                        elif isinstance(event, FinalResultEvent):
                            # Switch to text streaming for the final result
                            async for text in request_stream.stream_text():
                                yield _make_chunk(
                                    chunk_id, created, model, content=text,
                                )
                            break
            elif Agent.is_call_tools_node(node):
                # Tools executing silently (agent handles internally)
                pass

    yield _make_chunk(chunk_id, created, model, finish_reason="stop")
    yield "data: [DONE]\n\n"
```

### 3.3 Error Handling Strategy

```python
async def _stream_agent_safe(
    user_prompt: str,
    model: str,
    deps: VaultDependencies,
) -> AsyncIterator[str]:
    """Wrap streaming with error handling."""
    chunk_id = f"chatcmpl-{uuid4().hex[:12]}"
    created = int(time.time())

    try:
        yield _make_chunk(chunk_id, created, model, content="", role="assistant")

        async with vault_agent.run_stream(user_prompt, deps=deps) as response:
            async for delta_text in response.stream_text(delta=True):
                yield _make_chunk(chunk_id, created, model, content=delta_text)

        yield _make_chunk(chunk_id, created, model, finish_reason="stop")
        yield "data: [DONE]\n\n"

    except Exception as e:
        # If error occurs mid-stream, send error as text content then finish
        error_msg = f"\n\n[Error: {e!s}]"
        yield _make_chunk(chunk_id, created, model, content=error_msg)
        yield _make_chunk(chunk_id, created, model, finish_reason="stop")
        yield "data: [DONE]\n\n"
```

### 3.4 Non-Streaming Response Builder

```python
import time
from uuid import uuid4

from pydantic_ai.agent import AgentRunResult


def build_completion_response(
    model: str,
    result: AgentRunResult,
) -> dict:
    """Build a standard OpenAI chat completion response."""
    usage_data = result.usage()
    return {
        "id": f"chatcmpl-{uuid4().hex[:12]}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": result.output,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": usage_data.request_tokens or 0,
            "completion_tokens": usage_data.response_tokens or 0,
            "total_tokens": usage_data.total_tokens or 0,
        },
    }
```

---

## Part 4: Complete Flow Diagram

### Request → Agent → Chunks → SSE

```
Obsidian Copilot (Client)
    |
    | POST /v1/chat/completions
    | { model: "paddy", messages: [...], stream: true }
    |
    v
FastAPI Route Handler
    |
    | 1. Extract latest user message from messages[]
    | 2. Create VaultDependencies
    | 3. Check stream flag
    |
    |-- if stream=true ------>  StreamingResponse(_stream_agent(...))
    |                               |
    |                               | async generator yields:
    |                               |
    |                               | "data: {role:assistant}\n\n"      ← first chunk
    |                               |
    |                           vault_agent.run_stream(prompt, deps=deps)
    |                               |
    |                               | async for delta in response.stream_text(delta=True):
    |                               |     yield "data: {content:delta}\n\n"  ← text deltas
    |                               |
    |                               | yield "data: {finish_reason:stop}\n\n"  ← final chunk
    |                               | yield "data: [DONE]\n\n"               ← terminator
    |
    |-- if stream=false ----->  vault_agent.run(prompt, deps=deps)
    |                               |
    |                               | result = await run
    |                               | return JSONResponse(completion_response)
    |
    v
Obsidian Copilot (Client)
    |
    | ChatOpenAI / ChatOpenRouter processes chunks
    | extractDeltaContent(delta.content) → text
    | Displays streaming text in chat UI
```

---

## Part 5: Implementation Decisions

### 5.1 Which Streaming Approach for MVP?

**Recommendation: `run_stream()` with `stream_text(delta=True)`**

Reasons:
- Simplest code path with minimal boilerplate
- Agent handles tool calls internally (no manual node iteration needed)
- Text deltas map directly to OpenAI `delta.content`
- Less error-prone than manual `iter()` + `node.stream()` composition

### 5.2 Key Implementation Notes

1. **`stream_text(delta=True)` is critical** — without `delta=True`, you get accumulated text (the full response so far), not incremental chunks

2. **First chunk must include `role: "assistant"`** — Copilot's LangChain adapter expects the role in the first delta

3. **Empty `delta: {}` marks end of content** — combined with `finish_reason: "stop"`, this signals the stream is complete

4. **`data: [DONE]` terminates the SSE stream** — the OpenAI SDK and LangChain both look for this literal string

5. **`Content-Type: text/event-stream`** — required for SSE. Also set `Cache-Control: no-cache` and `X-Accel-Buffering: no` (for nginx proxies)

6. **Error during streaming** — once SSE has started, HTTP status code is already 200. Errors must be sent as text content within the stream, then terminated normally

### 5.3 What About `stream_options: {"include_usage": true}`?

The OpenAI spec allows clients to request token usage in the final streaming chunk. Copilot may send this parameter. For MVP, we can:
- Accept the parameter in the request model (ignore it)
- Optionally include `usage` in the final chunk after the `[DONE]` signal

If we want to include usage, send a usage-only chunk before `[DONE]`:

```json
{"id":"chatcmpl-abc","object":"chat.completion.chunk","created":1709000000,"model":"paddy","choices":[],"usage":{"prompt_tokens":50,"completion_tokens":100,"total_tokens":150}}
```

### 5.4 File Structure for Implementation

Following VSA, the streaming implementation should be organized as:

```
app/features/chat/
├── routes.py      # POST /v1/chat/completions (streaming + non-streaming)
├── models.py      # ChatCompletionRequest, ChatCompletionResponse, chunk models
├── streaming.py   # _make_chunk(), _stream_agent(), SSE formatting
```

---

## Appendix: Pydantic AI Event Types Reference

| Event | When it fires | Contains |
|---|---|---|
| `PartStartEvent` | A new response part begins | `index`, `part` (TextPart, ToolCallPart) |
| `PartDeltaEvent` | Incremental update to a part | `index`, `delta` (TextPartDelta, ToolCallPartDelta) |
| `PartEndEvent` | A response part is complete | `index`, `part` (final version) |
| `FinalResultEvent` | Agent determined this is the final result | `tool_name`, `tool_call_id` |
| `FunctionToolCallEvent` | Tool is about to be called | `part` (ToolCallPart) |
| `FunctionToolResultEvent` | Tool returned a result | `tool_call_id`, `result` |
| `AgentRunResultEvent` | Run is fully complete | `result` (AgentRunResult with `.output`) |

### Key Imports

```python
# For run_stream() approach
from pydantic_ai import Agent
from pydantic_ai.result import StreamedRunResult

# For iter() approach
from pydantic_ai import (
    Agent,
    FinalResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
)
from pydantic_graph import End

# For message history conversion
from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    UserPromptPart,
    TextPart,
)
```
