"""Error response schemas for API endpoints."""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""

    BAD_REQUEST = "BAD_REQUEST"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    INTERNAL = "INTERNAL"


class ErrorResponse(BaseModel):
    """Standard error response format."""

    error: dict[str, Any] = Field(
        ...,
        description="Error details containing code and message",
    )


def create_error_response(
    code: ErrorCode,
    message: str,
) -> ErrorResponse:
    """Create a standardized error response.

    Args:
        code: Error code enum
        message: Human-readable error message

    Returns:
        ErrorResponse: Formatted error response
    """
    return ErrorResponse(error={"code": code.value, "message": message})
