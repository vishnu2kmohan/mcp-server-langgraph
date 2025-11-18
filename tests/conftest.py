"""Pytest configuration and shared fixtures"""

# Import fixture organization enforcement plugin
# Must be defined before imports (pytest requirement)
pytest_plugins = ["tests.conftest_fixtures_plugin"]

import atexit  # noqa: E402

# ==============================================================================
# LiteLLM Atexit Handler Prevention (OpenAI Codex Finding 2025-11-17)
# ==============================================================================
# CRITICAL: Must be done BEFORE any litellm imports
# Monkey-patch litellm's atexit registration to prevent RuntimeWarnings
import sys  # noqa: E402

# Store original atexit.register
_original_atexit_register = atexit.register
_litellm_handlers = []


def _filtered_atexit_register(func, *args, **kwargs):
    """
    Intercept atexit.register calls and block litellm's cleanup_wrapper.

    This prevents litellm from registering an atexit handler that causes
    RuntimeWarning: coroutine 'close_litellm_async_clients' was never awaited
    """
    # Check if this is litellm's cleanup_wrapper
    if hasattr(func, "__name__") and func.__name__ == "cleanup_wrapper":
        # Check if it's from litellm module
        if hasattr(func, "__module__") and func.__module__ and "litellm" in func.__module__:
            # Store reference but don't register it
            _litellm_handlers.append((func, args, kwargs))
            return func  # Return func to maintain compatibility
        # Also check via closure variables (litellm uses nested functions)
        if hasattr(func, "__code__"):
            code_consts = str(func.__code__.co_consts)
            if "close_litellm_async_clients" in code_consts or "litellm" in code_consts:
                _litellm_handlers.append((func, args, kwargs))
                return func
    # For all other functions, use original atexit.register
    return _original_atexit_register(func, *args, **kwargs)


# Replace atexit.register before any litellm imports
atexit.register = _filtered_atexit_register

import asyncio  # noqa: E402
import logging  # noqa: E402
import os  # noqa: E402
import socket  # noqa: E402
import time  # noqa: E402
import warnings  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402
from typing import AsyncGenerator, Generator  # noqa: E402
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
    from hypothesis import settings  # noqa: E402

    HYPOTHESIS_AVAILABLE = True
except ImportError:
    HYPOTHESIS_AVAILABLE = False
    settings = None  # Define as None for type checking

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

# Suppress litellm async cleanup warning (OpenAI Codex Finding 2025-11-15)
# Root cause: litellm's atexit handler calls loop.create_task() without awaiting
# Our pytest_sessionfinish hook already handles cleanup properly
# This must be set at import time to catch warnings during atexit phase
warnings.filterwarnings("ignore", category=RuntimeWarning, module="litellm.llms.custom_httpx.async_client_cleanup")

# Also suppress grpc library logs
logging.getLogger("grpc").setLevel(logging.CRITICAL)
logging.getLogger("opentelemetry.exporter.otlp").setLevel(logging.CRITICAL)


# Configure Hypothesis profiles for property-based testing
# Only configure if Hypothesis is available to prevent AttributeError
if HYPOTHESIS_AVAILABLE:
    # Register CI profile with comprehensive testing (100 examples)
    settings.register_profile(
        "ci",
        max_examples=100,
        deadline=None,  # No deadline in CI for comprehensive testing
        print_blob=True,  # Print failing examples for debugging
        derandomize=True,  # Deterministic test execution in CI
    )

    # Register dev profile for fast iteration (25 examples)
    settings.register_profile(
        "dev",
        max_examples=25,
        deadline=2000,  # 2 second deadline for fast feedback
        print_blob=False,  # No blob printing in dev for clean output
        derandomize=False,  # Randomized for better coverage
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

            # Ensure at least 1 worker
            max_workers = max(1, max_workers)

            config.option.numprocesses = max_workers

            logging.info(
                f"Memory-aware worker tuning: {available_gb:.1f}GB available → "
                f"{max_workers} workers (CPU: {cpu_count}, Memory limit: {max_workers_by_memory})"
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

    Session scope ensures observability is initialized exactly once per test run,
    avoiding duplicate initialization and improving test performance.

    Consolidates 25+ duplicate module-scoped fixtures from individual test files.
    See: tests/test_fixture_organization.py for validation

    IMPORTANT: Properly shuts down OpenTelemetry exporters and processors after
    test session to prevent thread leaks and memory bloat.
    """
    from mcp_server_langgraph.core.config import Settings
    from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized, shutdown_observability

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
    Reset all dependency singletons after each test for complete isolation.

    Tests that modify singletons (_keycloak_client, _openfga_client, _api_key_manager,
    _service_principal_manager, _global_auth_middleware) can cause state pollution
    affecting subsequent tests.

    This fixture ensures clean singleton state by resetting all to None after each test.
    The next test that needs these dependencies will create fresh instances.

    See: tests/regression/test_auth_middleware_isolation.py
    """
    yield

    import sys

    # Reset all dependency singletons to ensure clean state for next test
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


# ==============================================================================
# Worker-Safe ID Helpers for pytest-xdist Isolation
# ==============================================================================


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
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    base_id = f"apikey_test_{worker_id}"
    return f"{base_id}_{suffix}" if suffix else base_id


# ==============================================================================
# Docker Infrastructure Fixtures (Automated Lifecycle Management)
# ==============================================================================


def _wait_for_port(host: str, port: int, timeout: float = 30.0) -> bool:
    """
    Wait for a TCP port to become available.

    Returns True if port is available, False if timeout is reached.
    """
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return True
        except socket.error:
            pass
        time.sleep(0.5)
    return False


def _check_http_health(url: str, timeout: float = 2.0) -> bool:
    """Check if HTTP endpoint is healthy."""
    try:
        import httpx

        response = httpx.get(url, timeout=timeout)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture(scope="session")
def docker_compose_file():
    """
    Provide path to root docker-compose.test.yml for pytest-docker-compose-v2.

    Uses root docker-compose.test.yml for local/CI parity (OpenAI Codex Finding #1).

    This enables automated docker-compose lifecycle management:
    - Services start automatically before test session
    - Services stop automatically after test session
    - No manual docker-compose commands needed
    """
    from pathlib import Path

    return str(Path(__file__).parent.parent / "docker-compose.test.yml")


@pytest.fixture(scope="session")
def docker_services_available(docker_compose_file):
    """
    Check if Docker is available and docker-compose.test.yml exists.

    This is a lightweight check that runs before attempting to start services.
    """
    # Check if docker-compose file exists
    if not os.path.exists(docker_compose_file):
        pytest.skip(f"Docker compose file not found: {docker_compose_file}")

    # Check if Docker is available
    try:
        import subprocess

        result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
        if result.returncode != 0:
            pytest.skip("Docker daemon not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("Docker not installed or not responding")

    return True


# ==============================================================================
# CLI Tool Availability Fixtures (OpenAI Codex Finding #1)
# ==============================================================================


@pytest.fixture(scope="session")
def kustomize_available():
    """
    Check if kustomize CLI tool is available.

    Returns:
        bool: True if kustomize is installed and accessible, False otherwise

    Usage:
        @pytest.mark.skipif(not kustomize_available(), reason="kustomize not installed")
        def test_kustomize_build():
            ...
    """
    import shutil

    return shutil.which("kustomize") is not None


@pytest.fixture(scope="session")
def kubectl_available():
    """
    Check if kubectl CLI tool is available.

    Returns:
        bool: True if kubectl is installed and accessible, False otherwise

    Usage:
        @pytest.mark.skipif(not kubectl_available(), reason="kubectl not installed")
        def test_kubectl_apply():
            ...
    """
    import shutil

    return shutil.which("kubectl") is not None


@pytest.fixture(scope="session")
def helm_available():
    """
    Check if helm CLI tool is available.

    Returns:
        bool: True if helm is installed and accessible, False otherwise

    Usage:
        @pytest.mark.skipif(not helm_available(), reason="helm not installed")
        def test_helm_template():
            ...
    """
    import shutil

    return shutil.which("helm") is not None


@pytest.fixture(scope="session")
def terraform_available():
    """
    Check if terraform CLI tool is available.

    Returns:
        bool: True if terraform is installed and accessible, False otherwise

    Usage:
        def test_terraform_plan(terraform_available):
            if not terraform_available:
                pytest.skip("terraform not installed")
            # Test logic here
    """
    import shutil

    return shutil.which("terraform") is not None


@pytest.fixture(scope="session")
def project_root():
    """
    Find project root directory in any environment (local, Docker, CI).

    Searches for project markers (.git, pyproject.toml) starting from the test
    file location and walking up the directory tree. This ensures tests work
    correctly regardless of:
    - Working directory
    - Docker vs local environment
    - pytest vs direct execution

    Returns:
        Path: Absolute path to project root

    Usage:
        def test_something(project_root):
            overlays_dir = project_root / "deployments" / "overlays"
            assert overlays_dir.exists()

    Raises:
        RuntimeError: If project root cannot be found

    References:
        - tests/regression/test_pod_deployment_regression.py (uses this pattern)
        - tests/test_mdx_validation.py (uses this pattern)
        - tests/unit/documentation/ (uses this pattern)
    """
    from pathlib import Path

    # Start from this file's location and walk up
    current = Path(__file__).resolve().parent

    # Markers that identify the project root
    markers = [".git", "pyproject.toml", "setup.py"]

    while current != current.parent:
        if any((current / marker).exists() for marker in markers):
            return current
        current = current.parent

    raise RuntimeError("Cannot find project root - no .git or pyproject.toml found")


@pytest.fixture(scope="session")
def docker_compose_available():
    """
    Check if docker compose CLI tool is available and functional.

    Returns:
        bool: True if docker compose is available and working

    Usage:
        def test_docker_compose_up(docker_compose_available):
            if not docker_compose_available:
                pytest.skip("docker compose not available")
            # Test logic here

    Raises:
        pytest.skip: If docker compose is not available or not working
    """
    import subprocess

    try:
        result = subprocess.run(
            ["docker", "compose", "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            pytest.skip("docker compose not available")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pytest.skip("docker compose not available")

    return True


def requires_tool(tool_name, skip_reason=None):
    """
    Decorator to skip tests if a required CLI tool is not available.

    This decorator checks for tool availability at test runtime using shutil.which(),
    and skips the test with a clear message if the tool is not found.

    Args:
        tool_name: Name of the CLI tool to check (e.g., "kustomize", "kubectl")
        skip_reason: Optional custom skip message. If None, uses default message.

    Returns:
        Decorator function that wraps the test function

    Usage:
        @requires_tool("kustomize")
        def test_kustomize_build():
            # Test will be skipped if kustomize is not installed
            result = subprocess.run(["kustomize", "build", "."])
            assert result.returncode == 0

        @requires_tool("terraform", skip_reason="Terraform 1.5+ required for this test")
        def test_terraform_plan():
            # Test will be skipped with custom message if terraform not found
            pass

    Example:
        This decorator is preferred over @pytest.mark.skipif because:
        1. It checks at runtime (not collection time)
        2. It provides clearer error messages
        3. It doesn't require calling fixtures directly
    """
    import functools
    import shutil

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not shutil.which(tool_name):
                reason = skip_reason or f"{tool_name} not installed"
                pytest.skip(reason)
            return func(*args, **kwargs)

        return wrapper

    return decorator


@pytest.fixture
def settings_isolation(monkeypatch):
    """
    Fixture that provides automatic settings isolation and restoration.

    This fixture allows tests to modify the global settings object without
    affecting other tests. All changes are automatically reverted after the test.

    Uses pytest's monkeypatch fixture internally for automatic cleanup.

    Usage:
        def test_checkpoint_backend(settings_isolation, monkeypatch):
            # Import settings
            from mcp_server_langgraph.core.config import settings

            # Modify settings using monkeypatch
            monkeypatch.setattr(settings, "checkpoint_backend", "redis")
            monkeypatch.setattr(settings, "enable_checkpointing", True)

            # Test logic here - settings are modified
            assert settings.checkpoint_backend == "redis"

            # After test completes, settings are automatically restored

    Note:
        This fixture doesn't do the isolation itself - it returns the monkeypatch
        fixture to make it clear that tests should use monkeypatch for isolation.
        The fixture name serves as documentation and ensures consistent usage.

    Returns:
        The monkeypatch fixture for use in the test
    """
    return monkeypatch


@pytest.fixture(scope="session")
def test_infrastructure_ports():
    """
    Define test infrastructure ports (offset by 1000 from production).

    **Single Shared Infrastructure (Session-Scoped)**:
    All pytest-xdist workers connect to the SAME infrastructure instance on FIXED ports.
    This provides a single docker-compose stack shared across all workers, with logical
    isolation via PostgreSQL schemas, Redis DB indices, OpenFGA stores, etc.

    Port Allocation:
    - All workers use base ports: postgres=9432, redis=9379, openfga=9080, etc.
    - Ports are FIXED (no worker-based offsets)
    - Maps directly to docker-compose.test.yml port bindings

    Logical Isolation Strategy:
    - PostgreSQL: Separate schemas per worker (test_worker_gw0, test_worker_gw1, ...)
    - Redis: Separate DB indices per worker (1, 2, 3, ...)
    - OpenFGA: Separate stores per worker (test_store_gw0, test_store_gw1, ...)
    - Qdrant: Separate collections per worker
    - Keycloak: Separate realms per worker

    This is faster and simpler than per-worker infrastructure with dynamic port allocation,
    avoiding "address already in use" errors through logical isolation instead of port offsets.

    References:
    - tests/meta/test_infrastructure_singleton.py (validates this architecture)
    - tests/regression/test_pytest_xdist_port_conflicts.py
    - OpenAI Codex Finding: conftest.py:583 port conflicts (RESOLVED)
    - ADR: Single shared test infrastructure with logical isolation
    """
    # Return FIXED base ports for all workers
    # All xdist workers (gw0, gw1, gw2, ...) connect to the same ports
    # Isolation is achieved via schemas, DB indices, stores, not port offsets
    return {
        "postgres": 9432,
        "redis_checkpoints": 9379,
        "redis_sessions": 9380,
        "qdrant": 9333,
        "qdrant_grpc": 9334,
        "openfga_http": 9080,
        "openfga_grpc": 9081,
        "keycloak": 9082,
    }


# ══════════════════════════════════════════════════════════════════════════════
# Environment Isolation Fixtures
# ══════════════════════════════════════════════════════════════════════════════


@pytest.fixture
def disable_auth_skip(monkeypatch):
    """
    Disable MCP_SKIP_AUTH for tests requiring real authentication.

    **Purpose**:
    Many tests need `MCP_SKIP_AUTH=false` to test actual auth behavior.
    This fixture provides that setting with automatic cleanup via monkeypatch.

    **Usage**:
    ```python
    def test_auth_required(disable_auth_skip):
        # MCP_SKIP_AUTH is now "false"
        # Test actual authentication...
        # Cleanup happens automatically
    ```

    **Why This Exists**:
    Replaces manual setup/teardown patterns that cause env pollution in pytest-xdist:
    ```python
    # OLD (manual cleanup, pollution risk):
    def setup_method(self):
        os.environ["MCP_SKIP_AUTH"] = "false"
    def teardown_method(self):
        del os.environ["MCP_SKIP_AUTH"]

    # NEW (automatic cleanup, xdist-safe):
    def test_something(self, disable_auth_skip):
        # MCP_SKIP_AUTH already set, auto-cleanup
    ```

    **References**:
    - OpenAI Codex Finding: 15+ test files with direct os.environ mutations (RESOLVED)
    - tests/meta/test_environment_isolation_enforcement.py (validates this pattern)
    - tests/PYTEST_XDIST_PREVENTION.md (documents xdist isolation)
    """
    monkeypatch.setenv("MCP_SKIP_AUTH", "false")


@pytest.fixture
def isolated_environment(monkeypatch):
    """
    Provide isolated environment for pollution-sensitive tests.

    **Purpose**:
    Some tests are sensitive to environment variable pollution from other tests
    running in the same pytest-xdist worker. This fixture provides a clean
    monkeypatch instance for the test to use.

    **Usage**:
    ```python
    def test_env_sensitive(isolated_environment):
        isolated_environment.setenv("SOME_VAR", "value")
        # Test code...
        # Cleanup happens automatically
    ```

    **Class-Level Usage (Autouse)**:
    ```python
    @pytest.fixture(autouse=True)
    def _isolated_env(self, isolated_environment):
        # All tests in this class get isolated environment
        return isolated_environment

    class TestEnvSensitive:
        def test_one(self, isolated_environment):
            isolated_environment.setenv("VAR", "val1")

        def test_two(self, isolated_environment):
            isolated_environment.setenv("VAR", "val2")
            # No pollution from test_one
    ```

    **Returns**:
    monkeypatch instance for test to use

    **References**:
    - OpenAI Codex Finding: Environment pollution in xdist workers (RESOLVED)
    - tests/meta/test_environment_isolation_enforcement.py
    """
    return monkeypatch


@pytest.fixture(scope="session")
def test_infrastructure(docker_services_available, docker_compose_file, test_infrastructure_ports):
    """
    Automated test infrastructure lifecycle management.

    This fixture:
    1. Starts all services via docker-compose.test.yml
    2. Waits for health checks to pass
    3. Yields control to tests
    4. Automatically tears down services after session

    Replaces manual:
        docker compose -f docker-compose.test.yml up -d
        docker compose -f docker-compose.test.yml down -v

    Usage:
        @pytest.mark.e2e
        def test_with_infrastructure(test_infrastructure):
            # All services are running and healthy
            ...
    """
    # Set TESTING environment variable for services
    # NOTE: This is intentionally session-scoped and not cleaned up.
    # Worker isolation is achieved via port offsets and schema/DB separation,
    # not separate Docker instances. The TESTING env var is shared across
    # all workers to enable test infrastructure detection.
    os.environ["TESTING"] = "true"

    # Check if python-on-whales is available
    try:
        from python_on_whales import DockerClient
    except ImportError:
        pytest.skip("python-on-whales not installed - infrastructure tests require Docker support")

    try:
        docker = DockerClient(compose_files=[docker_compose_file])

        # Start services
        logging.info("Starting test infrastructure via docker-compose...")
        docker.compose.up(detach=True, wait=False)

        # Wait for critical services to be ready
        logging.info("Waiting for test infrastructure health checks...")

        # PostgreSQL
        if not _wait_for_port("localhost", test_infrastructure_ports["postgres"], timeout=30):
            pytest.skip("PostgreSQL test service did not become ready in time - skipping infrastructure tests")
        logging.info("✓ PostgreSQL ready")

        # Redis (checkpoints)
        if not _wait_for_port("localhost", test_infrastructure_ports["redis_checkpoints"], timeout=20):
            pytest.skip("Redis checkpoints test service did not become ready in time - skipping infrastructure tests")
        logging.info("✓ Redis (checkpoints) ready")

        # Redis (sessions)
        if not _wait_for_port("localhost", test_infrastructure_ports["redis_sessions"], timeout=20):
            pytest.skip("Redis sessions test service did not become ready in time - skipping infrastructure tests")
        logging.info("✓ Redis (sessions) ready")

        # OpenFGA HTTP
        if not _wait_for_port("localhost", test_infrastructure_ports["openfga_http"], timeout=40):
            pytest.skip("OpenFGA test service did not become ready in time - skipping infrastructure tests")
        # Additional check for OpenFGA
        if not _check_http_health(f"http://localhost:{test_infrastructure_ports['openfga_http']}/healthz", timeout=5):
            pytest.skip("OpenFGA health check failed - skipping infrastructure tests")
        logging.info("✓ OpenFGA ready")

        # Keycloak (takes longer to start)
        if not _wait_for_port("localhost", test_infrastructure_ports["keycloak"], timeout=90):
            pytest.skip("Keycloak test service did not become ready in time - skipping infrastructure tests")
        # Additional check for Keycloak
        if not _check_http_health(f"http://localhost:{test_infrastructure_ports['keycloak']}/health/ready", timeout=10):
            pytest.skip("Keycloak health check failed - skipping infrastructure tests")
        logging.info("✓ Keycloak ready")

        # Qdrant
        if not _wait_for_port("localhost", test_infrastructure_ports["qdrant"], timeout=30):
            pytest.skip("Qdrant test service did not become ready in time - skipping infrastructure tests")
        logging.info("✓ Qdrant ready")

        logging.info("✅ All test infrastructure services ready")

        # Return infrastructure info
        yield {"ports": test_infrastructure_ports, "docker": docker, "ready": True}

    finally:
        # Cleanup: Stop and remove services
        logging.info("Tearing down test infrastructure...")
        try:
            docker.compose.down(volumes=True, remove_orphans=True, timeout=30)
            logging.info("✅ Test infrastructure cleaned up")
        except Exception as e:
            logging.error(f"Error during infrastructure cleanup: {e}")


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
# E2E FastAPI App Fixtures
# ==============================================================================


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
        keycloak_realm="master",  # Use master realm for tests
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
        from mcp_server_langgraph.app import create_app

        app = create_app()

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

    async with httpx.AsyncClient(app=test_fastapi_app, base_url="http://test") as client:
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
    yield container
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
        model_name="claude-3-5-sonnet-20241022",
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


@pytest.fixture(scope="session")
async def postgres_connection_real(integration_test_env):
    """Real PostgreSQL connection for integration tests"""
    if not integration_test_env:
        pytest.skip("Integration test environment not available (requires Docker)")

    try:
        import asyncpg
    except ImportError:
        pytest.skip("asyncpg not installed")

    # Connection params from environment (set in docker-compose.test.yml)
    # Note: Postgres test port is 9432 (offset from standard 5432 to avoid conflicts)
    conn = await asyncpg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "9432")),
        database=os.getenv("POSTGRES_DB", "gdpr_test"),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),  # Match docker-compose.test.yml
    )

    yield conn

    await conn.close()


@pytest.fixture(scope="session")
async def redis_client_real(integration_test_env):
    """Real Redis client for integration tests"""
    if not integration_test_env:
        pytest.skip("Integration test environment not available (requires Docker)")

    try:
        import redis.asyncio as redis
    except ImportError:
        pytest.skip("redis not installed")

    client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
    )

    # Test connection
    try:
        await client.ping()
    except Exception as e:
        pytest.skip(f"Redis not available: {e}")

    yield client

    # Cleanup test data
    await client.flushdb()
    await client.aclose()


@pytest.fixture(scope="session")
async def openfga_client_real(integration_test_env, test_infrastructure_ports):
    """Real OpenFGA client for integration tests with auto-initialization"""
    if not integration_test_env:
        pytest.skip("Integration test environment not available (requires Docker)")

    from mcp_server_langgraph.auth.openfga import OpenFGAClient, initialize_openfga_store

    # OpenFGA test URL - use infrastructure port from fixture (ensures consistency)
    api_url = os.getenv("OPENFGA_API_URL", f"http://localhost:{test_infrastructure_ports['openfga_http']}")

    # Create client without store/model initially
    client = OpenFGAClient(api_url=api_url, store_id=None, model_id=None)

    # Initialize OpenFGA store and authorization model for tests
    try:
        logging.info("Initializing OpenFGA test store and authorization model...")
        store_id = await initialize_openfga_store(client)
        model_id = client.model_id

        # Set environment variables so all tests can access the configured store
        os.environ["OPENFGA_STORE_ID"] = store_id
        os.environ["OPENFGA_MODEL_ID"] = model_id

        logging.info(f"✓ OpenFGA initialized: store_id={store_id}, model_id={model_id}")

        # Update client with store and model IDs
        client.store_id = store_id
        client.model_id = model_id
    except Exception as e:
        logging.warning(f"Failed to initialize OpenFGA for tests (will use fallback auth): {e}")
        # Tests will fall back to inmemory auth provider

    yield client

    # Cleanup happens per-test


# =============================================================================
# PER-TEST CLEANUP FIXTURES
# =============================================================================
# These function-scoped fixtures wrap the session-scoped infrastructure
# fixtures and provide automatic cleanup between tests for isolation.


@pytest.fixture
async def postgres_connection_clean(postgres_connection_real):
    """
    PostgreSQL connection with per-test cleanup and worker-scoped isolation.

    **Worker-Scoped Schema Isolation (pytest-xdist support):**
    - Each xdist worker gets its own PostgreSQL schema
    - Worker gw0: schema test_worker_gw0
    - Worker gw1: schema test_worker_gw1
    - Worker gw2: schema test_worker_gw2
    - Non-xdist: schema test_worker_gw0 (default)

    This prevents race conditions where one worker's TRUNCATE affects another
    worker's in-progress test data.

    Usage:
        @pytest.mark.asyncio
        async def test_my_feature(postgres_connection_clean):
            await postgres_connection_clean.execute("INSERT INTO ...")
            # Automatic cleanup after test

    References:
    - tests/regression/test_pytest_xdist_worker_database_isolation.py
    - OpenAI Codex Finding: conftest.py:1042
    """
    # Get worker ID from environment (set by pytest-xdist)
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    schema_name = f"test_worker_{worker_id}"

    # Create worker-scoped schema if it doesn't exist
    try:
        await postgres_connection_real.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_name}")
        # Set search_path to worker schema for all subsequent queries
        await postgres_connection_real.execute(f"SET search_path TO {schema_name}, public")
    except Exception as e:
        # Log but don't fail - some tests may not need the schema
        import warnings

        warnings.warn(f"Failed to create worker schema {schema_name}: {e}")

    yield postgres_connection_real

    # Cleanup: Drop entire worker schema (safe, isolated to this worker)
    # This is faster and more thorough than TRUNCATE
    try:
        await postgres_connection_real.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
    except Exception:
        # If cleanup fails, don't fail the test
        # The schema will be recreated on next test run
        pass


@pytest.fixture
async def redis_client_clean(redis_client_real):
    """
    Redis client with per-test cleanup and worker-scoped isolation.

    **Worker-Scoped DB Index Isolation (pytest-xdist support):**
    - Each xdist worker gets its own Redis database index
    - Worker gw0: DB 1 (DB 0 reserved for non-xdist)
    - Worker gw1: DB 2
    - Worker gw2: DB 3
    - Worker gw3: DB 4
    - Non-xdist: DB 1 (default)

    This prevents race conditions where one worker's FLUSHDB affects another
    worker's test data.

    Redis has 16 databases by default (0-15), supporting up to 15 concurrent
    xdist workers.

    Usage:
        @pytest.mark.asyncio
        async def test_my_feature(redis_client_clean):
            await redis_client_clean.set("key", "value")
            # Automatic cleanup after test

    References:
    - tests/regression/test_pytest_xdist_worker_database_isolation.py
    - OpenAI Codex Finding: conftest.py:1092
    """
    # Get worker ID from environment (set by pytest-xdist)
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")

    # Calculate worker-scoped DB index: gw0→1, gw1→2, gw2→3, etc.
    # DB 0 is reserved for non-xdist usage
    worker_num = int(worker_id.replace("gw", "")) if worker_id.startswith("gw") else 0
    db_index = worker_num + 1

    # Select worker-scoped database
    try:
        await redis_client_real.select(db_index)
    except Exception as e:
        # Log but don't fail - some tests may not need Redis
        import warnings

        warnings.warn(f"Failed to select Redis DB {db_index} for worker {worker_id}: {e}")

    yield redis_client_real

    # Cleanup: Flush worker-scoped database (safe, isolated to this worker)
    # This is fast (O(N) where N is number of keys, but typically < 1ms for tests)
    try:
        await redis_client_real.flushdb()
    except Exception:
        # If cleanup fails, don't fail the test
        pass


@pytest.fixture
async def openfga_client_clean(openfga_client_real):
    """
    OpenFGA client with per-test cleanup and worker-scoped isolation.

    **Worker-Scoped Store Isolation (pytest-xdist support):**
    - Each xdist worker gets its own OpenFGA store
    - Worker gw0: store test_store_gw0
    - Worker gw1: store test_store_gw1
    - Worker gw2: store test_store_gw2
    - Non-xdist: store test_store_gw0 (default)

    This prevents race conditions where one worker's tuple deletion affects
    another worker's test data.

    **Important:** This fixture requires tests to use `xdist_group` markers
    to serialize OpenFGA tests if they share stores. For better isolation,
    tests should use unique object IDs or worker-scoped stores.

    Usage:
        @pytest.mark.asyncio
        @pytest.mark.xdist_group(name="openfga_tests")
        async def test_my_feature(openfga_client_clean):
            await openfga_client_clean.write_tuples([...])
            # Automatic cleanup after test

    References:
    - tests/regression/test_pytest_xdist_worker_database_isolation.py
    - OpenAI Codex Finding: conftest.py:1116
    """
    # Get worker ID from environment (set by pytest-xdist)
    worker_id = os.getenv("PYTEST_XDIST_WORKER", "gw0")
    _store_name = f"test_store_{worker_id}"  # noqa: F841 Reserved for future use

    # Note: Worker-scoped store creation would require OpenFGA API calls.
    # For now, we track tuples and delete them (existing pattern).
    # Tests using OpenFGA should use @pytest.mark.xdist_group to serialize
    # if they share stores, or use unique object IDs for isolation.

    # Track tuples written during this test for cleanup
    written_tuples = []

    # Wrap write_tuples to track writes
    original_write = openfga_client_real.write_tuples

    async def tracked_write_tuples(tuples):
        written_tuples.extend(tuples)
        return await original_write(tuples)

    # Monkey-patch for test duration
    openfga_client_real.write_tuples = tracked_write_tuples

    yield openfga_client_real

    # Restore original method
    openfga_client_real.write_tuples = original_write

    # Cleanup: Delete all tuples written during test
    # This is safe if tests use unique object IDs or run serially via xdist_group
    if written_tuples:
        try:
            await openfga_client_real.delete_tuples(written_tuples)
        except Exception:
            # If cleanup fails, don't fail the test
            # Tuples will be cleaned up eventually or won't affect other tests
            # if using different object IDs
            pass


@pytest.fixture(scope="session")
async def postgres_with_schema(postgres_connection_real):
    """
    PostgreSQL connection with GDPR schema initialized.

    Runs the GDPR schema migration once per test session.
    Required for testing PostgreSQL storage backends.

    Usage:
        @pytest.mark.asyncio
        async def test_postgres_storage(postgres_with_schema):
            # Schema already created (audit_logs, consent_records, etc.)
    """
    from pathlib import Path

    # Find schema file
    project_root = Path(__file__).parent.parent
    schema_file = project_root / "migrations" / "001_gdpr_schema.sql"

    if not schema_file.exists():
        pytest.skip(f"Schema file not found: {schema_file}")

    # Read and execute schema
    schema_sql = schema_file.read_text()

    try:
        await postgres_connection_real.execute(schema_sql)
    except Exception:
        # Schema might already exist (idempotent CREATE TABLE IF NOT EXISTS)
        pass

    yield postgres_connection_real

    # No cleanup - schema persists for all tests in session


@pytest.fixture
async def db_pool_gdpr(integration_test_env):
    """
    PostgreSQL connection pool with GDPR schema for integration/security tests.

    Creates a connection pool and initializes GDPR schema tables.
    Used by security tests and GDPR compliance tests that need pool-based access.

    OpenAI Codex Finding Fix (2025-11-16):
    =======================================
    This fixture replaces the Alembic-based approach in test_sql_injection_gdpr.py
    which failed due to asyncio.run() conflicts in pytest-asyncio context.

    Executes schema SQL directly using async connection pool.
    """
    if not integration_test_env:
        pytest.skip("Integration test environment not available (requires Docker)")

    try:
        import asyncpg
    except ImportError:
        pytest.skip("asyncpg not installed")

    from pathlib import Path

    # Create connection pool
    # Note: Postgres test port is 9432 (offset from standard 5432 to avoid conflicts)
    pool = await asyncpg.create_pool(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "9432")),
        user=os.getenv("POSTGRES_USER", "postgres"),
        password=os.getenv("POSTGRES_PASSWORD", "postgres"),
        database=os.getenv("POSTGRES_DB", "gdpr_test"),
        min_size=1,
        max_size=5,
    )

    # Execute GDPR schema SQL directly
    project_root = Path(__file__).parent.parent
    schema_file = project_root / "migrations" / "001_gdpr_schema.sql"

    if schema_file.exists():
        schema_sql = schema_file.read_text()

        async with pool.acquire() as conn:
            try:
                await conn.execute(schema_sql)
            except Exception:
                # Schema might already exist (CREATE TABLE IF NOT EXISTS makes this idempotent)
                pass

    yield pool

    # Cleanup
    await pool.close()


@pytest.fixture(scope="session")
def qdrant_available():
    """Check if Qdrant is available for testing."""
    qdrant_url = os.getenv("QDRANT_URL", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

    try:
        import httpx

        # Quick check if Qdrant is accessible
        response = httpx.get(f"http://{qdrant_url}:{qdrant_port}/", timeout=2.0)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture
def qdrant_client():
    """Qdrant client for integration tests with vector search."""
    try:
        from qdrant_client import QdrantClient
    except ImportError:
        pytest.skip("Qdrant client not installed")

    qdrant_url = os.getenv("QDRANT_URL", "localhost")
    qdrant_port = int(os.getenv("QDRANT_PORT", "6333"))

    # Check if Qdrant is available
    try:
        import httpx

        response = httpx.get(f"http://{qdrant_url}:{qdrant_port}/", timeout=2.0)
        if response.status_code != 200:
            pytest.skip("Qdrant instance not available")
    except Exception as e:
        pytest.skip(f"Qdrant instance not available: {e}")

    # Create client
    client = QdrantClient(url=qdrant_url, port=qdrant_port)

    # Test connection
    try:
        client.get_collections()
    except Exception as e:
        pytest.skip(f"Cannot connect to Qdrant: {e}")

    yield client

    # Cleanup: Delete test collections
    try:
        collections = client.get_collections().collections
        test_collections = [c.name for c in collections if c.name.startswith("test_")]
        for collection_name in test_collections:
            try:
                client.delete_collection(collection_name)
            except Exception:
                pass  # Best effort cleanup
    except Exception:
        pass  # Ignore cleanup errors


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

    NOW = datetime.now(timezone.utc)

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

    yield

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

    yield

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
    - tests/meta/test_slow_test_detection.py: Detects slow tests > 10s
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
    yield

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
        except asyncio.TimeoutError:
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
