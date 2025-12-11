import pytest
import shutil
import subprocess
import functools


@pytest.fixture(scope="session")
def kustomize_available():
    """Check if kustomize CLI tool is available."""
    return shutil.which("kustomize") is not None


@pytest.fixture(scope="session")
def kubectl_available():
    """Check if kubectl CLI tool is available."""
    return shutil.which("kubectl") is not None


@pytest.fixture(scope="session")
def kubectl_connected():
    """
    Check if kubectl can connect to a Kubernetes cluster.

    This is needed for tests that use --dry-run=client because kubectl
    still downloads the OpenAPI schema from the cluster for validation.
    """
    if not shutil.which("kubectl"):
        return False
    try:
        result = subprocess.run(
            ["kubectl", "cluster-info", "--request-timeout=5s"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


@pytest.fixture(scope="session")
def gke_preview_cluster():
    """
    Check if kubectl is connected to the GKE Preview cluster.

    Returns the cluster name if connected to a GKE preview cluster,
    None otherwise. This prevents GKE-specific tests from running
    on local Kubernetes clusters (Docker Desktop, Minikube, etc.).

    GKE Preview cluster context pattern: gke_*_preview-mcp-server-langgraph-gke
    """
    if not shutil.which("kubectl"):
        return None
    try:
        result = subprocess.run(
            ["kubectl", "config", "current-context"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        context = result.stdout.strip()
        # Check for GKE preview cluster context pattern
        if "preview-mcp-server-langgraph-gke" in context:
            return context
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


@pytest.fixture(scope="session")
def helm_available():
    """Check if helm CLI tool is available."""
    return shutil.which("helm") is not None


@pytest.fixture(scope="session")
def terraform_available():
    """Check if terraform CLI tool is available."""
    return shutil.which("terraform") is not None


@pytest.fixture(scope="session")
def docker_compose_available():
    """Check if docker compose CLI tool is available and functional."""
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
    """Decorator to skip tests if a required CLI tool is not available."""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not shutil.which(tool_name):
                reason = skip_reason or f"{tool_name} not installed"
                pytest.skip(reason)
            return func(*args, **kwargs)

        return wrapper

    return decorator


# ==============================================================================
# Docker Test Infrastructure Fixtures
# ==============================================================================


def _check_service_health(host: str, port: int, path: str = "/", timeout: float = 2.0) -> bool:
    """
    Check if a service is responding at the given host:port/path.

    Args:
        host: Service hostname
        port: Service port
        path: Health check path
        timeout: Connection timeout in seconds

    Returns:
        True if service is healthy, False otherwise
    """
    import socket

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except (TimeoutError, OSError):
        return False


@pytest.fixture(scope="session")
def playground_service_available():
    """
    Check if the Playground API service is available.

    Returns True if the playground service is responding on TEST_PLAYGROUND_API_PORT.
    This fixture enables tests to skip gracefully when docker-compose.test.yml
    infrastructure isn't running.
    """
    from tests.constants import TEST_PLAYGROUND_API_PORT

    return _check_service_health("localhost", TEST_PLAYGROUND_API_PORT)


@pytest.fixture(scope="session")
def builder_service_available():
    """
    Check if the Builder API service is available.

    Returns True if the builder service is responding on TEST_BUILDER_API_PORT.
    This fixture enables tests to skip gracefully when docker-compose.test.yml
    infrastructure isn't running.
    """
    from tests.constants import TEST_BUILDER_API_PORT

    return _check_service_health("localhost", TEST_BUILDER_API_PORT)


@pytest.fixture(scope="session")
def test_postgres_available():
    """
    Check if the test PostgreSQL database is available.

    Returns True if PostgreSQL is responding on TEST_POSTGRES_PORT.
    """
    from tests.constants import TEST_POSTGRES_PORT

    return _check_service_health("localhost", TEST_POSTGRES_PORT)


@pytest.fixture(scope="session")
def test_redis_available():
    """
    Check if the test Redis service is available.

    Returns True if Redis is responding on TEST_REDIS_PORT.
    """
    from tests.constants import TEST_REDIS_PORT

    return _check_service_health("localhost", TEST_REDIS_PORT)


@pytest.fixture(scope="session")
def test_infra_available(
    test_postgres_available,
    test_redis_available,
):
    """
    Check if core test infrastructure is available.

    Returns True if PostgreSQL and Redis are both responding.
    This is the minimum infrastructure needed for most integration tests.
    """
    return test_postgres_available and test_redis_available


@pytest.fixture
def skip_if_no_playground_service(playground_service_available):
    """
    Skip test if the Playground API service is not available.

    Use this fixture for tests that require a running playground service
    from docker-compose.test.yml. Tests will be skipped with a clear
    message when infrastructure isn't available.
    """
    if not playground_service_available:
        pytest.skip("Playground service not available. Start test infrastructure with: make test-infra-up")
    return True


@pytest.fixture
def skip_if_no_builder_service(builder_service_available):
    """
    Skip test if the Builder API service is not available.

    Use this fixture for tests that require a running builder service
    from docker-compose.test.yml. Tests will be skipped with a clear
    message when infrastructure isn't available.
    """
    if not builder_service_available:
        pytest.skip("Builder service not available. Start test infrastructure with: make test-infra-up")
    return True


@pytest.fixture
def skip_if_no_test_infra(test_infra_available):
    """
    Skip test if core test infrastructure is not available.

    Use this fixture for tests that require PostgreSQL and Redis
    from docker-compose.test.yml.
    """
    if not test_infra_available:
        pytest.skip("Test infrastructure not available. Start with: make test-infra-up")
    return True
