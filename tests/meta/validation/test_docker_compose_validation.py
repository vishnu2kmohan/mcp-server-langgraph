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

import gc
from pathlib import Path
from typing import Any

import pytest
import yaml

# Mark as unit test to ensure it runs in CI
pytestmark = [pytest.mark.unit, pytest.mark.validation]


def get_repo_root() -> Path:
    """Find repository root with marker validation."""
    current = Path(__file__).parent
    markers = [".git", "pyproject.toml"]
    while current != current.parent:
        if any((current / m).exists() for m in markers):
            return current
        current = current.parent
    raise RuntimeError("Cannot find repo root")


# Root directory of the project
PROJECT_ROOT = get_repo_root()


def find_docker_compose_files() -> list[Path]:
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


def parse_docker_compose(file_path: Path) -> dict[str, Any]:
    """Parse a docker-compose file and return its contents."""
    with open(file_path) as f:
        return yaml.safe_load(f)


def extract_health_check_command(health_check: dict[str, Any]) -> list[str]:
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
        if parts and parts[0] in ["CMD", "CMD-SHELL"]:
            # For CMD-SHELL, split the shell command string into tokens
            return " ".join(parts[1:]).split()
        return parts
    elif isinstance(test, list):
        # List format
        if test and test[0] in ["CMD", "CMD-SHELL"]:
            # For CMD-SHELL with list format, parse the shell command string
            if len(test) > 1:
                return test[1].split()
            return test[1:]
        return test

    return []


@pytest.mark.xdist_group(name="testdockercomposeyamlsyntax")
class TestDockerComposeYAMLSyntax:
    """Test Docker Compose files have valid YAML syntax."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

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


@pytest.mark.xdist_group(name="testdockercomposehealthchecks")
class TestDockerComposeHealthChecks:
    """Test Docker Compose health check configurations."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

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
            "required_commands": ["bash", "timeout"],  # TCP check via /dev/tcp or timeout commands
            "forbidden_commands": ["wget", "curl"],
            "reason": "Qdrant removed wget/curl in v1.15+ for security (GitHub issue #3491). "
            "Use TCP checks (bash -c '</dev/tcp/localhost/6333') or HTTP /healthz if available. "
            "Note: grpc_health_probe won't work - Qdrant uses non-standard gRPC health protocol (issue #2614)",
        },
    }

    # Commands known to be available in specific images or services
    # These are exceptions to the PROBLEMATIC_COMMANDS warning
    ALLOWED_COMMANDS = {
        # Image pattern -> allowed commands
        "openfga/openfga": ["wget"],
        "keycloak/keycloak": ["curl"],
        "jaegertracing/all-in-one": ["wget", "nc"],
        "prom/prometheus": ["wget"],
        "prom/alertmanager": ["wget"],
        "grafana/grafana": ["wget"],
        # Service name -> allowed commands (for local builds or alias)
        "agent": ["wget"],
        "mcp-server-test": ["curl"],
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

            # Check if command is allowed for this specific service/image
            image = service_config.get("image", "")
            allowed_for_service = []

            # Check by service name
            if service_name in self.ALLOWED_COMMANDS:
                allowed_for_service.extend(self.ALLOWED_COMMANDS[service_name])

            # Check by image name
            for image_pattern, allowed_cmds in self.ALLOWED_COMMANDS.items():
                if image_pattern in image:
                    allowed_for_service.extend(allowed_cmds)

            if base_command in allowed_for_service:
                continue

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

            # Skip services with disabled healthchecks (e.g., distroless images like Mimir)
            if health_check.get("disable"):
                continue

            # Validate health check has required fields
            assert "test" in health_check, f"Service '{service_name}' health check missing 'test' field"

            # Validate test format
            test = health_check["test"]
            assert isinstance(test, (list, str)), (
                f"Service '{service_name}' health check 'test' must be list or string, got {type(test)}"
            )

            # Validate optional fields if present
            if "interval" in health_check:
                assert isinstance(health_check["interval"], (str, int)), (
                    f"Service '{service_name}' health check 'interval' must be string or int"
                )

            if "timeout" in health_check:
                assert isinstance(health_check["timeout"], (str, int)), (
                    f"Service '{service_name}' health check 'timeout' must be string or int"
                )

            if "retries" in health_check:
                assert isinstance(health_check["retries"], int), f"Service '{service_name}' health check 'retries' must be int"


@pytest.mark.xdist_group(name="testdockercomposeqdrantspecific")
class TestDockerComposeQdrantSpecific:
    """Specific tests for Qdrant service configuration."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.mark.parametrize("compose_file", find_docker_compose_files())
    def test_qdrant_uses_valid_health_check(self, compose_file: Path):
        """
        Test that Qdrant services use valid health check methods.

        Background (based on official Qdrant documentation):
        - Qdrant v1.15+ removed wget/curl for security (GitHub issue #3491)
        - grpc_health_probe is NOT included in Qdrant images (never was)
        - Official recommended endpoints: /healthz, /livez, /readyz (bypass auth)
        - HTTP endpoint :6333 and gRPC endpoint :6334 both available

        Valid health check methods:
        1. TCP check: /dev/tcp/localhost/6333 (works with minimal image, no HTTP client needed)
        2. HTTP check: curl/wget to /healthz, /livez, /readyz, or / (requires external HTTP client)
        3. Kubernetes httpGet probe (for K8s manifests, not tested here)

        Invalid methods:
        - wget/curl inside container (not in v1.15.1+ image)
        - grpc_health_probe (not in image, requires k8s 1.24+)

        References:
        - Qdrant Monitoring Guide: https://qdrant.tech/documentation/guides/monitoring/
        - GitHub #3491: curl not added to image (security)
        - GitHub #4250: Healthcheck command discussion
        """
        config = parse_docker_compose(compose_file)
        services = config.get("services", {})

        for service_name, service_config in services.items():
            image = service_config.get("image", "")

            # Find Qdrant services
            if "qdrant" not in image.lower():
                continue

            health_check = service_config.get("healthcheck")
            assert health_check, f"🔴 RED: Qdrant service '{service_name}' in {compose_file.name} MUST have a health check"

            # Get the raw test command (list or string)
            test_command = health_check.get("test", [])
            assert test_command, (
                f"🔴 RED: Qdrant service '{service_name}' in {compose_file.name} health check has no test command"
            )

            # Convert to string for pattern matching (works for both list and string formats)
            if isinstance(test_command, list):
                full_command = " ".join(str(part) for part in test_command)
            else:
                full_command = str(test_command)

            # Validate using one of the supported methods
            has_tcp_check = "/dev/tcp" in full_command
            has_http_check = any(
                endpoint in full_command
                for endpoint in ["/healthz", "/livez", "/readyz", "localhost:6333/", "127.0.0.1:6333/"]
            )

            assert has_tcp_check or has_http_check, (
                f"🔴 RED: Qdrant service '{service_name}' in {compose_file.name} "
                f"must use EITHER TCP check (/dev/tcp) OR HTTP check (/healthz, /livez, /readyz). "
                f"\n\nCurrent config: {health_check}"
                f"\n\nCurrent command: {full_command}"
                f"\n\nValid examples:"
                f'\n1. TCP check: ["CMD-SHELL", "timeout 2 bash -c \'</dev/tcp/localhost/6333\' || exit 1"]'
                f'\n2. TCP check: ["CMD", "/bin/bash", "-c", "(echo > /dev/tcp/localhost/6333) >/dev/null 2>&1"]'
                f'\n3. HTTP check (external): ["CMD", "curl", "-f", "http://localhost:6333/healthz"]'
                f"\n\nNote: wget/curl are NOT available inside Qdrant v1.15.1+ images."
                f"\nHTTP checks require external HTTP client or host-based healthcheck."
                f"\n\nFile location: {compose_file}"
            )

            # If using wget/curl inside container, fail (not available in image)
            if "wget " in full_command or "curl " in full_command:
                # Check if it's actually inside the container or external
                if "CMD-SHELL" in full_command or ("CMD" in full_command and "/bin/bash" not in full_command):
                    raise AssertionError(
                        f"🔴 RED: Qdrant service '{service_name}' in {compose_file.name} "
                        f"uses wget/curl which is NOT available in Qdrant v1.15.1+ images. "
                        f"\n\nCurrent: {full_command}"
                        f"\n\nUse TCP check instead: "
                        f'["CMD-SHELL", "timeout 2 bash -c \'</dev/tcp/localhost/6333\' || exit 1"]'
                        f"\n\nReference: GitHub issue #3491 (security hardening)"
                    )

            # Validate targeting HTTP port 6333 (not gRPC 6334)
            assert ":6333" in full_command or "6333" in full_command, (
                f"Qdrant service '{service_name}' health check should target "
                f"HTTP port :6333 for TCP/HTTP check. "
                f"Current: {full_command}"
            )


def test_all_compose_files_found():
    """Sanity test: Ensure we're finding all compose files."""
    compose_files = find_docker_compose_files()

    # We should have at least the ones we know about
    filenames = {f.name for f in compose_files}

    assert "docker-compose.test.yml" in filenames, (
        "docker-compose.test.yml not found - this file has the Qdrant health check issue"
    )

    # Log all found files for debugging
    print(f"\n📁 Found {len(compose_files)} Docker Compose files:")
    for f in sorted(compose_files):
        print(f"  - {f.relative_to(PROJECT_ROOT)}")
