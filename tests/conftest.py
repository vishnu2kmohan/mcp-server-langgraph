"""Pytest configuration and shared fixtures"""

# Import fixture modules and enforcement plugin
# Must be defined before imports (pytest requirement)
#
# Phase 3: conftest.py Modularization (Testing Strategy Remediation)
# Extracted non-autouse fixtures into separate modules for improved maintainability:
# - docker_fixtures: Docker Compose lifecycle, port waiting, schema verification
# - time_fixtures: Time freezing for deterministic tests
#
# Note: Autouse fixtures (observability, singleton reset) must remain in conftest.py
# per fixture organization enforcement rules (see tests/meta/test_fixture_organization.py)
pytest_plugins = [
    "tests.conftest_fixtures_plugin",
    "tests.fixtures.litellm_patch",
    "tests.fixtures.docker_fixtures",
    "tests.fixtures.time_fixtures",
    "tests.fixtures.database_fixtures",
    "tests.fixtures.tool_fixtures",
    "tests.fixtures.common_fixtures",
    "tests.fixtures.isolation_fixtures",
]

import asyncio  # noqa: E402, F401  # used in cleanup_asyncio_clients fixture (line ~1540)
import logging  # noqa: E402
import os  # noqa: E402
import sys  # noqa: E402
import warnings  # noqa: E402
from datetime import datetime, timedelta, UTC  # noqa: E402
from pathlib import Path  # noqa: E402
from unittest.mock import AsyncMock, MagicMock, patch  # noqa: E402

import pytest  # noqa: E402

from tests.constants import TEST_JWT_SECRET  # noqa: E402

# Guard optional dev dependencies - may not be installed in all environments
try:
    from freezegun import freeze_time  # noqa: E402

    FREEZEGUN_AVAILABLE = True
except ImportError:
    FREEZEGUN_AVAILABLE = False
    freeze_time = None  # Define as None for type checking

try:
    from hypothesis import Phase, settings  # noqa: E402

    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False
    settings = None  # Define as None for type checking
    Phase = None  # Define as None for type checking

from langchain_core.messages import HumanMessage  # noqa: E402
from opentelemetry import trace  # noqa: E402
from opentelemetry.sdk.trace import TracerProvider  # noqa: E402
from opentelemetry.sdk.trace.export import SimpleSpanProcessor  # noqa: E402
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter  # noqa: E402

# Set minimal test environment variables
# With container pattern, we no longer need to set all these before imports!
# The container handles test mode configuration automatically.
# We only set critical ones that can't be overridden:
os.environ.setdefault("ENVIRONMENT", "test")  # Trigger test mode
os.environ.setdefault("JWT_SECRET_KEY", TEST_JWT_SECRET)  # Use centralized test constant
os.environ.setdefault("HIPAA_INTEGRITY_SECRET", "test-hipaa-secret-key-for-testing-only")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")  # Disable OpenTelemetry SDK

# Suppress gRPC logging noise in tests
warnings.filterwarnings("ignore", message=".*failed to connect to all addresses.*")
warnings.filterwarnings("ignore", message=".*Connection refused.*")

# Also suppress grpc library logs
logging.getLogger("grpc").setLevel(logging.CRITICAL)
logging.getLogger("opentelemetry.exporter.otlp").setLevel(logging.CRITICAL)


# Configure Hypothesis profiles for property-based testing
# Only configure if Hypothesis is available to prevent AttributeError
if HYPOTHESIS_AVAILABLE:
    # WORKAROUND: Exclude Phase.target to avoid pytest-xdist import race condition
    # hypothesis.internal.conjecture.optimiser is lazily imported in optimise_targets(),
    # but on Python 3.11/3.13 with xdist workers, this import fails with ModuleNotFoundError.
    # Phase.target is for target optimization, which is nice-to-have but not essential.
    # See: https://github.com/HypothesisWorks/hypothesis/issues/3987 (similar issue)
    _phases_without_target = (Phase.explicit, Phase.reuse, Phase.generate, Phase.shrink)

    # Register CI profile with comprehensive testing (100 examples)
    settings.register_profile(
        "ci",
        max_examples=100,
        deadline=None,  # No deadline in CI for comprehensive testing
        print_blob=True,  # Print failing examples for debugging
        derandomize=True,  # Deterministic test execution in CI
        phases=_phases_without_target,  # Exclude target phase to avoid xdist import race
    )

    # Register dev profile for fast iteration (25 examples)
    settings.register_profile(
        "dev",
        max_examples=25,
        deadline=2000,  # 2 second deadline for fast feedback
        print_blob=False,  # No blob printing in dev for clean output
        derandomize=False,  # Randomized for better coverage
        phases=_phases_without_target,  # Exclude target phase to avoid xdist import race
    )

    # Load appropriate profile based on environment
    # CI sets HYPOTHESIS_PROFILE=ci, defaults to dev otherwise
    settings.load_profile(os.getenv("HYPOTHESIS_PROFILE", "dev"))


# ==============================================================================
# Pytest Hooks for Custom Behavior (CODEX Finding #4)
# ==============================================================================


def pytest_addoption(parser):
    """
    Add custom pytest CLI options.

    CODEX FINDING #4: Add --run-benchmarks flag to opt-in to benchmark execution.
    By default, benchmarks are skipped for faster test iteration.
    """
    parser.addoption(
        "--run-benchmarks",
        action="store_true",
        default=False,
        help="Run benchmark tests (disabled by default for faster iteration)",
    )


def pytest_configure(config):
    """
    Configure pytest behavior based on command-line options.

    CODEX FINDING #4: Skip benchmarks by default unless explicitly requested.
    """
    # Store benchmark flag in config for use in pytest_collection_modifyitems
    config._run_benchmarks = config.getoption("--run-benchmarks")

    # Enhancement #3: Memory-Aware Worker Tuning
    # Auto-tune pytest-xdist workers based on available RAM to prevent OOM
    # Codex Finding #6 Fix (2025-11-23): Hard cap at 15 workers (Redis DB index limit)
    if hasattr(config.option, "numprocesses") and config.option.numprocesses == "auto":
        try:
            import psutil

            # Get available memory in GB
            available_gb = psutil.virtual_memory().available / (1024**3)

            # Allocate 2GB per worker as safety margin
            # (empirical data: our tests use ~1-2GB RES per worker with memory protections)
            max_workers_by_memory = int(available_gb / 2)

            # Don't exceed CPU count (diminishing returns beyond CPU count)
            cpu_count = os.cpu_count() or 4
            max_workers = min(max_workers_by_memory, cpu_count)

            # Hard cap at 15 workers (Redis DB index limit: 1-15)
            # Redis has 16 databases by default (0-15), DB 0 reserved for non-xdist
            # See: tests/fixtures/database_fixtures.py:296-314 for DB index allocation
            MAX_WORKERS_REDIS = 15
            if max_workers > MAX_WORKERS_REDIS:
                logging.warning(
                    f"Worker count capped at {MAX_WORKERS_REDIS} (Redis DB index limit). "
                    f"Memory/CPU would allow {max_workers} workers. "
                    f"See tests/fixtures/database_fixtures.py:296-314 for DB index allocation."
                )
                max_workers = MAX_WORKERS_REDIS

            # Ensure at least 1 worker
            max_workers = max(1, max_workers)

            config.option.numprocesses = max_workers

            logging.info(
                f"Memory-aware worker tuning: {available_gb:.1f}GB available → "
                f"{max_workers} workers (CPU: {cpu_count}, Memory limit: {max_workers_by_memory}, "
                f"Redis limit: {MAX_WORKERS_REDIS})"
            )
        except ImportError:
            # psutil not available - fallback to CPU count
            cpu_count = os.cpu_count() or 4
            config.option.numprocesses = cpu_count
            logging.info(f"psutil not available - using CPU count: {cpu_count} workers")

    # JWT Secret Validation - Pre-validate before integration tests run
    # OpenAI Codex Finding (2025-11-16): Integration tests failed due to JWT secret mismatch
    # Validate JWT_SECRET_KEY is set correctly before tests run to fail fast with clear error
    jwt_secret = os.environ.get("JWT_SECRET_KEY")
    if jwt_secret and jwt_secret != TEST_JWT_SECRET:
        logging.warning(
            f"JWT_SECRET_KEY environment variable ('{jwt_secret}') does not match "
            f"TEST_JWT_SECRET constant ('{TEST_JWT_SECRET}'). "
            f"Integration tests may fail with authentication errors. "
            f"Update JWT_SECRET_KEY or tests/constants.py to match."
        )


def pytest_collection_modifyitems(config, items):
    """
    Modify test collection to skip benchmarks by default and handle CLI tool requirements.

    CODEX FINDING #4: Benchmarks run by default, slowing everyday test runs.
    Solution: Skip benchmarks unless:
    - --run-benchmarks flag is passed
    - -m benchmark is used (explicit marker selection)
    - --benchmark-only is used (pytest-benchmark flag)

    Also auto-skips tests requiring CLI tools that aren't installed.
    """
    import shutil

    run_benchmarks = getattr(config, "_run_benchmarks", False)
    benchmark_only = config.getoption("--benchmark-only", default=False)
    markexpr = config.getoption("-m", default="")

    # If user explicitly requests benchmarks, don't skip
    if not (run_benchmarks or benchmark_only or "benchmark" in markexpr):
        # Skip all tests marked with @pytest.mark.benchmark
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
# Observability Initialization (Session-Scoped Autouse Fixture)
# ==============================================================================


@pytest.fixture(scope="session", autouse=True)
def init_test_observability():
    """
    Initialize observability system for all tests (session-scoped).

    This fixture runs automatically before all tests and initializes the
    observability/telemetry system with test-appropriate settings.

    Configuration:
    - Text logging (no JSON in tests)
    - No file logging (console only)
    - LangSmith tracing disabled
    - OpenTelemetry backend for tracing
    - Default test environment variables to suppress warnings

    Session scope ensures observability is initialized exactly once per test run,
    avoiding duplicate initialization and improving test performance.

    Consolidates 25+ duplicate module-scoped fixtures from individual test files.
    See: tests/test_fixture_organization.py for validation

    IMPORTANT: Properly shuts down OpenTelemetry exporters and processors after
    test session to prevent thread leaks and memory bloat.
    """
    import os

    from mcp_server_langgraph.core.config import Settings
    from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized, shutdown_observability

    # Set default test environment variables to suppress warnings
    # These are only set if not already defined (allowing tests to override)
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

    yield

    # Teardown: Shutdown OpenTelemetry exporters and processors
    # Prevents thread leaks (OtelPeriodicExportingMetricReader, OtelBatchSpanRecordProcessor)
    # and memory bloat during test execution
    shutdown_observability()


@pytest.fixture(autouse=True)
def ensure_observability_initialized():
    """
    Ensure observability is re-initialized if shut down by previous test.

    Some tests (test_observability_cleanup.py, test_app_factory.py) call
    shutdown_observability() which sets _observability_config = None.
    This causes subsequent tests to fail with "Observability not initialized".

    This function-scoped autouse fixture re-initializes observability before
    each test if needed, preventing state pollution between tests.
    """
    from mcp_server_langgraph.core.config import Settings
    from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized

    # Before test: Re-initialize if shutdown by previous test
    if not is_initialized():
        test_settings = Settings(
            log_format="text",
            enable_file_logging=False,
            langsmith_tracing=False,
            observability_backend="opentelemetry",
        )
        init_observability(settings=test_settings, enable_file_logging=False)

    yield

    # After test: Check if this test shut down observability
    # If so, re-initialize for next test (defensive)
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
    """
    Reset all dependency singletons before AND after each test for complete isolation.

    Tests that modify singletons (_keycloak_client, _openfga_client, _api_key_manager,
    _service_principal_manager, _global_auth_middleware) can cause state pollution
    affecting subsequent tests.

    This fixture ensures clean singleton state by resetting all to None before each test
    (to clean up pollution from previous tests) and after each test (to clean up the
    current test's changes).

    See: tests/regression/test_auth_middleware_isolation.py
    """
    # BEFORE test: Reset to clean up pollution from previous tests
    try:
        # Only import if already loaded (don't pollute import cache for lazy import tests)
        if "mcp_server_langgraph.core.dependencies" in sys.modules:
            import mcp_server_langgraph.core.dependencies as deps

            deps._keycloak_client = None
            deps._openfga_client = None
            deps._api_key_manager = None
            deps._service_principal_manager = None
    except Exception:
        # If module not loaded or reset fails, continue (defensive)
        pass

    # Reset global auth middleware singleton (only if already loaded)
    try:
        # Only import if already loaded (don't pollute import cache for lazy import tests)
        if "mcp_server_langgraph.auth.middleware" in sys.modules:
            import mcp_server_langgraph.auth.middleware as middleware

            middleware._global_auth_middleware = None
    except Exception:
        # If module not loaded or reset fails, continue (defensive)
        pass

    # Reset GDPR storage singleton (only if already loaded)
    try:
        # Only import if already loaded (don't pollute import cache for lazy import tests)
        if "mcp_server_langgraph.compliance.gdpr.factory" in sys.modules:
            import mcp_server_langgraph.compliance.gdpr.factory as gdpr_factory

            gdpr_factory._gdpr_storage = None
    except Exception:
        # If module not loaded or reset fails, continue (defensive)
        pass

    yield

    # AFTER test: Reset all dependency singletons to ensure clean state for next test
    try:
        # Only import if already loaded (don't pollute import cache for lazy import tests)
        if "mcp_server_langgraph.core.dependencies" in sys.modules:
            import mcp_server_langgraph.core.dependencies as deps

            deps._keycloak_client = None
            deps._openfga_client = None
            deps._api_key_manager = None
            deps._service_principal_manager = None
    except Exception:
        # If module not loaded or reset fails, continue (defensive)
        pass

    # Reset global auth middleware singleton (only if already loaded)
    try:
        # Only import if already loaded (don't pollute import cache for lazy import tests)
        if "mcp_server_langgraph.auth.middleware" in sys.modules:
            import mcp_server_langgraph.auth.middleware as middleware

            middleware._global_auth_middleware = None
    except Exception:
        # If module not loaded or reset fails, continue (defensive)
        pass

    # Reset GDPR storage singleton (only if already loaded)
    try:
        # Only import if already loaded (don't pollute import cache for lazy import tests)
        if "mcp_server_langgraph.compliance.gdpr.factory" in sys.modules:
            import mcp_server_langgraph.compliance.gdpr.factory as gdpr_factory

            gdpr_factory._gdpr_storage = None
    except Exception:
        # If module not loaded or reset fails, continue (defensive)
        pass


# ==============================================================================
# Worker-Safe ID Helpers for pytest-xdist Isolation
# ==============================================================================

# Track usage of worker-safe helpers to enforce isolation
_isolation_helpers_used = set()


def get_user_id(suffix: str = "") -> str:
    """
    Generate worker-safe user ID for pytest-xdist parallel execution.

    This helper prevents ID pollution when running tests in parallel with pytest-xdist.
    Each xdist worker gets a unique ID namespace, preventing state contamination across workers.

    **Why This Exists:**
    Hardcoded IDs like "user:alice" cause state pollution in pytest-xdist because multiple
    workers share the same infrastructure (PostgreSQL, Redis, OpenFGA). When worker gw0
    creates a relationship for "user:alice" and worker gw1 also uses "user:alice", they
    interfere with each other, causing flaky test failures.

    **Worker Isolation Strategy:**
    - Worker gw0: user:test_gw0
    - Worker gw1: user:test_gw1
    - Worker gw2: user:test_gw2
    - Non-xdist: user:test_gw0 (default)

    Args:
        suffix: Optional suffix for test-specific ID differentiation
                (e.g., get_user_id("admin") → "user:test_gw0_admin")

    Returns:
        Worker-isolated user ID in OpenFGA format (e.g., "user:test_gw0")

    Usage:
        def test_authorization(self):
            user_id = get_user_id()  # ✅ Worker-safe
            # NOT: user_id = "user:alice"  # ❌ Hardcoded - causes pollution

    References:
        - tests/meta/test_id_pollution_prevention.py (validates this pattern)
        - scripts/validate_test_ids.py (pre-commit enforcement)
        - Pre-commit hook: validate-test-ids
    """
    _isolation_helpers_used.add("get_user_id")
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    base_id = f"user:test_{worker_id}"
    return f"{base_id}_{suffix}" if suffix else base_id


def get_api_key_id(suffix: str = "") -> str:
    """
    Generate worker-safe API key ID for pytest-xdist parallel execution.

    This helper prevents ID pollution when running tests in parallel with pytest-xdist.
    Each xdist worker gets a unique ID namespace, preventing state contamination across workers.

    **Why This Exists:**
    Hardcoded API key IDs like "apikey_test123" cause state pollution in pytest-xdist
    because multiple workers share the same Keycloak instance. When worker gw0 creates
    an API key "apikey_test123" and worker gw1 also uses "apikey_test123", they interfere
    with each other, causing flaky test failures.

    **Worker Isolation Strategy:**
    - Worker gw0: apikey_test_gw0
    - Worker gw1: apikey_test_gw1
    - Worker gw2: apikey_test_gw2
    - Non-xdist: apikey_test_gw0 (default)

    Args:
        suffix: Optional suffix for test-specific ID differentiation
                (e.g., get_api_key_id("admin") → "apikey_test_gw0_admin")

    Returns:
        Worker-isolated API key ID (e.g., "apikey_test_gw0")

    Usage:
        def test_api_key_creation(self):
            apikey_id = get_api_key_id()  # ✅ Worker-safe
            # NOT: apikey_id = "apikey_test123"  # ❌ Hardcoded - causes pollution

    References:
        - tests/meta/test_id_pollution_prevention.py (validates this pattern)
        - scripts/validate_test_ids.py (pre-commit enforcement)
        - Pre-commit hook: validate-test-ids
    """
    _isolation_helpers_used.add("get_api_key_id")
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    base_id = f"apikey_test_{worker_id}"
    return f"{base_id}_{suffix}" if suffix else base_id


@pytest.fixture(autouse=True)
def enforce_worker_isolation(request):
    """
    Enforce usage of worker-safe ID helpers in integration tests.

    This fixture ensures that any integration test that interacts with stateful
    services (DB, OpenFGA, etc.) uses the worker-safe ID helpers to prevent
    collisions during parallel execution.
    """
    # Reset tracker before test
    _isolation_helpers_used.clear()

    yield

    # Check enforcement after test
    # Only applies to tests marked as integration
    # Skip if test has skip_isolation_check marker
    if request.node.get_closest_marker("skip_isolation_check"):
        return

    if request.node.get_closest_marker("integration"):
        # List of fixtures that imply stateful interactions
        stateful_fixtures = [
            "db_session",
            "postgres_connection_real",
            "redis_client_real",
            "openfga_client_real",
            "keycloak_client",
            "test_fastapi_app",  # Implies full stack
        ]

        # Check if test used any stateful fixtures
        used_stateful = any(f in request.fixturenames for f in stateful_fixtures)

        if used_stateful:
            # Check if helpers were used
            if not _isolation_helpers_used:
                # STRICT ENFORCEMENT (2025-11-30):
                # Fail immediately if stateful fixtures are used without calling
                # the isolation helpers (get_user_id/get_api_key_id/get_thread_id).
                # This prevents hardcoded IDs that cause pytest-xdist collisions.
                pytest.fail(
                    f"Test {request.node.name} uses stateful fixtures "
                    f"({[f for f in stateful_fixtures if f in request.fixturenames]}) "
                    f"but didn't call any isolation helpers (get_user_id/get_api_key_id/get_thread_id). "
                    f"This can cause pytest-xdist collisions. "
                    f"Use the helper functions from tests/conftest.py or add "
                    f"@pytest.mark.skip_isolation_check to opt-out."
                )


# ==============================================================================
# Fixed Time Fixture for Deterministic Tests
# ==============================================================================


@pytest.fixture
def frozen_time():
    """
    Freeze time for deterministic timestamp testing.

    All datetime.now(), time.time(), etc. calls will return the fixed time.
    This eliminates test flakiness caused by time-dependent assertions.

    Usage:
        @pytest.mark.usefixtures("frozen_time")
        def test_timestamps():
            # datetime.now() will always return 2024-01-01T00:00:00Z
            assert datetime.now(timezone.utc).isoformat() == "2024-01-01T00:00:00+00:00"
    """
    if not FREEZEGUN_AVAILABLE:
        pytest.skip("freezegun not installed - required for time-freezing tests. Install with: pip install freezegun")

    with freeze_time("2024-01-01 00:00:00", tz_offset=0):
        yield


# ==============================================================================
# Mock App Settings Fixture (DRY pattern for app.settings mocking)
# ==============================================================================


@pytest.fixture
def mock_app_settings():
    """
    Complete mock for app settings with all required attributes.

    Use this fixture when patching mcp_server_langgraph.app.settings
    to ensure auth factory validation passes. The auth factory validates
    settings.auth_provider.lower() against ["inmemory", "keycloak"].

    This fixture provides all attributes that create_app() requires:
    - auth_provider: For UserProvider factory validation
    - jwt_secret_key: For JWT token signing/verification
    - environment: For environment-specific behavior
    - use_password_hashing: For auth mode configuration
    - cors_allowed_origins: For CORS middleware setup
    - get_cors_origins(): Method for CORS configuration

    Usage:
        def test_cors_config(self, mock_app_settings):
            mock_app_settings.cors_allowed_origins = ["http://localhost:3000"]
            mock_app_settings.get_cors_origins = MagicMock(
                return_value=["http://localhost:3000"]
            )
            with patch("mcp_server_langgraph.app.settings", mock_app_settings):
                app = create_app()
                assert isinstance(app, FastAPI)
    """
    mock = MagicMock()
    # Required for auth factory validation (see auth/factory.py:43-110)
    mock.auth_provider = "inmemory"
    mock.jwt_secret_key = "test-jwt-secret-key-for-testing"
    mock.environment = "development"
    mock.use_password_hashing = False
    # CORS settings
    mock.cors_allowed_origins = []
    mock.get_cors_origins = MagicMock(return_value=[])
    return mock


# ==============================================================================
# Repository Path Fixtures (DRY - prevents path resolution bugs)
# ==============================================================================


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Get the repository root directory.

    Use this fixture instead of manual Path(__file__).parents[N] navigation
    to prevent path resolution bugs in tests. The conftest.py is always in
    tests/, so parent.parent gets us to the repo root.

    Returns:
        Path to repository root directory
    """
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def deployments_dir(repo_root: Path) -> Path:
    """Get the deployments directory.

    Args:
        repo_root: Repository root path (injected by pytest)

    Returns:
        Path to deployments/ directory
    """
    return repo_root / "deployments"


# ==============================================================================
# E2E FastAPI App Fixtures
# ==============================================================================


@pytest.fixture(scope="session")
def test_infrastructure_ports():
    """
    Return fixed infrastructure service ports for ALL pytest-xdist workers.

    Single Shared Infrastructure Architecture:
    =========================================
    - ONE docker-compose instance runs on FIXED base ports (9432, 9379, etc.)
    - ALL xdist workers (gw0, gw1, gw2, ...) connect to the SAME ports
    - Isolation is achieved via logical separation, NOT port offsets:
      * PostgreSQL: Separate schemas per worker (test_worker_gw0, test_worker_gw1)
      * Redis: Separate DB indices per worker (DB 1, 2, 3, ...)
      * OpenFGA: Separate stores per worker (test_store_gw0, test_store_gw1)
      * Qdrant: Separate collections per worker
      * Keycloak: Separate realms per worker

    This is faster and simpler than per-worker infrastructure with dynamic port allocation.

    Port Mappings (from docker-compose.test.yml):
    ==============================================
    - postgres: 9432 -> 5432 (container port)
    - redis_checkpoints: 9379 -> 6379 (consolidated Redis instance)
    - redis_sessions: 9379 -> 6379 (consolidated Redis instance, same as checkpoints)
    - qdrant: 9333 -> 6333
    - qdrant_grpc: 9334 -> 6334
    - openfga_http: 9080 -> 8080
    - openfga_grpc: 9081 -> 8081
    - keycloak: 9082 -> 8080
    - keycloak_management: 9900 -> 9000

    Architecture Difference - Test vs Production:
    =============================================
    **Production (docker-compose.yml + Kubernetes):**
    - Separate redis (6379) and redis-sessions (6380) services
    - Better resource isolation and independent scaling

    **Test (docker-compose.test.yml):**
    - Single redis-test service on port 9379 (consolidated)
    - Both redis_checkpoints and redis_sessions point to same port
    - Logical isolation via DB indices:
      * DB 0: Sessions
      * DB 1: Checkpoints/conversation state
      * DB 2+: Worker-specific DBs

    **Why consolidate for tests?**
    - Faster startup (one Redis vs two)
    - Simpler infrastructure management
    - Lower memory footprint for CI runners
    - DB index isolation sufficient for test isolation

    Returns:
        Dict[str, int]: Fixed port mappings for all infrastructure services

    Related:
        - docker-compose.test.yml (test infrastructure with consolidated Redis)
        - docker/docker-compose.yml (production topology with separate Redis instances)
        - tests/meta/test_infrastructure_singleton.py (validates this architecture)
        - tests/utils/worker_utils.py (provides worker-specific identifiers)
    """
    return {
        "postgres": 9432,
        "redis_checkpoints": 9379,
        "redis_sessions": 9379,  # Same port as checkpoints (consolidated in test)
        "qdrant": 9333,
        "qdrant_grpc": 9334,
        "openfga_http": 9080,
        "openfga_grpc": 9081,
        "keycloak": 9082,
        "keycloak_management": 9900,
    }


@pytest.fixture
def test_app_settings(test_infrastructure_ports):
    """
    Create test settings configured to use test infrastructure services.

    Returns Settings object pointing to test ports (offset by 1000).
    """
    from mcp_server_langgraph.core.config import Settings

    return Settings(
        environment="test",
        service_name="test-mcp-server",
        # Database settings - use gdpr_postgres_url (individual postgres_* fields removed)
        gdpr_postgres_url=f"postgresql://postgres:postgres@localhost:{test_infrastructure_ports['postgres']}/gdpr",
        # Redis settings (use same port for both sessions and checkpoints in tests)
        redis_host="localhost",
        redis_port=test_infrastructure_ports["redis_checkpoints"],
        # Redis URLs are constructed from host/port
        redis_url=f"redis://localhost:{test_infrastructure_ports['redis_sessions']}/0",
        checkpoint_redis_url=f"redis://localhost:{test_infrastructure_ports['redis_checkpoints']}/1",
        # OpenFGA settings
        openfga_api_url=f"http://localhost:{test_infrastructure_ports['openfga_http']}",
        openfga_store_id=None,  # Will be created dynamically in tests
        openfga_model_id=None,
        # Keycloak settings
        keycloak_server_url=f"http://localhost:{test_infrastructure_ports['keycloak']}",
        keycloak_realm="default",  # Use default realm for tests
        keycloak_client_id="admin-cli",
        keycloak_admin_username="admin",
        keycloak_admin_password="admin",
        # Qdrant settings
        qdrant_url="localhost",
        qdrant_port=test_infrastructure_ports["qdrant"],
        # Security settings
        jwt_secret_key="test-jwt-secret-key-for-e2e-testing-only",
        hipaa_integrity_secret="test-hipaa-secret-for-e2e-testing-only",
        # Test-specific settings
        log_level="DEBUG",
        log_format="text",
        enable_file_logging=False,
        langsmith_tracing=False,
        observability_backend="opentelemetry",
    )


@pytest.fixture
async def test_fastapi_app(test_infrastructure, test_app_settings):
    """
    Create FastAPI app instance configured for E2E testing.

    This fixture:
    1. Waits for test infrastructure to be ready
    2. Creates app with test settings
    3. Yields app for testing
    4. Cleans up after tests

    Usage:
        @pytest.mark.e2e
        async def test_api_endpoint(test_fastapi_app):
            from fastapi.testclient import TestClient
            client = TestClient(test_fastapi_app)
            response = client.get("/health")
            assert response.status_code == 200
    """
    # Ensure infrastructure is ready
    assert test_infrastructure["ready"], "Test infrastructure not ready"

    # Override settings with test configuration
    with patch("mcp_server_langgraph.core.config.settings", test_app_settings):
        # Import and create app with patched settings
        # Use server_streamable app to match production transport
        from mcp_server_langgraph.mcp.server_streamable import app

        yield app

        # Cleanup: No explicit cleanup needed as infrastructure handles it


@pytest.fixture
def test_client(test_fastapi_app):
    """
    Create FastAPI TestClient for synchronous E2E testing.

    Usage:
        @pytest.mark.e2e
        def test_endpoint(test_client):
            response = test_client.get("/api/v1/health")
            assert response.status_code == 200
    """
    from fastapi.testclient import TestClient

    return TestClient(test_fastapi_app)


@pytest.fixture
async def test_async_client(test_fastapi_app):
    """
    Create httpx AsyncClient for asynchronous E2E testing.

    Usage:
        @pytest.mark.e2e
        async def test_async_endpoint(test_async_client):
            response = await test_async_client.get("/api/v1/health")
            assert response.status_code == 200
    """
    import httpx
    from httpx import ASGITransport

    # Create transport with the app
    transport = ASGITransport(app=test_fastapi_app)

    async with httpx.AsyncClient(transport=transport, base_url="http://test", follow_redirects=True) as client:
        yield client


# Container-based test fixtures (NEW APPROACH)
# These replace the old global initialization pattern


@pytest.fixture(scope="session")
def test_container():
    """
    Create test container for the session.

    This container:
    - Uses no-op telemetry (no output)
    - Uses no-op auth (accepts any token)
    - Uses in-memory storage
    - Has NO global side effects

    Replaces: pytest_configure(), init_observability_for_workers()
    """
    from mcp_server_langgraph.core.container import create_test_container

    container = create_test_container()
    return container
    # No cleanup needed - container has no global state


@pytest.fixture
def container(test_container):
    """
    Per-test container fixture.

    Use this when you need a fresh container for each test.
    For most tests, use test_container (session-scoped) instead.
    """
    from mcp_server_langgraph.core.container import create_test_container

    return create_test_container()


# ==============================================================================
# Shared Authentication Fixtures
# ==============================================================================


@pytest.fixture
def mock_current_user():
    """
    Shared mock current user fixture for API endpoint tests.

    Provides a consistent user identity with both OpenFGA and Keycloak formats:
    - user_id: OpenFGA format with worker-safe ID for pytest-xdist isolation
    - keycloak_id: Keycloak UUID format
    - username: Plain username
    - email: User email

    Worker-safe IDs prevent test data pollution across pytest-xdist workers.
    Each worker (gw0, gw1, etc.) gets isolated user IDs.
    """
    return {
        "user_id": get_user_id("alice"),  # Worker-safe OpenFGA format
        "keycloak_id": "8c7b4e5d-1234-5678-abcd-ef1234567890",  # Keycloak UUID
        "username": "alice",
        "email": "alice@example.com",
    }


# Mock MCP server initialization at session level to prevent event loop issues
@pytest.fixture(scope="session")
def mock_mcp_modules():
    """Mock MCP server modules to prevent async initialization at import time"""
    # Create mock MCP SDK Server
    mock_mcp_sdk_server = MagicMock()
    mock_tool_manager = MagicMock()
    mock_resource_manager = MagicMock()

    # Mock the managers
    type(mock_mcp_sdk_server)._tool_manager = property(lambda self: mock_tool_manager)
    type(mock_mcp_sdk_server)._resource_manager = property(lambda self: mock_resource_manager)

    # Create mock server instance
    mock_server_instance = MagicMock()
    mock_server_instance.server = mock_mcp_sdk_server
    mock_server_instance.auth = MagicMock()

    # Patch the class before any imports
    with patch("mcp_server_langgraph.mcp.server_streamable.MCPAgentStreamableServer", return_value=mock_server_instance):
        # Return dict with all mocks for test access
        yield {
            "server_instance": mock_server_instance,
            "tool_manager": mock_tool_manager,
            "resource_manager": mock_resource_manager,
        }


@pytest.fixture(scope="session")
def mock_settings(test_container):
    """
    Mock settings for testing (session-scoped for performance).

    Now uses container.settings instead of creating settings directly.
    This ensures consistency with the container pattern.
    """
    # You can still create custom settings for specific tests
    from mcp_server_langgraph.core.config import Settings

    return Settings(
        environment="test",
        service_name="test-service",
        otlp_endpoint="http://localhost:4317",
        jwt_secret_key="test-secret-key",
        anthropic_api_key="test-anthropic-key",
        model_name="claude-sonnet-4-5-20250929",
        log_level="DEBUG",
        openfga_api_url="http://localhost:8080",
        openfga_store_id="test-store-id",
        openfga_model_id="test-model-id",
    )


@pytest.fixture(scope="session")
def mock_openfga_response():
    """Mock OpenFGA API responses (session-scoped for performance)"""
    return {
        "check": {"allowed": True},
        "list_objects": {"objects": ["tool:chat", "tool:search"]},
        "write": {"writes": []},
        "read": {"tuples": [{"key": {"user": "user:alice", "relation": "executor", "object": "tool:chat"}}]},
    }


@pytest.fixture(scope="session")
def integration_test_env(test_infrastructure):
    """
    Check if running in integration test environment (Docker).

    DEPRECATED: Use test_infrastructure fixture directly for new tests.
    This fixture is kept for backward compatibility with existing tests.

    The test_infrastructure fixture now automatically manages the full
    docker-compose lifecycle, so this fixture will always return True
    when test_infrastructure is active.

    Scope: session - Must match the scope of dependent fixtures
    (postgres_connection_real, redis_client_real, openfga_client_real)
    """
    return test_infrastructure["ready"]


# =============================================================================
# DATABASE FIXTURES - EXTRACTED TO tests/fixtures/database_fixtures.py
# =============================================================================
# Phase 1.1: Infrastructure Improvements (2025-11-22)
# Fixtures for PostgreSQL, Redis, OpenFGA, and Qdrant extracted to improve
# conftest.py maintainability (target: < 500 lines from 2,559 lines).
#
# All fixtures now loaded via pytest_plugins["tests.fixtures.database_fixtures"]
#
# Extracted fixtures:
# - postgres_connection_real: Session-scoped PostgreSQL connection pool
# - redis_client_real: Session-scoped Redis client
# - openfga_client_real: Session-scoped OpenFGA client with auto-initialization
# - postgres_connection_clean: Function-scoped Postgres with per-test cleanup
# - redis_client_clean: Function-scoped Redis with per-test cleanup
# - openfga_client_clean: Function-scoped OpenFGA with per-test cleanup
# - db_pool_gdpr: PostgreSQL pool with GDPR schema for security tests
# - qdrant_available: Check if Qdrant is available
# - qdrant_client: Qdrant client for vector search tests
#
# References:
# - CODEX_FINDINGS_VALIDATION_REPORT_2025-11-21.md: conftest.py bloat issue
# - tests/fixtures/database_fixtures.py: Extracted fixture module
# =============================================================================


@pytest.fixture(scope="session")
def mock_infisical_response():
    """Mock Infisical API responses (session-scoped for performance)"""
    return {
        "secrets": [
            {"secretKey": "JWT_SECRET_KEY", "secretValue": "test-jwt-secret", "version": 1},
            {"secretKey": "ANTHROPIC_API_KEY", "secretValue": "sk-ant-test-key", "version": 1},
        ]
    }


@pytest.fixture
def mock_jwt_token():
    """
    Generate a mock JWT token with current timestamps.

    Uses datetime.now(UTC) to ensure token is always valid during test execution.
    Expiration is set to TEST_JWT_EXPIRATION_HOURS (1 hour) from now.

    IMPORTANT: Uses TEST_JWT_SECRET from tests/constants.py to ensure
    token signing matches server verification in all test environments.

    OpenAI Codex Finding (2025-11-16):
    ====================================
    Previous implementation used FIXED_TIME=2024-01-01, causing "Token expired"
    errors in integration tests because the token was 2 years old.

    Fixed by using datetime.now(UTC) for current time instead of fixed timestamp.
    """
    import jwt

    from tests.constants import TEST_JWT_EXPIRATION_HOURS

    NOW = datetime.now(UTC)

    payload = {
        "sub": "alice",
        "exp": NOW + timedelta(hours=TEST_JWT_EXPIRATION_HOURS),
        "iat": NOW,
    }
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")


@pytest.fixture(scope="session")
def mock_user_alice():
    """Mock user alice (session-scoped for performance)"""
    return {"username": "alice", "tier": "premium", "organization": "acme", "roles": ["admin", "user"]}


@pytest.fixture(scope="session")
def mock_user_bob():
    """Mock user bob (session-scoped for performance)"""
    return {"username": "bob", "tier": "standard", "organization": "acme", "roles": ["user"]}


@pytest.fixture(scope="session")
def register_mcp_test_users():
    """
    Register test users for MCP integration tests (session-scoped).

    Creates InMemoryUserProvider with pre-registered test users that match
    JWT tokens created by mock_jwt_token fixture. This ensures authorization
    works in fallback mode.

    Returns:
        InMemoryUserProvider with "alice" user registered

    OpenAI Codex Finding (2025-11-16):
    ===================================
    MCP integration tests failed with "user not found" because:
    - mock_jwt_token creates JWT with sub="alice"
    - InMemoryUserProvider starts empty (security requirement: CWE-798 prevention)
    - Tests tried to add alice AFTER server creation, but timing/instance mismatch

    Solution: Session-scoped fixture registers alice BEFORE any MCP tests run,
    so all tests share the same provider instance with pre-registered users.

    Usage in tests:
        @pytest.fixture
        async def mcp_server(register_mcp_test_users):
            auth = AuthMiddleware(user_provider=register_mcp_test_users, ...)
            return MCPAgentServer(auth=auth)
    """
    from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider

    # Create provider with TEST_JWT_SECRET for token verification
    provider = InMemoryUserProvider(secret_key=TEST_JWT_SECRET)

    # Register "alice" user (matches mock_jwt_token fixture sub claim)
    provider.add_user(
        username="alice",
        password="test-password",
        email="alice@example.com",
        roles=["user", "admin"],
    )

    return provider


@pytest.fixture
def mock_agent_state():
    """Mock LangGraph agent state"""
    return {
        "messages": [HumanMessage(content="Hello, what can you do?")],
        "next_action": "respond",
        "user_id": "alice",
        "request_id": "test-request-123",
    }


@pytest.fixture
def in_memory_span_exporter():
    """Create in-memory span exporter for testing traces"""
    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    yield exporter

    # Clear spans after test
    exporter.clear()


@pytest.fixture
async def mock_httpx_client():
    """Mock httpx async client"""
    mock_client = AsyncMock()
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_response.raise_for_status = MagicMock()
    mock_client.post.return_value = mock_response
    mock_client.get.return_value = mock_response

    return mock_client


@pytest.fixture
def mock_anthropic_client():
    """Mock Anthropic API client"""
    mock_client = MagicMock()
    mock_message = MagicMock()
    mock_message.content = [MagicMock(text="I am Claude, an AI assistant.")]
    mock_message.stop_reason = "end_turn"

    mock_client.messages.create.return_value = mock_message

    return mock_client


@pytest.fixture(scope="session")
def mock_mcp_request():
    """Mock MCP JSON-RPC request (session-scoped for performance)"""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {"name": "chat", "arguments": {"message": "What is 2+2?", "username": "alice"}},
    }


@pytest.fixture(scope="session")
def mock_mcp_initialize_request():
    """Mock MCP initialize request (session-scoped for performance)"""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {"protocolVersion": "0.1.0", "clientInfo": {"name": "test-client", "version": "1.0.0"}},
    }


@pytest.fixture
async def mock_openfga_client(mock_openfga_response):
    """Mock OpenFGA client"""
    with patch("openfga_client.httpx.AsyncClient") as mock_client:
        mock_response = AsyncMock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_openfga_response["check"]
        mock_response.raise_for_status = MagicMock()

        mock_instance = AsyncMock()
        mock_instance.post.return_value = mock_response
        mock_instance.get.return_value = mock_response
        mock_client.return_value.__aenter__.return_value = mock_instance

        yield mock_client


@pytest.fixture
async def mock_infisical_client(mock_infisical_response):
    """Mock Infisical client"""
    # FIXED: Corrected patch path to match actual runtime module location
    # The runtime module is mcp_server_langgraph.secrets.manager, not secrets_manager
    with patch("mcp_server_langgraph.secrets.manager.InfisicalClient") as mock_client:
        mock_instance = MagicMock()
        mock_instance.get_secret.return_value = mock_infisical_response["secrets"][0]
        mock_instance.list_secrets.return_value = mock_infisical_response["secrets"]
        mock_client.return_value = mock_instance

        yield mock_client


@pytest.fixture(scope="session")
def sample_openfga_tuples():
    """Sample OpenFGA relationship tuples (session-scoped for performance)"""
    return [
        {"user": "user:alice", "relation": "executor", "object": "tool:chat"},
        {"user": "user:alice", "relation": "admin", "object": "organization:acme"},
        {"user": "user:bob", "relation": "member", "object": "organization:acme"},
        {"user": "organization:acme#member", "relation": "executor", "object": "tool:search"},
    ]


@pytest.fixture
def temp_checkpoint_dir(tmp_path):
    """Create temporary directory for checkpoints"""
    checkpoint_dir = tmp_path / "checkpoints"
    checkpoint_dir.mkdir()
    return str(checkpoint_dir)


# Async context manager helpers
@pytest.fixture(scope="session")
def async_context_manager():
    """Helper to create async context managers for mocking (session-scoped for performance)"""

    def _create(return_value):
        class AsyncContextManager:
            async def __aenter__(self):
                return return_value

            async def __aexit__(self, *args):
                pass

        return AsyncContextManager()

    return _create


def _reset_circuit_breakers(reset_fn):
    """Helper to reset all known circuit breakers."""
    if not reset_fn:
        return
    known_services = ["llm", "openfga", "redis", "keycloak", "qdrant"]
    for service in known_services:
        try:
            reset_fn(service)
        except Exception:
            pass  # Ignore errors if service not initialized


def _reset_bulkheads(reset_fn):
    """Helper to reset all known bulkheads."""
    if not reset_fn:
        return
    known_bulkheads = ["default", "llm", "openfga", "redis"]
    for bulkhead_name in known_bulkheads:
        try:
            reset_fn(bulkhead_name)
        except Exception:
            pass  # Ignore errors if bulkhead not initialized


@pytest.fixture
def test_circuit_breaker_config():
    """
    Configure circuit breaker with minimal timeout for testing.

    Use this fixture in tests that need fast circuit breaker recovery.
    By default, circuit breakers have 60s timeout which is too slow for tests.
    This fixture configures 1s timeout for faster test iteration.

    Usage:
        def test_my_feature(test_circuit_breaker_config):
            # Circuit breaker now has 1s timeout
            pass
    """
    from mcp_server_langgraph.resilience.circuit_breaker import _circuit_breakers
    from mcp_server_langgraph.resilience.config import CircuitBreakerConfig, ResilienceConfig, set_resilience_config

    # Set up test-friendly resilience config with very short timeout
    test_config = ResilienceConfig(
        enabled=True,
        circuit_breakers={
            "llm": CircuitBreakerConfig(
                name="llm",
                fail_max=5,
                timeout_duration=1,  # 1 second instead of 60 - allows quick recovery in tests
            ),
        },
    )
    set_resilience_config(test_config)

    # Clear any existing circuit breaker instances to force recreation with new config
    # This is critical for CI where state can pollute between sequential tests
    if "llm" in _circuit_breakers:
        del _circuit_breakers["llm"]

    return

    # Cleanup handled by reset_resilience_state autouse fixture


@pytest.fixture
def fast_resilience_config():
    """
    Configure all circuit breakers with minimal timeouts for fast testing.

    Use this fixture in tests that need fast circuit breaker recovery across all services.
    This is especially important for tests that intentionally trigger circuit breaker opens
    and need to verify fail-open/fail-closed behavior quickly.

    Reduces test time from 45s → <2s by using:
    - fail_max=3 (need only 3 failures to open, down from 5-10)
    - timeout_duration=1 (circuit recovers in 1 second, down from 30-60s)

    Usage:
        def test_circuit_breaker_behavior(fast_resilience_config):
            # All circuit breakers now have 1s timeout and fail_max=3
            pass
    """
    from mcp_server_langgraph.resilience.circuit_breaker import _circuit_breakers
    from mcp_server_langgraph.resilience.config import CircuitBreakerConfig, ResilienceConfig, set_resilience_config

    # Set up test-friendly resilience config with very short timeouts for all services
    test_config = ResilienceConfig(
        enabled=True,
        circuit_breakers={
            "llm": CircuitBreakerConfig(name="llm", fail_max=3, timeout_duration=1),
            "openfga": CircuitBreakerConfig(name="openfga", fail_max=3, timeout_duration=1),
            "redis": CircuitBreakerConfig(name="redis", fail_max=3, timeout_duration=1),
            "keycloak": CircuitBreakerConfig(name="keycloak", fail_max=3, timeout_duration=1),
            "prometheus": CircuitBreakerConfig(name="prometheus", fail_max=3, timeout_duration=1),
        },
    )
    set_resilience_config(test_config)

    # Clear any existing circuit breaker instances to force recreation with new config
    # This is critical for CI where state can pollute between sequential tests
    for service in ["llm", "openfga", "redis", "keycloak", "prometheus"]:
        if service in _circuit_breakers:
            del _circuit_breakers[service]

    return

    # Cleanup handled by reset_resilience_state autouse fixture


@pytest.fixture
def fast_retry_config():
    """
    Configure retry logic with minimal attempts for fast testing.

    Reduces test time dramatically by minimizing retry attempts:
    - max_attempts=1 (no retries, fail immediately)
    - exponential_base=1 (no exponential growth)
    - exponential_max=0.1 (100ms max delay)

    **Performance Impact:**
    - OpenFGA circuit breaker tests: 45s → <5s (90% reduction)
    - Any test with @retry_with_backoff decorator benefits

    **When to use:**
    - Tests that intentionally trigger failures (circuit breaker tests)
    - Tests that validate retry logic itself (use freezegun instead)
    - Any test where retries add unnecessary delay

    **Usage:**
    ```python
    @pytest.mark.asyncio
    async def test_circuit_breaker_behavior(fast_retry_config):
        # Test runs with no retries - fails immediately
        # Circuit breaker tests complete in <5s instead of 45s
        ...
    ```

    **Why this works:**
    The @retry_with_backoff decorator reads configuration from get_resilience_config().retry.
    By setting max_attempts=1, we eliminate retry overhead while still testing
    the core business logic.

    **Trade-offs:**
    - ✅ Dramatically faster tests (90% reduction for retry-heavy tests)
    - ✅ Still tests business logic (circuit breaker, error handling)
    - ❌ Doesn't test actual retry behavior (use separate retry-specific tests)
    - ❌ May need to adjust assertions for single-attempt behavior

    Related:
    - fast_resilience_config: Reduces circuit breaker timeout_duration
    - pytest --durations=50: Use in CI to detect slow tests
    """
    from mcp_server_langgraph.resilience.config import ResilienceConfig, RetryConfig, set_resilience_config

    # Get current config
    current_config = ResilienceConfig()

    # Create fast retry config
    fast_retry = RetryConfig(
        max_attempts=1,  # No retries - fail immediately
        exponential_base=1.0,  # No exponential growth
        exponential_max=0.1,  # 100ms max delay (minimal)
        jitter=False,  # No jitter for deterministic testing
    )

    # Combine with current config (preserve circuit breaker, timeout, bulkhead settings)
    test_config = ResilienceConfig(
        enabled=current_config.enabled,
        circuit_breakers=current_config.circuit_breakers,
        retry=fast_retry,  # Use fast retry config
        timeout=current_config.timeout,
        bulkhead=current_config.bulkhead,
    )

    set_resilience_config(test_config)
    return

    # Cleanup handled by reset_resilience_state autouse fixture


@pytest.fixture(autouse=True)
def reset_resilience_state(request):
    """
    Reset all resilience patterns between tests to prevent state pollution.

    This fixture automatically runs before each test to ensure:
    - Circuit breakers are closed
    - Bulkheads are cleared
    - Retry state is reset

    This prevents test failures caused by resilience state from previous tests.

    Tests can opt-out by using the @pytest.mark.skip_resilience_reset marker.
    This is useful for tests that intentionally manipulate resilience state.
    """
    # Check if test is marked to skip resilience reset
    skip_reset_marker = request.node.get_closest_marker("skip_resilience_reset")
    if skip_reset_marker:
        # Skip reset for this test - just yield without resetting
        yield
        return

    # Import resilience modules
    try:
        from mcp_server_langgraph.resilience.circuit_breaker import reset_circuit_breaker
    except ImportError:
        reset_circuit_breaker = None

    try:
        from mcp_server_langgraph.resilience.bulkhead import reset_bulkhead
    except ImportError:
        reset_bulkhead = None

    # Reset before test
    _reset_circuit_breakers(reset_circuit_breaker)
    _reset_bulkheads(reset_bulkhead)

    yield

    # Cleanup after test (helps with test isolation)
    _reset_circuit_breakers(reset_circuit_breaker)
    _reset_bulkheads(reset_bulkhead)


# ==============================================================================
# LiteLLM Async Client Cleanup (OpenAI Codex Finding)
# ==============================================================================


def pytest_sessionfinish(session, exitstatus):
    """
    Ensure litellm's async HTTP clients are properly closed at session end.

    **OpenAI Codex Finding (2025-11-17 - RESOLVED):**
    - RuntimeWarning: coroutine 'close_litellm_async_clients' was never awaited
    - Source: litellm/llms/custom_httpx/async_client_cleanup.py:78
    - Occurred during test teardown when event loop closes

    **Root Cause:**
    - litellm registers an atexit handler that calls loop.create_task() without awaiting
    - During pytest shutdown (especially with pytest-xdist workers), loop.is_running() returns True
    - Task is created but never awaited before loop closes
    - Python 3.12+ removed atexit._exithandlers, making handler unregistration difficult

    **Solution (2025-11-17):**
    - Monkey-patch atexit.register at import time (top of conftest.py) to intercept litellm's registration
    - Filter out litellm's cleanup_wrapper to prevent atexit handler from ever being registered
    - Run cleanup manually in pytest_sessionfinish (before atexit phase)
    - Clear litellm's in-memory cache to make any remaining handlers no-ops

    **Impact:**
    - BEFORE: 9 RuntimeWarnings per regression test run
    - AFTER: 0 RuntimeWarnings (confirmed with Python 3.12.12)

    **References:**
    - tests/regression/test_litellm_cleanup_warnings.py (all 4 tests passing)
    - https://github.com/BerriAI/litellm/issues (async client cleanup)
    - Monkey-patch implementation: lines 7-46 (top of this file)
    """
    # Skip cleanup for informational pytest commands that don't run tests
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

        # Strategy: Clear litellm's cache after cleanup to make atexit handler a no-op
        # This prevents RuntimeWarning when atexit runs and finds no clients to close
        # Run cleanup manually in a new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            loop.run_until_complete(asyncio.wait_for(litellm.close_litellm_async_clients(), timeout=30.0))
            logging.debug("Successfully closed all litellm async clients")
        except TimeoutError:
            logging.warning("litellm async client cleanup timed out after 30s (non-critical)")
        finally:
            loop.close()

        # Clear litellm's in-memory cache to prevent atexit handler from finding clients
        # This makes the atexit handler a no-op (it won't create any tasks)
        if hasattr(litellm, "in_memory_llm_clients_cache"):
            cache = litellm.in_memory_llm_clients_cache
            if hasattr(cache, "cache_dict"):
                cache.cache_dict.clear()
                logging.debug("Cleared litellm in-memory client cache")

    except ImportError:
        pass
    except AttributeError:
        logging.debug("litellm async client cleanup not available (older version)")
    except Exception as e:
        logging.debug(f"litellm async client cleanup failed (non-critical): {e}")
