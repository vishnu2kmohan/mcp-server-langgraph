# Infrastructure Auto-Setup for Tests

This guide explains how to write tests that gracefully handle missing infrastructure (Postgres, Redis, etc.) and optionally auto-start required services.

## Problem Statement

Some tests require external infrastructure:
- **Alembic schema tests** need Postgres
- **Session management tests** need Redis
- **Integration tests** need full Docker Compose stack

When infrastructure isn't running, these tests fail with connection errors instead of skipping gracefully.

## Solution: Infrastructure Detection + Auto-Skip

Tests can detect missing infrastructure and automatically skip with a helpful message.

### Basic Pattern

```python
import pytest
from tests.infrastructure_helpers import is_postgres_available

# Skip marker for module-level or class-level application
skip_without_postgres = pytest.mark.skipif(
    not is_postgres_available(),
    reason=(
        "PostgreSQL not available. "
        "Run 'make setup-infra' or 'docker-compose up -d postgres' to start infrastructure."
    ),
)

@skip_without_postgres
class TestRequiresPostgres:
    """Tests that need Postgres will auto-skip if it's not running."""

    def test_database_migration(self):
        # This test only runs if Postgres is available
        ...
```

### Using Infrastructure Helpers

The `tests/infrastructure_helpers.py` module provides utilities for infrastructure detection:

```python
from tests.infrastructure_helpers import (
    is_postgres_available,      # Check if Postgres is reachable
    is_redis_available,          # Check if Redis is reachable
    is_docker_available,         # Check if Docker daemon is running
    ensure_postgres_running,     # Auto-start Postgres if needed
    skip_if_infrastructure_unavailable,  # Skip test if infra missing
)

def test_with_infrastructure_check():
    """Test that auto-skips if infrastructure is unavailable."""
    skip_if_infrastructure_unavailable(["postgres", "redis"])

    # Test code that needs both Postgres and Redis
    ...
```

## Auto-Start Infrastructure (Optional)

Tests can optionally auto-start infrastructure via Docker Compose:

### Environment Variable Control

Set `AUTO_SETUP_INFRA=1` to enable auto-starting:

```bash
# Auto-start infrastructure before running tests
AUTO_SETUP_INFRA=1 pytest tests/meta/test_alembic_schema_parity.py

# Or export for entire session
export AUTO_SETUP_INFRA=1
pytest tests/
```

### Programmatic Auto-Start

```python
from tests.infrastructure_helpers import ensure_postgres_running

def test_with_auto_start():
    """Test that auto-starts Postgres if not running."""
    # Attempt to ensure Postgres is running
    postgres_available = ensure_postgres_running(auto_start=True)

    if not postgres_available:
        pytest.skip("Could not start Postgres (Docker not available?)")

    # Run test that needs Postgres
    ...
```

## Examples

### Example 1: Module-Level Skip

Skip all tests in a module if Postgres isn't available:

```python
# tests/meta/test_alembic_schema_parity.py
import pytest
from tests.infrastructure_helpers import is_postgres_available

skip_without_postgres = pytest.mark.skipif(
    not is_postgres_available(),
    reason="PostgreSQL not available. Run 'make setup-infra' to start infrastructure.",
)

@pytest.mark.asyncio
@skip_without_postgres
class TestAlembicSchemaParity:
    """All tests in this class require Postgres."""

    async def test_alembic_migration_creates_tables(self):
        # Only runs if Postgres is available
        ...
```

### Example 2: Function-Level Skip with Fixture

```python
import pytest
from tests.infrastructure_helpers import skip_if_infrastructure_unavailable

@pytest.fixture(autouse=True)
def require_postgres():
    """Require Postgres for this test."""
    skip_if_infrastructure_unavailable(["postgres"])

def test_database_query():
    """Test that requires Postgres."""
    # Only runs if Postgres is available
    ...
```

### Example 3: Auto-Start Infrastructure

```python
import pytest
from tests.infrastructure_helpers import ensure_infrastructure_running

@pytest.fixture(scope="module", autouse=True)
def setup_infrastructure():
    """Ensure required infrastructure is running."""
    status = ensure_infrastructure_running(["postgres", "redis"], auto_start=True)

    if not status["postgres"]:
        pytest.skip("Could not start Postgres")

    if not status["redis"]:
        pytest.skip("Could not start Redis")

    yield

    # Optional: Teardown infrastructure after module
    # (usually not needed - leave running for other tests)

class TestRequiresInfrastructure:
    """Tests in this module have infrastructure auto-started."""

    def test_postgres_and_redis(self):
        # Postgres and Redis are guaranteed to be running
        ...
```

## Available Helper Functions

### Detection Functions

| Function | Description | Returns |
|----------|-------------|---------|
| `is_postgres_available()` | Check if Postgres is reachable at configured host:port | `bool` |
| `is_redis_available()` | Check if Redis is reachable at configured host:port | `bool` |
| `is_docker_available()` | Check if Docker daemon is running | `bool` |
| `is_service_available(host, port)` | Generic service connectivity check | `bool` |

### Auto-Start Functions

| Function | Description | Returns |
|----------|-------------|---------|
| `ensure_postgres_running(auto_start=None)` | Ensure Postgres is running, optionally auto-start | `bool` |
| `ensure_redis_running(auto_start=None)` | Ensure Redis is running, optionally auto-start | `bool` |
| `ensure_infrastructure_running(services, auto_start)` | Ensure multiple services are running | `dict[str, bool]` |

### Skip Functions

| Function | Description | Raises |
|----------|-------------|--------|
| `skip_if_infrastructure_unavailable(services, auto_start)` | Skip test if required infrastructure is unavailable | `pytest.skip` |

## Configuration

Infrastructure is detected using environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_HOST` | `localhost` | Postgres hostname |
| `POSTGRES_PORT` | `5432` | Postgres port |
| `POSTGRES_USER` | `postgres` | Postgres username |
| `POSTGRES_PASSWORD` | `postgres` | Postgres password |
| `REDIS_HOST` | `localhost` | Redis hostname |
| `REDIS_PORT` | `6379` | Redis port |
| `AUTO_SETUP_INFRA` | `""` | Set to `"1"` to enable auto-starting infrastructure |

## Best Practices

### 1. Use Module-Level Skips for Infrastructure-Heavy Tests

```python
# ✅ Good: Skip entire test class if infrastructure missing
@skip_without_postgres
class TestDatabaseMigrations:
    # All tests require Postgres
    ...
```

```python
# ❌ Bad: Duplicate skip logic in every test
class TestDatabaseMigrations:
    def test_migration_1(self):
        if not is_postgres_available():
            pytest.skip("...")

    def test_migration_2(self):
        if not is_postgres_available():  # Duplicate!
            pytest.skip("...")
```

### 2. Provide Helpful Skip Messages

```python
# ✅ Good: Clear instructions on how to fix
skip_without_postgres = pytest.mark.skipif(
    not is_postgres_available(),
    reason=(
        "PostgreSQL not available. "
        "Run 'make setup-infra' or 'docker-compose up -d postgres' to start infrastructure."
    ),
)
```

```python
# ❌ Bad: Vague error message
skip_without_postgres = pytest.mark.skipif(
    not is_postgres_available(),
    reason="No Postgres",  # Not helpful!
)
```

### 3. Use Auto-Start for CI/CD, Manual Control for Development

```python
# ✅ Good: Respect AUTO_SETUP_INFRA environment variable
ensure_postgres_running(auto_start=None)  # Uses AUTO_SETUP_INFRA

# CI/CD pipeline:
#   AUTO_SETUP_INFRA=1 pytest tests/  # Auto-starts infrastructure

# Local development:
#   make setup-infra  # Manual control
#   pytest tests/     # Uses existing infrastructure
```

### 4. Fail Fast with Clear Messages

```python
# ✅ Good: Check infrastructure early and provide clear message
@pytest.fixture(scope="module", autouse=True)
def require_postgres():
    if not is_postgres_available():
        pytest.skip(
            "PostgreSQL not available. "
            "Run 'make setup-infra' to start Docker Compose services."
        )
```

## Troubleshooting

### Issue: Tests fail with connection errors instead of skipping

**Cause**: Infrastructure detection check happens too late (inside test instead of decorator/fixture).

**Solution**: Move infrastructure check to module-level or fixture-level:

```python
# ✅ Good: Check before test runs
@skip_without_postgres
def test_database():
    ...

# ❌ Bad: Check inside test (still attempts connection)
def test_database():
    if not is_postgres_available():  # Too late!
        pytest.skip("...")
    db.connect()  # May fail before skip check
```

### Issue: Auto-start doesn't work

**Cause**: Docker not available or environment variable not set.

**Solution**: Verify Docker is running and `AUTO_SETUP_INFRA=1` is set:

```bash
# Check Docker
docker info

# Check environment variable
echo $AUTO_SETUP_INFRA

# Start infrastructure manually
make setup-infra
```

### Issue: Tests skip in CI but should run

**Cause**: Infrastructure not started in CI environment.

**Solution**: Update CI workflow to start infrastructure or set `AUTO_SETUP_INFRA=1`:

```yaml
# .github/workflows/ci.yaml
jobs:
  test:
    steps:
      - name: Start infrastructure
        run: make setup-infra

      - name: Run tests
        env:
          AUTO_SETUP_INFRA: "1"  # Auto-start if not running
        run: pytest tests/
```

## Summary

**For test authors:**
- Use `@skip_without_postgres` or similar decorators for infrastructure-dependent tests
- Provide helpful skip messages with instructions on how to start infrastructure
- Consider using `AUTO_SETUP_INFRA` for optional auto-starting in CI/CD

**For CI/CD:**
- Either start infrastructure explicitly (`make setup-infra`) or enable auto-starting (`AUTO_SETUP_INFRA=1`)
- Monitor for skipped tests that should be running

**For developers:**
- Run `make setup-infra` once to start all infrastructure
- Tests will automatically skip if infrastructure isn't available
- Use `AUTO_SETUP_INFRA=1` to have tests auto-start infrastructure as needed
