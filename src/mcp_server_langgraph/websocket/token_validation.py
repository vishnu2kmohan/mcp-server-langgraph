"""
WebSocket Token Validation.

Provides functions for checking JWT token expiration during active
WebSocket connections. Used for periodic validation to detect expired
tokens and close connections gracefully with code 4010.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

import jwt

logger = logging.getLogger(__name__)


def is_token_expired(token: str) -> bool:
    """
    Check if a JWT token is expired.

    Decodes the token without signature verification to check the exp claim.
    Returns True (fail-safe) if the token is invalid or missing exp claim.

    Args:
        token: The JWT token string.

    Returns:
        True if token is expired or invalid, False if still valid.
    """
    try:
        # Decode without verification to extract claims
        # (signature was already verified at connection time)
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")
        if exp is None:
            logger.warning("Token missing exp claim, treating as expired")
            return True

        # exp is a Unix timestamp
        exp_datetime = datetime.fromtimestamp(exp, tz=UTC)
        now = datetime.now(UTC)

        return now >= exp_datetime
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token during expiration check: {e}")
        return True
    except Exception as e:
        logger.warning(f"Error checking token expiration: {e}")
        return True


def is_token_expiring_soon(token: str, buffer_seconds: int = 300) -> bool:
    """
    Check if a JWT token is expiring within the buffer period.

    Used for proactive token refresh before actual expiration.

    Args:
        token: The JWT token string.
        buffer_seconds: Number of seconds before expiration to consider
            as "expiring soon". Default is 300 (5 minutes).

    Returns:
        True if token expires within buffer period or is already expired,
        False otherwise.
    """
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")
        if exp is None:
            return True

        exp_datetime = datetime.fromtimestamp(exp, tz=UTC)
        now = datetime.now(UTC)

        # Check if token expires within buffer
        time_remaining = (exp_datetime - now).total_seconds()
        return time_remaining <= buffer_seconds
    except jwt.InvalidTokenError:
        return True
    except Exception:
        return True


def get_token_expiration(token: str) -> datetime | None:
    """
    Extract the expiration datetime from a JWT token.

    Args:
        token: The JWT token string.

    Returns:
        Datetime of token expiration, or None if token is invalid
        or missing exp claim.
    """
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
        exp = payload.get("exp")
        if exp is None:
            return None

        return datetime.fromtimestamp(exp, tz=UTC)
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None
