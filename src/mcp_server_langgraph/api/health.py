"""
Health Check and Startup Validation

Provides health check endpoint and startup validation to ensure all critical
systems are properly initialized before the app accepts requests.

This module prevents the classes of issues found in OpenAI Codex audit from recurring.
"""

from typing import Dict, List

from fastapi import APIRouter, status
from pydantic import BaseModel

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger

router = APIRouter(prefix="/api/v1/health", tags=["health"])


class HealthCheckResult(BaseModel):
    """Health check result model"""

    status: str
    checks: Dict[str, bool]
    errors: List[str]
    warnings: List[str]


class SystemValidationError(Exception):
    """Raised when critical system validation fails at startup"""


def validate_observability_initialized() -> tuple[bool, str]:
    """
    Validate that observability system is properly initialized.

    Returns:
        Tuple of (is_healthy, message)

    Related to: OpenAI Codex Finding #2 - Observability not initialized
    """
    try:
        # Test that logger is usable
        logger.debug("Observability health check")
        return True, "Observability initialized and functional"
    except RuntimeError as e:
        return False, f"Observability not initialized: {e}"


def validate_session_store_registered() -> tuple[bool, str]:
    """
    Validate that session store is properly registered globally.

    Returns:
        Tuple of (is_healthy, message)

    Related to: OpenAI Codex Finding #3 - Session storage miswired
    """
    if settings.auth_mode != "session":
        return True, "Session auth not enabled (token mode)"

    try:
        from mcp_server_langgraph.auth.session import get_session_store

        session_store = get_session_store()

        # Note: get_session_store() always returns SessionStore (never None per type signature)
        # If it were to return None, it would have raised an error already in dependency injection

        # Check if we're using the fallback (warning in logs indicates this)
        store_type = type(session_store).__name__

        # Expected: RedisSessionStore if redis configured, InMemorySessionStore if memory configured
        if settings.session_backend == "redis" and store_type != "RedisSessionStore":
            return False, f"Expected RedisSessionStore, got {store_type} (fallback detected)"

        return True, f"Session store registered: {store_type}"
    except Exception as e:
        return False, f"Session store validation failed: {e}"


def validate_api_key_cache_configured() -> tuple[bool, str]:
    """
    Validate that API key cache is properly configured if enabled.

    Returns:
        Tuple of (is_healthy, message)

    Related to: OpenAI Codex Finding #5 - Redis API key caching not used
    """
    if not settings.api_key_cache_enabled:
        return True, "API key caching disabled by configuration"

    if not settings.redis_url:
        return True, "API key caching disabled (no redis_url configured)"

    # We can't easily check the singleton without triggering initialization
    # Instead, we validate the configuration is consistent
    warnings = []

    if settings.api_key_cache_ttl <= 0:
        warnings.append(f"Cache TTL is {settings.api_key_cache_ttl}, should be > 0")

    if warnings:
        return False, f"API key cache configuration issues: {', '.join(warnings)}"

    return True, "API key caching properly configured"


def validate_docker_sandbox_security() -> tuple[bool, str]:
    """
    Validate that Docker sandbox has proper security configuration.

    Returns:
        Tuple of (is_healthy, message)

    Related to: OpenAI Codex Finding #4 - Docker sandbox security
    """
    # This is informational - we can't check Docker runtime config without creating a container
    warnings = []

    # Check if network allowlist is being used (not fully implemented)
    if hasattr(settings, "sandbox_network_mode"):
        if settings.sandbox_network_mode == "allowlist":
            warnings.append("Network allowlist mode is not fully implemented - using unrestricted bridge network")

    if warnings:
        return True, f"Docker sandbox warnings: {', '.join(warnings)}"

    return True, "Docker sandbox security checks not applicable (runtime validation required)"


def run_startup_validation() -> None:
    """
    Run all startup validations and raise SystemValidationError if critical checks fail.

    This function should be called during application startup to ensure all
    systems are properly initialized before accepting requests.

    Raises:
        SystemValidationError: If any critical validation fails

    Example:
        # In app.py or startup event
        try:
            run_startup_validation()
        except SystemValidationError as e:
            logger.critical(f"Startup validation failed: {e}")
            raise
    """
    checks = {
        "observability": validate_observability_initialized(),
        "session_store": validate_session_store_registered(),
        "api_key_cache": validate_api_key_cache_configured(),
        "docker_sandbox": validate_docker_sandbox_security(),
    }

    errors = []
    warnings = []

    for check_name, (is_healthy, message) in checks.items():
        if is_healthy:
            logger.info(f"✓ {check_name}: {message}")
            if "warning" in message.lower():
                warnings.append(f"{check_name}: {message}")
        else:
            logger.error(f"✗ {check_name}: {message}")
            errors.append(f"{check_name}: {message}")

    if errors:
        error_msg = f"Startup validation failed: {', '.join(errors)}"
        logger.critical(error_msg)
        raise SystemValidationError(error_msg)

    if warnings:
        logger.warning(f"Startup validation warnings: {', '.join(warnings)}")

    logger.info("All startup validations passed")


@router.get(
    "",
    response_model=HealthCheckResult,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Check the health status of all critical systems",
)
async def health_check() -> HealthCheckResult:
    """
    Health check endpoint that validates all critical systems.

    Returns:
        HealthCheckResult with status and detailed check results

    Example:
        ```
        GET /api/v1/health
        {
            "status": "healthy",
            "checks": {
                "observability": true,
                "session_store": true,
                "api_key_cache": true,
                "docker_sandbox": true
            },
            "errors": [],
            "warnings": []
        }
        ```
    """
    checks_dict = {
        "observability": validate_observability_initialized(),
        "session_store": validate_session_store_registered(),
        "api_key_cache": validate_api_key_cache_configured(),
        "docker_sandbox": validate_docker_sandbox_security(),
    }

    # Convert to bool dict and collect errors/warnings
    checks = {}
    errors = []
    warnings = []

    for check_name, (is_healthy, message) in checks_dict.items():
        checks[check_name] = is_healthy
        if not is_healthy:
            errors.append(f"{check_name}: {message}")
        elif "warning" in message.lower():
            warnings.append(f"{check_name}: {message}")

    # Overall status
    overall_status = "healthy" if not errors else "unhealthy"
    if warnings and not errors:
        overall_status = "degraded"

    return HealthCheckResult(
        status=overall_status,
        checks=checks,
        errors=errors,
        warnings=warnings,
    )
