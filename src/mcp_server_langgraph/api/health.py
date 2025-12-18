"""
Health Check and Startup Validation

Provides health check endpoint and startup validation to ensure all critical
systems are properly initialized before the app accepts requests.

This module prevents the classes of issues found in OpenAI Codex audit from recurring.
"""

from fastapi import APIRouter, status
from pydantic import BaseModel

from mcp_server_langgraph.core.config import settings
from mcp_server_langgraph.observability.telemetry import logger

router = APIRouter(prefix="/api/v1/health", tags=["health"])


class HealthCheckResult(BaseModel):
    """Health check result model"""

    status: str
    checks: dict[str, bool]
    errors: list[str]
    warnings: list[str]


class LivenessResult(BaseModel):
    """Liveness probe result (K8s livenessProbe)."""

    status: str  # "alive" or "dead"


class ReadinessResult(BaseModel):
    """Readiness probe result (K8s readinessProbe)."""

    status: str  # "ready" or "not_ready"
    checks: dict[str, bool]


class StartupResult(BaseModel):
    """Startup probe result (K8s startupProbe)."""

    status: str  # "started" or "starting"
    observability: bool


class DependencyStatus(BaseModel):
    """Detailed dependency status."""

    name: str
    healthy: bool
    message: str
    latency_ms: float | None = None


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
    if hasattr(settings, "sandbox_network_mode") and settings.sandbox_network_mode == "allowlist":
        warnings.append("Network allowlist mode is not fully implemented - using unrestricted bridge network")

    if warnings:
        return True, f"Docker sandbox warnings: {', '.join(warnings)}"

    return True, "Docker sandbox security checks not applicable (runtime validation required)"


def validate_database_connectivity() -> tuple[bool, str]:
    """
    Validate that PostgreSQL database is accessible.

    Returns:
        Tuple of (is_healthy, message)

    Related to: PostgreSQL dependency chain validation
    """
    import asyncio

    from mcp_server_langgraph.infrastructure.database import check_database_connectivity

    # Parse the postgres URL from settings
    postgres_url = settings.gdpr_postgres_url

    logger.debug(f"Validating database connectivity to {postgres_url.split('@')[-1]}")

    # Run the async check synchronously
    try:
        return asyncio.run(check_database_connectivity(postgres_url, timeout=5.0))
    except RuntimeError as e:
        # If we're already in an event loop (shouldn't happen in startup)
        if "cannot be called from a running event loop" in str(e):
            return False, "Database validation failed: already in event loop"
        raise


async def validate_database_connectivity_async() -> tuple[bool, str]:
    """
    Validate that PostgreSQL database is accessible (async version).

    Returns:
        Tuple of (is_healthy, message)
    """
    from mcp_server_langgraph.infrastructure.database import check_database_connectivity

    # Parse the postgres URL from settings
    postgres_url = settings.gdpr_postgres_url

    logger.debug(f"Validating database connectivity to {postgres_url.split('@')[-1]}")

    return await check_database_connectivity(postgres_url, timeout=5.0)


async def validate_loki_connectivity_async() -> tuple[bool, str]:
    """
    Validate Loki log aggregation connectivity.

    This function is skipped if Loki is not configured (no loki_url).

    Returns:
        Tuple of (is_healthy, message)

    Related to: LGTM Stack validation for observability
    """
    # Skip validation if Loki is not configured
    if not settings.loki_url:
        return True, "Loki disabled - not configured"

    try:
        from mcp_server_langgraph.core.startup_validation import validate_loki_connection

        result = await validate_loki_connection(
            url=settings.loki_url,
            timeout=5,
        )

        if result.success:
            return True, result.message or "Loki connected"
        else:
            return False, result.error or "Loki connection failed"

    except Exception as e:
        logger.error(
            "Loki validation error",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        return False, f"Loki validation failed: {e}"


async def validate_tempo_connectivity_async() -> tuple[bool, str]:
    """
    Validate Tempo distributed tracing connectivity.

    This function is skipped if Tempo is not configured (no tempo_url).

    Returns:
        Tuple of (is_healthy, message)

    Related to: LGTM Stack validation for observability
    """
    # Skip validation if Tempo is not configured
    if not settings.tempo_url:
        return True, "Tempo disabled - not configured"

    try:
        from mcp_server_langgraph.core.startup_validation import validate_tempo_connection

        result = await validate_tempo_connection(
            url=settings.tempo_url,
            timeout=5,
        )

        if result.success:
            return True, result.message or "Tempo connected"
        else:
            return False, result.error or "Tempo connection failed"

    except Exception as e:
        logger.error(
            "Tempo validation error",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        return False, f"Tempo validation failed: {e}"


async def validate_mimir_connectivity_async() -> tuple[bool, str]:
    """
    Validate Mimir metrics connectivity.

    This function is skipped if Mimir is not configured (no mimir_url).

    Returns:
        Tuple of (is_healthy, message)

    Related to: LGTM Stack validation for observability
    """
    # Skip validation if Mimir is not configured
    if not settings.mimir_url:
        return True, "Mimir disabled - not configured"

    try:
        from mcp_server_langgraph.core.startup_validation import validate_mimir_connection

        result = await validate_mimir_connection(
            url=settings.mimir_url,
            timeout=5,
        )

        if result.success:
            return True, result.message or "Mimir connected"
        else:
            return False, result.error or "Mimir connection failed"

    except Exception as e:
        logger.error(
            "Mimir validation error",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        return False, f"Mimir validation failed: {e}"


async def bootstrap_qdrant_default_collection_async() -> tuple[bool, str]:
    """
    Bootstrap the default Qdrant collection at startup.

    Creates the collection if it doesn't exist. This ensures E2E tests
    and new deployments have the required collection available.

    Returns:
        Tuple of (success, message)

    Related to: VectorsPage E2E test failures - collection not bootstrapped
    """
    # Skip if Qdrant is not configured
    if not settings.qdrant_url and not settings.enable_dynamic_context_loading:
        return True, "Qdrant bootstrap skipped - not configured"

    if not settings.qdrant_url:
        return True, "Qdrant bootstrap skipped - no qdrant_url configured"

    try:
        from mcp_server_langgraph.core.startup_validation import bootstrap_qdrant_collection

        result = await bootstrap_qdrant_collection(
            url=settings.qdrant_url,
            collection_name=settings.qdrant_collection_name,
            vector_size=getattr(settings, "qdrant_vector_size", 384),
            timeout=10,
        )

        if result.success:
            if result.created:
                return True, f"Qdrant collection '{settings.qdrant_collection_name}' created"
            else:
                return True, f"Qdrant collection '{settings.qdrant_collection_name}' already exists"
        else:
            return False, f"Qdrant bootstrap failed: {result.error}"

    except Exception as e:
        logger.warning(
            "Qdrant bootstrap failed",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        return False, f"Qdrant bootstrap error: {e}"


async def validate_qdrant_connectivity_async() -> tuple[bool, str]:
    """
    Validate Qdrant vector database connectivity.

    This function is skipped if Qdrant is not configured (no qdrant_url and
    dynamic context loading is disabled).

    Returns:
        Tuple of (is_healthy, message)

    Related to: E2E Test infrastructure validation - VectorsPage failures
    """
    # Skip validation if Qdrant is not configured
    if not settings.qdrant_url and not settings.enable_dynamic_context_loading:
        return True, "Qdrant disabled - not configured"

    # If URL is empty but dynamic context loading is expected, it's a config issue
    if not settings.qdrant_url:
        return True, "Qdrant not configured (no qdrant_url)"

    try:
        from mcp_server_langgraph.core.startup_validation import validate_qdrant_connection

        result = await validate_qdrant_connection(
            url=settings.qdrant_url,
            timeout=5,
        )

        if result.success:
            return True, result.message or "Qdrant connected"
        else:
            return False, result.error or "Qdrant connection failed"

    except Exception as e:
        logger.error(
            "Qdrant validation error",
            extra={"error": str(e), "error_type": type(e).__name__},
        )
        return False, f"Qdrant validation failed: {e}"


def run_startup_validation() -> None:
    """
    Run all startup validations and raise SystemValidationError if critical checks fail.
    ...
    """
    checks = {
        "observability": validate_observability_initialized(),
        "session_store": validate_session_store_registered(),
        "api_key_cache": validate_api_key_cache_configured(),
        "docker_sandbox": validate_docker_sandbox_security(),
        "database_connectivity": validate_database_connectivity(),
    }
    _process_validation_results(checks)


async def run_startup_validation_async() -> None:
    """
    Run all startup validations asynchronously.
    """
    checks = {
        "observability": validate_observability_initialized(),
        "session_store": validate_session_store_registered(),
        "api_key_cache": validate_api_key_cache_configured(),
        "docker_sandbox": validate_docker_sandbox_security(),
        "database_connectivity": await validate_database_connectivity_async(),
        "qdrant_connectivity": await validate_qdrant_connectivity_async(),
        "loki_connectivity": await validate_loki_connectivity_async(),
        "tempo_connectivity": await validate_tempo_connectivity_async(),
        "mimir_connectivity": await validate_mimir_connectivity_async(),
    }
    _process_validation_results(checks)

    # Bootstrap Qdrant collection if configured (after connectivity validation)
    # This ensures E2E tests and new deployments have required collections
    if settings.qdrant_url:
        success, message = await bootstrap_qdrant_default_collection_async()
        if success:
            logger.info(f"✓ qdrant_bootstrap: {message}")
        else:
            # Graceful degradation - log warning but don't block startup
            logger.warning(f"⚠ qdrant_bootstrap: {message}")


def _process_validation_results(checks: dict[str, tuple[bool, str]]) -> None:
    """Process validation results and raise error if needed."""
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
        "database_connectivity": await validate_database_connectivity_async(),
        "qdrant_connectivity": await validate_qdrant_connectivity_async(),
        "loki_connectivity": await validate_loki_connectivity_async(),
        "tempo_connectivity": await validate_tempo_connectivity_async(),
        "mimir_connectivity": await validate_mimir_connectivity_async(),
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


# ==============================================================================
# Granular Health Probes (K8s Probe Pattern)
# ==============================================================================


@router.get(
    "/live",
    status_code=status.HTTP_200_OK,
    summary="Liveness Probe",
    description="Lightweight check that app is responsive (K8s livenessProbe)",
)
async def liveness_probe() -> LivenessResult:
    """
    Liveness probe endpoint for Kubernetes livenessProbe.

    This is a lightweight check that returns immediately if the app is responsive.
    Use this to detect deadlocked or hung processes.

    Returns:
        LivenessResult with status "alive"

    K8s Usage:
        livenessProbe:
          httpGet:
            path: /api/v1/health/live
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 10
    """
    return LivenessResult(status="alive")


@router.get(
    "/startup",
    status_code=status.HTTP_200_OK,
    summary="Startup Probe",
    description="Check if app has completed initialization (K8s startupProbe)",
)
async def startup_probe() -> StartupResult:
    """
    Startup probe endpoint for Kubernetes startupProbe.

    Checks that the app has completed initialization, including observability.
    This is used during container startup to determine when the app is ready
    to receive liveness and readiness probes.

    Returns:
        StartupResult with initialization status

    K8s Usage:
        startupProbe:
          httpGet:
            path: /api/v1/health/startup
            port: 8000
          failureThreshold: 30
          periodSeconds: 10
    """
    observability_ok, _ = validate_observability_initialized()

    return StartupResult(
        status="started" if observability_ok else "starting",
        observability=observability_ok,
    )


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness Probe",
    description="Check if all dependencies are healthy (K8s readinessProbe)",
)
async def readiness_probe() -> ReadinessResult:
    """
    Readiness probe endpoint for Kubernetes readinessProbe.

    Checks that all dependencies (database, cache, observability) are healthy.
    When not ready, K8s will remove the pod from service endpoints.

    Returns:
        ReadinessResult with dependency status

    K8s Usage:
        readinessProbe:
          httpGet:
            path: /api/v1/health/ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
    """
    # Check critical dependencies
    checks = {
        "observability": validate_observability_initialized()[0],
        "database": (await validate_database_connectivity_async())[0],
    }

    # All checks must pass for ready status
    all_ready = all(checks.values())

    return ReadinessResult(
        status="ready" if all_ready else "not_ready",
        checks=checks,
    )


@router.get(
    "/deps",
    status_code=status.HTTP_200_OK,
    summary="Dependency Status",
    description="Detailed dependency health status with latency metrics",
)
async def dependency_status() -> list[DependencyStatus]:
    """
    Detailed dependency status endpoint.

    Returns health status and latency for each dependency. This is useful
    for debugging and monitoring dependency performance.

    Returns:
        List of DependencyStatus with detailed info per dependency
    """
    import time

    dependencies = []

    # Check observability
    start = time.perf_counter()
    healthy, message = validate_observability_initialized()
    latency = (time.perf_counter() - start) * 1000
    dependencies.append(DependencyStatus(name="observability", healthy=healthy, message=message, latency_ms=round(latency, 2)))

    # Check database
    start = time.perf_counter()
    healthy, message = await validate_database_connectivity_async()
    latency = (time.perf_counter() - start) * 1000
    dependencies.append(DependencyStatus(name="database", healthy=healthy, message=message, latency_ms=round(latency, 2)))

    # Check Qdrant (if configured)
    if settings.qdrant_url:
        start = time.perf_counter()
        healthy, message = await validate_qdrant_connectivity_async()
        latency = (time.perf_counter() - start) * 1000
        dependencies.append(DependencyStatus(name="qdrant", healthy=healthy, message=message, latency_ms=round(latency, 2)))

    # Check LGTM stack (if configured)
    if settings.loki_url:
        start = time.perf_counter()
        healthy, message = await validate_loki_connectivity_async()
        latency = (time.perf_counter() - start) * 1000
        dependencies.append(DependencyStatus(name="loki", healthy=healthy, message=message, latency_ms=round(latency, 2)))

    if settings.tempo_url:
        start = time.perf_counter()
        healthy, message = await validate_tempo_connectivity_async()
        latency = (time.perf_counter() - start) * 1000
        dependencies.append(DependencyStatus(name="tempo", healthy=healthy, message=message, latency_ms=round(latency, 2)))

    if settings.mimir_url:
        start = time.perf_counter()
        healthy, message = await validate_mimir_connectivity_async()
        latency = (time.perf_counter() - start) * 1000
        dependencies.append(DependencyStatus(name="mimir", healthy=healthy, message=message, latency_ms=round(latency, 2)))

    return dependencies
