---
purpose: Prevent configuration drift across test environments with shared constants
priority: high
category: testing
last-updated: 2026-02-05
---

# Test Constants Pattern

---

## Quick Reference

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
```

---

## The Problem

**Codex Finding (2025-11-16)**: JWT secret mismatch across three configuration files caused 50+ integration test failures.

| Location | Value | Result |
|----------|-------|--------|
| `conftest.py` | `"test-secret-key"` | Token signing |
| `docker compose.test.yml` | `"test-secret-key-for-integration-tests"` | Token verification |
| **Symptom** | `PermissionError: Invalid authentication token` | Tests fail |

---

## The Solution: Single Source of Truth

**Location**: `tests/constants.py`

```python
# tests/constants.py

# JWT Authentication
TEST_JWT_SECRET = "test-secret-key-for-integration-tests"
TEST_JWT_ALGORITHM = "HS256"
TEST_JWT_EXPIRATION_HOURS = 1

# Test User Credentials
TEST_USER_ID = "alice"
TEST_USER_EMAIL = "alice@example.com"

# Test Environment
TEST_THREAD_ID = "test-thread-123"
TEST_RUN_ID = "test-run-123"

# Validation (runs on import)
def validate_jwt_secret() -> None:
    if len(TEST_JWT_SECRET) < 16:
        raise ValueError("TEST_JWT_SECRET must be at least 16 characters")
    if "test" not in TEST_JWT_SECRET.lower():
        raise ValueError("TEST_JWT_SECRET should contain 'test' for safety")

validate_jwt_secret()
```

---

## Usage Patterns

### Test Fixtures

```python
# tests/conftest.py
from tests.constants import TEST_JWT_SECRET, TEST_JWT_ALGORITHM

@pytest.fixture
def mock_jwt_token():
    payload = {"sub": "test-user", "exp": datetime.utcnow() + timedelta(hours=1)}
    return jwt.encode(payload, TEST_JWT_SECRET, algorithm=TEST_JWT_ALGORITHM)
```

### Docker Compose

```yaml
# docker/docker compose.test.yml
services:
  mcp-server:
    environment:
      JWT_SECRET_KEY: "test-secret-key-for-integration-tests"  # Must match TEST_JWT_SECRET
```

### CI Workflows

```yaml
# .github/workflows/ci.yaml
jobs:
  integration-tests:
    env:
      JWT_SECRET_KEY: "test-secret-key-for-integration-tests"  # Must match TEST_JWT_SECRET
```

---

## Available Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `TEST_JWT_SECRET` | `"test-secret-key-for-integration-tests"` | JWT signing/verification |
| `TEST_JWT_ALGORITHM` | `"HS256"` | JWT algorithm |
| `TEST_JWT_EXPIRATION_HOURS` | `1` | Token expiration |
| `TEST_USER_ID` | `"alice"` | Default test user |
| `TEST_USER_EMAIL` | `"alice@example.com"` | Default test email |
| `TEST_THREAD_ID` | `"test-thread-123"` | LangGraph thread ID |
| `TEST_RUN_ID` | `"test-run-123"` | Distributed tracing run ID |

---

## Validation & Enforcement

### Pre-commit Hook

```yaml
# .pre-commit-config.yaml
- id: validate-test-constants
  name: Validate Test Constants Synchronization
  entry: uv run --frozen python scripts/validation/validate-test-constants.py
```

**Checks**:
1. `docker compose.test.yml` uses `TEST_JWT_SECRET`
2. `.github/workflows/*.yaml` use `TEST_JWT_SECRET`
3. No hardcoded test secrets in test files

### Meta-Test

```python
# tests/meta/test_constants.py
@pytest.mark.meta
def test_jwt_secret_requirements():
    assert len(TEST_JWT_SECRET) >= 16
    assert "test" in TEST_JWT_SECRET.lower()
```

---

## Anti-Patterns (AVOID)

| Anti-Pattern | Problem | Fix |
|--------------|---------|-----|
| Hardcoded values | Breaks on change, hard to track | Import from `tests/constants.py` |
| Duplicate definitions | Nightmare to update, causes mismatches | Single definition |
| Magic values | Unclear meaning, inconsistent | Use named constants |
| Required env vars | Breaks local dev | Defaults with optional overrides |

---

## Advanced Patterns

### Environment Overrides

```python
# Allow CI/CD flexibility
TEST_REDIS_HOST = os.getenv("TEST_REDIS_HOST", "localhost")
```

### Derived Constants

```python
# Automatically consistent
TEST_REDIS_URL = f"redis://{TEST_REDIS_HOST}:{TEST_REDIS_PORT}/{TEST_REDIS_DB}"
```

### Type-Safe with Pydantic

```python
class TestConfiguration(BaseModel):
    jwt_secret: str = Field(min_length=16)
    jwt_algorithm: str = "HS256"

TEST_CONFIG = TestConfiguration(jwt_secret="test-secret-key-for-integration-tests")
```

---

## Security Notes

**CRITICAL**: `TEST_JWT_SECRET` is FOR TESTING ONLY

- ❌ Never use test secrets in production
- ❌ Never commit production secrets to version control
- ✅ Production secrets: 32+ chars, secure RNG, secret management, regular rotation

---

## Troubleshooting

| Issue | Diagnosis | Fix |
|-------|-----------|-----|
| JWT validation failing | `grep -r "JWT_SECRET"` across configs | Ensure all use same value |
| Constants not synchronized | Run `validate-test-constants.py` | Update Docker/CI to match |
| ImportError | Check `tests/` in Python path | Verify `pyproject.toml` pythonpath |

---

## Related Docs

- Constants Source: `tests/constants.py`
- Validation: `scripts/validation/validate-test-constants.py`
- Meta-Tests: `tests/meta/test_constants.py`
- xdist Safety: `.claude/context/xdist-safety-patterns.md`

---

**Enforcement**: Pre-commit hooks + import-time validation + meta-tests
