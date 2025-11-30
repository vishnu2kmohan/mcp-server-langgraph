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
