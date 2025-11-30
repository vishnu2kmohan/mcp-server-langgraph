"""
Unit tests for dependency injection wiring

Tests CRITICAL to prevent: ImportError, CircularImportError in production

Following TDD best practices (RED-GREEN-REFACTOR):
1. RED: These tests define expected behavior
2. GREEN: Implementation must make these pass
3. REFACTOR: Improve quality while keeping tests green

OpenAI Codex Finding (2025-11-17):
====================================
This test file was missing, causing test_all_critical_tests_exist to fail.
Created to ensure dependency wiring is validated before production deployments.
"""

import gc
import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest

from mcp_server_langgraph.core.config import Settings

# Mark as unit test for CI filtering
pytestmark = pytest.mark.unit

# ============================================================================
# MODULE IMPORT TESTS (Prevent ImportError in production)
# ============================================================================


@pytest.mark.xdist_group(name="test_dependencies_wiring")
class TestModuleImports:
    """Validate all critical modules can be imported without errors"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_all_core_modules_importable(self):
        """All core modules should import without errors"""
        critical_modules = [
            "mcp_server_langgraph",
            "mcp_server_langgraph.core.agent",
            "mcp_server_langgraph.core.config",
            "mcp_server_langgraph.core.container",
            "mcp_server_langgraph.mcp.server_streamable",
            "mcp_server_langgraph.mcp.server_stdio",
            "mcp_server_langgraph.auth.middleware",
            "mcp_server_langgraph.auth.user_provider",
            "mcp_server_langgraph.observability.telemetry",
        ]

        for module_name in critical_modules:
            try:
                # Fresh import to catch any import errors
                if module_name in sys.modules:
                    importlib.reload(sys.modules[module_name])
                else:
                    importlib.import_module(module_name)
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {e}")

    def test_no_circular_imports_in_core(self):
        """Core modules should not have circular import dependencies"""
        # This test validates by successfully importing all modules
        # Circular imports would cause ImportError or recursion
        try:
            import mcp_server_langgraph.core.agent  # noqa: F401
            import mcp_server_langgraph.core.config  # noqa: F401
            import mcp_server_langgraph.core.container  # noqa: F401
        except (ImportError, RecursionError) as e:
            pytest.fail(f"Circular import detected in core modules: {e}")


# ============================================================================
# SETTINGS INJECTION TESTS (Prevent runtime configuration errors)
# ============================================================================


@pytest.mark.xdist_group(name="testsettingsinjection")
class TestSettingsInjection:
    """Validate settings can be injected into all components"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        import gc

        gc.collect()

    def test_settings_can_be_created_with_minimal_config(self):
        """Settings should work with minimal required configuration"""
        settings = Settings(
            service_name="test",
            jwt_secret_key="test-key",
            anthropic_api_key="test-key",
        )

        assert settings.service_name == "test"
        assert settings.jwt_secret_key == "test-key"
        assert settings.anthropic_api_key == "test-key"

    @patch("mcp_server_langgraph.core.agent.create_llm_from_config")
    def test_agent_accepts_settings_injection(self, mock_llm):
        """Agent graph creation should accept settings parameter"""
        from mcp_server_langgraph.core.agent import create_agent_graph

        test_settings = Settings(
            service_name="test",
            jwt_secret_key="test-key",
            anthropic_api_key="test-key",
            enable_checkpointing=False,  # Disable for unit test
        )

        mock_llm.return_value = MagicMock()

        # Should not raise
        graph = create_agent_graph(settings=test_settings)
        assert graph is not None

    def test_container_can_be_created_with_settings(self):
        """ApplicationContainer should accept custom settings"""
        from mcp_server_langgraph.core.container import create_test_container

        test_settings = Settings(
            service_name="test",
            jwt_secret_key="test-key",
            anthropic_api_key="test-key",
        )

        # Should not raise - use factory function with settings override
        container = create_test_container(settings=test_settings)
        assert container is not None
        assert container.settings.service_name == "test"


# ============================================================================
# DEPENDENCY INITIALIZATION ORDER TESTS
# ============================================================================


@pytest.mark.xdist_group(name="testinitializationorder")
class TestInitializationOrder:
    """Validate components initialize in correct order"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        import gc

        gc.collect()

    def test_observability_can_initialize_before_agent(self):
        """Observability must be initialized before agent creation"""
        from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized

        test_settings = Settings(
            service_name="test",
            jwt_secret_key="test-key",
            anthropic_api_key="test-key",
        )

        # Initialize observability
        init_observability(settings=test_settings, enable_file_logging=False)

        # Should be marked as initialized
        assert is_initialized()

    def test_agent_works_after_observability_init(self):
        """Agent should work correctly when observability is initialized first"""
        from mcp_server_langgraph.core.agent import create_agent_graph
        from mcp_server_langgraph.observability.telemetry import init_observability, is_initialized

        test_settings = Settings(
            service_name="test",
            jwt_secret_key="test-key",
            anthropic_api_key="test-key",
            enable_checkpointing=False,
        )

        # Initialize observability first (production pattern)
        if not is_initialized():
            init_observability(settings=test_settings, enable_file_logging=False)

        # Create agent with mocked LLM
        with patch("mcp_server_langgraph.core.agent.create_llm_from_config") as mock_llm:
            mock_llm.return_value = MagicMock()
            graph = create_agent_graph(settings=test_settings)
            assert graph is not None


# ============================================================================
# PRODUCTION READINESS VALIDATION
# ============================================================================


@pytest.mark.xdist_group(name="test_dependencies_wiring")
class TestProductionReadiness:
    """Validate production deployment readiness"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_all_required_dependencies_present(self):
        """All required dependencies should be importable"""
        # Note: 'anthropic' is NOT a direct dependency - the project uses litellm
        # for multi-LLM support, which handles Anthropic/OpenAI/etc. internally
        required_packages = [
            "fastapi",
            "uvicorn",
            "pydantic",
            "pydantic_settings",
            "redis",
            "asyncpg",
            "langchain_core",
            "langgraph",
            "litellm",
            "openfga_sdk",
        ]

        missing = []
        for package in required_packages:
            try:
                importlib.import_module(package)
            except ImportError:
                missing.append(package)

        assert len(missing) == 0, f"Missing required packages: {missing}"

    def test_settings_validation_prevents_invalid_config(self):
        """Settings should validate field types"""
        from pydantic import ValidationError

        # Invalid field types should raise ValidationError
        with pytest.raises(ValidationError):
            Settings(
                jwt_expiration_seconds="not-an-integer",  # Should be int
            )


# ============================================================================
# INTEGRATION POINT TESTS
# ============================================================================


@pytest.mark.xdist_group(name="testintegrationpoints")
class TestIntegrationPoints:
    """Validate integration between major components"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        import gc

        gc.collect()

    def test_fastapi_app_can_be_created(self):
        """FastAPI app should be creatable without errors"""
        from mcp_server_langgraph.mcp.server_streamable import app

        assert app is not None
        assert hasattr(app, "routes")

    @patch("mcp_server_langgraph.core.agent.create_llm_from_config")
    def test_mcp_server_can_be_retrieved(self, mock_llm):
        """MCP server singleton should be retrievable"""
        from mcp_server_langgraph.mcp.server_streamable import get_mcp_server

        mock_llm.return_value = MagicMock()

        # Should not raise
        server = get_mcp_server()
        assert server is not None
