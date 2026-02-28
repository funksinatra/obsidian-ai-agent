"""Unit tests for chat feature Pydantic models."""

from app.features.chat.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ChatMessage,
    Choice,
    ContentPart,
    ResponseMessage,
    Usage,
)


def test_chat_message_string_content():
    msg = ChatMessage(role="user", content="Hello world")
    assert msg.text_content == "Hello world"


def test_chat_message_array_content():
    msg = ChatMessage(
        role="user",
        content=[
            ContentPart(type="text", text="First part"),
            ContentPart(type="text", text=" second part"),
        ],
    )
    assert msg.text_content == "First part second part"


def test_chat_message_mixed_array_content():
    msg = ChatMessage(
        role="user",
        content=[
            ContentPart(type="text", text="What is this?"),
            ContentPart(type="image_url", image_url={"url": "data:image/png;base64,..."}),
        ],
    )
    assert msg.text_content == "What is this?"


def test_chat_completion_request_defaults():
    req = ChatCompletionRequest(
        model="paddy",
        messages=[ChatMessage(role="user", content="Hi")],
    )
    assert req.stream is False
    assert req.temperature is None
    assert req.max_tokens is None
    assert req.top_p is None
    assert req.frequency_penalty is None


def test_chat_completion_response_structure():
    resp = ChatCompletionResponse(
        id="chatcmpl-abc123",
        created=1700000000,
        model="paddy",
        choices=[
            Choice(
                message=ResponseMessage(content="Hello!"),
            ),
        ],
        usage=Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15),
    )
    data = resp.model_dump()

    assert data["id"] == "chatcmpl-abc123"
    assert data["object"] == "chat.completion"
    assert data["created"] == 1700000000
    assert data["model"] == "paddy"
    assert len(data["choices"]) == 1
    assert data["choices"][0]["message"]["role"] == "assistant"
    assert data["choices"][0]["message"]["content"] == "Hello!"
    assert data["choices"][0]["finish_reason"] == "stop"
    assert data["usage"]["prompt_tokens"] == 10
    assert data["usage"]["completion_tokens"] == 5
    assert data["usage"]["total_tokens"] == 15


def test_content_part_text_only():
    part = ContentPart(type="text", text="Some text")
    assert part.type == "text"
    assert part.text == "Some text"
    assert part.image_url is None


def test_usage_defaults():
    usage = Usage()
    assert usage.prompt_tokens == 0
    assert usage.completion_tokens == 0
    assert usage.total_tokens == 0
