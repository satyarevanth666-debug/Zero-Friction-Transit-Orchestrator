"""Common dependency injection providers."""

from fastapi import Request


def get_request_id(request: Request) -> str:
    """Extract or return active request ID."""
    return getattr(request.state, "request_id", "req-unknown")
