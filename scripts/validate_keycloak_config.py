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
from typing import Dict, List, Optional

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


def validate_keycloak_service_exists(config: Dict) -> Optional[str]:
    """Validate keycloak-test service exists in docker-compose."""
    if "services" not in config:
        return "No services defined in docker-compose.test.yml"

    if "keycloak-test" not in config["services"]:
        return "keycloak-test service not found in docker-compose.test.yml. Service must be uncommented for E2E auth testing."

    return None  # Success


def validate_health_check(keycloak_service: Dict) -> Optional[str]:
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


def validate_start_period(keycloak_service: Dict) -> Optional[str]:
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


def validate_environment_variables(keycloak_service: Dict) -> Optional[str]:
    """Validate Keycloak has required environment variables."""
    if "environment" not in keycloak_service:
        return "keycloak-test service must have environment variables"

    env_vars = keycloak_service["environment"]
    required_vars = [
        "KEYCLOAK_ADMIN",
        "KEYCLOAK_ADMIN_PASSWORD",
        "KC_DB",
        "KC_DB_URL",
        "KC_HEALTH_ENABLED",
    ]

    # Convert list of KEY=VALUE or dict to set of keys
    if isinstance(env_vars, list):
        env_keys = {var.split("=")[0] for var in env_vars}
    else:
        env_keys = set(env_vars.keys())

    missing_vars = [var for var in required_vars if var not in env_keys]

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
