"""OpenAI ↔ Pydantic AI message format conversion.

Converts between the OpenAI chat completion message format (used by
Obsidian Copilot) and Pydantic AI's internal ``ModelMessage`` types.
This adapter is shared because it will serve both the non-streaming
and future streaming chat endpoints.
"""

import uuid

from pydantic_ai.messages import (
    ModelMessage,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)

from app.core.logging import get_logger
from app.features.chat.models import (
    ChatCompletionResponse,
    ChatMessage,
    Choice,
    ResponseMessage,
    Usage,
)
from app.shared.utils import utcnow

logger = get_logger(__name__)


def openai_messages_to_pydantic(
    messages: list[ChatMessage],
) -> tuple[str, list[ModelMessage]]:
    """Convert OpenAI message array to Pydantic AI format.

    Extracts the last user message as the prompt and converts all prior
    user/assistant messages into ``ModelRequest``/``ModelResponse`` pairs
    for Pydantic AI's ``message_history`` parameter.

    System messages are discarded — the agent's own system prompt
    (defined in ``core/agent.py``) is used instead.

    Args:
        messages: The full OpenAI ``messages`` array from the request.

    Returns:
        A tuple of ``(user_prompt, message_history)`` where
        ``user_prompt`` is the text of the last user message and
        ``message_history`` is a list of prior turns as ``ModelMessage``.

    Raises:
        ValueError: If ``messages`` is empty or contains no user message.
    """
    if not messages:
        raise ValueError("Messages array must not be empty.")

    user_prompt: str | None = None
    system_skipped = 0
    prior_messages: list[ChatMessage] = []

    for msg in reversed(messages):
        if msg.role == "user" and user_prompt is None:
            user_prompt = msg.text_content
        elif msg.role == "system":
            system_skipped += 1
        else:
            prior_messages.append(msg)

    if user_prompt is None:
        raise ValueError("Messages must contain at least one user message.")

    prior_messages.reverse()

    history: list[ModelMessage] = []
    for msg in prior_messages:
        if msg.role == "user":
            history.append(ModelRequest(parts=[UserPromptPart(content=msg.text_content)]))
        elif msg.role == "assistant":
            history.append(ModelResponse(parts=[TextPart(content=msg.text_content)]))

    logger.info(
        "adapter.openai.messages_converted",
        total_messages=len(messages),
        history_messages=len(history),
        system_messages_skipped=system_skipped,
    )

    return user_prompt, history


def build_chat_response(
    output: str,
    model: str,
    request_tokens: int | None = None,
    response_tokens: int | None = None,
    total_tokens: int | None = None,
) -> ChatCompletionResponse:
    """Build an OpenAI-compatible chat completion response.

    Args:
        output: The agent's text output.
        model: The model name to echo back in the response.
        request_tokens: Prompt token count (from agent usage).
        response_tokens: Completion token count (from agent usage).
        total_tokens: Total token count (from agent usage).

    Returns:
        A ``ChatCompletionResponse`` ready for JSON serialization.
    """
    response_id = f"chatcmpl-{uuid.uuid4().hex[:29]}"
    created = int(utcnow().timestamp())

    return ChatCompletionResponse(
        id=response_id,
        created=created,
        model=model,
        choices=[
            Choice(
                message=ResponseMessage(content=output),
            ),
        ],
        usage=Usage(
            prompt_tokens=request_tokens or 0,
            completion_tokens=response_tokens or 0,
            total_tokens=total_tokens or 0,
        ),
    )
