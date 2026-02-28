"""Unit tests for the OpenAI ↔ Pydantic AI message adapter."""

import pytest
from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

from app.features.chat.models import ChatMessage, ContentPart
from app.shared.openai_adapter import build_chat_response, openai_messages_to_pydantic


def test_single_user_message():
    messages = [ChatMessage(role="user", content="Hello")]
    prompt, history = openai_messages_to_pydantic(messages)

    assert prompt == "Hello"
    assert history == []


def test_multi_turn_conversation():
    messages = [
        ChatMessage(role="user", content="First question"),
        ChatMessage(role="assistant", content="First answer"),
        ChatMessage(role="user", content="Follow-up question"),
    ]
    prompt, history = openai_messages_to_pydantic(messages)

    assert prompt == "Follow-up question"
    assert len(history) == 2

    assert isinstance(history[0], ModelRequest)
    assert isinstance(history[0].parts[0], UserPromptPart)
    assert history[0].parts[0].content == "First question"

    assert isinstance(history[1], ModelResponse)
    assert isinstance(history[1].parts[0], TextPart)
    assert history[1].parts[0].content == "First answer"


def test_system_messages_ignored():
    messages = [
        ChatMessage(role="system", content="You are a helpful assistant."),
        ChatMessage(role="user", content="Hi there"),
    ]
    prompt, history = openai_messages_to_pydantic(messages)

    assert prompt == "Hi there"
    assert history == []


def test_array_content_normalized():
    messages = [
        ChatMessage(
            role="user",
            content=[
                ContentPart(type="text", text="Describe "),
                ContentPart(type="text", text="this image"),
                ContentPart(type="image_url", image_url={"url": "data:..."}),
            ],
        ),
    ]
    prompt, _history = openai_messages_to_pydantic(messages)

    assert prompt == "Describe this image"


def test_empty_messages_raises():
    with pytest.raises(ValueError, match="must not be empty"):
        openai_messages_to_pydantic([])


def test_no_user_message_raises():
    messages = [
        ChatMessage(role="system", content="System prompt"),
        ChatMessage(role="assistant", content="Previous response"),
    ]
    with pytest.raises(ValueError, match="at least one user message"):
        openai_messages_to_pydantic(messages)


def test_build_chat_response_structure():
    resp = build_chat_response(
        output="The answer is 42",
        model="paddy",
        request_tokens=50,
        response_tokens=10,
        total_tokens=60,
    )

    assert resp.object == "chat.completion"
    assert resp.model == "paddy"
    assert len(resp.choices) == 1
    assert resp.choices[0].message.role == "assistant"
    assert resp.choices[0].message.content == "The answer is 42"
    assert resp.choices[0].finish_reason == "stop"
    assert resp.usage.prompt_tokens == 50
    assert resp.usage.completion_tokens == 10
    assert resp.usage.total_tokens == 60
    assert resp.created > 0


def test_build_chat_response_id_format():
    resp = build_chat_response(output="test", model="paddy")

    assert resp.id.startswith("chatcmpl-")
    assert len(resp.id) > len("chatcmpl-")


def test_message_history_alternating_order():
    messages = [
        ChatMessage(role="system", content="System"),
        ChatMessage(role="user", content="Q1"),
        ChatMessage(role="assistant", content="A1"),
        ChatMessage(role="user", content="Q2"),
        ChatMessage(role="assistant", content="A2"),
        ChatMessage(role="user", content="Q3"),
    ]
    prompt, history = openai_messages_to_pydantic(messages)

    assert prompt == "Q3"
    assert len(history) == 4

    assert isinstance(history[0], ModelRequest)
    assert isinstance(history[1], ModelResponse)
    assert isinstance(history[2], ModelRequest)
    assert isinstance(history[3], ModelResponse)

    req0 = history[0].parts[0]
    assert isinstance(req0, UserPromptPart)
    assert req0.content == "Q1"

    resp1 = history[1].parts[0]
    assert isinstance(resp1, TextPart)
    assert resp1.content == "A1"

    req2 = history[2].parts[0]
    assert isinstance(req2, UserPromptPart)
    assert req2.content == "Q2"

    resp3 = history[3].parts[0]
    assert isinstance(resp3, TextPart)
    assert resp3.content == "A2"
