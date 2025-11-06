# Smoke Tests

## Purpose

Smoke tests are **fast, critical validation tests** that run in CI/CD pipelines to catch deployment-blocking issues before they reach production. These tests are designed to execute in under 30 seconds and require no external dependencies.

## What Smoke Tests Do

Smoke tests validate **critical startup functionality**:

1. ✅ **All core modules import successfully** (no syntax errors, missing deps)
2. ✅ **Settings initialize with defaults** (no config validation errors)
3. ✅ **Dependency injection works** (all factories instantiate correctly)
4. ✅ **Graceful degradation works** (system handles disabled services)
5. ✅ **Security configuration honored** (credentials, SSL, etc.)

## What Smoke Tests DON'T Do

Smoke tests are NOT:
- ❌ Comprehensive integration tests
- ❌ Performance tests
- ❌ Full feature validation
- ❌ External service connectivity tests

For comprehensive testing, see:
- `tests/integration/` - Integration tests
- `tests/unit/` - Unit tests
- `tests/e2e/` - End-to-end tests

## Critical Bugs Caught

These smoke tests prevent the following production outages:

### Bug #1: Missing Keycloak Admin Credentials
```python
# Test validates admin credentials are wired
assert client.config.admin_username is not None
assert client.config.admin_password is not None
```

### Bug #2: OpenFGA Client with None store_id
```python
# Test validates None returned when config incomplete
assert get_openfga_client() is None  # When disabled
```

### Bug #3: Service Principal AttributeError
```python
# Test validates manager accepts None OpenFGA
manager = ServicePrincipalManager(keycloak=mock, openfga=None)
assert manager.openfga is None  # Should not crash
```

### Bug #4: L2 Cache Ignoring Redis Password
```python
# Test validates secure Redis config accepted
cache = CacheService(redis_password="secret", redis_ssl=True)
```

### Bug #5: Missing Test Coverage
```python
# Test validates all critical tests exist
assert Path("tests/unit/test_dependencies_wiring.py").exists()
```

## Running Smoke Tests

### Locally

```bash
# Run all smoke tests
python tests/smoke/test_ci_startup_smoke.py

# Or via pytest
pytest tests/smoke/ -m smoke -v

# Quick validation
pytest tests/smoke/test_ci_startup_smoke.py::TestCriticalStartupValidation -v
```

### In CI/CD

Smoke tests run automatically via `.github/workflows/smoke-tests.yml`:

```yaml
jobs:
  smoke-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run smoke tests
        run: python tests/smoke/test_ci_startup_smoke.py
```

### Exit Codes

- **0**: All smoke tests passed - Safe to deploy
- **1**: Smoke tests failed - DO NOT DEPLOY

## When to Run

### Always Run
- ✅ Before deploying to production
- ✅ Before deploying to staging
- ✅ On every PR to main branch
- ✅ On every commit to main branch

### Optional but Recommended
- ✅ Before creating a PR
- ✅ After major refactoring
- ✅ After dependency updates

## Adding New Smoke Tests

When adding critical functionality:

1. **Identify critical startup behavior**
   - Does it need external services?
   - What happens if misconfigured?
   - What's the failure mode?

2. **Write smoke test**
   ```python
   @pytest.mark.smoke
   def test_critical_feature_starts(self):
       """Test that critical feature can start"""
       # Minimal test that catches critical failures
       feature = initialize_feature()
       assert feature is not None
   ```

3. **Keep tests fast**
   - No actual network calls
   - No database connections
   - Use mocks for external dependencies
   - Target: < 5 seconds per test

4. **Make tests fail-fast**
   - Test most critical things first
   - Use clear assertion messages
   - Fail immediately on critical errors

## Test Organization

```
tests/smoke/
├── README.md                        # This file
├── test_ci_startup_smoke.py         # Main CI smoke tests
└── __init__.py                      # Pytest configuration
```

### test_ci_startup_smoke.py Structure

```python
@pytest.mark.smoke
class TestCriticalStartupValidation:
    """Tests that MUST pass before deployment"""

    def test_import_core_modules(self): ...
    def test_settings_initialize(self): ...
    def test_dependency_factories(self): ...

@pytest.mark.smoke
class TestGracefulDegradation:
    """Tests for fallback modes"""

    def test_works_without_redis(self): ...
    def test_works_without_openfga(self): ...
```

## Integration with Other Testing Layers

```
┌─────────────────────────────────────────┐
│         Smoke Tests (CI/CD)             │  ← YOU ARE HERE
│  Fast, critical, no external deps       │
├─────────────────────────────────────────┤
│     Integration Tests (Pre-deploy)      │
│  Slower, real DI, some mocking          │
├─────────────────────────────────────────┤
│         Unit Tests (Development)        │
│  Isolated, mocked, comprehensive        │
├─────────────────────────────────────────┤
│         E2E Tests (Staging)             │
│  Complete workflows, real services      │
└─────────────────────────────────────────┘
```

## Success Criteria

Smoke tests are successful when:

1. ✅ All tests pass in < 30 seconds
2. ✅ No external service dependencies required
3. ✅ Catches critical startup failures
4. ✅ Clear error messages when failures occur
5. ✅ Documented in this README

## Troubleshooting

### "Module not found" errors

**Problem**: Missing test dependencies

**Solution**:
```bash
pip install pytest pytest-asyncio pytest-mock
pip install -e .
```

### "Attribute Error" in tests

**Problem**: Singleton not reset between tests

**Solution**: Reset singletons in test setup
```python
import mcp_server_langgraph.core.dependencies as deps
deps._singleton_client = None
```

### Tests hang

**Problem**: Actual network calls being made

**Solution**: Ensure all external calls are mocked
```python
with patch('module.external_call') as mock:
    mock.return_value = Mock()
    # ... test code ...
```

## Maintenance

These smoke tests are **critical infrastructure** and must be maintained:

- Review monthly for relevance
- Update when adding critical features
- Keep fast (< 30 seconds total)
- Keep clear and understandable
- Document all changes

Last Updated: 2025-01-28
Related: ADR-0042 (Dependency Injection Configuration Fixes)
