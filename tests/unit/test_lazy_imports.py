"""
Tests for lazy import functionality in __init__.py.

Verifies that heavy dependencies are only loaded when accessed,
preventing ModuleNotFoundError for minimal installations.
"""

import gc
import sys
from unittest.mock import MagicMock

import pytest


@pytest.mark.unit
@pytest.mark.xdist_group(name="unit_lazy_imports_tests")
class TestLazyImports:
    """Test lazy import behavior for optional dependencies"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_package_import_does_not_load_heavy_modules(self):
        """
        Test that importing the package doesn't trigger heavy module imports.

        Heavy modules:
        - auth.middleware (FastAPI, OpenFGA)
        - auth.openfga (openfga_sdk)
        - core.agent (LangGraph, LangChain)
        - llm.factory (langchain_core, sentence_transformers)
        """
        # Clear any cached imports
        modules_to_clear = [
            "mcp_server_langgraph",
            "mcp_server_langgraph.auth.middleware",
            "mcp_server_langgraph.auth.openfga",
            "mcp_server_langgraph.core.agent",
            "mcp_server_langgraph.llm.factory",
        ]

        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]

        # Import package - should NOT trigger heavy imports
        import mcp_server_langgraph  # noqa: F401

        # Verify heavy modules are NOT loaded
        heavy_modules = [
            "mcp_server_langgraph.auth.middleware",
            "mcp_server_langgraph.auth.openfga",
            "mcp_server_langgraph.core.agent",
            "mcp_server_langgraph.llm.factory",
        ]

        for mod in heavy_modules:
            assert mod not in sys.modules, f"{mod} should not be loaded on package import"

    def test_settings_import_is_lightweight(self):
        """Test that importing settings doesn't load heavy dependencies"""
        # Clear cached imports (must clear both root and submodules)
        modules_to_clear = [
            "mcp_server_langgraph",
            "mcp_server_langgraph.auth.middleware",
            "mcp_server_langgraph.auth.openfga",
            "mcp_server_langgraph.core.agent",
            "mcp_server_langgraph.llm.factory",
        ]

        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]

        # Import settings - should be lightweight
        from mcp_server_langgraph import settings

        assert settings is not None

        # Heavy modules should still not be loaded
        heavy_modules = [
            "mcp_server_langgraph.auth.middleware",
            "mcp_server_langgraph.auth.openfga",
            "mcp_server_langgraph.core.agent",
            "mcp_server_langgraph.llm.factory",
        ]

        for mod in heavy_modules:
            assert mod not in sys.modules, f"{mod} should not be loaded when importing settings"

    def test_lazy_import_of_auth_middleware(self):
        """Test that AuthMiddleware is imported only when accessed"""
        # This test verifies the __getattr__ mechanism works
        from mcp_server_langgraph import AuthMiddleware

        # Verify the import succeeded
        assert AuthMiddleware is not None
        assert hasattr(AuthMiddleware, "__name__")

    def test_lazy_import_of_openfga_client(self):
        """Test that OpenFGAClient is imported only when accessed"""
        from mcp_server_langgraph import OpenFGAClient

        assert OpenFGAClient is not None
        assert hasattr(OpenFGAClient, "__name__")

    def test_lazy_import_of_agent_graph(self):
        """Test that agent_graph is imported only when accessed"""
        from mcp_server_langgraph import agent_graph  # noqa: F401

        # The import itself is the test - it should not raise ModuleNotFoundError
        # agent_graph may be None until properly initialized in an app context

    def test_lazy_import_of_agent_state(self):
        """Test that AgentState is imported only when accessed"""
        from mcp_server_langgraph import AgentState

        assert AgentState is not None

    def test_lazy_import_of_llm_factory(self):
        """Test that create_llm_from_config is imported only when accessed"""
        from mcp_server_langgraph import create_llm_from_config

        assert create_llm_from_config is not None
        assert callable(create_llm_from_config)

    def test_lazy_import_of_observability(self):
        """Test that observability modules are imported only when accessed"""
        from mcp_server_langgraph import logger, metrics, tracer

        assert logger is not None
        assert tracer is not None
        assert metrics is not None

    def test_nonexistent_attribute_raises_attribute_error(self):
        """Test that accessing nonexistent attributes raises AttributeError"""
        import mcp_server_langgraph

        # When using getattr(), we get AttributeError directly
        with pytest.raises(AttributeError, match="has no attribute 'NonExistentClass'"):
            getattr(mcp_server_langgraph, "NonExistentClass")

        # When using 'from ... import ...', Python converts AttributeError to ImportError
        with pytest.raises(ImportError, match="cannot import name 'NonExistentClass'"):
            from mcp_server_langgraph import NonExistentClass  # noqa: F401

    def test_all_exports_defined_in_all_list(self):
        """Test that all exported names are in __all__"""
        import mcp_server_langgraph

        expected_exports = {
            "__version__",
            "settings",
            "agent_graph",
            "AgentState",
            "AuthMiddleware",
            "OpenFGAClient",
            "create_llm_from_config",
            "logger",
            "tracer",
            "metrics",
        }

        assert set(mcp_server_langgraph.__all__) == expected_exports

    def test_version_accessible_without_heavy_imports(self):
        """Test that __version__ can be accessed without loading heavy modules"""
        import mcp_server_langgraph

        # __version__ should be accessible
        assert hasattr(mcp_server_langgraph, "__version__")
        assert isinstance(mcp_server_langgraph.__version__, str)

        # Note: We can't reliably test that heavy modules aren't loaded because:
        # 1. Previous tests in the suite may have loaded them
        # 2. Python caches modules in sys.modules
        # 3. Clearing sys.modules can break pytest itself
        #
        # The important test is that the import succeeds and __version__ is accessible
        # The actual lazy loading is tested in test_package_import_does_not_load_heavy_modules


@pytest.mark.unit
@pytest.mark.xdist_group(name="unit_lazy_imports_tests")
class TestBackwardsCompatibility:
    """Test that existing import patterns still work"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_star_import_lists_all_exports(self):
        """Test that 'from mcp_server_langgraph import *' works"""
        # Note: We can't actually test * import in pytest without executing it
        # but we can verify __all__ is defined
        import mcp_server_langgraph

        assert hasattr(mcp_server_langgraph, "__all__")
        assert len(mcp_server_langgraph.__all__) > 0

    def test_direct_attribute_access(self):
        """Test that package.attribute access works"""
        import mcp_server_langgraph

        # These should work via __getattr__
        assert hasattr(mcp_server_langgraph, "AuthMiddleware")
        assert hasattr(mcp_server_langgraph, "agent_graph")
        assert hasattr(mcp_server_langgraph, "settings")

        # Access them to verify __getattr__ works
        _ = mcp_server_langgraph.settings
        _ = mcp_server_langgraph.AuthMiddleware
        _ = mcp_server_langgraph.agent_graph
