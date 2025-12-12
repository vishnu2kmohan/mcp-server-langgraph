"""
Bundle Size Tests

Tests for frontend bundle size optimization.
"""

import gc
from unittest.mock import patch

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_bundle_size")
class TestBundleSizeTargets:
    """Tests for bundle size targets and validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_bundle_size_config_has_targets(self) -> None:
        """GIVEN bundle size configuration
        WHEN accessing targets
        THEN should have defined targets
        """
        from mcp_server_langgraph.studio.performance import BUNDLE_SIZE_TARGETS

        assert "initial" in BUNDLE_SIZE_TARGETS
        assert "gzipped" in BUNDLE_SIZE_TARGETS

    def test_bundle_size_target_initial_under_500kb(self) -> None:
        """GIVEN bundle size targets
        WHEN checking initial bundle
        THEN target should be under 500KB gzipped
        """
        from mcp_server_langgraph.studio.performance import BUNDLE_SIZE_TARGETS

        assert BUNDLE_SIZE_TARGETS["gzipped"] <= 500 * 1024  # 500KB

    def test_bundle_analyzer_calculates_size_correctly(self) -> None:
        """GIVEN bundle analyzer
        WHEN calculating bundle sizes
        THEN should return accurate sizes
        """
        from mcp_server_langgraph.studio.performance import BundleAnalyzer

        analyzer = BundleAnalyzer()

        # Mock the dist directory check
        with patch.object(analyzer, "_get_bundle_files") as mock_files:
            mock_files.return_value = [
                ("main.js", 100000),
                ("vendor.js", 200000),
            ]

            result = analyzer.calculate_total_size()
            assert result == 300000


@pytest.mark.unit
@pytest.mark.xdist_group(name="test_bundle_size")
class TestBundleOptimization:
    """Tests for bundle optimization features."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_code_splitting_config_exists(self) -> None:
        """GIVEN Vite config
        WHEN checking code splitting
        THEN should have manual chunks configured
        """
        from mcp_server_langgraph.studio.performance import CODE_SPLITTING_CONFIG

        assert "vendor" in CODE_SPLITTING_CONFIG or "manualChunks" in CODE_SPLITTING_CONFIG

    def test_lazy_routes_are_defined(self) -> None:
        """GIVEN routing config
        WHEN checking lazy loading
        THEN should have lazy-loaded routes
        """
        from mcp_server_langgraph.studio.performance import LAZY_LOADED_ROUTES

        assert len(LAZY_LOADED_ROUTES) > 0
        # Check that major routes are lazy loaded
        assert any("workflows" in route.lower() for route in LAZY_LOADED_ROUTES)
