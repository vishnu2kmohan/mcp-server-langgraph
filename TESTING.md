# Testing Guide

This document describes the testing strategy, conventions, and best practices for the MCP Server LangGraph project.

## Table of Contents

- [Test Organization](#test-organization)
- [Test Categories](#test-categories)
  - [Deployment Configuration Tests](#deployment-configuration-tests-pytestmarkdeployment)
- [Fixture Standards](#fixture-standards)
- [Identity & Authentication](#identity--authentication)
- [Running Tests](#running-tests)
- [TDD Best Practices](#tdd-best-practices)
- [Deployment Testing](#deployment-configuration-tests-pytestmarkdeployment)

---

## Test Organization

```
tests/
├── api/                        # API endpoint tests
│   ├── test_api_keys_endpoints.py
│   ├── test_service_principals_endpoints.py
│   └── test_openapi_compliance.py
├── e2e/                        # End-to-end journey tests
│   ├── test_full_user_journey.py
│   ├── test_scim_provisioning.py
│   └── helpers.py              # E2E test helpers
├── conftest.py                 # Shared fixtures
├── test_gdpr.py               # GDPR compliance tests
└── test_auth.py               # Authentication tests
```

---

## Test Categories

### Unit Tests (`@pytest.mark.unit`)
- **Purpose**: Test individual components in isolation
- **Dependencies**: Mocked
- **Speed**: Fast (<1s per test)
- **Examples**: Model validation, business logic, utility functions

### API Tests (`@pytest.mark.api`)
- **Purpose**: Test REST API endpoints with mocked dependencies
- **Dependencies**: FastAPI TestClient with dependency injection overrides
- **Speed**: Fast (<1s per test)
- **Examples**: API key endpoints, service principal endpoints, GDPR endpoints

### Integration Tests (`@pytest.mark.integration`)
- **Purpose**: Test multiple components working together
- **Dependencies**: Some real, some mocked
- **Speed**: Medium (1-5s per test)
- **Examples**: Database + business logic, external API integrations

### E2E Tests (`@pytest.mark.e2e`)
- **Purpose**: Test complete user journeys
- **Infrastructure**: Requires `docker-compose.test.yml` services
- **Speed**: Slow (5-30s per test)
- **Current Status**: **Transitioning from mocks to real infrastructure**

#### E2E Test Strategy Decision (2025-01-05)

**Decision**: Migrate E2E tests from mocks to real infrastructure

**Rationale**:
1. Infrastructure validation already exists (`test_infrastructure_check`)
2. Mock-based E2E tests provide false confidence
3. Real E2E tests catch integration issues that unit tests miss

**Implementation Plan**:
- ✅ Phase 1: Document current state (this file)
- 🔄 Phase 2: Remove mock dependencies from E2E tests (future)
- 🔄 Phase 3: Implement real Keycloak/OpenFGA integration (future)
- 🔄 Phase 4: Remove `@pytest.mark.skip` from journey tests (future)

**Current State**:
- Tests marked as `@pytest.mark.e2e` but use mocks (lines 116-131 in `test_full_user_journey.py`)
- Infrastructure check validates real services (PostgreSQL, Redis, OpenFGA, Keycloak, Qdrant)
- Comment on line 115: "Use HTTP mock until real Keycloak is implemented"

**Recommendation**: Keep mocks for now, migrate incrementally as infrastructure matures

### Deployment Configuration Tests (`@pytest.mark.deployment`)
- **Purpose**: Validate Helm charts, Kustomize overlays, and deployment manifests
- **Dependencies**: File system, helm/kustomize CLI tools (optional)
- **Speed**: Fast (<1s per test)
- **Examples**: Secret key alignment, CORS security, version consistency
- **Location**: `tests/deployment/`

**Test Coverage** (11 tests, 91% coverage):
- ✅ Helm secret template validation (missing keys detection)
- ✅ CORS security (prevents wildcard + credentials vulnerability)
- ✅ Hard-coded credential detection
- ✅ Placeholder validation (YOUR_PROJECT_ID, REPLACE_ME, example.com)
- ✅ ExternalSecrets key alignment
- ✅ Namespace consistency across overlays
- ✅ Version consistency across deployment methods
- ✅ Resource limits and security contexts
- ✅ Pod security standards compliance

**Running Deployment Tests**:

```bash
# Run all deployment configuration tests
pytest tests/deployment/ -v

# Run unit tests (no helm/kustomize required)
pytest tests/deployment/test_helm_configuration.py -v

# Run E2E tests (requires helm/kustomize installed)
pytest tests/deployment/test_deployment_e2e.py -v

# Validate all deployment configs (comprehensive script)
./scripts/validate-deployments.sh

# Check deployed cluster health (requires kubectl)
./scripts/check-deployment-health.sh production-mcp-server-langgraph mcp
```

**Pre-commit Validation**:

Deployment tests run automatically on commit via pre-commit hooks:
- `validate-deployment-secrets` - Secret key alignment
- `validate-cors-security` - CORS configuration safety
- `check-hardcoded-credentials` - Credential exposure prevention
- `validate-redis-password-required` - Redis authentication enforcement
- `check-dangerous-placeholders` - Placeholder leak detection

**CI/CD Integration**:

GitHub Actions workflow (`.github/workflows/validate-deployments.yml`) runs on every PR:
- Helm chart linting and template rendering
- Kustomize build validation across 5 environments (matrix)
- YAML syntax validation
- Security scanning (gitleaks, CORS, placeholders)
- Version consistency checks

See `adr/adr-0046-deployment-configuration-tdd-infrastructure.md` for full details.

---

## Fixture Standards

### Shared Fixtures (`tests/conftest.py`)

#### `mock_current_user` (Function-scoped)
Standard authenticated user fixture for API tests.

```python
{
    "user_id": "user:alice",              # OpenFGA format
    "keycloak_id": "8c7b4e5d-...",       # Keycloak UUID
    "username": "alice",
    "email": "alice@example.com"
}
```

**Usage**:
```python
def test_my_endpoint(test_client, mock_current_user):
    # Test client already has auth override
    response = test_client.get("/api/v1/resource")
    assert response.status_code == 200
```

#### `test_container` (Session-scoped)
Dependency injection container for test environment.

```python
@pytest.fixture(scope="session")
def test_container():
    from mcp_server_langgraph.core.container import create_test_container
    return create_test_container()
```

**Features**:
- No-op telemetry (no output)
- No-op auth (accepts any token)
- In-memory storage
- No global side effects

#### `container` (Function-scoped)
Per-test container for isolated testing.

```python
@pytest.fixture
def container(test_container):
    from mcp_server_langgraph.core.container import create_test_container
    return create_test_container()
```

---

## Identity & Authentication

### User Identity Formats

The system uses **dual identity formats** for compatibility:

#### 1. OpenFGA Format (Authorization)
```python
"user:alice"  # Format: user:{username}
```
- Used for: OpenFGA tuples, API responses, authorization checks
- Best Practice: Always use this format for `user_id` fields in API responses

#### 2. Keycloak UUID Format (Authentication)
```python
"8c7b4e5d-1234-5678-abcd-ef1234567890"
```
- Used for: Keycloak Admin API calls, internal database keys
- Best Practice: Use this format for `keycloak_id` when interacting with Keycloak

### Examples

#### ✅ Correct Usage
```python
# API endpoint handler
await api_key_manager.create_api_key(
    user_id=current_user.get("keycloak_id"),  # UUID for database
    name=request.name,
)

# API response
return {
    "user_id": "user:alice",  # OpenFGA format for client
    "username": "alice"
}
```

#### ❌ Incorrect Usage
```python
# Don't use plain usernames without prefix
user_id = "alice"  # Wrong!

# Don't use wrong format for Keycloak
await keycloak.get_user(user_id="user:alice")  # Should use UUID

# Don't use UUID for OpenFGA
await openfga.check(user="8c7b4e5d-...")  # Should use user:alice format
```

### Test Fixture Patterns

#### API Endpoint Tests
```python
@pytest.fixture
def test_client(mock_current_user):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    app = FastAPI()
    app.include_router(router)

    # Override auth dependency
    app.dependency_overrides[get_current_user] = lambda: mock_current_user

    return TestClient(app)

def test_endpoint(test_client, mock_current_user):
    response = test_client.get("/api/v1/resource")
    assert response.json()["user_id"] == mock_current_user["user_id"]
```

#### Admin Permission Tests
```python
@pytest.fixture
def mock_admin_user(mock_current_user):
    """User with elevated permissions"""
    admin_user = mock_current_user.copy()
    admin_user["roles"] = ["admin"]
    return admin_user

@pytest.fixture
def admin_test_client(mock_sp_manager, mock_admin_user):
    # ... setup with mock_admin_user
    return TestClient(app)
```

---

## Running Tests

### Run All Tests
```bash
pytest
```

### Run by Category
```bash
pytest -m unit           # Unit tests only
pytest -m api            # API tests only
pytest -m integration    # Integration tests only
pytest -m e2e            # E2E tests only (requires infrastructure)
```

### Run by File
```bash
pytest tests/api/test_api_keys_endpoints.py
pytest tests/test_gdpr.py::TestGDPREndpoints
```

### Run Specific Test
```bash
pytest tests/api/test_api_keys_endpoints.py::TestCreateAPIKey::test_create_api_key_success
```

### Useful Flags
```bash
pytest -v              # Verbose output
pytest -x              # Stop on first failure
pytest --tb=short      # Short traceback format
pytest -k "api_key"    # Run tests matching pattern
pytest --lf            # Run last failed tests
pytest --co            # Show collected tests without running
```

### E2E Infrastructure Setup
```bash
# Start test infrastructure
docker compose -f docker-compose.test.yml up -d

# Wait for services to be healthy (30-60s)
docker compose -f docker-compose.test.yml ps

# Run E2E tests
TESTING=true pytest -m e2e

# Cleanup
docker compose -f docker-compose.test.yml down -v
```

---

## TDD Best Practices

### 1. Red-Green-Refactor Cycle
```python
# RED: Write failing test first
def test_new_feature():
    result = new_function()
    assert result == expected_value  # Fails - function doesn't exist

# GREEN: Implement minimal code to pass
def new_function():
    return expected_value  # Passes

# REFACTOR: Improve implementation
def new_function():
    # Clean, efficient implementation
    return calculate_expected_value()
```

### 2. Test One Thing at a Time
```python
# ✅ Good - Single assertion
def test_create_api_key_returns_id():
    result = create_api_key(...)
    assert "key_id" in result

def test_create_api_key_returns_secret():
    result = create_api_key(...)
    assert "api_key" in result

# ❌ Bad - Multiple unrelated assertions
def test_create_api_key():
    result = create_api_key(...)
    assert "key_id" in result
    assert "api_key" in result
    assert result["name"] == "Test"
    assert len(result["api_key"]) > 20
```

### 3. Use Exact Mock Assertions
```python
# ✅ Good - Validates exact call
mock_manager.create_api_key.assert_called_once_with(
    user_id="8c7b4e5d-1234-5678-abcd-ef1234567890",
    name="Test Key",
    expires_days=365,
)

# ❌ Bad - Doesn't validate parameters
mock_manager.create_api_key.assert_called()
```

### 4. Arrange-Act-Assert Pattern
```python
def test_endpoint():
    # Arrange - Set up test data
    user_data = {"name": "Alice", "email": "alice@example.com"}

    # Act - Perform the action
    response = client.post("/users", json=user_data)

    # Assert - Verify the outcome
    assert response.status_code == 201
    assert response.json()["name"] == "Alice"
```

### 5. Test Error Cases
```python
def test_create_api_key_max_keys_exceeded(test_client, mock_api_key_manager):
    """Test API key creation when user has reached the limit"""
    mock_api_key_manager.create_api_key.side_effect = ValueError(
        "Maximum of 5 API keys allowed per user"
    )

    response = test_client.post("/api/v1/api-keys/", json={...})

    assert response.status_code == 400
    assert "Maximum of 5 API keys" in response.json()["detail"]
```

### 6. Use Descriptive Test Names
```python
# ✅ Good - Clear what's being tested
def test_delete_user_account_without_confirmation():
    """Test deletion requires explicit confirmation"""

# ❌ Bad - Vague test name
def test_delete():
    """Test delete"""
```

---

## GDPR Testing Requirements

Tests for GDPR compliance endpoints must validate:

### Article 15 - Right to Access
- ✅ User can retrieve all personal data
- ✅ Data includes: profile, sessions, conversations, preferences, audit log, consents
- ✅ Export includes metadata (export_id, timestamp)

### Article 16 - Right to Rectification
- ✅ User can update profile fields
- ✅ Only provided fields are updated (partial update)
- ✅ Empty updates are rejected

### Article 17 - Right to Erasure
- ✅ Deletion requires explicit confirmation (`confirm=true`)
- ✅ All user data is deleted (sessions, conversations, preferences, consents)
- ✅ Audit logs are anonymized (not deleted)
- ✅ Audit record is created with deletion details

### Article 20 - Right to Data Portability
- ✅ Data exported in machine-readable format (JSON)
- ✅ CSV format supported for tabular data
- ✅ Export includes proper Content-Disposition headers
- ✅ Invalid formats are rejected (422 status)

### Article 21 - Right to Object (Consent)
- ✅ User can grant consent
- ✅ User can revoke consent
- ✅ Consent includes metadata (timestamp, IP, user agent)
- ✅ Current consent status can be retrieved

---

## Common Patterns

### Testing Async Endpoints
```python
@pytest.mark.asyncio
async def test_async_endpoint():
    async with httpx.AsyncClient(base_url="http://test") as client:
        response = await client.get("/async-endpoint")
        assert response.status_code == 200
```

### Mocking Async Methods
```python
from unittest.mock import AsyncMock

mock_service = AsyncMock()
mock_service.get_data.return_value = {"key": "value"}
mock_service.create.return_value = "created_id"
```

### Testing File Downloads
```python
def test_export_csv(test_client):
    response = test_client.get("/export?format=csv")

    # Verify headers
    assert "text/csv" in response.headers["content-type"]
    assert "attachment" in response.headers["content-disposition"]

    # Verify content
    content = response.content.decode("utf-8")
    assert "," in content  # CSV delimiter
```

---

## Troubleshooting

### Tests Fail with "No module named X"
```bash
# Ensure you're in the virtual environment
source .venv/bin/activate

# Install test dependencies
pip install -e ".[test]"
```

### Async Mocks Not Working
```python
# ✅ Use AsyncMock for async methods
mock_storage.get_data.return_value = {"data": "value"}

# ❌ Don't use regular Mock for async
mock_storage.get_data = Mock(return_value={"data": "value"})
```

### E2E Tests Skipping
```bash
# 1. Start infrastructure
docker compose -f docker-compose.test.yml up -d

# 2. Set environment variable
export TESTING=true

# 3. Wait for services (check health)
docker compose -f docker-compose.test.yml ps

# 4. Run tests
pytest -m e2e
```

### Fixture Scope Issues
- Use `scope="session"` for expensive setup (containers, database connections)
- Use `scope="module"` for per-file setup
- Use `scope="function"` (default) for test isolation
- Broader-scoped fixtures cannot use narrower-scoped ones

---

## Migration Notes

### Deprecated Patterns

#### ❌ Global `pytest_configure`
```python
# DEPRECATED: Don't use global initialization
def pytest_configure(config):
    init_observability(...)  # Creates global state
```

#### ✅ Container Fixtures
```python
# RECOMMENDED: Use container fixtures
@pytest.fixture
def container(test_container):
    return create_test_container()  # Isolated, no global state
```

### Migration Status
- ✅ API key tests: Migrated to shared fixtures
- ✅ Service principal tests: Migrated to shared fixtures
- ✅ GDPR tests: Using shared fixtures
- 🔄 E2E tests: Partially migrated (mocks → real infrastructure)
- 🔄 Container migration: In progress

---

## Contributing

### Adding New Tests

1. **Choose the right category**: unit, api, integration, or e2e
2. **Use shared fixtures**: Check `conftest.py` first
3. **Follow TDD**: Write failing test, then implement
4. **Test error cases**: Don't just test the happy path
5. **Use descriptive names**: Test name should explain what's being tested

### Updating Fixtures

1. **Update `conftest.py`**: For shared fixtures
2. **Document changes**: Update this file
3. **Run affected tests**: Ensure no regressions
4. **Use type hints**: Help IDE and future developers

---

## References

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [GDPR Requirements](https://gdpr-info.eu/)
- [OpenFGA Best Practices](https://openfga.dev/docs)
- [TDD Best Practices](https://martinfowler.com/bliki/TestDrivenDevelopment.html)

---

**Last Updated**: 2025-01-05
**Status**: ✅ Complete and current
