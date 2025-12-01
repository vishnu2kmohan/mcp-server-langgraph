#!/usr/bin/env python3
"""
Pre-commit Hook: Dependency Injection Configuration Validation

This hook validates that dependency injection is properly wired before allowing
commits. It catches the critical bugs that were identified by OpenAI Codex.

Validation Checks:
1. Keycloak admin credentials wired in dependencies.py
2. OpenFGA client validates config and returns Optional
3. Service principal manager accepts Optional[OpenFGAClient]
4. Cache service uses redis.from_url() with credentials

Exit Codes:
- 0: All checks passed
- 1: Validation failed, commit blocked
"""

import sys
from pathlib import Path


class DependencyValidationError(Exception):
    """Raised when dependency validation fails"""

    pass


def check_keycloak_admin_credentials_wired() -> list[str]:
    """
    Check that Keycloak admin credentials are passed to KeycloakConfig.

    Bug #1: dependencies.py must pass admin_username and admin_password.
    """
    errors = []
    dependencies_file = Path("src/mcp_server_langgraph/core/dependencies.py")

    if not dependencies_file.exists():
        return errors  # File might not exist in partial commits

    content = dependencies_file.read_text()

    # Check that KeycloakConfig initialization includes admin credentials
    if "KeycloakConfig(" in content:
        if "admin_username=" not in content:
            errors.append(
                "❌ CRITICAL: Keycloak admin_username not wired in dependencies.py\n"
                "   Fix: Add 'admin_username=settings.keycloak_admin_username' to KeycloakConfig()"
            )
        if "admin_password=" not in content:
            errors.append(
                "❌ CRITICAL: Keycloak admin_password not wired in dependencies.py\n"
                "   Fix: Add 'admin_password=settings.keycloak_admin_password' to KeycloakConfig()"
            )

    return errors


def check_openfga_returns_optional() -> list[str]:
    """
    Check that get_openfga_client returns Optional[OpenFGAClient].

    Bug #2: Function must return None when store_id/model_id are missing.
    """
    errors = []
    dependencies_file = Path("src/mcp_server_langgraph/core/dependencies.py")

    if not dependencies_file.exists():
        return errors

    content = dependencies_file.read_text()

    # Check function signature - accept both Optional[OpenFGAClient] and OpenFGAClient | None
    if "def get_openfga_client()" in content:
        if "Optional[OpenFGAClient]" not in content and "OpenFGAClient | None" not in content:
            errors.append(
                "❌ CRITICAL: get_openfga_client must return Optional[OpenFGAClient]\n"
                "   Fix: Change return type to 'Optional[OpenFGAClient]'"
            )

        # Check for validation logic
        if "store_id" in content and "model_id" in content:
            if "return None" not in content:
                errors.append(
                    "⚠️  WARNING: get_openfga_client should return None when config incomplete\n"
                    "   Recommendation: Add validation that returns None when store_id or model_id missing"
                )

    return errors


def check_service_principal_accepts_optional_openfga() -> list[str]:
    """
    Check that ServicePrincipalManager accepts Optional[OpenFGAClient].

    Bug #3: Manager must handle None OpenFGA client gracefully.
    """
    errors = []
    sp_file = Path("src/mcp_server_langgraph/auth/service_principal.py")

    if not sp_file.exists():
        return errors

    content = sp_file.read_text()

    # Check constructor signature - accept both Optional[OpenFGAClient] and OpenFGAClient | None
    if "def __init__" in content and "openfga_client" in content:
        if "Optional[OpenFGAClient]" not in content and "OpenFGAClient | None" not in content:
            errors.append(
                "❌ CRITICAL: ServicePrincipalManager.__init__ must accept Optional[OpenFGAClient]\n"
                "   Fix: Change parameter type to 'openfga_client: Optional[OpenFGAClient]'"
            )

        # Check for guards
        if "_sync_to_openfga" in content and "if self.openfga is None" not in content and "if not self.openfga" not in content:
            errors.append(
                "⚠️  WARNING: _sync_to_openfga should guard against None OpenFGA\n"
                "   Recommendation: Add 'if self.openfga is None: return' at start of method"
            )

    return errors


def check_cache_uses_redis_from_url() -> list[str]:
    """
    Check that CacheService uses redis.from_url() with credentials.

    Bug #4: Cache must use from_url() pattern, not Redis(host=..., port=...).
    """
    errors = []
    cache_file = Path("src/mcp_server_langgraph/core/cache.py")

    if not cache_file.exists():
        return errors

    content = cache_file.read_text()

    # Check CacheService.__init__ signature
    if "class CacheService" in content and "def __init__" in content:
        if "redis_password" not in content or "redis_ssl" not in content:
            errors.append(
                "❌ CRITICAL: CacheService.__init__ must accept redis_password and redis_ssl\n"
                "   Fix: Add 'redis_password: Optional[str]' and 'redis_ssl: bool' parameters"
            )

        # Check for from_url pattern
        if "redis.from_url" not in content and "redis.Redis(" in content:
            errors.append(
                "⚠️  WARNING: CacheService should use redis.from_url() not redis.Redis()\n"
                "   Recommendation: Use 'redis.from_url(url, password=..., ssl=...)' pattern"
            )

    return errors


def check_tests_exist() -> list[str]:
    """
    Check that dependency wiring tests exist.

    Bug #5: Missing test coverage allowed bugs to reach production.
    """
    errors = []

    required_tests = [
        ("tests/integration/test_dependencies_wiring.py", "Dependency wiring tests"),
        ("tests/integration/test_cache_redis_config.py", "Cache Redis configuration tests"),
        ("tests/integration/test_app_startup_validation.py", "App startup validation tests"),
        ("tests/smoke/test_ci_startup_smoke.py", "CI smoke tests"),
    ]

    for test_file, description in required_tests:
        if not Path(test_file).exists():
            errors.append(f"⚠️  WARNING: Missing {description}\n   Expected: {test_file}")

    return errors


def main() -> int:
    """
    Run all dependency validation checks.

    Returns:
        0 if all checks pass
        1 if any check fails
    """
    print("🔍 Validating dependency injection configuration...")
    print()

    all_errors = []

    # Run all checks
    checks = [
        ("Keycloak admin credentials", check_keycloak_admin_credentials_wired),
        ("OpenFGA optional return", check_openfga_returns_optional),
        ("Service principal OpenFGA guards", check_service_principal_accepts_optional_openfga),
        ("Cache Redis configuration", check_cache_uses_redis_from_url),
        ("Test coverage", check_tests_exist),
    ]

    for check_name, check_func in checks:
        errors = check_func()
        if errors:
            all_errors.extend(errors)
            print(f"❌ {check_name}: FAILED")
            for error in errors:
                print(f"   {error}")
        else:
            print(f"✅ {check_name}: PASSED")

    print()

    if all_errors:
        print("=" * 80)
        print("DEPENDENCY VALIDATION FAILED")
        print("=" * 80)
        print()
        print("Critical dependency injection bugs detected!")
        print("Please fix the issues above before committing.")
        print()
        print("These checks prevent production outages from:")
        print("  1. Missing Keycloak admin credentials")
        print("  2. OpenFGA client with None store_id")
        print("  3. Service principal crashes when OpenFGA disabled")
        print("  4. L2 cache ignoring secure Redis settings")
        print("  5. Missing test coverage")
        print()
        print("See ADR-0042 for details on these critical bugs.")
        print()
        return 1
    print("=" * 80)
    print("✅ ALL DEPENDENCY VALIDATION CHECKS PASSED")
    print("=" * 80)
    return 0


if __name__ == "__main__":
    sys.exit(main())
