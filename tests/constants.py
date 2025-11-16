"""
Centralized test constants for consistent configuration across all test environments.

This module provides a single source of truth for test configuration values that must
be synchronized across:
- Test fixtures (conftest.py)
- Docker Compose configurations (docker/docker-compose.test.yml)
- CI/CD workflows (.github/workflows/*.yaml)

OpenAI Codex Finding (2025-11-16):
==================================Integration tests failed due to JWT secret mismatch:
- conftest.py mock_jwt_token used "test-secret-key"
- docker-compose.test.yml used "test-secret-key-for-integration-tests"
- CI workflows used "test-secret-key-for-ci"
- Auth middleware validated with settings.jwt_secret_key from environment
- Token signing vs validation mismatch caused PermissionError in MCP tests

Root Cause:
-----------
The JWT secret used to SIGN tokens in test fixtures did not match the JWT secret
used to VERIFY tokens in the running server. This caused all integration tests
to fail with "Invalid authentication token" errors before they could even test
the intended functionality.

Solution:
---------
1. Define TEST_JWT_SECRET as single source of truth (this file)
2. Update mock_jwt_token fixture to import and use TEST_JWT_SECRET
3. Update docker-compose.test.yml to use TEST_JWT_SECRET value
4. Update CI/CD workflows to use TEST_JWT_SECRET value
5. Add validation test (test_constants.py) to prevent future mismatches

Benefits:
---------
- Single source of truth prevents configuration drift
- Tests validate consistency across all environments
- Pre-commit hooks enforce synchronization
- Clear documentation of test security configuration

Security Note:
--------------
This secret is FOR TESTING ONLY. Never use this value in production.
Production JWT secrets must be:
- Generated with cryptographically secure random number generator
- At least 32 characters (256 bits)
- Stored in secure secret management system (e.g., Infisical)
- Rotated regularly
- Never committed to version control
"""

# ==============================================================================
# JWT Authentication
# ==============================================================================

# JWT secret for test token signing and verification
# IMPORTANT: This MUST match the value in:
#   - docker/docker-compose.test.yml (JWT_SECRET_KEY environment variable)
#   - .github/workflows/*.yaml (JWT_SECRET_KEY environment variable)
#   - tests/conftest.py (mock_jwt_token fixture)
TEST_JWT_SECRET = "test-secret-key-for-integration-tests"

# JWT algorithm for test token encoding/decoding
# IMPORTANT: Must match settings.jwt_algorithm in core/config.py
TEST_JWT_ALGORITHM = "HS256"

# JWT token expiration time for tests (in hours)
# Short expiration to ensure tests don't accidentally use stale tokens
TEST_JWT_EXPIRATION_HOURS = 1


# ==============================================================================
# Test User Credentials
# ==============================================================================

# Default test user identifier
TEST_USER_ID = "alice"

# Default test user for authentication tests
TEST_USER_EMAIL = "alice@example.com"


# ==============================================================================
# Test Environment Configuration
# ==============================================================================

# Thread ID for LangGraph checkpointer tests
TEST_THREAD_ID = "test-thread-123"

# Run ID for distributed tracing tests
TEST_RUN_ID = "test-run-123"


# ==============================================================================
# Validation Functions
# ==============================================================================


def validate_jwt_secret() -> None:
    """
    Validate that TEST_JWT_SECRET meets minimum security requirements for testing.

    Raises:
        ValueError: If TEST_JWT_SECRET does not meet requirements
    """
    if len(TEST_JWT_SECRET) < 16:
        raise ValueError(f"TEST_JWT_SECRET must be at least 16 characters. " f"Current length: {len(TEST_JWT_SECRET)}")

    if "test" not in TEST_JWT_SECRET.lower():
        raise ValueError(
            f"TEST_JWT_SECRET should contain 'test' to clearly indicate it's for testing. "
            f"Current value: '{TEST_JWT_SECRET}'"
        )


# Run validation on import
validate_jwt_secret()
