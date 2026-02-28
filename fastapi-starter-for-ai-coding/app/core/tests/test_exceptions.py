"""Unit tests for custom exceptions and exception handlers."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    NoteNotFoundError,
    PaddyError,
    VaultError,
    VaultPathError,
    paddy_exception_handler,
    setup_exception_handlers,
)


def test_paddy_error_is_exception() -> None:
    """Test that PaddyError is properly defined and can be raised."""
    with pytest.raises(PaddyError):
        raise PaddyError("Test error")


def test_vault_error_inherits_from_paddy_error() -> None:
    """Test that VaultError inherits from PaddyError."""
    assert issubclass(VaultError, PaddyError)

    with pytest.raises(VaultError):
        raise VaultError("Vault error")

    with pytest.raises(PaddyError):
        raise VaultError("Vault error")


def test_note_not_found_error_inherits_from_vault_error() -> None:
    """Test that NoteNotFoundError inherits from VaultError."""
    assert issubclass(NoteNotFoundError, VaultError)

    with pytest.raises(NoteNotFoundError):
        raise NoteNotFoundError("Note not found")

    with pytest.raises(PaddyError):
        raise NoteNotFoundError("Note not found")


def test_vault_path_error_inherits_from_vault_error() -> None:
    """Test that VaultPathError inherits from VaultError."""
    assert issubclass(VaultPathError, VaultError)

    with pytest.raises(VaultPathError):
        raise VaultPathError("Path is invalid")

    with pytest.raises(PaddyError):
        raise VaultPathError("Path is invalid")


@pytest.mark.asyncio
async def test_paddy_exception_handler_logs_and_returns_json() -> None:
    """Test that the exception handler logs errors and returns proper JSON."""
    mock_request = MagicMock(spec=Request)
    mock_request.url.path = "/test/path"
    mock_request.method = "GET"
    exc = PaddyError("Test paddy error")

    with patch("app.core.exceptions.logger.error") as mock_logger:
        response = await paddy_exception_handler(mock_request, exc)

        mock_logger.assert_called_once()
        call_kwargs = mock_logger.call_args.kwargs
        assert call_kwargs["exc_info"] is True
        assert call_kwargs["error_type"] == "PaddyError"
        assert call_kwargs["error_message"] == "Test paddy error"

    assert isinstance(response, JSONResponse)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.body is not None


@pytest.mark.asyncio
async def test_paddy_exception_handler_returns_404_for_note_not_found() -> None:
    """Test that NoteNotFoundError returns 404 status code."""
    mock_request = MagicMock(spec=Request)
    mock_request.url.path = "/test/path"
    mock_request.method = "GET"
    exc = NoteNotFoundError("Missing note")

    with patch("app.core.exceptions.logger.error"):
        response = await paddy_exception_handler(mock_request, exc)

    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_paddy_exception_handler_returns_400_for_path_error() -> None:
    """Test that VaultPathError returns 400 status code."""
    mock_request = MagicMock(spec=Request)
    mock_request.url.path = "/test/path"
    mock_request.method = "GET"
    exc = VaultPathError("Invalid path")

    with patch("app.core.exceptions.logger.error"):
        response = await paddy_exception_handler(mock_request, exc)

    assert response.status_code == status.HTTP_400_BAD_REQUEST


def test_setup_exception_handlers_registers_handlers() -> None:
    """Test that setup_exception_handlers registers all exception handlers."""
    mock_app = MagicMock()
    setup_exception_handlers(mock_app)

    assert mock_app.add_exception_handler.call_count == 4
    call_args_list = [call[0][0] for call in mock_app.add_exception_handler.call_args_list]
    assert PaddyError in call_args_list
    assert VaultError in call_args_list
    assert NoteNotFoundError in call_args_list
    assert VaultPathError in call_args_list
