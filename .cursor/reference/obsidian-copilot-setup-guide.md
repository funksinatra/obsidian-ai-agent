# Obsidian Copilot Setup Guide for Paddy

Connect the Obsidian Copilot plugin to your self-hosted Paddy agent.

---

## Prerequisites

1. **Paddy is running** — either via `docker compose up` or `uv run uvicorn app.main:application --port 8000`
2. **API key is configured** — `API_KEY` is set in your `.env` file
3. **Obsidian Copilot plugin is installed** — available from the Obsidian community plugins

---

## Step-by-Step Configuration

### 1. Open Copilot Settings

In Obsidian, go to **Settings → Copilot → Model** tab.

### 2. Add a Custom Model

Click **Add Custom Model** and fill in:

| Field | Value |
|---|---|
| **Model Name** | `paddy` (or any name you prefer) |
| **Provider** | `3rd party (openai-format)` |
| **Base URL** | `http://localhost:8000/v1` |
| **API Key** | The value of `API_KEY` from your `.env` file |
| **Enable CORS** | Leave **unchecked** (not needed for localhost) |

### 3. Save and Select the Model

Click **Add Model**, then select `paddy` as your active model in the Copilot model dropdown.

### 4. Disable Streaming (Required for MVP)

In the Copilot model settings, set **Stream** to `false`. Paddy's MVP does not yet support streaming responses. If streaming is left enabled, you'll receive a 400 error with a helpful message.

Alternatively, enabling the **CORS bypass** option in Copilot automatically disables streaming.

---

## Verification

### Test the Connection

Open the Copilot chat panel in Obsidian and send:

```
Hello, are you connected?
```

You should receive a response from Paddy confirming it can communicate.

### Test Vault Interaction

Try a vault-specific query:

```
What notes do I have?
```

Paddy should use its tools to query your vault and respond with information about your notes.

### Test Multi-Turn Conversation

Send a follow-up question referencing the previous response. Copilot sends the full conversation history with each request, so Paddy maintains context across turns.

---

## Troubleshooting

### Connection Refused

- Verify Paddy is running: `curl http://localhost:8000/health`
- Check the port matches your configuration (default: 8000)
- If running in Docker, ensure port 8000 is mapped

### 401 Unauthorized

- Verify the API key in Copilot settings matches `API_KEY` in your `.env`
- The key is sent as `Authorization: Bearer <key>` — Copilot handles this automatically
- Check for leading/trailing whitespace in either the `.env` value or the Copilot field

### 400 Bad Request — "Streaming not yet supported"

- Set streaming to `false` in Copilot's model settings
- Or enable CORS bypass mode (which disables streaming)

### CORS Errors

- Paddy's CORS is pre-configured for `app://obsidian.md`
- If you see CORS errors, try enabling the **CORS bypass** option in Copilot settings
- Verify `ALLOWED_ORIGINS` in `.env` includes `app://obsidian.md`

### Slow Responses

- Agent responses involve LLM calls plus potential tool execution
- Check your LLM provider's latency and rate limits
- Consider using a faster model (e.g., `gpt-4.1-nano` for OpenAI)

---

## How It Works

```
Obsidian Copilot → POST http://localhost:8000/v1/chat/completions
                   Authorization: Bearer <API_KEY>
                   Content-Type: application/json

                   {
                     "model": "paddy",
                     "messages": [...],
                     "stream": false
                   }

Paddy → Converts messages → Runs agent → Returns OpenAI-format response
```

The Copilot plugin uses the OpenAI SDK under the hood, which automatically appends `/chat/completions` to the base URL you configure. That's why you enter `http://localhost:8000/v1` (not the full endpoint path).
