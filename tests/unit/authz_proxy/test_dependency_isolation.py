"""
Tests for authz-proxy dependency isolation.

These tests verify that the authz-proxy module can be imported with only its
minimal dependency set, without pulling in heavy dependencies like LangGraph,
LLM providers, or full database stack.

This ensures the Docker image can remain small (~400MB instead of 1.4GB).

Reference: pyproject.toml [dependency-groups.authz-proxy]
"""

import gc
import sys

import pytest

pytestmark = pytest.mark.unit

# Heavy modules that should NOT be imported by authz-proxy
FORBIDDEN_MODULES = {
    # LangGraph ecosystem (adds ~800MB)
    "langgraph",
    "langchain",
    "langchain_core",
    "langsmith",
    "litellm",
    # LLM provider SDKs (adds ~200MB each)
    "anthropic",
    "openai",
    "google.cloud.aiplatform",
    "boto3",
    "azure.identity",
    # Full database stack (we only need sqlalchemy core)
    "alembic",
    # Heavy ML libraries
    "tiktoken",
    "qdrant_client",
    # Secrets management (optional)
    "infisical",
}


@pytest.mark.unit
@pytest.mark.xdist_group(name="authz_proxy_isolation")
class TestAuthzProxyDependencyIsolation:
    """Tests to ensure authz-proxy doesn't import heavy dependencies."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_server_import_does_not_load_forbidden_modules(self) -> None:
        """
        Verify that importing authz_proxy.server doesn't load LangGraph or LLM SDKs.

        This test validates the dependency isolation achieved through:
        1. Lazy imports in core/__init__.py
        2. Lightweight authz_proxy/dependencies.py (instead of core/dependencies.py)
        3. Minimal dependency group in pyproject.toml
        """
        # Record modules loaded before import
        modules_before = set(sys.modules.keys())

        # Import the authz-proxy server
        from mcp_server_langgraph.authz_proxy import server  # noqa: F401

        # Record modules loaded after import
        modules_after = set(sys.modules.keys())

        # Find newly loaded modules
        new_modules = modules_after - modules_before

        # Check for forbidden modules
        violations = []
        for module in new_modules:
            # Check if module starts with any forbidden prefix
            for forbidden in FORBIDDEN_MODULES:
                if module == forbidden or module.startswith(f"{forbidden}."):
                    violations.append(module)
                    break

        if violations:
            pytest.fail(
                f"authz-proxy imported forbidden heavy modules:\n"
                f"  {violations}\n\n"
                f"This will bloat the Docker image from ~400MB to ~1.4GB.\n"
                f"Fix by using lazy imports or lightweight alternatives."
            )

    def test_dependencies_module_is_lightweight(self) -> None:
        """
        Verify authz_proxy/dependencies.py doesn't import from core/dependencies.py.

        core/dependencies.py imports repositories, storage, and database modules
        which are not needed for authz-proxy's simple OpenFGA client lookup.
        """
        # Import the lightweight dependencies module
        from mcp_server_langgraph.authz_proxy import dependencies

        # Verify it only imports what's needed
        import inspect

        source = inspect.getsource(dependencies)

        # Should NOT import from core.dependencies
        assert "from mcp_server_langgraph.core.dependencies" not in source, (
            "authz_proxy/dependencies.py should not import from core/dependencies.py. "
            "Use the lightweight local implementation instead."
        )

        # Should NOT import repositories
        assert "from mcp_server_langgraph.repositories" not in source, (
            "authz_proxy/dependencies.py should not import repositories. "
            "These are not needed for the authz-proxy functionality."
        )

    def test_pyproject_authz_proxy_group_exists(self) -> None:
        """
        Verify the authz-proxy dependency group is defined in pyproject.toml.

        This is a meta-test that validates the dependency group configuration
        rather than testing installed packages (which differ between dev and Docker).
        """
        from pathlib import Path
        import tomllib

        # tests/unit/authz_proxy/test_*.py -> parents[3] = project root
        pyproject_path = Path(__file__).parents[3] / "pyproject.toml"
        with open(pyproject_path, "rb") as f:
            pyproject = tomllib.load(f)

        assert "dependency-groups" in pyproject, "pyproject.toml missing [dependency-groups]"
        assert "authz-proxy" in pyproject["dependency-groups"], "pyproject.toml missing [dependency-groups.authz-proxy]"

        # Verify key dependencies are in the group
        authz_deps = pyproject["dependency-groups"]["authz-proxy"]
        authz_deps_str = " ".join(authz_deps).lower()

        required_in_group = [
            "fastapi",
            "uvicorn",
            "httpx",
            "python-jose",
            "pyjwt",
            "openfga-sdk",
            "pydantic",
            "sqlalchemy",
            "opentelemetry",
            "prometheus-client",
            "bcrypt",
        ]

        missing = [dep for dep in required_in_group if dep not in authz_deps_str]
        if missing:
            pytest.fail(
                f"authz-proxy dependency group missing required packages:\n"
                f"  {missing}\n\n"
                f"Add these to [dependency-groups.authz-proxy] in pyproject.toml."
            )

    def test_metrics_endpoint_dependencies(self) -> None:
        """Verify prometheus_client is available for /metrics endpoint."""
        from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

        # Should be able to generate metrics
        output = generate_latest()
        assert isinstance(output, bytes)
        assert CONTENT_TYPE_LATEST is not None

    def test_health_endpoint_has_no_external_dependencies(self) -> None:
        """Verify health endpoint can respond without external services."""
        from mcp_server_langgraph.authz_proxy.server import health

        # Health check should be a simple function
        import inspect

        sig = inspect.signature(health)

        # Should have no required parameters (all have defaults or are FastAPI deps)
        required_params = [p for p in sig.parameters.values() if p.default is inspect.Parameter.empty]
        assert len(required_params) == 0, (
            "Health endpoint should have no required parameters to ensure "
            "it can respond even when external services are unavailable."
        )
