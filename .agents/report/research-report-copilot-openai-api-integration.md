# Research Report: Obsidian Copilot OpenAI-Compatible API Integration

**Date:** 2026-02-28
**Repository:** https://github.com/logancyang/obsidian-copilot (master branch)
**Scope:** Message content format, endpoint path construction, implementation requirements for Paddy

---

## 1. Message Content Format Discovery

### 1.1 How Copilot Sends Messages to the LLM

Obsidian Copilot uses **LangChain** (`@langchain/openai`'s `ChatOpenAI` class) as its LLM abstraction layer. It does **not** make raw HTTP calls to OpenAI-compatible endpoints. Instead, it calls LangChain's `.stream()` or `.invoke()` methods, which internally use the **OpenAI Node SDK** (`openai` npm package) to make the actual HTTP request.

#### The Message Flow

```
User Input → ContextEnvelope (L1-L5 layers) → LayerToMessagesConverter → ProviderMessage[]
→ LangChain ChatOpenAI.stream(messages) → OpenAI SDK → HTTP POST /chat/completions
```

#### Source: `LayerToMessagesConverter.ts` — The Message Format

The converter produces a `ProviderMessage[]` array with **string content**:

```typescript
// src/context/LayerToMessagesConverter.ts
export interface ProviderMessage {
  role: "system" | "user" | "assistant";
  content: string;  // Always a plain string
}
```

Messages are constructed as:
1. **System message** (`role: "system"`): L1 (system prompt) + L2 (cumulative context library) merged into a single string
2. **Chat history**: Loaded from LangChain memory (previous user/assistant turns)
3. **User message** (`role: "user"`): L3 (smart references) + L5 (user query) merged into a single string

**Key finding:** The standard text-only path always produces `content: string`.

#### Source: `LLMChainRunner.ts` — Multimodal Content (Array Format)

When images are present, the content becomes an **array of content parts** (OpenAI multimodal format):

```typescript
// src/LLMProviders/chainRunner/LLMChainRunner.ts, lines 39-52
if (userMessage.content && Array.isArray(userMessage.content)) {
  // Merge envelope text with multimodal content (images)
  const updatedContent = userMessage.content.map((item: any) => {
    if (item.type === "text") {
      return { ...item, text: userMessageContent.content };
    }
    return item;
  });
  messages.push({
    role: "user",
    content: updatedContent,  // Array<{type: "text", text: string} | {type: "image_url", ...}>
  });
} else {
  messages.push(userMessageContent);  // {role: "user", content: string}
}
```

### 1.2 What Arrives at the HTTP Endpoint

LangChain's `ChatOpenAI` passes messages through the OpenAI SDK, which sends them as the standard OpenAI chat completion request:

**Text-only request (most common):**
```json
{
  "model": "paddy",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant.\n\n## Context Library\n\n..."},
    {"role": "user", "content": "Find my notes about Python"},
    {"role": "assistant", "content": "I found 3 notes about Python..."},
    {"role": "user", "content": "Tell me more about the first one"}
  ],
  "stream": true,
  "temperature": 0.1,
  "max_tokens": 1000
}
```

**Multimodal request (with images):**
```json
{
  "model": "paddy",
  "messages": [
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": [
      {"type": "text", "text": "What's in this image?"},
      {"type": "image_url", "image_url": {"url": "data:image/png;base64,..."}}
    ]}
  ],
  "stream": true
}
```

### 1.3 Content Format Summary

| Scenario | `content` field type | Example |
|---|---|---|
| Text-only chat (99% of cases) | `string` | `"Find my notes about Python"` |
| Chat with images (vision models) | `array` of `{type, text/image_url}` | `[{"type": "text", "text": "..."}, {"type": "image_url", ...}]` |

### 1.4 Content Normalization in the Plugin

The `ChatOpenRouter.extractDeltaContent()` method shows how the plugin handles **response** content that might come back as either format:

```typescript
// src/LLMProviders/ChatOpenRouter.ts
private extractDeltaContent(content: unknown): string {
  if (typeof content === "string") {
    return content;
  }
  if (Array.isArray(content)) {
    return content
      .map((part) => {
        if (typeof part === "string") {
          return part;
        }
        if (part && typeof part === "object" && typeof part.text === "string") {
          return part.text;
        }
        return "";
      })
      .join("");
  }
  return "";
}
```

Similarly, `getNumTokens` in `chatModelManager.ts` handles both formats:

```typescript
// src/LLMProviders/chatModelManager.ts, lines 771-779
newModelInstance.getNumTokens = async (
  content: string | Array<{ type: string; text?: string }>
) => {
  const text =
    typeof content === "string"
      ? content
      : content.map((item) => (typeof item === "string" ? item : (item.text ?? ""))).join("");
  return Math.ceil(text.length / 4);
};
```

**Conclusion:** Copilot's codebase consistently handles both `string` and `array` content formats, but **text-only string content is the primary format** for non-vision interactions.

---

## 2. Endpoint Path Construction

### 2.1 How Copilot Configures the Base URL

For the `OPENAI_FORMAT` provider (which is what users would select to connect to Paddy), the configuration is:

```typescript
// src/LLMProviders/chatModelManager.ts, lines 316-330
[ChatModelProviders.OPENAI_FORMAT]: {
  modelName: modelName,
  apiKey: await getDecryptedKey(customModel.apiKey || settings.openAIApiKey),
  streamUsage: customModel.streamUsage ?? false,
  configuration: {
    baseURL: customModel.baseUrl,    // <-- User enters this in Copilot settings
    fetch: customModel.enableCors ? safeFetch : undefined,
    defaultHeaders: { "dangerously-allow-browser": true },
  },
  ...this.getOpenAISpecialConfig(modelName, maxTokens, temperature, customModel),
},
```

The `baseURL` from `customModel.baseUrl` is passed directly into `ChatOpenAI`'s `configuration.baseURL`, which passes it to the OpenAI SDK's `new OpenAI({ baseURL: ... })`.

### 2.2 OpenAI SDK Path Appending Behavior

The OpenAI Node SDK (`openai` npm package) **automatically appends** the endpoint path to the `baseURL`. When `chat.completions.create()` is called, the SDK constructs the final URL as:

```
FINAL_URL = baseURL + "/chat/completions"
```

**Evidence from OpenAI SDK source and GitHub issues:**
- Default `baseURL` is `https://api.openai.com/v1`
- When calling `chat.completions.create()`, the SDK appends `/chat/completions`
- Final URL becomes `https://api.openai.com/v1/chat/completions`
- GitHub issue #282 confirms: setting `baseURL: 'pp'` causes requests to `pp/chat/completions`

### 2.3 What Users Should Enter in Copilot Settings

The `ProviderInfo` for `OPENAI_FORMAT` shows the expected format:

```typescript
// src/constants.ts, lines 668-674
[ChatModelProviders.OPENAI_FORMAT]: {
  label: "OpenAI Format",
  host: "https://api.example.com/v1",        // Example with /v1 suffix
  curlBaseURL: "https://api.example.com/v1",  // Same pattern
  keyManagementURL: "",
  listModelURL: "",
},
```

**Therefore, users should enter:** `http://localhost:8000/v1`

The SDK will automatically append `/chat/completions`, making the final request URL:
```
http://localhost:8000/v1/chat/completions
```

### 2.4 URL Construction Summary

| User enters in "Base URL" | SDK appends | Final request URL |
|---|---|---|
| `http://localhost:8000/v1` | `/chat/completions` | `http://localhost:8000/v1/chat/completions` |
| `http://localhost:8000` | `/chat/completions` | `http://localhost:8000/chat/completions` |
| `http://192.168.1.100:8000/v1` | `/chat/completions` | `http://192.168.1.100:8000/v1/chat/completions` |

**Recommended Paddy endpoint:** `POST /v1/chat/completions`

This matches the OpenAI convention and allows users to enter `http://localhost:8000/v1` as the Base URL.

---

## 3. Additional Request Parameters

### 3.1 Streaming

Copilot **always** enables streaming by default:

```typescript
// src/LLMProviders/chatModelManager.ts, line 157
streaming: customModel.stream ?? true,
```

This means the request will include `"stream": true`, and Copilot expects **Server-Sent Events (SSE)** responses.

**However:** The Copilot settings page notes: *"Obsidian currently does not support streaming with this CORS mode, so in this case you will lose streaming."* This means Paddy must support **both streaming and non-streaming** responses.

### 3.2 Additional Parameters Sent

Based on the `OPENAI_FORMAT` config in `chatModelManager.ts`, the request will also include:

| Parameter | Default | Source |
|---|---|---|
| `model` | User-configured model name | `modelName` from custom model config |
| `temperature` | `0.1` (default from settings) | `settings.temperature` |
| `max_tokens` | `1000` (default from settings) | `settings.maxTokens` |
| `stream` | `true` | `customModel.stream ?? true` |
| `top_p` | Optional | Only if user configures it |
| `frequency_penalty` | Optional | Only if user configures it |

### 3.3 Authentication

The `OPENAI_FORMAT` provider uses the `apiKey` from the custom model configuration. The OpenAI SDK sends this as:

```
Authorization: Bearer <apiKey>
```

This matches Paddy's planned authentication scheme exactly.

---

## 4. Expected Response Format

### 4.1 Non-Streaming Response

Copilot expects a standard OpenAI chat completion response:

```json
{
  "id": "chatcmpl-abc123",
  "object": "chat.completion",
  "created": 1709000000,
  "model": "paddy",
  "choices": [{
    "index": 0,
    "message": {
      "role": "assistant",
      "content": "I found 5 notes about machine learning..."
    },
    "finish_reason": "stop"
  }],
  "usage": {
    "prompt_tokens": 50,
    "completion_tokens": 100,
    "total_tokens": 150
  }
}
```

### 4.2 Streaming Response (SSE)

Each SSE chunk should follow:

```
data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1709000000,"model":"paddy","choices":[{"index":0,"delta":{"content":"I found"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1709000000,"model":"paddy","choices":[{"index":0,"delta":{"content":" 5 notes"},"finish_reason":null}]}

data: {"id":"chatcmpl-abc123","object":"chat.completion.chunk","created":1709000000,"model":"paddy","choices":[{"index":0,"delta":{},"finish_reason":"stop"}]}

data: [DONE]
```

### 4.3 Response Content Format

The plugin's `extractDeltaContent()` method can handle both:
- `content: "text string"` — preferred, standard format
- `content: [{type: "text", text: "..."}]` — array format (for multimodal responses)

**Recommendation:** Use simple `string` content in responses. It's simpler and universally supported.

---

## 5. Implementation Requirements for Paddy

### 5.1 FastAPI Endpoint

Paddy needs: `POST /v1/chat/completions`

```python
from fastapi import APIRouter

router = APIRouter(prefix="/v1")

@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest) -> ChatCompletionResponse:
    ...
```

### 5.2 Pydantic Request Model

The request must accept **both** content formats:

```python
from pydantic import BaseModel, field_validator

class ContentPart(BaseModel):
    type: str  # "text" or "image_url"
    text: str | None = None
    image_url: dict | None = None

class ChatMessage(BaseModel):
    role: str  # "system", "user", "assistant"
    content: str | list[ContentPart]

    @property
    def text_content(self) -> str:
        """Normalize content to plain text string."""
        if isinstance(self.content, str):
            return self.content
        return "".join(
            part.text for part in self.content
            if part.type == "text" and part.text
        )

class ChatCompletionRequest(BaseModel):
    model: str
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None
```

### 5.3 Content Normalization Strategy

Since Paddy's MVP doesn't support vision/images, normalize all content to strings:

```python
def extract_user_message(messages: list[ChatMessage]) -> str:
    """Extract the latest user message as plain text."""
    for msg in reversed(messages):
        if msg.role == "user":
            return msg.text_content
    return ""
```

### 5.4 Pydantic AI Integration

Pydantic AI's `agent.run()` accepts a simple string prompt. The OpenAI adapter must:

1. Extract the user's message text from the OpenAI format
2. Pass it to `vault_agent.run(user_prompt, deps=deps)`
3. Convert the Pydantic AI `RunResult` back to OpenAI response format

```python
from pydantic_ai import Agent

result = await vault_agent.run(
    user_prompt=extract_user_message(request.messages),
    deps=VaultDependencies(vault_path=settings.obsidian_vault_path),
)

# Convert to OpenAI format
response = ChatCompletionResponse(
    id=f"chatcmpl-{uuid4().hex[:12]}",
    object="chat.completion",
    created=int(time.time()),
    model=request.model,
    choices=[Choice(
        index=0,
        message=ResponseMessage(role="assistant", content=result.output),
        finish_reason="stop",
    )],
    usage=Usage(
        prompt_tokens=result.usage().request_tokens or 0,
        completion_tokens=result.usage().response_tokens or 0,
        total_tokens=result.usage().total_tokens or 0,
    ),
)
```

### 5.5 Conversation History Handling

Copilot manages conversation history **client-side** via LangChain memory. It sends the full history in the `messages` array each request. For MVP, Paddy can:

1. Extract just the latest user message for the agent prompt
2. Optionally pass prior messages as `message_history` to Pydantic AI for multi-turn context

### 5.6 CORS Configuration

Copilot needs CORS allowed for `app://obsidian.md`:

```python
# Already configured in Paddy's middleware.py
allow_origins=["app://obsidian.md", "capacitor://localhost"]
```

If the user enables CORS bypass in Copilot settings (for providers that don't support CORS natively), requests go through Obsidian's `requestUrl` API instead of direct `fetch`. In this case CORS headers don't matter, but streaming is disabled.

**For local development:** Since Paddy runs on `localhost`, CORS should work without the bypass. But supporting non-streaming responses ensures compatibility either way.

---

## 6. Copilot Configuration Guide for Users

### Step-by-step Setup

1. **Open Copilot Settings** → Model tab → Add Custom Model
2. **Model Name:** Enter `paddy` (or any name — it's passed in the `model` field but Paddy ignores it)
3. **Provider:** Select `3rd party (openai-format)`
4. **Base URL:** Enter `http://localhost:8000/v1`
5. **API Key:** Enter the API key configured in Paddy's `.env` file
6. **Enable CORS:** Leave unchecked (localhost doesn't need CORS bypass)
7. Click **Add Model**

### Expected Behavior

- Copilot sends requests to `http://localhost:8000/v1/chat/completions`
- Authentication via `Authorization: Bearer <API_KEY>`
- Streaming enabled by default
- Full conversation history included in each request

---

## 7. Key Takeaways

| Finding | Detail |
|---|---|
| **Content format** | Usually `string`, can be `array` for vision. Accept both, normalize to string for MVP. |
| **Endpoint path** | Must be `/v1/chat/completions`. SDK auto-appends `/chat/completions` to `baseURL`. |
| **User base URL** | Users enter `http://localhost:8000/v1` in Copilot settings. |
| **Streaming** | Copilot defaults to `stream: true`. Must support SSE. Non-streaming needed for CORS bypass mode. |
| **Auth** | Standard `Bearer` token in `Authorization` header. |
| **Response format** | Standard OpenAI chat completion response. String content in `choices[0].message.content`. |
| **Conversation history** | Managed client-side. Full history sent in `messages` array each request. |
| **LangChain abstraction** | Plugin uses LangChain `ChatOpenAI`, not raw HTTP. Same OpenAI SDK behavior underneath. |

---

## Appendix: Source Files Analyzed

| File | Purpose |
|---|---|
| `src/LLMProviders/chatModelManager.ts` | Model initialization, provider configs, baseURL configuration |
| `src/LLMProviders/ChatOpenRouter.ts` | Content extraction/normalization, streaming, tool call handling |
| `src/LLMProviders/chainManager.ts` | Chain orchestration, model selection |
| `src/LLMProviders/chainRunner/LLMChainRunner.ts` | Message construction, multimodal handling, streaming |
| `src/LLMProviders/chainRunner/BaseChainRunner.ts` | Response handling, error handling |
| `src/context/LayerToMessagesConverter.ts` | Envelope-to-messages conversion (L1-L5 layers) |
| `src/types/message.ts` | ChatMessage, StoredMessage types |
| `src/constants.ts` | Provider enums, ProviderInfo metadata, built-in models |
| `src/aiParams.ts` | CustomModel interface, model configuration |
