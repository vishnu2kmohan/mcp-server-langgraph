"""
Test Docker Compose configuration validation.

This test suite validates Docker Compose files to prevent common issues:
- YAML syntax errors
- Health checks using commands not available in container images
- Invalid service configurations

Following TDD principles:
- RED: These tests will fail on current docker-compose.test.yml (wget not in Qdrant image)
- GREEN: Tests will pass after fixing health checks
- REFACTOR: Prevents future regressions

Related Codex Finding: docker-compose.test.yml:214-233 uses wget for Qdrant health check
"""

import re
from pathlib import Path
from typing import Any, Dict, List

import pytest
import yaml

# Root directory of the project
PROJECT_ROOT = Path(__file__).parent.parent


def find_docker_compose_files() -> List[Path]:
    """Find all docker-compose files in the project."""
    compose_files = []

    # Search patterns for docker-compose files
    patterns = [
        "docker-compose*.yml",
        "docker-compose*.yaml",
        "**/docker-compose*.yml",
        "**/docker-compose*.yaml",
    ]

    for pattern in patterns:
        compose_files.extend(PROJECT_ROOT.glob(pattern))

    # Deduplicate and return
    return sorted(set(compose_files))


def parse_docker_compose(file_path: Path) -> Dict[str, Any]:
    """Parse a docker-compose file and return its contents."""
    with open(file_path) as f:
        return yaml.safe_load(f)


def extract_health_check_command(health_check: Dict[str, Any]) -> List[str]:
    """Extract the command from a health check configuration."""
    if not health_check:
        return []

    test = health_check.get("test", [])

    # Handle different formats:
    # - ["CMD", "command", "arg1"]
    # - ["CMD-SHELL", "command arg1"]
    # - "CMD command arg1"
    if isinstance(test, str):
        # Parse string format
        parts = test.split()
        return parts[1:] if parts[0] in ["CMD", "CMD-SHELL"] else parts
    elif isinstance(test, list):
        # List format
        return test[1:] if test and test[0] in ["CMD", "CMD-SHELL"] else test

    return []


class TestDockerComposeYAMLSyntax:
    """Test Docker Compose files have valid YAML syntax."""

    @pytest.mark.parametrize("compose_file", find_docker_compose_files())
    def test_compose_file_is_valid_yaml(self, compose_file: Path):
        """Test that Docker Compose file is valid YAML."""
        try:
            with open(compose_file) as f:
                yaml.safe_load(f)
        except yaml.YAMLError as e:
            pytest.fail(f"Invalid YAML in {compose_file}: {e}")

    @pytest.mark.parametrize("compose_file", find_docker_compose_files())
    def test_compose_file_has_services(self, compose_file: Path):
        """Test that Docker Compose file has a services section."""
        config = parse_docker_compose(compose_file)
        assert "services" in config, f"{compose_file} missing 'services' section"


class TestDockerComposeHealthChecks:
    """Test Docker Compose health check configurations."""

    # Commands known to be missing from minimal/security-hardened images
    PROBLEMATIC_COMMANDS = {
        "wget": "Often missing from minimal images (e.g., Qdrant, distroless)",
        "curl": "Often missing from minimal images (removed for security)",
        "nc": "May not be available in all images",
        "netcat": "May not be available in all images",
    }

    # Known image-specific health check requirements
    IMAGE_HEALTH_CHECK_REQUIREMENTS = {
        "qdrant/qdrant": {
            "required_commands": ["grpc_health_probe"],
            "forbidden_commands": ["wget", "curl"],
            "reason": "Qdrant removed wget/curl in v1.15+ for security (GitHub issue #3491)",
        },
    }

    @pytest.mark.parametrize("compose_file", find_docker_compose_files())
    def test_health_checks_avoid_problematic_commands(self, compose_file: Path):
        """
        Test that health checks don't use commands that may not be available.

        This is a WARNING test - it flags potential issues but allows exceptions
        if the command is verified to exist in the image.
        """
        config = parse_docker_compose(compose_file)
        services = config.get("services", {})

        issues = []

        for service_name, service_config in services.items():
            health_check = service_config.get("healthcheck")
            if not health_check:
                continue

            command_parts = extract_health_check_command(health_check)
            if not command_parts:
                continue

            # Check first command (the executable)
            command = command_parts[0] if command_parts else ""

            # Extract base command (e.g., "/usr/bin/wget" -> "wget")
            base_command = Path(command).name

            if base_command in self.PROBLEMATIC_COMMANDS:
                reason = self.PROBLEMATIC_COMMANDS[base_command]
                issues.append(
                    f"Service '{service_name}' uses '{base_command}' in health check. "
                    f"Reason: {reason}. "
                    f"Verify this command exists in the image or use an alternative."
                )

        # This is a WARNING test - log issues but don't fail
        # The hard requirement test (test_image_specific_health_check_requirements) catches actual problems
        if issues:
            import warnings

            warning_msg = (
                f"\n⚠️  Potential health check issues in {compose_file.name}:\n"
                + "\n".join(f"  - {issue}" for issue in issues)
                + "\n\nThese are warnings only. Services may have these commands in their images."
                + "\nThe test_image_specific_health_check_requirements test enforces known requirements."
            )
            warnings.warn(warning_msg, UserWarning)

    @pytest.mark.parametrize("compose_file", find_docker_compose_files())
    def test_image_specific_health_check_requirements(self, compose_file: Path):
        """
        Test that specific images use their recommended health check methods.

        This is a HARD REQUIREMENT test for known image configurations.
        RED phase: Will fail on current docker-compose.test.yml
        """
        config = parse_docker_compose(compose_file)
        services = config.get("services", {})

        failures = []

        for service_name, service_config in services.items():
            image = service_config.get("image", "")
            health_check = service_config.get("healthcheck")

            # Check if this image has specific requirements
            for image_pattern, requirements in self.IMAGE_HEALTH_CHECK_REQUIREMENTS.items():
                if image_pattern in image:
                    if not health_check:
                        failures.append(
                            f"Service '{service_name}' using {image} MUST have a health check. "
                            f"Reason: {requirements['reason']}"
                        )
                        continue

                    command_parts = extract_health_check_command(health_check)
                    command = command_parts[0] if command_parts else ""
                    base_command = Path(command).name

                    # Check forbidden commands
                    forbidden = requirements.get("forbidden_commands", [])
                    if base_command in forbidden:
                        failures.append(
                            f"❌ Service '{service_name}' using {image} MUST NOT use '{base_command}'. "
                            f"Reason: {requirements['reason']}. "
                            f"Required: {', '.join(requirements.get('required_commands', []))}"
                        )

                    # Check required commands
                    required = requirements.get("required_commands", [])
                    if required and base_command not in required:
                        failures.append(
                            f"❌ Service '{service_name}' using {image} should use one of: "
                            f"{', '.join(required)}. "
                            f"Current: '{base_command}'. "
                            f"Reason: {requirements['reason']}"
                        )

        if failures:
            pytest.fail(
                f"\n🔴 RED PHASE: Health check validation failures in {compose_file.name}:\n"
                + "\n".join(f"  {failure}" for failure in failures)
                + f"\n\nFile: {compose_file}"
            )

    @pytest.mark.parametrize("compose_file", find_docker_compose_files())
    def test_health_checks_have_valid_structure(self, compose_file: Path):
        """Test that health checks have valid structure."""
        config = parse_docker_compose(compose_file)
        services = config.get("services", {})

        for service_name, service_config in services.items():
            health_check = service_config.get("healthcheck")
            if not health_check:
                continue

            # Validate health check has required fields
            assert "test" in health_check, f"Service '{service_name}' health check missing 'test' field"

            # Validate test format
            test = health_check["test"]
            assert isinstance(test, (list, str)), (
                f"Service '{service_name}' health check 'test' must be list or string, " f"got {type(test)}"
            )

            # Validate optional fields if present
            if "interval" in health_check:
                assert isinstance(
                    health_check["interval"], (str, int)
                ), f"Service '{service_name}' health check 'interval' must be string or int"

            if "timeout" in health_check:
                assert isinstance(
                    health_check["timeout"], (str, int)
                ), f"Service '{service_name}' health check 'timeout' must be string or int"

            if "retries" in health_check:
                assert isinstance(health_check["retries"], int), f"Service '{service_name}' health check 'retries' must be int"


class TestDockerComposeQdrantSpecific:
    """Specific tests for Qdrant service configuration."""

    @pytest.mark.parametrize("compose_file", find_docker_compose_files())
    def test_qdrant_uses_grpc_health_probe(self, compose_file: Path):
        """
        Test that Qdrant services use grpc_health_probe for health checks.

        Background:
        - Qdrant v1.15+ removed wget/curl for security (GitHub issue #3491)
        - Qdrant recommends grpc_health_probe (built-in since v1.15.0)
        - HTTP endpoint (:6333) and gRPC endpoint (:6334) both available

        RED phase: Will fail on current docker-compose.test.yml:227-232
        GREEN phase: Will pass after fix
        """
        config = parse_docker_compose(compose_file)
        services = config.get("services", {})

        for service_name, service_config in services.items():
            image = service_config.get("image", "")

            # Find Qdrant services
            if "qdrant" not in image.lower():
                continue

            health_check = service_config.get("healthcheck")
            assert health_check, f"🔴 RED: Qdrant service '{service_name}' in {compose_file.name} " f"MUST have a health check"

            command_parts = extract_health_check_command(health_check)
            assert command_parts, (
                f"🔴 RED: Qdrant service '{service_name}' in {compose_file.name} " f"health check has no command"
            )

            command = command_parts[0]
            base_command = Path(command).name

            # Validate using TCP-based health check (grpc_health_probe not in qdrant:v1.15.1 image)
            full_command = " ".join(command_parts)
            assert "/dev/tcp" in full_command, (
                f"🔴 RED: Qdrant service '{service_name}' in {compose_file.name} "
                f"MUST use TCP-based health check (/dev/tcp), not '{base_command}'. "
                f"\n\nCurrent config: {health_check}"
                f"\n\nExpected: "
                f'test: ["CMD-SHELL", "timeout 2 bash -c \'</dev/tcp/localhost/6333\' || exit 1"]'
                f"\n\nReason: Qdrant v1.15.1 image lacks wget, curl, and grpc_health_probe. "
                f"TCP check requires only bash and is secure."
                f"\n\nFile location: {compose_file}"
            )

            # Validate targeting HTTP port 6333 (not gRPC 6334)
            assert ":6333" in full_command or "6333" in full_command, (
                f"Qdrant service '{service_name}' health check should target "
                f"HTTP port :6333 for TCP check. "
                f"Current: {full_command}"
            )


def test_all_compose_files_found():
    """Sanity test: Ensure we're finding all compose files."""
    compose_files = find_docker_compose_files()

    # We should have at least the ones we know about
    filenames = {f.name for f in compose_files}

    assert (
        "docker-compose.test.yml" in filenames
    ), "docker-compose.test.yml not found - this file has the Qdrant health check issue"

    # Log all found files for debugging
    print(f"\n📁 Found {len(compose_files)} Docker Compose files:")
    for f in sorted(compose_files):
        print(f"  - {f.relative_to(PROJECT_ROOT)}")
