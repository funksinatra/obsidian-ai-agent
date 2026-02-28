"""Tests for shared Pydantic schemas."""

from app.shared.schemas import ErrorResponse


def test_error_response_structure() -> None:
    """Test ErrorResponse structure."""
    error = ErrorResponse(
        error="Invalid input",
        type="validation_error",
        detail="The provided email is not valid",
    )

    assert error.error == "Invalid input"
    assert error.type == "validation_error"
    assert error.detail == "The provided email is not valid"


def test_error_response_optional_detail() -> None:
    """Test that ErrorResponse detail is optional."""
    error = ErrorResponse(
        error="Server error",
        type="internal_error",
    )

    assert error.error == "Server error"
    assert error.type == "internal_error"
    assert error.detail is None
