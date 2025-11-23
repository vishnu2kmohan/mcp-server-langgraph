# Test Constants Pattern

**Last Updated**: 2025-11-23
**Purpose**: Prevent configuration drift across test environments
**Critical**: Fixes Codex Finding - JWT secret mismatch (2025-11-16)

---

## Quick Reference

### Always Use Centralized Constants

```python
# ✅ CORRECT - Import from tests/constants.py
from tests.constants import (
    TEST_JWT_SECRET,
    TEST_JWT_ALGORITHM,
    TEST_USER_ID,
    TEST_THREAD_ID,
)

# ❌ WRONG - Hardcoded values
secret = "test-secret-key"  # Risk of mismatch!
user_id = "alice"            # Inconsistent across tests
```

### Quick Import

```python
from tests.constants import (
    TEST_JWT_SECRET,          # JWT secret for token signing/verification
    TEST_JWT_ALGORITHM,       # HS256
    TEST_JWT_EXPIRATION_HOURS,  # 1 hour
    TEST_USER_ID,             # "alice"
    TEST_USER_EMAIL,          # "alice@example.com"
    TEST_THREAD_ID,           # "test-thread-123"
    TEST_RUN_ID,              # "test-run-123"
)
```

---

## The Problem: Configuration Drift

### OpenAI Codex Finding (2025-11-16)

**Issue**: Integration tests failed due to JWT secret mismatch across three configuration files

**Symptom**:
```
PermissionError: Invalid authentication token
```

**Root Cause**:
- `conftest.py` mock_jwt_token fixture: `"test-secret-key"`
- `docker-compose.test.yml` JWT_SECRET_KEY: `"test-secret-key-for-integration-tests"`
- `.github/workflows/*.yaml` JWT_SECRET_KEY: `"test-secret-key-for-ci"`

**Result**: Token signing secret ≠ verification secret → All integration tests failed

**Impact**:
- 50+ integration tests failing
- Confusing error messages (auth error, not test logic error)
- Wasted debugging time (appeared to be auth bug, not configuration issue)
- CI/CD unreliable

---

## The Solution: Single Source of Truth

### Centralized Constants File

**Location**: `tests/constants.py`

**Purpose**:
- Single source of truth for all test configuration values
- Synchronized across test fixtures, Docker Compose, and CI/CD
- Validated on import to catch errors early
- Documented with clear usage guidelines

**Structure**:
```python
# tests/constants.py

# ==============================================================================
# JWT Authentication
# ==============================================================================

TEST_JWT_SECRET = "test-secret-key-for-integration-tests"
TEST_JWT_ALGORITHM = "HS256"
TEST_JWT_EXPIRATION_HOURS = 1

# ==============================================================================
# Test User Credentials
# ==============================================================================

TEST_USER_ID = "alice"
TEST_USER_EMAIL = "alice@example.com"

# ==============================================================================
# Test Environment Configuration
# ==============================================================================

TEST_THREAD_ID = "test-thread-123"
TEST_RUN_ID = "test-run-123"

# ==============================================================================
# Validation Functions
# ==============================================================================

def validate_jwt_secret() -> None:
    """Validate TEST_JWT_SECRET meets minimum requirements"""
    if len(TEST_JWT_SECRET) < 16:
        raise ValueError("TEST_JWT_SECRET must be at least 16 characters")

    if "test" not in TEST_JWT_SECRET.lower():
        raise ValueError("TEST_JWT_SECRET should contain 'test' for safety")

# Run validation on import
validate_jwt_secret()
```

---

## Usage Patterns

### Pattern 1: Test Fixtures

**File**: `tests/conftest.py`

```python
from tests.constants import TEST_JWT_SECRET, TEST_JWT_ALGORITHM

@pytest.fixture
def mock_jwt_token(mock_auth_settings):
    """Generate valid JWT token for testing"""
    from jose import jwt
    import datetime

    payload = {
        "sub": "test-user",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
        "iat": datetime.datetime.utcnow(),
    }

    # ✅ CORRECT - Use centralized constant
    token = jwt.encode(payload, TEST_JWT_SECRET, algorithm=TEST_JWT_ALGORITHM)
    return token
```

**Why**: Ensures fixture generates tokens with same secret server uses for verification

---

### Pattern 2: Docker Compose Configuration

**File**: `docker/docker-compose.test.yml`

```yaml
services:
  mcp-server:
    environment:
      # ✅ CORRECT - Must match tests/constants.py::TEST_JWT_SECRET
      JWT_SECRET_KEY: "test-secret-key-for-integration-tests"
      JWT_ALGORITHM: "HS256"
```

**Validation**: Pre-commit hook checks synchronization:
```bash
# scripts/validation/validate-test-constants.py
def validate_docker_compose():
    """Ensure docker-compose.test.yml uses TEST_JWT_SECRET"""
    from tests.constants import TEST_JWT_SECRET

    with open("docker/docker-compose.test.yml") as f:
        content = f.read()

    if TEST_JWT_SECRET not in content:
        raise ValueError(
            f"docker-compose.test.yml JWT_SECRET_KEY does not match "
            f"tests/constants.py::TEST_JWT_SECRET ({TEST_JWT_SECRET})"
        )
```

---

### Pattern 3: CI/CD Workflows

**File**: `.github/workflows/ci.yaml`

```yaml
jobs:
  integration-tests:
    env:
      # ✅ CORRECT - Must match tests/constants.py::TEST_JWT_SECRET
      JWT_SECRET_KEY: "test-secret-key-for-integration-tests"
      JWT_ALGORITHM: "HS256"
    steps:
      - name: Run Integration Tests
        run: make test-integration
```

**Validation**: Pre-commit hook checks synchronization:
```bash
# scripts/validation/validate-test-constants.py
def validate_ci_workflows():
    """Ensure CI workflows use TEST_JWT_SECRET"""
    from tests.constants import TEST_JWT_SECRET

    for workflow in glob.glob(".github/workflows/*.yaml"):
        with open(workflow) as f:
            content = f.read()

        if "JWT_SECRET_KEY" in content and TEST_JWT_SECRET not in content:
            raise ValueError(
                f"{workflow} JWT_SECRET_KEY does not match "
                f"tests/constants.py::TEST_JWT_SECRET"
            )
```

---

### Pattern 4: Test Code

**File**: `tests/integration/test_auth.py`

```python
from tests.constants import (
    TEST_JWT_SECRET,
    TEST_JWT_ALGORITHM,
    TEST_USER_ID,
    TEST_USER_EMAIL,
)

@pytest.mark.integration
async def test_jwt_token_validation():
    """Test that server validates JWT tokens correctly"""
    from jose import jwt
    import datetime

    # Generate token with TEST_JWT_SECRET
    payload = {
        "sub": TEST_USER_ID,
        "email": TEST_USER_EMAIL,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
    }

    token = jwt.encode(payload, TEST_JWT_SECRET, algorithm=TEST_JWT_ALGORITHM)

    # Server should accept token (same secret)
    response = await client.get(
        "/api/protected",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
```

**Why**: Ensures test token generation uses same secret as server validation

---

### Pattern 5: LangGraph Thread IDs

**File**: `tests/integration/test_langgraph_checkpointer.py`

```python
from tests.constants import TEST_THREAD_ID

@pytest.mark.integration
async def test_redis_checkpointer():
    """Test LangGraph Redis checkpointer with consistent thread ID"""
    from langgraph.checkpoint.redis import RedisSaver

    checkpointer = RedisSaver(redis_client)

    # ✅ CORRECT - Use centralized thread ID
    config = {"configurable": {"thread_id": TEST_THREAD_ID}}

    state = await checkpointer.aget(config)
    # ...
```

**Why**: Consistent thread IDs across tests prevent checkpoint conflicts

---

## Available Constants

### JWT Authentication

| Constant | Value | Purpose |
|----------|-------|---------|
| `TEST_JWT_SECRET` | `"test-secret-key-for-integration-tests"` | JWT signing and verification secret |
| `TEST_JWT_ALGORITHM` | `"HS256"` | JWT encoding algorithm |
| `TEST_JWT_EXPIRATION_HOURS` | `1` | Token expiration time |

**Must match**:
- `docker-compose.test.yml` → `JWT_SECRET_KEY`
- `.github/workflows/*.yaml` → `JWT_SECRET_KEY`
- `tests/conftest.py` → `mock_jwt_token` fixture

---

### Test User Credentials

| Constant | Value | Purpose |
|----------|-------|---------|
| `TEST_USER_ID` | `"alice"` | Default test user identifier |
| `TEST_USER_EMAIL` | `"alice@example.com"` | Default test user email |

**Used in**:
- User provider fixtures
- Authentication tests
- Authorization tests
- Session management tests

---

### Test Environment Configuration

| Constant | Value | Purpose |
|----------|-------|---------|
| `TEST_THREAD_ID` | `"test-thread-123"` | LangGraph checkpointer thread ID |
| `TEST_RUN_ID` | `"test-run-123"` | Distributed tracing run ID |

**Used in**:
- LangGraph Redis checkpointer tests
- OpenTelemetry tracing tests
- Multi-step conversation tests

---

## Validation & Enforcement

### Import-Time Validation

**Automatic validation** when `tests/constants.py` is imported:

```python
# tests/constants.py

def validate_jwt_secret() -> None:
    """Validate TEST_JWT_SECRET meets minimum requirements"""
    # Check length (minimum 16 characters)
    if len(TEST_JWT_SECRET) < 16:
        raise ValueError(
            f"TEST_JWT_SECRET must be at least 16 characters. "
            f"Current length: {len(TEST_JWT_SECRET)}"
        )

    # Check contains 'test' (safety check)
    if "test" not in TEST_JWT_SECRET.lower():
        raise ValueError(
            f"TEST_JWT_SECRET should contain 'test' to clearly indicate "
            f"it's for testing. Current value: '{TEST_JWT_SECRET}'"
        )

# Run on import
validate_jwt_secret()
```

**Benefit**: Catches invalid constants before any tests run

---

### Pre-commit Hook Validation

**Hook**: `validate-test-constants` (in `.pre-commit-config.yaml`)

```yaml
- repo: local
  hooks:
    - id: validate-test-constants
      name: Validate Test Constants Synchronization
      entry: uv run python scripts/validation/validate-test-constants.py
      language: system
      pass_filenames: false
```

**Checks**:
1. `docker-compose.test.yml` uses `TEST_JWT_SECRET`
2. `.github/workflows/*.yaml` use `TEST_JWT_SECRET`
3. No hardcoded test secrets in test files
4. All references to test constants import from `tests/constants.py`

**To run manually**:
```bash
python scripts/validation/validate-test-constants.py
```

---

### Meta-Test Validation

**File**: `tests/meta/test_constants.py`

```python
import pytest
from tests.constants import (
    TEST_JWT_SECRET,
    TEST_JWT_ALGORITHM,
    TEST_USER_ID,
)

@pytest.mark.meta
def test_jwt_secret_requirements():
    """Verify TEST_JWT_SECRET meets security requirements"""
    # Minimum length
    assert len(TEST_JWT_SECRET) >= 16, "JWT secret too short"

    # Contains 'test' indicator
    assert "test" in TEST_JWT_SECRET.lower(), "JWT secret should indicate testing"

    # Not a common default
    assert TEST_JWT_SECRET != "secret", "JWT secret too generic"
    assert TEST_JWT_SECRET != "test-secret", "JWT secret too simple"


@pytest.mark.meta
def test_constants_synchronized():
    """Verify constants are synchronized across configurations"""
    import yaml

    # Check docker-compose.test.yml
    with open("docker/docker-compose.test.yml") as f:
        docker_config = yaml.safe_load(f)

    jwt_secret = docker_config["services"]["mcp-server"]["environment"]["JWT_SECRET_KEY"]
    assert jwt_secret == TEST_JWT_SECRET, "Docker Compose JWT secret mismatch"

    # Check CI workflows
    # (implementation depends on workflow structure)
```

**Runs**: Automatically in CI/CD and pre-push hooks

---

## Adding New Constants

### Step 1: Add to `tests/constants.py`

```python
# tests/constants.py

# ==============================================================================
# Redis Configuration
# ==============================================================================

# Redis host for integration tests
TEST_REDIS_HOST = "localhost"

# Redis port for integration tests
TEST_REDIS_PORT = 6379

# Redis database number for tests (separate from dev db 0)
TEST_REDIS_DB = 1
```

---

### Step 2: Update Validation

```python
# tests/constants.py

def validate_redis_config() -> None:
    """Validate Redis configuration for tests"""
    if not (1024 <= TEST_REDIS_PORT <= 65535):
        raise ValueError(f"Invalid Redis port: {TEST_REDIS_PORT}")

    if not (0 <= TEST_REDIS_DB <= 15):
        raise ValueError(f"Invalid Redis database number: {TEST_REDIS_DB}")

# Add to import-time validation
validate_redis_config()
```

---

### Step 3: Update Docker Compose

```yaml
# docker-compose.test.yml
services:
  redis:
    ports:
      - "6379:6379"  # Match TEST_REDIS_PORT
```

---

### Step 4: Update Pre-commit Hook

```python
# scripts/validation/validate-test-constants.py

def validate_redis_configuration():
    """Ensure Redis config matches constants"""
    from tests.constants import TEST_REDIS_PORT, TEST_REDIS_DB

    with open("docker-compose.test.yml") as f:
        config = yaml.safe_load(f)

    redis_port = config["services"]["redis"]["ports"][0].split(":")[0]
    assert int(redis_port) == TEST_REDIS_PORT, "Redis port mismatch"
```

---

### Step 5: Update Documentation

```markdown
# Update this file with new constant
| Constant | Value | Purpose |
|----------|-------|---------|
| `TEST_REDIS_HOST` | `"localhost"` | Redis host for integration tests |
| `TEST_REDIS_PORT` | `6379` | Redis port for integration tests |
| `TEST_REDIS_DB` | `1` | Redis database number (test isolation) |
```

---

## Common Patterns

### Pattern: Environment-Specific Configuration

```python
# tests/constants.py

import os

# Allow override via environment variable (for CI/CD flexibility)
TEST_REDIS_HOST = os.getenv("TEST_REDIS_HOST", "localhost")
TEST_REDIS_PORT = int(os.getenv("TEST_REDIS_PORT", "6379"))
```

**Benefit**: Supports different environments while maintaining defaults

---

### Pattern: Derived Constants

```python
# tests/constants.py

# Base constants
TEST_REDIS_HOST = "localhost"
TEST_REDIS_PORT = 6379
TEST_REDIS_DB = 1

# Derived constant (automatically consistent)
TEST_REDIS_URL = f"redis://{TEST_REDIS_HOST}:{TEST_REDIS_PORT}/{TEST_REDIS_DB}"
```

**Benefit**: Reduces duplication, ensures consistency

---

### Pattern: Type-Safe Constants with Pydantic

```python
# tests/constants.py

from pydantic import BaseModel, Field

class TestConfiguration(BaseModel):
    """Type-safe test configuration"""

    jwt_secret: str = Field(min_length=16)
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = Field(ge=1, le=24)

    redis_host: str = "localhost"
    redis_port: int = Field(ge=1024, le=65535)
    redis_db: int = Field(ge=0, le=15)

# Single instance
TEST_CONFIG = TestConfiguration(
    jwt_secret="test-secret-key-for-integration-tests"
)

# Export as constants for backward compatibility
TEST_JWT_SECRET = TEST_CONFIG.jwt_secret
TEST_JWT_ALGORITHM = TEST_CONFIG.jwt_algorithm
```

**Benefit**: Automatic validation, type safety, IDE autocomplete

---

## Anti-Patterns to AVOID

### ❌ Anti-Pattern 1: Hardcoded Values

```python
# ❌ WRONG - Hardcoded JWT secret
def mock_jwt_token():
    return jwt.encode(payload, "test-secret-key", algorithm="HS256")
```

**Problem**: Breaks when secret changes, hard to track usages

**Fix**: Import from `tests/constants.py`

---

### ❌ Anti-Pattern 2: Duplicate Constants

```python
# ❌ WRONG - Duplicate constant definition
# tests/test_auth.py
JWT_SECRET = "test-secret-key"  # Duplicate!

# tests/test_session.py
JWT_SECRET = "test-secret-key"  # Another duplicate!
```

**Problem**: Nightmare to update, easy to create mismatches

**Fix**: Single definition in `tests/constants.py`

---

### ❌ Anti-Pattern 3: Magic Values

```python
# ❌ WRONG - Magic values without context
def test_checkpointer():
    config = {"configurable": {"thread_id": "test-123"}}  # What is this?
```

**Problem**: Unclear meaning, hard to grep, inconsistent

**Fix**: Use `TEST_THREAD_ID` constant

---

### ❌ Anti-Pattern 4: Environment Variable Overload

```python
# ❌ WRONG - Everything from environment variables
TEST_JWT_SECRET = os.environ["TEST_JWT_SECRET"]  # Fails if not set!
```

**Problem**: Requires external configuration, breaks local development

**Fix**: Defaults with optional environment overrides

---

## Security Considerations

### Test Secrets Are NOT Production Secrets

**CRITICAL**: `TEST_JWT_SECRET` is **FOR TESTING ONLY**

**Never**:
- ❌ Use test secrets in production
- ❌ Commit production secrets to version control
- ❌ Copy test secret patterns to production

**Production secrets must**:
- ✅ Be generated with cryptographically secure RNG
- ✅ Be at least 32 characters (256 bits)
- ✅ Be stored in secure secret management (e.g., Infisical)
- ✅ Be rotated regularly
- ✅ Never be committed to version control

---

### Test Secret Validation

```python
# tests/constants.py

def validate_jwt_secret():
    """Ensure test secret is clearly marked as test-only"""
    if "test" not in TEST_JWT_SECRET.lower():
        raise ValueError(
            "TEST_JWT_SECRET must contain 'test' to prevent accidental "
            "production use"
        )

    if len(TEST_JWT_SECRET) < 16:
        raise ValueError("TEST_JWT_SECRET too short for secure testing")
```

**Benefit**: Prevents accidental production misuse

---

## Troubleshooting

### Issue: JWT Validation Failing in Tests

**Symptoms**:
```
PermissionError: Invalid authentication token
```

**Diagnosis**:
```bash
# Check if TEST_JWT_SECRET matches across configurations
grep -r "JWT_SECRET" docker-compose.test.yml
grep -r "JWT_SECRET" .github/workflows/
python -c "from tests.constants import TEST_JWT_SECRET; print(TEST_JWT_SECRET)"
```

**Fix**: Ensure all three use same value from `tests/constants.py`

---

### Issue: Constants Not Synchronized

**Symptoms**:
- Pre-commit hook failure
- CI failing with configuration errors
- Test failures with "connection refused" or similar

**Diagnosis**:
```bash
# Run validation manually
python scripts/validation/validate-test-constants.py
```

**Fix**: Update `docker-compose.test.yml` or `.github/workflows/*.yaml` to match

---

### Issue: Can't Import Constants

**Symptoms**:
```python
ImportError: cannot import name 'TEST_JWT_SECRET' from 'tests.constants'
```

**Diagnosis**:
```bash
# Check if constants.py exists
ls -la tests/constants.py

# Check Python path
python -c "import sys; print('\n'.join(sys.path))"
```

**Fix**: Ensure `tests/` is in Python path (check `pyproject.toml` → `pythonpath`)

---

## Related Documentation

- Constants Source: `tests/constants.py`
- Validation Script: `scripts/validation/validate-test-constants.py`
- Meta-Tests: `tests/meta/test_constants.py`
- Pre-commit Hook: `.pre-commit-config.yaml` → `validate-test-constants`
- Docker Compose: `docker/docker-compose.test.yml`
- CI Workflows: `.github/workflows/ci.yaml`
- xdist Safety Patterns: `.claude/context/xdist-safety-patterns.md` (AsyncMock configuration)

---

**Last Audit**: 2025-11-23
**Codex Finding**: 2025-11-16 (JWT secret mismatch - FIXED)
**Enforcement**: Pre-commit hooks + import-time validation + meta-tests
**Status**: Production-ready, prevents configuration drift
