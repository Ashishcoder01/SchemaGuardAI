
import secrets

from fastapi import Header, HTTPException

from .config import settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> bool:
    """Validate API-key authentication for protected endpoints."""

    if not settings.api_key:
        if settings.environment.lower() == "development":
            return True

        raise HTTPException(
            status_code=503,
            detail="API authentication is not configured.",
        )

    if not secrets.compare_digest(x_api_key or "", settings.api_key):
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key.",
        )

    return True
