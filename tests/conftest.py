"""Pytest configuration and shared fixtures

This file contains ONLY:
1. pytest_plugins list (fixture loading)
2. pytest hooks (addoption, configure, collection_modifyitems, sessionfinish)
3. Autouse fixtures (must remain here per fixture organization rules)
4. Worker-safe ID helpers for pytest-xdist isolation
5. Fixtures that depend on the above (mock_current_user, in_memory_span_exporter)

All other fixtures have been extracted to plugins (Phase 5 reduction):
- tests/plugins/mcp_plugin.py: MCP fixtures
- tests/plugins/resilience_plugin.py: Circuit breaker fixtures
- tests/plugins/infrastructure_plugin.py: E2E infrastructure fixtures
- tests/plugins/mock_fixtures_plugin.py: General mock fixtures
- tests/plugins/container_plugin.py: DI container fixtures
"""

# Import fixture modules and enforcement plugin
# Must be defined before imports (pytest requirement)
pytest_plugins = [
    "tests.conftest_fixtures_plugin",
    "tests.fixtures.litellm_patch",
    "tests.fixtures.docker_fixtures",
    "tests.fixtures.time_fixtures",
    "tests.fixtures.database_fixtures",
    "tests.fixtures.tool_fixtures",
    "tests.fixtures.common_fixtures",
    "tests.fixtures.isolation_fixtures",
    # Phase 4: Domain-specific plugins (P1.3 Test Fixture Optimization)
    "tests.plugins.auth_plugin",
    "tests.plugins.settings_plugin",
    "tests.plugins.agent_plugin",
    # Phase 5: Additional plugins (conftest.py reduction)
    "tests.plugins.mcp_plugin",
    "tests.plugins.resilience_plugin",
    "tests.plugins.infrastructure_plugin",
    "tests.plugins.mock_fixtures_plugin",
    "tests.plugins.container_plugin",
]

import logging
import os
import sys
import warnings

import pytest

from tests.constants import TEST_JWT_SECRET

# Guard optional dev dependencies
try:
    from hypothesis import Phase, settings

    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False
    settings = None
    Phase = None

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

# Set minimal test environment variables
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("JWT_SECRET_KEY", TEST_JWT_SECRET)
os.environ.setdefault("HIPAA_INTEGRITY_SECRET", "test-hipaa-secret-key-for-testing-only")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")

# Suppress gRPC logging noise in tests
warnings.filterwarnings("ignore", message=".*failed to connect to all addresses.*")
warnings.filterwarnings("ignore", message=".*Connection refused.*")
logging.getLogger("grpc").setLevel(logging.CRITICAL)
logging.getLogger("opentelemetry.exporter.otlp").setLevel(logging.CRITICAL)


# Configure Hypothesis profiles for property-based testing
if HYPOTHESIS_AVAILABLE:
    _phases_without_target = (Phase.explicit, Phase.reuse, Phase.generate, Phase.shrink)

    settings.register_profile(
        "ci",
        max_examples=100,
        deadline=None,
        print_blob=True,
        derandomize=True,
        phases=_phases_without_target,
    )

    settings.register_profile(
        "dev",
        max_examples=25,
        deadline=2000,
        print_blob=False,
        derandomize=False,
        phases=_phases_without_target,
    )

    settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))


# ==============================================================================
# Pytest Hooks
# ==============================================================================


def pytest_addoption(parser):
    """Add custom pytest CLI options."""
    parser.addoption(
        "--run-benchmarks",
        action="store_true",
        default=False,
        help="Run benchmark tests (disabled by default for faster iteration)",
    )


def pytest_configure(config):
    """Configure pytest behavior based on command-line options."""
    config._run_benchmarks = config.getoption("--run-benchmarks")

    # Memory-aware worker tuning for pytest-xdist
    if hasattr(config.option, "numprocesses") and config.option.numprocesses == "auto":
        try:
            import psutil

            available_gb = psutil.virtual_memory().available / (1024**3)
            max_workers_by_memory = int(available_gb / 2)
            cpu_count = os.cpu_count() or 4
            max_workers = min(max_workers_by_memory, cpu_count)

            # Hard cap at 15 workers (Redis DB index limit)
            MAX_WORKERS_REDIS = 15
            if max_workers > MAX_WORKERS_REDIS:
                logging.warning(
                    f"Worker count capped at {MAX_WORKERS_REDIS} (Redis DB index limit). "
                    f"Memory/CPU would allow {max_workers} workers."
                )
                max_workers = MAX_WORKERS_REDIS

            max_workers = max(1, max_workers)
            config.option.numprocesses = max_workers
        except ImportError:
            cpu_count = os.cpu_count() or 4
            config.option.numprocesses = cpu_count

    # JWT Secret Validation
    jwt_secret = os.environ.get("JWT_SECRET_KEY")
    if jwt_secret and jwt_secret != TEST_JWT_SECRET:
        logging.warning("JWT_SECRET_KEY mismatch: Integration tests may fail with authentication errors.")


def pytest_collection_modifyitems(config, items):
    """Modify test collection to skip benchmarks by default and handle CLI tool requirements."""
    import shutil

    run_benchmarks = getattr(config, "_run_benchmarks", False)
    benchmark_only = config.getoption("--benchmark-only", default=False)
    markexpr = config.getoption("-m", default="")

    if not (run_benchmarks or benchmark_only or "benchmark" in markexpr):
        skip_benchmark = pytest.mark.skip(reason="Benchmark tests skipped by default. Use --run-benchmarks to enable.")
        for item in items:
            if "benchmark" in item.keywords:
                item.add_marker(skip_benchmark)

    # Auto-skip tests requiring CLI tools that aren't installed
    cli_tools = {
        "requires_kubectl": ("kubectl", "kubectl not installed"),
        "requires_helm": ("helm", "helm not installed"),
        "requires_kustomize": ("kustomize", "kustomize not installed"),
    }

    for item in items:
        for marker_name, (tool_name, skip_reason) in cli_tools.items():
            if marker_name in item.keywords:
                if not shutil.which(tool_name):
                    item.add_marker(pytest.mark.skip(reason=skip_reason))


# ==============================================================================
# Autouse Fixtures (MUST remain in conftest.py)
# ==============================================================================


@pytest.fixture(scope="session", autouse=True)
def init_test_observability():
    """Initialize observability system for all tests (session-scoped).

    IMPORTANT (xdist safety): We do NOT call shutdown_observability() at session
    end because it destroys the TracerProvider/MeterProvider, making ALL module-level
    OTEL instruments (counters, histograms, etc.) stale. Under pytest-xdist, this
    causes cascading failures in subsequent tests on the same worker that use those
    instruments. The Python process exits anyway at session end, so cleanup is
    unnecessary.
    """
    import os

    from mcp_server_langgraph.core.config import Settings
    from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized

    os.environ.setdefault("OPENFGA_STORE_ID", "test-store-id")
    os.environ.setdefault("OPENFGA_MODEL_ID", "test-model-id")
    os.environ.setdefault("GOOGLE_API_KEY", "test-google-api-key")

    if not is_initialized():
        test_settings = Settings(
            log_format="text",
            enable_file_logging=False,
            langsmith_tracing=False,
            observability_backend="opentelemetry",
        )
        init_observability(settings=test_settings, enable_file_logging=False)

    return
    # No shutdown_observability() — see docstring above


@pytest.fixture(autouse=True)
def ensure_observability_initialized(request):
    """Ensure observability is re-initialized if shut down by previous test.

    Skip for tests marked with @pytest.mark.skip_observability_init to allow
    isolated testing of OTEL components like SessionPropagatingSpanProcessor.
    """
    # Allow tests to skip this fixture for isolated OTEL component testing
    if request.node.get_closest_marker("skip_observability_init"):
        yield
        return

    from mcp_server_langgraph.core.config import Settings
    from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized

    if not is_initialized():
        test_settings = Settings(
            log_format="text",
            enable_file_logging=False,
            langsmith_tracing=False,
            observability_backend="opentelemetry",
        )
        init_observability(settings=test_settings, enable_file_logging=False)

    yield

    if not is_initialized():
        test_settings = Settings(
            log_format="text",
            enable_file_logging=False,
            langsmith_tracing=False,
            observability_backend="opentelemetry",
        )
        init_observability(settings=test_settings, enable_file_logging=False)


@pytest.fixture(autouse=True)
def reset_dependency_singletons():
    """Reset all dependency singletons before AND after each test for complete isolation."""
    # BEFORE test: Reset to clean up pollution from previous tests
    _reset_all_singletons()

    yield

    # AFTER test: Reset all dependency singletons
    _reset_all_singletons()


def _reset_all_singletons() -> None:
    """Reset all module-level singletons for complete test isolation.

    Covers: core.dependencies, auth.middleware, compliance.gdpr,
    database.session, resilience.circuit_breaker, skills.auto_update.
    """
    try:
        if "mcp_server_langgraph.core.dependencies" in sys.modules:
            import mcp_server_langgraph.core.dependencies as deps

            deps._keycloak_client = None
            deps._openfga_client = None
            deps._api_key_manager = None
            deps._service_principal_manager = None
            deps._user_provider = None
            deps._token_denylist = None
            deps._semantic_index_manager = None
    except Exception:
        pass

    try:
        if "mcp_server_langgraph.auth.middleware" in sys.modules:
            import mcp_server_langgraph.auth.middleware as middleware

            middleware._global_auth_middleware = None
    except Exception:
        pass

    try:
        if "mcp_server_langgraph.compliance.gdpr.factory" in sys.modules:
            import mcp_server_langgraph.compliance.gdpr.factory as gdpr_factory

            gdpr_factory._gdpr_storage = None
    except Exception:
        pass

    try:
        if "mcp_server_langgraph.database.session" in sys.modules:
            import mcp_server_langgraph.database.session as session_module

            session_module._engine = None
            session_module._async_session_maker = None
    except Exception:
        pass

    # Circuit breakers: reset all to CLOSED state (prevents cross-test trip contamination)
    try:
        if "mcp_server_langgraph.resilience.circuit_breaker" in sys.modules:
            from mcp_server_langgraph.resilience.circuit_breaker import reset_all_circuit_breakers

            reset_all_circuit_breakers()
    except Exception:
        pass

    # Skills auto-update scheduler singleton
    try:
        if "mcp_server_langgraph.skills.auto_update" in sys.modules:
            from mcp_server_langgraph.skills.auto_update import reset_auto_update_scheduler

            reset_auto_update_scheduler()
    except Exception:
        pass

    # WebSocket config singletons (streaming enabled flag, max chunk size)
    try:
        if "mcp_server_langgraph.mcp.websocket.config" in sys.modules:
            import mcp_server_langgraph.mcp.websocket.config as ws_config

            ws_config._streaming_enabled = True  # Default value
            ws_config._streaming_max_chunk_size = None  # Default value
    except Exception:
        pass

    # WebSocket streaming metrics collector (clear accumulated stream data in-place)
    # Clear via both module paths to handle potential object identity divergence:
    # - streaming.py module-level variable (canonical)
    # - __init__.py cached import (used by endpoint)
    try:
        if "mcp_server_langgraph.mcp.websocket.streaming" in sys.modules:
            import mcp_server_langgraph.mcp.websocket.streaming as _ws_streaming

            _ws_streaming.streaming_metrics_collector._streams.clear()
    except Exception:
        pass
    try:
        if "mcp_server_langgraph.mcp.websocket" in sys.modules:
            import mcp_server_langgraph.mcp.websocket as _ws_pkg

            _ws_pkg.streaming_metrics_collector._streams.clear()
    except Exception:
        pass

    # Storage contextvar: reset user_id to prevent cross-test ownership leaks
    try:
        if "mcp_server_langgraph.storage.session.adapter" in sys.modules:
            from mcp_server_langgraph.storage.session.adapter import set_current_user_id

            set_current_user_id("")
    except Exception:
        pass

    # Observability service singleton: prevent cached ObservabilityServiceImpl
    # from leaking across tests (causes real Prometheus queries in mock tests)
    try:
        if "mcp_server_langgraph.api.v1.observability" in sys.modules:
            from mcp_server_langgraph.api.v1.observability import reset_observability_service

            reset_observability_service()
    except Exception:
        pass


# ==============================================================================
# Worker-Safe ID Helpers for pytest-xdist Isolation
# ==============================================================================

_isolation_helpers_used = set()


def get_user_id(suffix: str = "") -> str:
    """Generate worker-safe user ID for pytest-xdist parallel execution."""
    _isolation_helpers_used.add("get_user_id")
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    base_id = f"user:test_{worker_id}"
    return f"{base_id}_{suffix}" if suffix else base_id


def get_api_key_id(suffix: str = "") -> str:
    """Generate worker-safe API key ID for pytest-xdist parallel execution."""
    _isolation_helpers_used.add("get_api_key_id")
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    base_id = f"apikey_test_{worker_id}"
    return f"{base_id}_{suffix}" if suffix else base_id


def get_log_id(suffix: str = "") -> str:
    """Generate worker-safe log ID for pytest-xdist parallel execution."""
    _isolation_helpers_used.add("get_log_id")
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    base_id = f"test_{worker_id}"
    return f"{base_id}_{suffix}" if suffix else base_id


@pytest.fixture(autouse=True)
def enforce_worker_isolation(request):
    """Enforce usage of worker-safe ID helpers in integration tests."""
    _isolation_helpers_used.clear()

    yield

    if request.node.get_closest_marker("skip_isolation_check"):
        return

    if request.node.get_closest_marker("integration"):
        stateful_fixtures = [
            "db_session",
            "postgres_connection_real",
            "redis_client_real",
            "openfga_client_real",
            "keycloak_client",
            "test_fastapi_app",
        ]

        used_stateful = any(f in request.fixturenames for f in stateful_fixtures)

        if used_stateful:
            if not _isolation_helpers_used:
                pytest.fail(
                    f"Test {request.node.name} uses stateful fixtures "
                    f"({[f for f in stateful_fixtures if f in request.fixturenames]}) "
                    f"but didn't call any isolation helpers (get_user_id/get_api_key_id/get_thread_id). "
                    f"This can cause pytest-xdist collisions. "
                    f"Use the helper functions from tests/conftest.py or add "
                    f"@pytest.mark.skip_isolation_check to opt-out."
                )


# ==============================================================================
# Resilience Reset Helpers (used by autouse fixture)
# ==============================================================================


def _reset_circuit_breakers(reset_fn):
    """Helper to reset all known circuit breakers."""
    if not reset_fn:
        return
    known_services = ["llm", "openfga", "redis", "keycloak", "qdrant"]
    for service in known_services:
        try:
            reset_fn(service)
        except Exception:
            pass


def _reset_bulkheads(reset_fn):
    """Helper to reset all known bulkheads."""
    if not reset_fn:
        return
    known_bulkheads = ["default", "llm", "openfga", "redis"]
    for bulkhead_name in known_bulkheads:
        try:
            reset_fn(bulkhead_name)
        except Exception:
            pass


@pytest.fixture(autouse=True)
def reset_resilience_state(request):
    """Reset all resilience patterns between tests to prevent state pollution."""
    skip_reset_marker = request.node.get_closest_marker("skip_resilience_reset")
    if skip_reset_marker:
        yield
        return

    try:
        from mcp_server_langgraph.resilience.circuit_breaker import reset_circuit_breaker
    except ImportError:
        reset_circuit_breaker = None

    try:
        from mcp_server_langgraph.resilience.bulkhead import reset_bulkhead
    except ImportError:
        reset_bulkhead = None

    _reset_circuit_breakers(reset_circuit_breaker)
    _reset_bulkheads(reset_bulkhead)

    yield

    _reset_circuit_breakers(reset_circuit_breaker)
    _reset_bulkheads(reset_bulkhead)


# ==============================================================================
# Fixtures that depend on conftest.py helpers
# ==============================================================================


@pytest.fixture
def mock_current_user():
    """
    Shared mock current user fixture for API endpoint tests.

    Contains all fields expected by get_current_user dependency:
    - sub: User ID (OpenID Connect standard claim)
    - user_id: Alias for sub (for compatibility)
    - username: User's preferred username
    - email: User's email address
    - roles: List of roles
    - realm_access: Keycloak realm roles structure

    Usage in tests:
        def test_endpoint(mock_current_user):
            app.dependency_overrides[get_current_user] = lambda: mock_current_user
    """
    user_id = get_user_id("alice")
    return {
        "sub": user_id,
        "user_id": user_id,
        "keycloak_id": "8c7b4e5d-1234-5678-abcd-ef1234567890",
        "username": "alice",
        "email": "alice@example.com",
        "roles": ["developer"],
        "realm_access": {"roles": ["developer"]},
    }


@pytest.fixture
def mock_admin_user():
    """
    Shared mock admin user fixture for API endpoint tests.

    Contains all fields expected by get_current_user dependency with admin role.

    Usage in tests:
        def test_admin_endpoint(mock_admin_user):
            app.dependency_overrides[get_current_user] = lambda: mock_admin_user
    """
    user_id = get_user_id("admin")
    return {
        "sub": user_id,
        "user_id": user_id,
        "keycloak_id": "admin-1234-5678-abcd-ef1234567890",
        "username": "admin",
        "email": "admin@example.com",
        "roles": ["admin", "developer"],
        "realm_access": {"roles": ["admin", "developer"]},
    }


@pytest.fixture
def mock_bob_user():
    """
    Shared mock standard user (bob) fixture for API endpoint tests.

    Bob is a standard user with limited permissions.

    Usage in tests:
        def test_user_endpoint(mock_bob_user):
            app.dependency_overrides[get_current_user] = lambda: mock_bob_user
    """
    user_id = get_user_id("bob")
    return {
        "sub": user_id,
        "user_id": user_id,
        "keycloak_id": "bob-1234-5678-abcd-ef1234567890",  # gitleaks:allow
        "username": "bob",
        "email": "bob@example.com",
        "roles": ["user"],
        "realm_access": {"roles": ["user"]},
    }


@pytest.fixture
def in_memory_span_exporter():
    """Create in-memory span exporter for testing traces."""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    yield exporter

    exporter.clear()


# ==============================================================================
# Mock Factory Fixtures
# ==============================================================================


@pytest.fixture
def configured_async_mock():  # type: ignore[no-untyped-def]
    """
    Factory fixture for creating properly configured AsyncMock instances.

    Returns a factory function that creates AsyncMock objects with
    configurable return values, side effects, and specs.

    Usage:
        def test_something(configured_async_mock):
            # Mock with return value
            mock_service = configured_async_mock(return_value={"status": "ok"})
            result = await mock_service()
            assert result == {"status": "ok"}

            # Mock with side effect
            mock_error = configured_async_mock(side_effect=ValueError("test error"))
            with pytest.raises(ValueError):
                await mock_error()

            # Mock with spec
            from mymodule import MyService
            mock_typed = configured_async_mock(spec=MyService, return_value=True)
            result = await mock_typed.some_method()
            assert result is True

    Best Practices:
        - Always specify `spec` parameter to ensure type safety
        - Use `return_value` for simple return values
        - Use `side_effect` for exceptions or sequential returns
        - See tests/ASYNC_MOCK_GUIDELINES.md for complete guidelines
        - Remember to add `teardown_method() + gc.collect()` for xdist safety

    Args:
        return_value: Value to return when the mock is called (optional)
        side_effect: Exception to raise or sequence of return values (optional)
        spec: Class/object to spec the mock against (optional but recommended)

    Returns:
        Configured AsyncMock instance
    """
    from unittest.mock import AsyncMock

    def _factory(return_value=None, side_effect=None, spec=None):  # type: ignore[no-untyped-def]
        mock = AsyncMock(spec=spec)
        if return_value is not None:
            mock.return_value = return_value
        if side_effect is not None:
            mock.side_effect = side_effect
        return mock

    return _factory


@pytest.fixture
def configured_mock():  # type: ignore[no-untyped-def]
    """
    Factory fixture for creating properly configured MagicMock instances.

    Returns a factory function that creates MagicMock objects with
    configurable return values, side effects, and specs.

    Usage:
        def test_something(configured_mock):
            # Mock with return value
            mock_service = configured_mock(return_value={"status": "ok"})
            result = mock_service()
            assert result == {"status": "ok"}

            # Mock with side effect
            mock_error = configured_mock(side_effect=ValueError("test error"))
            with pytest.raises(ValueError):
                mock_error()

            # Mock with spec
            from mymodule import MyService
            mock_typed = configured_mock(spec=MyService, return_value=True)
            result = mock_typed.some_method()
            assert result is True

    Best Practices:
        - Always specify `spec` parameter to ensure type safety
        - Use `return_value` for simple return values
        - Use `side_effect` for exceptions or sequential returns
        - See tests/ASYNC_MOCK_GUIDELINES.md for complete guidelines
        - Remember to add `teardown_method() + gc.collect()` for xdist safety

    Args:
        return_value: Value to return when the mock is called (optional)
        side_effect: Exception to raise or sequence of return values (optional)
        spec: Class/object to spec the mock against (optional but recommended)

    Returns:
        Configured MagicMock instance
    """
    from unittest.mock import MagicMock

    def _factory(return_value=None, side_effect=None, spec=None):  # type: ignore[no-untyped-def]
        mock = MagicMock(spec=spec)
        if return_value is not None:
            mock.return_value = return_value
        if side_effect is not None:
            mock.side_effect = side_effect
        return mock

    return _factory


@pytest.fixture(scope="session")
def test_infrastructure_ports():
    """
    Centralized source of truth for test infrastructure port mappings.

    All test ports use offsets from standard ports to avoid conflicts with local development:
    - postgres: 9432 (+4000 from 5432)
    - redis: 9379 (+3000 from 6379) - consolidated for both checkpoints and sessions
    - openfga: 9080 (+1000 from 8080), grpc: 9081
    - qdrant: 9333 (+3000 from 6333), grpc: 9334
    - keycloak: 9082, management: 9900

    See tests/constants.py for the authoritative port definitions.

    All xdist workers connect to the SAME ports - isolation is achieved via
    PostgreSQL schemas, Redis DBs, and namespace prefixes, NOT port offsets.

    **Scope**: Session-scoped to be consistent with test_infrastructure and openfga_client_real
    fixtures that depend on these ports. Using function scope here would cause ScopeMismatch.
    """
    from tests.constants import (
        TEST_POSTGRES_PORT,
        TEST_REDIS_PORT,
        TEST_OPENFGA_HTTP_PORT,
        TEST_OPENFGA_GRPC_PORT,
        TEST_QDRANT_PORT,
        TEST_KEYCLOAK_PORT,
    )

    return {
        "postgres": TEST_POSTGRES_PORT,
        "redis_checkpoints": TEST_REDIS_PORT,
        "redis_sessions": TEST_REDIS_PORT,  # Consolidated - same as checkpoints
        "qdrant": TEST_QDRANT_PORT,
        "qdrant_grpc": TEST_QDRANT_PORT + 1,  # gRPC is port + 1
        "openfga_http": TEST_OPENFGA_HTTP_PORT,
        "openfga_grpc": TEST_OPENFGA_GRPC_PORT,
        "keycloak": TEST_KEYCLOAK_PORT,
        "keycloak_management": 9900,  # Management port
    }


# ==============================================================================
# LiteLLM Async Client Cleanup (pytest hook)
# ==============================================================================


def pytest_sessionfinish(session, exitstatus):
    """Ensure litellm's async HTTP clients are properly closed at session end."""
    if hasattr(session.config.option, "help") and session.config.option.help:
        return
    if hasattr(session.config.option, "version") and session.config.option.version:
        return
    if hasattr(session.config.option, "markers") and session.config.option.markers:
        return
    if hasattr(session.config.option, "showfixtures") and session.config.option.showfixtures:
        return

    try:
        import asyncio

        import litellm

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(asyncio.wait_for(litellm.close_litellm_async_clients(), timeout=30.0))
            logging.debug("Successfully closed all litellm async clients")
        except TimeoutError:
            logging.warning("litellm async client cleanup timed out after 30s (non-critical)")
        finally:
            loop.close()

        if hasattr(litellm, "in_memory_llm_clients_cache"):
            cache = litellm.in_memory_llm_clients_cache
            if hasattr(cache, "cache_dict"):
                cache.cache_dict.clear()

    except ImportError:
        pass
    except AttributeError:
        logging.debug("litellm async client cleanup not available (older version)")
    except Exception as e:
        logging.debug(f"litellm async client cleanup failed (non-critical): {e}")


# ==============================================================================
# Service Client Registry Reset Fixtures (targeted, NOT autouse)
# ==============================================================================


@pytest.fixture(scope="function")
def reset_engine_registry():
    """
    Reset database engine registry for tests that need isolation.

    USAGE: Only request this fixture in tests that specifically need
    clean engine state. Not autouse to avoid breaking tests that rely
    on long-lived engines.

    Example:
        def test_engine_creation(reset_engine_registry):
            # Test starts with empty registry
            engine = get_engine("postgresql://...")
    """
    from mcp_server_langgraph.database import session as session_module

    # Clear before test
    session_module._engines.clear()
    session_module._session_makers.clear()
    yield
    # Cleanup after test
    session_module._engines.clear()
    session_module._session_makers.clear()


@pytest.fixture(scope="function")
def reset_qdrant_client():
    """
    Reset Qdrant client for tests that need isolation.

    USAGE: Only request this fixture in tests that specifically need
    a fresh Qdrant client. Not autouse to avoid breaking tests that
    rely on persistent client state.

    Example:
        def test_qdrant_singleton(reset_qdrant_client):
            # Test starts with no cached client
            client = get_shared_qdrant_client()
    """
    from mcp_server_langgraph.storage.vectors.factory import close_qdrant_client

    close_qdrant_client()
    yield
    close_qdrant_client()
