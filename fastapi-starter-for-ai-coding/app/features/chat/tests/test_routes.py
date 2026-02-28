"""Unit tests for the chat completions route."""

from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import application

TEST_API_KEY = "test-secret-key"


@pytest.fixture
def client() -> TestClient:
    return TestClient(application)


def _auth_header(key: str = TEST_API_KEY) -> dict[str, str]:
    return {"Authorization": f"Bearer {key}"}


def _chat_body(
    content: str = "Hello",
    stream: bool = False,
    model: str = "paddy",
) -> dict[str, Any]:
    return {
        "model": model,
        "messages": [{"role": "user", "content": content}],
        "stream": stream,
    }


class _MockAgentRun:
    """Async-iterable mock that simulates an AgentRun."""

    def __init__(self, result: Any) -> None:
        self.result = result

    def __aiter__(self) -> "_MockAgentRun":
        return self

    async def __anext__(self) -> None:
        raise StopAsyncIteration


class _MockAgentContext:
    """Async context manager mock that simulates ``vault_agent.iter()``."""

    def __init__(self, result: Any) -> None:
        self._run = _MockAgentRun(result)

    async def __aenter__(self) -> _MockAgentRun:
        return self._run

    async def __aexit__(self, *args: Any) -> bool:
        return False


def _mock_agent_context() -> _MockAgentContext:
    """Build a mock for ``vault_agent.iter()`` that simulates a successful run."""
    mock_usage = MagicMock()
    mock_usage.request_tokens = 10
    mock_usage.response_tokens = 5
    mock_usage.total_tokens = 15

    mock_result = MagicMock()
    mock_result.data = "Mocked agent response"
    mock_result.usage.return_value = mock_usage

    return _MockAgentContext(mock_result)


def test_chat_completions_requires_auth(client: TestClient) -> None:
    response = client.post("/v1/chat/completions", json=_chat_body())
    assert response.status_code == 403  # HTTPBearer returns 403 when no header


def test_chat_completions_rejects_bad_key(client: TestClient) -> None:
    with patch("app.features.chat.routes.get_settings") as mock_settings:
        mock_settings.return_value.api_key = TEST_API_KEY
        response = client.post(
            "/v1/chat/completions",
            json=_chat_body(),
            headers=_auth_header("wrong-key"),
        )
    assert response.status_code == 401


def test_chat_completions_accepts_valid_key(client: TestClient) -> None:
    settings = MagicMock()
    settings.api_key = TEST_API_KEY
    settings.obsidian_vault_path = "/vault"

    with (
        patch("app.features.chat.routes.get_settings", return_value=settings),
        patch("app.features.chat.routes.vault_agent") as mock_agent,
    ):
        mock_agent.iter.return_value = _mock_agent_context()
        response = client.post(
            "/v1/chat/completions",
            json=_chat_body(),
            headers=_auth_header(),
        )
    assert response.status_code == 200


def test_chat_completions_returns_openai_format(client: TestClient) -> None:
    settings = MagicMock()
    settings.api_key = TEST_API_KEY
    settings.obsidian_vault_path = "/vault"

    with (
        patch("app.features.chat.routes.get_settings", return_value=settings),
        patch("app.features.chat.routes.vault_agent") as mock_agent,
    ):
        mock_agent.iter.return_value = _mock_agent_context()
        response = client.post(
            "/v1/chat/completions",
            json=_chat_body(),
            headers=_auth_header(),
        )

    assert response.status_code == 200
    data: dict[str, Any] = response.json()

    assert "id" in data
    assert data["id"].startswith("chatcmpl-")
    assert data["object"] == "chat.completion"
    assert "created" in data
    assert data["model"] == "paddy"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert data["choices"][0]["message"]["content"] == "Mocked agent response"
    assert data["choices"][0]["finish_reason"] == "stop"
    assert "usage" in data
    assert data["usage"]["prompt_tokens"] == 10
    assert data["usage"]["completion_tokens"] == 5
    assert data["usage"]["total_tokens"] == 15


def test_chat_completions_rejects_streaming(client: TestClient) -> None:
    with patch("app.features.chat.routes.get_settings") as mock_settings:
        mock_settings.return_value.api_key = TEST_API_KEY
        response = client.post(
            "/v1/chat/completions",
            json=_chat_body(stream=True),
            headers=_auth_header(),
        )
    assert response.status_code == 400
    assert "Streaming not yet supported" in response.json()["detail"]


def test_chat_completions_empty_messages_returns_400(client: TestClient) -> None:
    with patch("app.features.chat.routes.get_settings") as mock_settings:
        mock_settings.return_value.api_key = TEST_API_KEY
        response = client.post(
            "/v1/chat/completions",
            json={"model": "paddy", "messages": []},
            headers=_auth_header(),
        )
    assert response.status_code == 400


def test_cors_headers_for_obsidian_origin(client: TestClient) -> None:
    response = client.options(
        "/v1/chat/completions",
        headers={
            "Origin": "app://obsidian.md",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type, Authorization",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "app://obsidian.md"
