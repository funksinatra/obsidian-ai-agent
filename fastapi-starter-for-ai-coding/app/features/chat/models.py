"""OpenAI-compatible Pydantic models for the chat completions API.

These models define the request and response schema for the
POST /v1/chat/completions endpoint, matching the OpenAI chat
completion format that Obsidian Copilot expects.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class ContentPart(BaseModel):
    """A single content part in a multimodal message.

    Used when Copilot sends array-format content (e.g., with images).
    For text-only messages, Copilot sends content as a plain string.
    """

    type: str
    text: str | None = None
    image_url: dict[str, Any] | None = None


class ChatMessage(BaseModel):
    """A single message in the OpenAI chat format.

    Copilot sends content as a string in 99% of cases. Array format
    is used only for vision/multimodal requests. The ``text_content``
    property normalizes both formats to a plain string.
    """

    role: Literal["system", "user", "assistant"]
    content: str | list[ContentPart]

    @property
    def text_content(self) -> str:
        """Normalize content to a plain text string.

        Returns:
            The message text extracted from either string or array content.
        """
        if isinstance(self.content, str):
            return self.content
        return "".join(part.text for part in self.content if part.type == "text" and part.text)


class ChatCompletionRequest(BaseModel):
    """OpenAI-compatible chat completion request.

    Accepted by POST /v1/chat/completions. Optional parameters like
    ``temperature`` and ``max_tokens`` are accepted for compatibility
    but not forwarded to the agent in the MVP.
    """

    model: str
    messages: list[ChatMessage]
    stream: bool = False
    temperature: float | None = None
    max_tokens: int | None = None
    top_p: float | None = None
    frequency_penalty: float | None = None


class ResponseMessage(BaseModel):
    """Assistant message returned inside a chat completion choice."""

    role: Literal["assistant"] = "assistant"
    content: str


class Choice(BaseModel):
    """A single completion choice in the response."""

    index: int = 0
    message: ResponseMessage
    finish_reason: Literal["stop", "length"] = "stop"


class Usage(BaseModel):
    """Token usage statistics for the completion."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    """OpenAI-compatible chat completion response.

    Matches the format expected by Obsidian Copilot and the OpenAI SDK.
    """

    id: str
    object: Literal["chat.completion"] = "chat.completion"
    created: int
    model: str
    choices: list[Choice]
    usage: Usage = Field(default_factory=Usage)
