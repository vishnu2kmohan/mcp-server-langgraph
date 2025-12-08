#!/usr/bin/env python3
"""
Pre-commit hook: validate-keycloak-config

Validates Keycloak service configuration in docker-compose.test.yml.

This script ensures:
1. keycloak-test service exists and is uncommented
2. Health check configuration is present
3. Required environment variables are configured
4. start_period is adequate (60s for Keycloak initialization)

Prevents regression of Codex Finding #2: Keycloak service unavailable

Exit codes:
    0: Validation passed
    1: Validation failed with error message to stderr

References:
    - ADR-0053: Codex Integration Test Findings
    - tests/meta/test_precommit_keycloak_validation.py
"""

import sys
from pathlib import Path

import yaml


def parse_start_period(start_period_str: str) -> int:
    """
    Parse Docker start_period string to seconds.

    Examples:
        "60s" -> 60
        "1m" -> 60
        "90s" -> 90
    """
    if start_period_str.endswith("s"):
        return int(start_period_str[:-1])
    elif start_period_str.endswith("m"):
        return int(start_period_str[:-1]) * 60
    else:
        # Assume seconds if no unit
        return int(start_period_str)


def validate_keycloak_service_exists(config: dict) -> str | None:
    """Validate keycloak-test service exists in docker-compose."""
    if "services" not in config:
        return "No services defined in docker-compose.test.yml"

    if "keycloak-test" not in config["services"]:
        return "keycloak-test service not found in docker-compose.test.yml. Service must be uncommented for E2E auth testing."

    return None  # Success


def validate_health_check(keycloak_service: dict) -> str | None:
    """Validate Keycloak service has proper health check configuration."""
    if "healthcheck" not in keycloak_service:
        return "keycloak-test service must have healthcheck configuration"

    healthcheck = keycloak_service["healthcheck"]

    if "test" not in healthcheck:
        return "Health check must define test command"

    if "interval" not in healthcheck:
        return "Health check must define interval"

    if "start_period" not in healthcheck:
        return "Health check must define start_period"

    return None  # Success


def validate_start_period(keycloak_service: dict) -> str | None:
    """Validate Keycloak has adequate start_period (60s minimum)."""
    healthcheck = keycloak_service.get("healthcheck", {})
    start_period = healthcheck.get("start_period")

    if not start_period:
        return "Health check missing start_period"

    try:
        start_period_seconds = parse_start_period(start_period)
        if start_period_seconds < 60:
            return f"start_period too short ({start_period}). Keycloak requires at least 60s to initialize."
    except (ValueError, IndexError):
        return f"Invalid start_period format: {start_period}"

    return None  # Success


def is_optimized_keycloak_build(keycloak_service: dict) -> bool:
    """
    Check if Keycloak uses an optimized pre-built image.

    Optimized builds (using docker/Dockerfile.keycloak) have KC_DB, KC_HEALTH_ENABLED,
    and KC_METRICS_ENABLED baked in at build time, so they don't need to be set as
    runtime environment variables.

    Returns:
        True if using optimized build, False otherwise
    """
    build_config = keycloak_service.get("build", {})
    if isinstance(build_config, str):
        # Simple string format: build: ./path
        return "keycloak" in build_config.lower()
    elif isinstance(build_config, dict):
        # Dict format: build: {context: ., dockerfile: docker/Dockerfile.keycloak}
        dockerfile = build_config.get("dockerfile", "")
        return "keycloak" in dockerfile.lower()
    return False


def validate_environment_variables(keycloak_service: dict) -> str | None:
    """
    Validate Keycloak has required environment variables.

    Accepts both old (KEYCLOAK_ADMIN*) and new (KC_BOOTSTRAP_ADMIN*) variable names
    for Keycloak 26.4+ compatibility.

    For optimized builds (using docker/Dockerfile.keycloak), KC_DB and KC_HEALTH_ENABLED
    are baked into the image at build time and don't need runtime environment variables.
    """
    if "environment" not in keycloak_service:
        return "keycloak-test service must have environment variables"

    env_vars = keycloak_service["environment"]

    # Convert list of KEY=VALUE or dict to set of keys
    if isinstance(env_vars, list):
        env_keys = {var.split("=")[0] for var in env_vars}
    else:
        env_keys = set(env_vars.keys())

    # Check for admin credentials (old or new format)
    has_admin_user = "KEYCLOAK_ADMIN" in env_keys or "KC_BOOTSTRAP_ADMIN_USERNAME" in env_keys
    has_admin_pass = "KEYCLOAK_ADMIN_PASSWORD" in env_keys or "KC_BOOTSTRAP_ADMIN_PASSWORD" in env_keys

    if not has_admin_user:
        return "keycloak-test service missing admin username (KEYCLOAK_ADMIN or KC_BOOTSTRAP_ADMIN_USERNAME)"

    if not has_admin_pass:
        return "keycloak-test service missing admin password (KEYCLOAK_ADMIN_PASSWORD or KC_BOOTSTRAP_ADMIN_PASSWORD)"

    # Check for other required variables
    # For optimized builds, KC_DB and KC_HEALTH_ENABLED are baked into the image
    if is_optimized_keycloak_build(keycloak_service):
        # Only require KC_DB_URL for optimized builds (runtime DB connection)
        other_required_vars = ["KC_DB_URL"]
    else:
        # Standard Keycloak image requires all runtime config
        other_required_vars = ["KC_DB", "KC_DB_URL", "KC_HEALTH_ENABLED"]

    missing_vars = [var for var in other_required_vars if var not in env_keys]

    if missing_vars:
        return f"keycloak-test service missing required environment variables: {', '.join(missing_vars)}"

    return None  # Success


def validate_keycloak_config(compose_file_path: str) -> int:
    """
    Main validation function.

    Returns:
        0 if validation passes
        1 if validation fails
    """
    compose_path = Path(compose_file_path)

    if not compose_path.exists():
        print(f"ERROR: File not found: {compose_file_path}", file=sys.stderr)
        return 1

    try:
        with open(compose_path) as f:
            compose_config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"ERROR: Failed to parse YAML: {e}", file=sys.stderr)
        return 1

    # Validation 1: Service exists
    error = validate_keycloak_service_exists(compose_config)
    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    keycloak_service = compose_config["services"]["keycloak-test"]

    # Validation 2: Health check exists
    error = validate_health_check(keycloak_service)
    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # Validation 3: Adequate start_period
    error = validate_start_period(keycloak_service)
    if error:
        print(f"WARNING: {error}", file=sys.stderr)
        return 1

    # Validation 4: Required environment variables
    error = validate_environment_variables(keycloak_service)
    if error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    # All validations passed
    print("✅ Keycloak configuration validation passed", file=sys.stdout)
    return 0


def main():
    """CLI entry point."""
    if len(sys.argv) < 2:
        print("Usage: python scripts/validate_keycloak_config.py <docker-compose-file>", file=sys.stderr)
        sys.exit(1)

    compose_file = sys.argv[1]
    exit_code = validate_keycloak_config(compose_file)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
