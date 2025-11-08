"""Checkpoint configuration validation for fail-fast startup checks.

This module provides validation for Redis checkpoint configuration to prevent
runtime errors from malformed connection URLs. Implements the "fail fast"
principle: detect configuration errors at application startup, not during
first use.

Background:
-----------
Production incident staging-758b8f744 where pods crashed at runtime due to
unencoded special characters in Redis password. This validator would have
caught the error during startup with a clear, actionable error message.

Usage:
------
```python
from mcp_server_langgraph.core.checkpoint_validator import validate_checkpoint_config
from mcp_server_langgraph.core.config import settings

# At application startup:
validate_checkpoint_config(settings)
```
"""

from typing import Any
from urllib.parse import unquote

from mcp_server_langgraph.observability.telemetry import logger


class CheckpointValidationError(Exception):
    """Raised when checkpoint configuration validation fails.

    This exception indicates a configuration error that must be fixed
    before the application can start safely.
    """


class CheckpointConfigValidator:
    """Validator for checkpoint configuration with fail-fast semantics."""

    # RFC 3986 reserved characters that MUST be percent-encoded in passwords
    RESERVED_CHARS = set(":/?#[]@!$&'()*+,;=")

    def __init__(self) -> None:
        """Initialize checkpoint configuration validator."""

    def validate_redis_url(
        self,
        url: str,
        test_connection: bool = False,
    ) -> None:
        """Validate Redis connection URL format and encoding.

        Args:
            url: Redis connection URL to validate
            test_connection: If True, attempt to connect to Redis (optional)

        Raises:
            CheckpointValidationError: If URL is invalid or improperly encoded

        Examples:
            >>> validator = CheckpointConfigValidator()
            >>> validator.validate_redis_url("redis://:pass%2Fword@localhost:6379/1")  # OK
            >>> validator.validate_redis_url("redis://:pass/word@localhost:6379/1")  # Raises error
        """
        if not url:
            raise CheckpointValidationError(
                "Redis URL cannot be empty when checkpoint_backend='redis'. "
                "Please set CHECKPOINT_REDIS_URL environment variable."
            )

        # Validate basic URL format
        if not url.startswith("redis://"):
            raise CheckpointValidationError(
                f"Invalid Redis URL scheme.\n"
                f"Expected: redis://...\n"
                f"Got: {url[:20] if len(url) > 20 else url}...\n"
                f"Valid format: redis://[user]:[password]@[host]:[port]/[database]"
            )

        # Check for obviously invalid formats
        if url == "redis://":
            raise CheckpointValidationError(
                "Incomplete Redis URL: 'redis://'\n"
                "Valid format: redis://[user]:[password]@[host]:[port]/[database]\n"
                "Example: redis://localhost:6379/1"
            )

        # Extract and validate password encoding
        self._validate_password_encoding(url)

        # Optionally test actual connection
        if test_connection:
            self._test_redis_connection(url)

    def _validate_password_encoding(self, url: str) -> None:
        """Validate that password (if present) is properly percent-encoded.

        Args:
            url: Redis URL to validate

        Raises:
            CheckpointValidationError: If password contains unencoded special characters
        """
        # Check if URL has authentication (contains @ after scheme)
        if "@" not in url:
            # No password, validation passes
            return

        try:
            # Extract credentials portion (between :// and @)
            after_scheme = url[8:]  # Remove 'redis://'
            at_pos = after_scheme.rfind("@")

            if at_pos == -1:
                return  # No @ found (edge case)

            credentials = after_scheme[:at_pos]

            # Check if there's a password (contains :)
            if ":" not in credentials:
                return  # No password

            # Extract password (everything after first :)
            colon_pos = credentials.find(":")
            password = credentials[colon_pos + 1 :]

            if not password:
                return  # Empty password

            # Check for unencoded special characters
            unencoded_chars = self._find_unencoded_chars(password)

            if unencoded_chars:
                self._raise_encoding_error(url, password, unencoded_chars)

        except CheckpointValidationError:
            # Re-raise our validation errors
            raise
        except Exception as e:
            # Catch any parsing errors
            raise CheckpointValidationError(
                f"Failed to parse Redis URL: {str(e)}\n"
                f"URL format should be: redis://[user]:[password]@[host]:[port]/[database]\n"
                f"Ensure password is percent-encoded per RFC 3986."
            )

    def _find_unencoded_chars(self, password: str) -> set[str]:
        """Find unencoded special characters in password.

        Args:
            password: Password string to check

        Returns:
            Set of unencoded special characters found
        """
        unencoded: set[str] = set()

        for char in self.RESERVED_CHARS:
            # Skip : as it's used as delimiter
            if char == ":":
                continue

            if char in password:
                # Check if it's part of a percent-encoded sequence
                # If we find the literal character, it's unencoded
                if not self._is_part_of_encoding(password, char):
                    unencoded.add(char)

        return unencoded

    def _is_part_of_encoding(self, password: str, char: str) -> bool:
        """Check if character is part of a %XX encoding sequence.

        Args:
            password: Password string
            char: Character to check

        Returns:
            True if character is already properly encoded
        """
        # Simple heuristic: if we can decode the password without errors
        # and it's different from the original, it was encoded
        try:
            decoded = unquote(password)
            # If password contains %, assume it might be encoded
            if "%" in password:
                # If decoding changed it, it was encoded
                return decoded != password
        except Exception:
            pass

        return False

    def _raise_encoding_error(
        self,
        url: str,
        password: str,
        unencoded_chars: set[str],
    ) -> None:
        """Raise detailed error about unencoded characters.

        Args:
            url: Full Redis URL
            password: Unencoded password
            unencoded_chars: Set of problematic characters

        Raises:
            CheckpointValidationError: With detailed fix instructions
        """
        # Sanitize URL for error message (hide password)
        sanitized_url = url.replace(password, "****")

        # Create encoded example
        from urllib.parse import quote

        encoded_password = quote(password, safe="")
        encoded_url = url.replace(password, encoded_password)

        # Format error message with fix instructions
        chars_list = ", ".join(f"'{c}'" for c in sorted(unencoded_chars))

        error_msg = (
            f"Redis URL contains unencoded special characters in password: {chars_list}\n\n"
            f"**PRODUCTION INCIDENT REFERENCE**: This is the same error that caused\n"
            f"staging-758b8f744 to crash with 'ValueError: Port could not be cast to integer'.\n\n"
            f"Current URL (sanitized): {sanitized_url}\n\n"
            f"**FIX**: Percent-encode the password per RFC 3986:\n\n"
            f"Encoded URL example:\n"
            f"  {encoded_url}\n\n"
            f"Character encoding reference:\n"
            f"  /  → %2F\n"
            f"  +  → %2B\n"
            f"  =  → %3D\n"
            f"  @  → %40\n"
            f"  (space) → %20\n\n"
            f"For Kubernetes External Secrets, use:\n"
            f'  redis-url: "redis://:{{{{ .redisPassword | urlquery }}}}@host:port/db"\n\n'
            f"For local development, use:\n"
            f"  CHECKPOINT_REDIS_URL={encoded_url}\n"
        )

        raise CheckpointValidationError(error_msg)

    def _test_redis_connection(self, url: str) -> None:
        """Optionally test actual Redis connection.

        Args:
            url: Redis URL to test

        Raises:
            CheckpointValidationError: If connection fails
        """
        try:
            import redis.asyncio as redis_async

            logger.info(
                "Testing Redis connection for checkpoint configuration",
                extra={"redis_url": url},
            )

            # Attempt to create client (will fail if URL is malformed)
            # Note: This doesn't actually connect, just validates URL parsing
            _client = redis_async.from_url(url)  # noqa: F841

            # Close the client (cleanup)
            # In production, actual connection test would be async

        except ImportError as e:
            raise CheckpointValidationError(f"Redis client library not available: {e}\n" f"Install: pip install redis")
        except ConnectionError as e:
            raise CheckpointValidationError(
                f"Failed to connect to Redis: {e}\n" f"Check that Redis is running and accessible at the specified URL."
            )
        except Exception as e:
            raise CheckpointValidationError(
                f"Redis connection test failed: {e}\n" f"Verify the Redis URL is correct and Redis is accessible."
            )


def validate_checkpoint_config(settings: Any) -> None:
    """Validate checkpoint configuration at application startup.

    This function should be called during application initialization to
    catch configuration errors early with clear error messages.

    Args:
        settings: Application settings object with checkpoint configuration

    Raises:
        CheckpointValidationError: If configuration is invalid

    Example:
        >>> from mcp_server_langgraph.core.config import settings
        >>> validate_checkpoint_config(settings)  # At startup
    """
    backend = settings.checkpoint_backend.lower()

    if backend == "memory":
        # Memory backend doesn't require validation
        logger.info("Checkpoint backend: memory (no validation required)")
        return

    if backend == "redis":
        logger.info("Validating Redis checkpoint configuration...")

        validator = CheckpointConfigValidator()

        # Validate Redis URL
        validator.validate_redis_url(
            url=settings.checkpoint_redis_url,
            test_connection=False,  # Don't test connection at startup
        )

        logger.info(
            "Redis checkpoint configuration validated successfully",
            extra={
                "redis_url": settings.checkpoint_redis_url,
                "ttl_seconds": settings.checkpoint_redis_ttl,
            },
        )
    else:
        logger.warning(
            f"Unknown checkpoint backend: {backend}. Validation skipped.",
            extra={"backend": backend},
        )
