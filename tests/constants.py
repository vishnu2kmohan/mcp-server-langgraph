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
#   - docker-compose.test.yml (JWT_SECRET_KEY environment variable)
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
# Service Ports (Test Environment)
# ==============================================================================
# Test ports use +1000 or +3000 offset to avoid conflicts with dev environment
# These MUST match docker-compose.test.yml port mappings

# Core Infrastructure Ports
TEST_POSTGRES_PORT = 9432  # +4000 from standard 5432
TEST_POSTGRES_HOST = "localhost"  # Docker-compose test network
TEST_POSTGRES_USER = "postgres"  # Test database user
TEST_POSTGRES_PASSWORD = "postgres"  # Test database password (not for production)
TEST_POSTGRES_DB = "mcp_test"  # Test database name
TEST_REDIS_PORT = 9379  # +3000 from standard 6379
TEST_QDRANT_PORT = 9333  # +3000 from standard 6333
TEST_OPENFGA_HTTP_PORT = 9080  # +1000 from standard 8080
TEST_OPENFGA_GRPC_PORT = 9081  # +1000 from standard 8081
TEST_KEYCLOAK_PORT = 9082  # +1002 from standard 8080

# Application Service Ports
TEST_MCP_SERVER_PORT = 8000  # Main MCP server
TEST_BUILDER_API_PORT = 9001  # +1000 from dev port 8001
TEST_PLAYGROUND_API_PORT = 9002  # +1000 from dev port 8002

# Observability Ports (Grafana LGTM Stack)
# Jaeger replaced by Tempo, Prometheus/Alertmanager replaced by Mimir + Alloy
TEST_TEMPO_PORT = 13200  # +10000 from standard 3200
TEST_LOKI_PORT = 13100  # +10000 from standard 3100
TEST_MIMIR_PORT = 19009  # +10000 from standard 9009
TEST_ALLOY_PORT = 12345  # Alloy UI/API (no offset, uses standard port)
TEST_GRAFANA_PORT = 13001  # +10000 from prod's 3001

# Legacy port aliases (deprecated, use new names above)
# These are kept for backwards compatibility with existing tests
TEST_JAEGER_UI_PORT = TEST_TEMPO_PORT  # Jaeger replaced by Tempo
TEST_PROMETHEUS_PORT = TEST_MIMIR_PORT  # Prometheus replaced by Mimir
TEST_ALERTMANAGER_PORT = TEST_MIMIR_PORT  # Alertmanager replaced by Grafana Unified Alerting

# Redis Database Indices (same Redis instance, different databases)
TEST_REDIS_CHECKPOINT_DB = 1  # LangGraph checkpoints
TEST_REDIS_SESSION_DB = 0  # Session storage
TEST_REDIS_PLAYGROUND_DB = 2  # Playground sessions


# ==============================================================================
# Playground Configuration
# ==============================================================================

# Maximum messages per playground session
TEST_MAX_MESSAGES_PER_SESSION = 50

# Session timeout in seconds
TEST_SESSION_TIMEOUT_SECONDS = 60


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
        raise ValueError(f"TEST_JWT_SECRET must be at least 16 characters. Current length: {len(TEST_JWT_SECRET)}")

    if "test" not in TEST_JWT_SECRET.lower():
        raise ValueError(
            f"TEST_JWT_SECRET should contain 'test' to clearly indicate it's for testing. Current value: '{TEST_JWT_SECRET}'"
        )


# Run validation on import
validate_jwt_secret()
