"""POST /v1/chat/completions endpoint for Obsidian Copilot integration.

This module implements the OpenAI-compatible chat completions endpoint
that Obsidian Copilot connects to. It handles API key authentication,
message conversion, agent execution via ``agent.iter()``, and response
formatting.
"""

import time

from fastapi import APIRouter, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.agent import vault_agent
from app.core.config import get_settings
from app.core.dependencies import VaultDependencies
from app.core.logging import get_logger
from app.features.chat.models import ChatCompletionRequest, ChatCompletionResponse
from app.shared.openai_adapter import build_chat_response, openai_messages_to_pydantic

logger = get_logger(__name__)

router = APIRouter(prefix="/v1", tags=["chat"])

security = HTTPBearer()


async def verify_api_key(
    credentials: HTTPAuthorizationCredentials = Security(security),  # noqa: B008
) -> HTTPAuthorizationCredentials:
    """Validate the Bearer token against the configured API key.

    Args:
        credentials: The parsed Authorization header.

    Returns:
        The validated credentials.

    Raises:
        HTTPException: 401 if the token does not match ``settings.api_key``.
    """
    settings = get_settings()
    if credentials.credentials != settings.api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    return credentials


@router.post(
    "/chat/completions",
    response_model=ChatCompletionResponse,
    dependencies=[Security(verify_api_key)],
)
async def chat_completions(
    request: ChatCompletionRequest,
) -> ChatCompletionResponse:
    """OpenAI-compatible chat completions endpoint.

    Accepts a standard OpenAI chat completion request, converts the
    messages to Pydantic AI format, runs the agent, and returns an
    OpenAI-compatible response.

    Args:
        request: The chat completion request body.

    Returns:
        An OpenAI-compatible chat completion response.

    Raises:
        HTTPException: 400 if streaming is requested or messages are invalid.
        HTTPException: 500 if the agent run fails.
    """
    logger.info(
        "chat.completions.request_received",
        model=request.model,
        message_count=len(request.messages),
        stream=request.stream,
    )

    if request.stream:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Streaming not yet supported. Set stream to false in "
                "Copilot settings or enable CORS bypass."
            ),
        )

    try:
        user_prompt, message_history = openai_messages_to_pydantic(request.messages)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        ) from e

    settings = get_settings()
    deps = VaultDependencies(vault_path=settings.obsidian_vault_path)

    logger.info(
        "chat.completions.agent_run_started",
        user_prompt_length=len(user_prompt),
        history_length=len(message_history),
    )

    start = time.time()
    try:
        async with vault_agent.iter(
            user_prompt=user_prompt,
            message_history=message_history,
            deps=deps,
        ) as agent_run:
            async for _node in agent_run:
                pass
        result = agent_run.result
    except Exception as e:
        logger.error(
            "chat.completions.request_failed",
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent execution failed. Check server logs for details.",
        ) from e

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent returned no result.",
        )

    duration = time.time() - start
    usage = result.usage()

    logger.info(
        "chat.completions.response_completed",
        total_tokens=usage.total_tokens,
        duration_seconds=round(duration, 3),
    )

    return build_chat_response(
        output=result.data,
        model=request.model,
        request_tokens=usage.request_tokens,
        response_tokens=usage.response_tokens,
        total_tokens=usage.total_tokens,
    )
