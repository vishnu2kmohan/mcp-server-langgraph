"""
Meta tests for consolidated security suite.

Tests the change detection logic and scope determination
for the unified security scanner.

Reference: Codex Audit - Security scanning fragmentation (2025-12-01)
"""

import gc

import pytest

pytestmark = pytest.mark.meta


@pytest.mark.xdist_group(name="security_suite")
class TestSecuritySuiteChangeDetection:
    """Test change detection for security scans."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.parametrize(
        "changed_files,expected_scopes",
        [
            # Single scope triggers
            (["deployments/kubernetes/base/deployment.yaml"], {"k8s-manifests"}),
            (["deployments/kubernetes/overlays/production/kustomization.yaml"], {"k8s-manifests"}),
            (["deployments/helm/values.yaml"], {"helm-full"}),
            (["deployments/helm/mcp-server-langgraph/Chart.yaml"], {"helm-full"}),
            (["deployments/helm/mcp-server-langgraph/templates/deployment.yaml"], {"helm-full"}),
            (["terraform/main.tf"], {"terraform"}),
            (["terraform/modules/gke/variables.tf"], {"terraform"}),
            # Multiple scope triggers
            (
                ["deployments/kubernetes/base/deployment.yaml", "deployments/helm/values.yaml"],
                {"k8s-manifests", "helm-full"},
            ),
            (
                ["terraform/main.tf", "deployments/helm/values.yaml"],
                {"terraform", "helm-full"},
            ),
            # No security-relevant changes → scan all
            (["src/main.py"], {"all"}),
            (["tests/unit/test_auth.py"], {"all"}),
            (["README.md"], {"all"}),
            # Empty changes → scan all
            ([], {"all"}),
        ],
    )
    def test_detect_security_scope(self, changed_files: list[str], expected_scopes: set[str]) -> None:
        """Test that security scope detection works correctly."""
        from scripts.security.run_security_suite import detect_security_scope

        assert detect_security_scope(changed_files) == expected_scopes


@pytest.mark.xdist_group(name="security_suite")
class TestSecuritySuiteToolChecks:
    """Test tool availability checks."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_check_tool_available_for_common_tools(self) -> None:
        """Test that check_tool_available works for common tools."""
        from scripts.security.run_security_suite import check_tool_available

        # These should always be available in a Unix environment
        assert check_tool_available("python3") or check_tool_available("python")
        assert check_tool_available("git")

        # Non-existent tool should return False
        assert not check_tool_available("nonexistent-tool-xyz-12345")


@pytest.mark.xdist_group(name="security_suite")
class TestSecuritySuiteIntegration:
    """Integration tests for security suite."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_security_suite_imports_successfully(self) -> None:
        """Test that the security suite module imports without errors."""
        from scripts.security import run_security_suite

        assert run_security_suite is not None
        assert hasattr(run_security_suite, "main")
        assert hasattr(run_security_suite, "detect_security_scope")
        assert hasattr(run_security_suite, "get_changed_files")
        assert hasattr(run_security_suite, "run_k8s_manifests_scan")
        assert hasattr(run_security_suite, "run_helm_full_scan")
        assert hasattr(run_security_suite, "run_terraform_scan")

    def test_get_changed_files_returns_list(self) -> None:
        """Test that get_changed_files returns a list."""
        from scripts.security.run_security_suite import get_changed_files

        result = get_changed_files()
        assert isinstance(result, list)
