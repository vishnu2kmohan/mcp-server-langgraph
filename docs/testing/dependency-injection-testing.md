---
title: "Dependency Injection Testing Guide"
description: "Comprehensive guide for testing dependency injection to prevent critical production failures"
icon: "shield-check"
---

# Dependency Injection Testing Guide

## Overview

This guide explains how to properly test dependency injection in the MCP Server LangGraph project to prevent critical production failures. These best practices were established after fixing 5 critical bugs identified by OpenAI Codex (see [ADR-0042](/architecture/adr-0042-dependency-injection-configuration-fixes)).

## Critical Bugs Prevented

Our testing framework prevents these classes of failures:

1. **Missing Configuration**: Required settings not passed to constructors
2. **Incomplete Configuration**: Services created with None/empty required fields
3. **No Graceful Degradation**: Crashes when optional services are disabled
4. **Ignored Security Settings**: Credentials/SSL settings not honored
5. **Missing Test Coverage**: Bugs reach production undetected

## Testing Pyramid for Dependency Injection

### Level 1: Unit Tests (Fast, Isolated)

**Location**: `tests/unit/test_dependencies_wiring.py`

**Purpose**: Validate that each dependency factory properly wires configuration from settings to client instances.

```python
def test_keycloak_client_receives_admin_credentials(self):
    """Verify admin credentials are passed from settings to KeycloakConfig"""
    from mcp_server_langgraph.core.dependencies import get_keycloak_client

    with patch('mcp_server_langgraph.core.dependencies.settings') as mock_settings:
        mock_settings.keycloak_admin_username = "admin"
        mock_settings.keycloak_admin_password = "admin-password"
        # ... other settings ...

        client = get_keycloak_client()

        # CRITICAL: Verify credentials are wired
        assert client.config.admin_username == "admin"
        assert client.config.admin_password == "admin-password"
```

**What to Test**:
- ✅ All required settings passed to constructors
- ✅ Optional settings have sensible defaults
- ✅ None/empty configs handled gracefully
- ✅ Type hints match actual behavior

### Level 2: Integration Tests (Medium, Real DI)

**Location**: `tests/integration/test_app_startup_validation.py`

**Purpose**: Validate that the full dependency injection system works with various real-world configurations.

```python
def test_app_starts_with_disabled_openfga(self, monkeypatch):
    """Test app starts even when OpenFGA is disabled"""
    from mcp_server_langgraph.infrastructure.app_factory import create_app

    monkeypatch.setenv("OPENFGA_STORE_ID", "")
    monkeypatch.setenv("OPENFGA_MODEL_ID", "")

    app = create_app()  # Should NOT crash

    assert app is not None
```

**What to Test**:
- ✅ App starts with minimal configuration
- ✅ App starts with disabled optional services
- ✅ App starts with partial configuration
- ✅ Graceful degradation when services unavailable

### Level 3: Smoke Tests (Fast, CI/CD)

**Location**: `tests/smoke/test_ci_startup_smoke.py`

**Purpose**: Fast validation in CI/CD pipelines to prevent deployment of broken configurations.

```python
@pytest.mark.smoke
def test_keycloak_client_factory_with_minimal_config(self, monkeypatch):
    """CRITICAL: Keycloak client must initialize with minimal config"""
    from mcp_server_langgraph.core.dependencies import get_keycloak_client

    # Set minimal required config
    monkeypatch.setenv("KEYCLOAK_ADMIN_USERNAME", "admin")
    monkeypatch.setenv("KEYCLOAK_ADMIN_PASSWORD", "admin-password")
    # ...

    client = get_keycloak_client()

    # Validate critical configuration
    assert client.config.admin_username == "admin"
    assert client.config.admin_password == "admin-password"
```

**What to Test**:
- ✅ All modules import without errors
- ✅ Settings initialize with defaults
- ✅ All dependency factories instantiate
- ✅ Critical configuration properly wired

### Level 4: End-to-End Tests (Slow, Complete)

**Location**: `tests/integration/test_mcp_startup_validation.py`

**Purpose**: Validate complete workflows including MCP server startup.

```python
@pytest.mark.asyncio
async def test_service_principal_creation_without_openfga(self):
    """E2E: Complete service principal workflow without OpenFGA"""
    # Full workflow test from factory → creation → validation
```

**What to Test**:
- ✅ Complete workflows (create → read → update → delete)
- ✅ Multiple dependencies working together
- ✅ Real async operations
- ✅ Error handling and recovery

## Best Practices

### 1. Test Configuration Wiring

**DO**: Test that settings are passed to constructors

```python
def test_config_wiring(self):
    """Test that all settings are wired correctly"""
    client = get_some_client()

    assert client.config.required_field == settings.required_field
    assert client.config.optional_field == settings.optional_field
```

**DON'T**: Assume configuration is wired correctly

```python
def test_client_works(self):
    """Test that client works"""
    client = get_some_client()
    # Missing: Validation that config was passed correctly
```

### 2. Test Optional Dependencies

**DO**: Test that system works when optional services are disabled

```python
def test_with_disabled_optional_service(self, monkeypatch):
    """Test graceful degradation when service disabled"""
    monkeypatch.setenv("OPTIONAL_SERVICE_ENABLED", "false")

    result = get_optional_service()

    assert result is None  # Graceful degradation
```

**DON'T**: Assume optional services are always available

```python
def test_with_service(self):
    """Test with service"""
    service = get_optional_service()
    service.do_something()  # Crash if service is None!
```

### 3. Test Guard Clauses

**DO**: Test that None checks prevent crashes

```python
@pytest.mark.asyncio
async def test_handles_none_dependency(self):
    """Test that manager handles None dependency gracefully"""
    manager = SomeManager(required_dep=mock_dep, optional_dep=None)

    # Should NOT crash
    await manager.do_something()

    # Verify guard worked
    assert manager.optional_dep is None
```

**DON'T**: Skip testing None scenarios

### 4. Test Secure Configuration

**DO**: Test that security settings are honored

```python
def test_secure_redis_config(self):
    """Test that Redis password and SSL are used"""
    cache = CacheService(
        redis_password="secure-password",
        redis_ssl=True
    )

    # Verify settings accepted and used
    assert cache is not None
```

**DON'T**: Only test happy path without security settings

## Automated Validation

### Pre-commit Hook

**Script**: `.githooks/pre-commit-dependency-validation`

Runs automatically on commits to validate:
- ✅ Keycloak admin credentials wired
- ✅ OpenFGA returns Optional type
- ✅ Service principal accepts Optional OpenFGA
- ✅ Cache uses redis.from_url() pattern
- ✅ Required tests exist

### CI/CD Smoke Tests

**Workflow**: `.github/workflows/smoke-tests.yml`

Runs on all PRs and commits to validate:
- ✅ Dependency injection properly configured
- ✅ All modules import successfully
- ✅ App starts with various configurations
- ✅ Graceful degradation works

### GitHub Actions Workflow

```yaml
jobs:
  dependency-validation:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Validate dependencies
        run: python .githooks/pre-commit-dependency-validation

  smoke-tests:
    needs: dependency-validation
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run smoke tests
        run: python tests/smoke/test_ci_startup_smoke.py
```

## TDD Workflow for New Dependencies

When adding new dependencies, follow this TDD workflow:

### 1. Write Tests First (RED Phase)

```python
def test_new_dependency_wired_correctly(self):
    """Test that new dependency gets all required config"""
    from my_module import get_new_dependency

    with patch('my_module.settings') as mock_settings:
        mock_settings.new_dep_api_key = "test-key"
        mock_settings.new_dep_url = "http://test"

        dep = get_new_dependency()

        # Verify all settings wired
        assert dep.api_key == "test-key"
        assert dep.url == "http://test"
```

### 2. Implement Minimal Fix (GREEN Phase)

```python
def get_new_dependency() -> NewDependency:
    """Get new dependency (singleton)"""
    global _new_dependency

    if _new_dependency is None:
        config = NewDependencyConfig(
            api_key=settings.new_dep_api_key,
            url=settings.new_dep_url,
        )
        _new_dependency = NewDependency(config=config)

    return _new_dependency
```

### 3. Add Guard Tests (REFACTOR Phase)

```python
def test_new_dependency_handles_missing_config(self):
    """Test graceful degradation when config missing"""
    with patch('my_module.settings') as mock_settings:
        mock_settings.new_dep_api_key = None  # Not configured

        dep = get_new_dependency()

        # Should return None or raise clear error
        assert dep is None or isinstance(dep, NewDependency)
```

### 4. Update Validation Hook

Add check to `.githooks/pre-commit-dependency-validation`:

```python
def check_new_dependency_wired() -> List[str]:
    """Check that new dependency is properly wired"""
    errors = []
    # ... validation logic ...
    return errors
```

### 5. Add to CI Smoke Tests

Add to `tests/smoke/test_ci_startup_smoke.py`:

```python
def test_new_dependency_factory(self):
    """Smoke test for new dependency"""
    dep = get_new_dependency()
    assert dep is not None or dep is None  # Both valid
```

## Common Pitfalls

### ❌ Pitfall #1: Missing Required Configuration

**Problem**: Settings exist but not passed to constructor

```python
# BAD: Missing required_setting
config = SomeConfig(
    url=settings.some_url,
    # Missing: required_setting=settings.required_setting
)
```

**Solution**: Always pass ALL relevant settings

```python
# GOOD: All settings passed
config = SomeConfig(
    url=settings.some_url,
    required_setting=settings.required_setting,
    optional_setting=settings.optional_setting,
)
```

### ❌ Pitfall #2: No Validation for Incomplete Config

**Problem**: Creating clients with None required fields

```python
# BAD: Always create client
def get_client() -> Client:
    config = ClientConfig(
        store_id=settings.store_id,  # Could be None!
    )
    return Client(config)  # Crashes at runtime
```

**Solution**: Validate config and return None or fail fast

```python
# GOOD: Validate before creating
def get_client() -> Optional[Client]:
    if not settings.store_id:
        logger.warning("Client disabled - store_id not configured")
        return None

    config = ClientConfig(store_id=settings.store_id)
    return Client(config)
```

### ❌ Pitfall #3: No Guards for Optional Dependencies

**Problem**: Assuming dependencies are always available

```python
# BAD: No guard
async def sync_to_service(self):
    await self.optional_service.write_data(...)  # Crashes if None!
```

**Solution**: Guard all optional dependency operations

```python
# GOOD: Guarded
async def sync_to_service(self):
    if self.optional_service is None:
        return  # Graceful degradation

    await self.optional_service.write_data(...)
```

### ❌ Pitfall #4: Ignoring Security Settings

**Problem**: Not using secure connection parameters

```python
# BAD: Ignoring password and SSL
redis_client = redis.Redis(
    host=settings.redis_host,
    port=settings.redis_port,
    # Missing: password, ssl
)
```

**Solution**: Use from_url() pattern with full config

```python
# GOOD: Full security config
redis_client = redis.from_url(
    f"{settings.redis_url}/{db}",
    password=settings.redis_password,
    ssl=settings.redis_ssl,
)
```

## Running the Tests

### Run All Dependency Tests

```bash
# Unit tests
pytest tests/unit/test_dependencies_wiring.py -v

# Integration tests
pytest tests/integration/test_app_startup_validation.py -v

# Smoke tests
python tests/smoke/test_ci_startup_smoke.py

# All dependency tests
pytest tests/unit/test_dependencies_wiring.py \
       tests/unit/test_cache_redis_config.py \
       tests/integration/test_app_startup_validation.py \
       tests/integration/test_mcp_startup_validation.py -v
```

### Run Pre-commit Validation

```bash
# Manual validation
python .githooks/pre-commit-dependency-validation

# Via pre-commit
pre-commit run validate-dependency-injection --all-files
```

### Run CI Smoke Tests Locally

```bash
# Simulate CI environment
python tests/smoke/test_ci_startup_smoke.py
```

## Continuous Improvement

### Adding New Dependency Factories

When adding a new `get_X_client()` function:

1. ✅ Write unit test validating configuration wiring
2. ✅ Write test for incomplete configuration handling
3. ✅ Add integration test for app startup with new dependency
4. ✅ Update pre-commit validation hook
5. ✅ Add to CI smoke tests
6. ✅ Document in ADR if it's a critical dependency

### Modifying Existing Dependencies

When modifying existing `get_X_client()` functions:

1. ✅ Run existing tests to ensure no regressions
2. ✅ Add new tests for new configuration parameters
3. ✅ Update pre-commit validation if validation logic changes
4. ✅ Run full test suite before committing

## References

- [ADR-0042: Dependency Injection Configuration Fixes](/architecture/adr-0042-dependency-injection-configuration-fixes)
<!-- TODO: Add the following documentation pages:
- TDD Best Practices
- Pre-commit Hooks Guide
-->

## Checklist for New Dependencies

Before committing new dependency injection code:

- [ ] Unit tests written and passing
- [ ] Integration tests cover startup scenarios
- [ ] Smoke tests added for CI/CD
- [ ] Pre-commit validation updated
- [ ] Documentation updated
- [ ] ADR created for critical dependencies
- [ ] All tests pass locally
- [ ] Pre-commit hooks pass
- [ ] CI smoke tests pass

## Contact

For questions about dependency injection testing:
- See ADR-0042 for historical context
- Review existing tests in `tests/unit/test_dependencies_wiring.py`
- Check CI workflow in `.github/workflows/smoke-tests.yml`
