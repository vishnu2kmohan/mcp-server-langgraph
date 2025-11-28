#!/usr/bin/env python3
"""
Tests for shell script safety and Docker Compose health checks.

Following TDD principles:
1. RED: Verify shell scripts quote variables and validate paths
2. GREEN: Fix shellcheck warnings and Docker health checks
3. REFACTOR: Document safety patterns
"""

import gc
import re
from pathlib import Path

import pytest
import yaml

# Mark as unit test to ensure it runs in CI
pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="testshellscriptsafety")
class TestShellScriptSafety:
    """Test shell scripts for safety and proper quoting."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def scripts_dir(self, repo_root):
        """Get scripts directory using shared repo_root fixture (DRY pattern)."""
        return repo_root / "scripts"

    def test_check_pr_status_quotes_variables(self, scripts_dir):
        """
        Test that check-pr-status.sh properly quotes all variables.

        This test will initially FAIL because variables are unquoted.
        After fix, all variable expansions should be quoted to prevent word-splitting.
        """
        script_file = scripts_dir / "check-pr-status.sh"

        if not script_file.exists():
            pytest.skip("check-pr-status.sh not found")

        content = script_file.read_text()

        # Check for common unquoted variable patterns that should be quoted
        # Pattern: $(command ...) or $variable used without quotes in dangerous contexts
        dangerous_patterns = [
            (r"\$pr_number(?!\s*[\"'])", "pr_number should be quoted"),
            (r"\$pr_data(?!\s*[\"'])", "pr_data should be quoted"),
            (r"\$total_checks(?!\s*[\"'])", "total_checks should be quoted"),
            (r"gh pr view \$pr_number", "gh command args should use quoted variables"),
        ]

        issues = []
        for pattern, message in dangerous_patterns:
            if re.search(pattern, content):
                # Find line numbers
                for line_num, line in enumerate(content.split("\n"), 1):
                    if re.search(pattern, line):
                        issues.append(f"Line {line_num}: {message}\n  {line.strip()}")

        # After fix, these patterns should not be found
        assert len(issues) == 0, "Found unquoted variables:\n" + "\n".join(issues[:5])

    def test_build_infisical_wheels_rm_safety(self, scripts_dir):
        """
        Test that build-infisical-wheels.sh validates OUTPUT_DIR before rm -rf.

        This test will initially FAIL if path validation is missing.
        After fix, should validate OUTPUT_DIR is not empty or root before deletion.
        """
        script_file = scripts_dir / "build-infisical-wheels.sh"

        if not script_file.exists():
            pytest.skip("build-infisical-wheels.sh not found")

        content = script_file.read_text()

        # Find the rm -rf line
        rm_pattern = r'rm\s+-rf\s+["\']?\$OUTPUT_DIR'
        if not re.search(rm_pattern, content):
            pytest.skip("rm -rf $OUTPUT_DIR not found in script")

        # Check for validation before rm -rf
        # Should have checks like: [ -z "$OUTPUT_DIR" ] or [ "$OUTPUT_DIR" = "/" ]
        has_empty_check = re.search(r'\[\s+-z\s+"\$OUTPUT_DIR"\s+\]', content)
        has_root_check = re.search(r'\[\s+"\$OUTPUT_DIR"\s+=\s+"/"\s+\]', content)

        assert has_empty_check or has_root_check, (
            "build-infisical-wheels.sh should validate OUTPUT_DIR before rm -rf\n"
            'Expected validation: [ -z "$OUTPUT_DIR" ] || [ "$OUTPUT_DIR" = "/" ]'
        )


@pytest.mark.xdist_group(name="testdockercomposehealthchecks")
class TestDockerComposeHealthChecks:
    """Test Docker Compose health check configurations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def docker_compose_file(self, repo_root):
        """Get docker-compose.test.yml using shared repo_root fixture (DRY pattern)."""
        return repo_root / "docker-compose.test.yml"

    def test_keycloak_health_check_uses_native_command(self, docker_compose_file):
        """
        Test that Keycloak health check uses native kc.sh command instead of curl.

        This test will initially FAIL because curl is not available in Keycloak image.
        After fix, should use /opt/keycloak/bin/kc.sh show-health or similar.
        """
        compose_file = docker_compose_file

        if not compose_file.exists():
            pytest.skip("docker-compose.test.yml not found")

        with open(compose_file) as f:
            compose_config = yaml.safe_load(f)

        keycloak_service = compose_config.get("services", {}).get("keycloak-test")
        if not keycloak_service:
            pytest.skip("keycloak-test service not found")

        healthcheck = keycloak_service.get("healthcheck", {})
        test_cmd = healthcheck.get("test", [])

        # Health check should not use curl (not available in image)
        test_str = " ".join(test_cmd) if isinstance(test_cmd, list) else test_cmd

        assert "curl" not in test_str.lower(), (
            "Keycloak health check should not use curl (not in image)\n"
            "Use: /opt/keycloak/bin/kc.sh show-health or health endpoint"
        )

        # Should use native Keycloak command or built-in health endpoint
        assert "kc.sh" in test_str or "/health" in test_str, (
            "Keycloak health check should use native command or health endpoint"
        )

    def test_qdrant_health_check_uses_available_command(self, docker_compose_file):
        """
        Test that Qdrant health check uses TCP port check (not wget/curl/grpc_health_probe).

        Qdrant v1.15.1 image does not include wget, curl, or grpc_health_probe.
        Use TCP-based health check via /dev/tcp which requires no external tools.
        """
        compose_file = docker_compose_file

        if not compose_file.exists():
            pytest.skip("docker-compose.test.yml not found")

        with open(compose_file) as f:
            compose_config = yaml.safe_load(f)

        qdrant_service = compose_config.get("services", {}).get("qdrant-test")
        if not qdrant_service:
            pytest.skip("qdrant-test service not found")

        healthcheck = qdrant_service.get("healthcheck", {})
        test_cmd = healthcheck.get("test", [])

        # Health check should use TCP port check (no external dependencies needed)
        test_str = " ".join(test_cmd) if isinstance(test_cmd, list) else test_cmd

        # Should use TCP-based check (works without external binaries)
        assert "/dev/tcp" in test_str, (
            "Qdrant health check should use TCP port check via /dev/tcp\n"
            "Works with bash in Qdrant v1.15.1+ without external dependencies"
        )

    def test_all_health_checks_have_proper_intervals(self, docker_compose_file):
        """Test that all services have reasonable health check intervals."""
        compose_file = docker_compose_file

        if not compose_file.exists():
            pytest.skip("docker-compose.test.yml not found")

        with open(compose_file) as f:
            compose_config = yaml.safe_load(f)

        services_with_healthchecks = []
        for service_name, service_config in compose_config.get("services", {}).items():
            if "healthcheck" in service_config:
                healthcheck = service_config["healthcheck"]
                services_with_healthchecks.append(service_name)

                # Validate health check has required fields
                assert "test" in healthcheck, f"{service_name}: health check missing 'test'"
                assert "interval" in healthcheck, f"{service_name}: health check missing 'interval'"
                assert "timeout" in healthcheck, f"{service_name}: health check missing 'timeout'"

                # Intervals should be reasonable (not too frequent)
                interval_str = healthcheck.get("interval", "5s")
                timeout_str = healthcheck.get("timeout", "5s")

                # Parse seconds from strings like "5s", "30s"
                interval_seconds = int(interval_str.rstrip("s"))
                timeout_seconds = int(timeout_str.rstrip("s"))

                assert interval_seconds >= 3, f"{service_name}: interval too frequent (min 3s recommended)"
                assert timeout_seconds <= interval_seconds, f"{service_name}: timeout should be <= interval"

        # Should have at least some services with health checks
        assert len(services_with_healthchecks) > 0, "No services with health checks found"


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line("markers", "shell: tests for shell script safety")
    config.addinivalue_line("markers", "docker: tests for Docker Compose configuration")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
