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

```text
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

### Performance & Benchmark Tests (`@pytest.mark.benchmark`)
- **Purpose**: Validate system performance and detect regressions
- **Dependencies**: pytest-benchmark plugin
- **Speed**: Slow (100 iterations, ~30s per benchmark suite)
- **Examples**: JWT encoding/decoding, OpenFGA authorization, LLM request handling
- **Location**: `tests/performance/`

**CODEX FINDINGS #2 & #4: Performance Optimizations**

**Finding #2: Timeout Test Performance**
- Problem: Timeout tests used real asyncio.sleep(5-10s), burning ~15s per run
- Solution: Reduced to 0.05-0.3s sleeps (100x faster, same behavior)
- Impact: Tests now complete in ~6s instead of 15s (60% speedup)
- Validation: Meta-tests prevent regression (test_performance_regression.py)

**Finding #4: Benchmark Opt-In Model**
- Problem: Benchmarks ran by default, slowing everyday test runs
- Solution: Benchmarks now skip unless explicitly requested
- Impact: 90% faster test runs (benchmarks skipped in 0.57s vs 30+ seconds)
- Usage: See "Run Performance Benchmarks" section above

**Running Performance Tests**:

```bash
# Run benchmarks (opt-in)
pytest --run-benchmarks

# Run only benchmarks (CI pattern)
pytest -m benchmark --benchmark-only

# Exclude benchmarks (default behavior)
pytest  # Benchmarks automatically skipped

# Compare benchmark results over time
pytest-benchmark compare 0001 0002

# View benchmark history
pytest-benchmark list
```

**Benchmark Test Structure**:

```python
from tests.performance.conftest import PercentileBenchmark

@pytest.mark.benchmark
class TestMyBenchmarks:
    def test_operation_performance(self, percentile_benchmark):
        """
        Benchmark operation with percentile-based assertions.

        Uses 100 iterations for statistical accuracy.
        """
        result = percentile_benchmark(my_operation, arg1, arg2)

        # Assert p95 latency < 10ms (more stable than mean)
        percentile_benchmark.assert_percentile(95, 0.010)

        # Assert p99 latency < 15ms
        percentile_benchmark.assert_percentile(99, 0.015)
```

**Why percentile-based assertions?**
- More stable than mean (resistant to outliers)
- Better reflects user experience (p95/p99 SLA targets)
- Industry standard for performance testing

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

### Run Performance Benchmarks (CODEX Finding #4)
```bash
# Benchmarks are SKIPPED by default for faster iteration

# Option 1: Run with custom flag
pytest --run-benchmarks

# Option 2: Run only benchmarks (CI pattern)
pytest -m benchmark --benchmark-only

# Option 3: Exclude benchmarks explicitly
pytest -m "not benchmark"

# Compare benchmark results
pytest-benchmark compare 0001 0002
```

**Why benchmarks are opt-in:**
- Benchmarks run 100 iterations for statistical accuracy (~30s per suite)
- Normal development doesn't need benchmark validation
- CI explicitly runs benchmarks in dedicated job
- 90% faster test runs for everyday development

### Run Tests Requiring CLI Tools (CODEX Finding #1)
```bash
# Tests requiring external CLI tools skip gracefully if tools not installed

# Kustomize tests (deployment validation)
pytest -m requires_kustomize
# Skips with message if kustomize not installed

# Kubectl tests (K8s integration)
pytest -m requires_kubectl
# Skips with message if kubectl not installed

# Helm tests (chart validation)
pytest -m requires_helm
# Skips with message if helm not installed

# Exclude CLI-dependent tests
pytest -m "not requires_kustomize and not requires_helm"
```

**Installation instructions:**
```bash
# Kustomize
curl -s https://raw.githubusercontent.com/kubernetes-sigs/kustomize/master/hack/install_kustomize.sh | bash

# Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Kubectl
# See: https://kubernetes.io/docs/tasks/tools/
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
# CODEX FINDING #3: E2E tests now auto-run when docker is available
# No need to set TESTING=true anymore!

# Start test infrastructure
docker compose -f docker-compose.test.yml up -d

# Wait for services to be healthy (30-60s)
docker compose -f docker-compose.test.yml ps

# Run E2E tests (infrastructure check is automatic)
pytest -m e2e

# Cleanup
docker compose -f docker-compose.test.yml down -v
```

### Run Meta-Validation (CODEX Finding #5)
```bash
# Comprehensive test suite validation
python scripts/validate_test_suite.py

# Strict mode (warnings treated as errors)
python scripts/validate_test_suite.py --strict

# Checks performed:
# - Marker consistency (no conflicting unit+integration markers)
# - Test naming conventions
# - Import guards for optional dependencies
# - CLI tool availability guards
```

### Git Hooks and Validation

**Updated:** 2025-11-13 - Reorganized for developer productivity and CI parity

This project uses a two-stage validation strategy to balance speed and comprehensiveness:

#### Pre-commit Hooks (Fast - < 30 seconds)
Runs on **changed files only** at commit time. Optimized for rapid iteration.

**What runs:**
- Auto-fixers: black, isort, trailing-whitespace, etc.
- Fast linters: flake8, bandit, shellcheck
- Critical safety: memory safety, fixture organization, async mock usage
- File-specific validators: workflow syntax, MDX frontmatter

```bash
# Test pre-commit performance
echo "# test" >> README.md
git add README.md
git commit -m "test: verify pre-commit speed"
# Target: < 30 seconds
```

#### Pre-push Hooks (Comprehensive - 8-12 minutes)
Runs on **all files** before push. Matches CI validation exactly to eliminate surprises.

**4-Phase Validation:**

**Phase 1: Fast Checks (< 30s)**
- Lockfile validation (`uv lock --check`)
- Workflow validation tests

**Phase 2: Type Checking (1-2 min, warning only)**
- MyPy type checking (non-blocking)

**Phase 3: Test Suite (3-5 min)**
- Unit tests: `pytest tests/ -m unit -x --tb=short`
- Smoke tests: `pytest tests/smoke/ -v --tb=short`
- Integration tests (last failed): `pytest tests/integration/ -x --tb=short --lf`
- Property tests: `HYPOTHESIS_PROFILE=ci pytest -m property -x --tb=short`

**Phase 4: Pre-commit Hooks (5-8 min)**
- All comprehensive validators (documentation, deployment, etc.)
- Runs with `--hook-stage push` flag

```bash
# Install hooks
make git-hooks
# Or: pre-commit install --hook-type pre-commit --hook-type pre-push

# Verify configuration
python scripts/validate_pre_push_hook.py

# Test push validation (full 4-phase suite)
git push
# Target: 8-12 minutes, matches CI exactly
```

#### Performance Monitoring

```bash
# Measure pre-commit performance
python scripts/measure_hook_performance.py --stage commit

# Measure pre-push performance
python scripts/measure_hook_performance.py --stage push

# Measure both stages
python scripts/measure_hook_performance.py --stage all
```

#### Expected Performance

| Stage | Target | Files | Description |
|-------|--------|-------|-------------|
| Pre-commit | < 30s | Changed only | Fast feedback for commits |
| Pre-push | 8-12 min | All files | Comprehensive CI-equivalent validation |

#### Benefits

- **Fast commits:** 80-90% faster than before (2-5 min → 15-30s)
- **Zero surprises:** Pre-push matches CI exactly
- **Early detection:** Catches issues before push, not in CI
- **CI reliability:** Expected 80%+ reduction in CI failures

#### Troubleshooting

If pre-commit hooks fail:
```bash
# See specific failures
pre-commit run --all-files

# Run specific hook
pre-commit run black --all-files

# Skip hooks (emergency only)
git commit --no-verify
```

If pre-push hooks fail:
```bash
# Run specific phase
uv run pytest tests/ -m unit  # Phase 3: Unit tests
uv run pytest tests/smoke/    # Phase 3: Smoke tests
pre-commit run --all-files --hook-stage push  # Phase 4

# Skip pre-push (emergency only - will likely fail in CI!)
git push --no-verify
```

#### Documentation

- Categorization: `docs-internal/HOOK_CATEGORIZATION.md`
- Migration guide: `docs-internal/PRE_COMMIT_PRE_PUSH_REORGANIZATION.md`
- Performance monitoring: `scripts/measure_hook_performance.py`

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

## Regression Test Patterns

### Overview

Regression tests prevent fixed bugs from reoccurring by encoding the fix as a permanent test case. This section documents patterns for writing effective regression tests based on real Codex findings.

### Pattern 1: API Contract Violations

**Problem**: Implementation doesn't match documented API schema.

**Example**: API key creation returned `created` timestamp to Keycloak but omitted it from the response, violating `CreateAPIKeyResponse` schema.

**Regression Test Pattern**:
```python
def test_api_response_matches_schema():
    """
    REGRESSION TEST: Ensure response includes all required schema fields.

    Previous bug: API stored 'created' timestamp but didn't return it,
    causing clients to receive empty string as fallback.
    """
    # Arrange
    manager = APIKeyManager(...)

    # Act
    result = await manager.create_api_key(user_id="test", name="Test Key")

    # Assert - Verify ALL required fields present
    assert "key_id" in result, "key_id is required by schema"
    assert "api_key" in result, "api_key is required by schema"
    assert "name" in result, "name is required by schema"
    assert "created" in result, "created is required by CreateAPIKeyResponse schema"
    assert "expires_at" in result, "expires_at is required by schema"

    # Assert - Verify field is valid, not just present
    assert result["created"] != "", "created must not be empty string"
    created_dt = datetime.fromisoformat(result["created"])
    assert abs((datetime.utcnow() - created_dt).total_seconds()) < 60
```

**Key Principles**:
- Test against the schema/contract, not just implementation
- Validate field presence AND validity
- Document the original bug in test docstring
- Use descriptive assertion messages

**Files**: `tests/test_api_key_manager.py:105-141`

### Pattern 2: API Parameter Type Confusion

**Problem**: Method expects specific parameter type (UUID) but receives different type (username).

**Example**: `get_service_principal()` called `get_user(f"svc_{service_id}")` but `get_user()` expects UUID, not username.

**Regression Test Pattern**:
```python
def test_parameter_type_enforcement():
    """
    REGRESSION TEST: Ensure correct API method is used for parameter type.

    Previous bug: get_user() expects UUID but was called with username,
    causing 404 errors. Should use get_user_by_username() instead.
    """
    # Arrange
    service_id = "test-service"
    expected_username = f"svc_{service_id}"

    # Mock the CORRECT method to return data
    mock_client.get_user_by_username = AsyncMock(return_value={
        "id": "user-uuid-123",
        "username": expected_username,
        ...
    })

    # Mock the INCORRECT method to raise error if called
    mock_client.get_user = AsyncMock(
        side_effect=Exception("get_user requires UUID, not username")
    )

    # Act
    result = await manager.get_service_principal(service_id)

    # Assert - Verify CORRECT method was called
    mock_client.get_user_by_username.assert_called_once_with(expected_username)
    # If get_user was called incorrectly, exception would have been raised
    assert result is not None
```

**Key Principles**:
- Mock both correct and incorrect methods
- Make incorrect method raise exception to catch misuse
- Verify exact method calls with parameter validation
- Test the integration point, not just the function

**Files**: `tests/test_service_principal_manager.py:320-368`

### Pattern 3: Test Time Bombs (Future-Dated Values)

**Problem**: Tests use real future values that will break when those values become reality.

**Example**: Tests used "gpt-5" which will break when OpenAI releases GPT-5.

**Regression Test Pattern**:
```python
# ❌ BAD: Will break when GPT-5 is released
TEST_MODEL = "gpt-5"

# ✅ GOOD: Obviously fake, will never conflict
TEST_NONEXISTENT_OPENAI_MODEL = "gpt-999-test-nonexistent"
TEST_NONEXISTENT_ANTHROPIC_MODEL = "claude-999-test-nonexistent"
TEST_NONEXISTENT_GOOGLE_MODEL = "gemini-999-test-nonexistent"

def test_missing_credentials_warning():
    """Test that config warns about missing API keys for fallback models."""
    settings = Settings(
        openai_api_key=None,
        fallback_models=[TEST_NONEXISTENT_OPENAI_MODEL],  # Clearly fake
    )

    settings._validate_fallback_credentials()

    # Test behavior, not specific model name
    assert any(TEST_NONEXISTENT_OPENAI_MODEL in log.message for log in logs)
    assert any("OPENAI_API_KEY" in log.message for log in logs)
```

**Key Principles**:
- Use obviously fake values (999, nonexistent, test)
- Test behavior/logic, not specific values
- Constants make intent clear
- Prevents time-bomb test failures

**Files**: `tests/test_config_validation.py:16-17, 28, 46, 62, 74, 115, 127`

### Pattern 4: Mock-Based Tests Hiding Bugs

**Problem**: Mock provides fields that real implementation doesn't return.

**Example**: API key endpoint test mocked `create_api_key()` return value with "created" field, but real implementation didn't return it.

**Anti-Pattern**:
```python
# ❌ BAD: Mock hides the bug
def test_create_api_key_endpoint(mock_manager):
    # Mock provides "created" field
    mock_manager.create_api_key.return_value = {
        "key_id": "123",
        "api_key": "key",
        "name": "Test",
        "created": "2025-01-01T00:00:00",  # Mock provides this
        "expires_at": "2026-01-01T00:00:00"
    }

    response = client.post("/api-keys", json={...})
    assert response.json()["created"]  # Passes but implementation broken!
```

**Fixed Pattern**:
```python
# ✅ GOOD: Test real implementation behavior
def test_create_api_key_returns_created_timestamp(manager):
    """Test that create_api_key ACTUALLY returns created timestamp."""
    # Use REAL manager, not mock
    result = await manager.create_api_key(
        user_id="test", name="Test Key", expires_days=365
    )

    # Test what the implementation actually returns
    assert "created" in result, "create_api_key must return created timestamp"
    assert result["created"] != "", "created must not be empty"
```

**Key Principles**:
- Test manager/service layer directly, not just API layer
- Mocks should match reality exactly
- Add tests at multiple layers (manager + endpoint)
- Use real implementations when possible

**Trade-offs**:

| Approach | Pros | Cons | When to Use |
|----------|------|------|-------------|
| **Mock Everything** | Fast, isolated, no dependencies | Can hide contract violations | Unit tests for logic |
| **Real Implementation** | Catches contract bugs, realistic | Slower, more dependencies | Critical paths, regression tests |
| **Hybrid (Recommended)** | Balance speed and confidence | Requires careful planning | Most scenarios |

**Recommendation**: For regression tests of contract violations, always test the real implementation at least once, then use mocks for variations.

### Pattern 5: CLI Smoke Tests

**Problem**: CLI commands had zero test coverage, making refactoring risky.

**Regression Test Pattern**:
```python
from click.testing import CliRunner

def test_cli_command_help():
    """Smoke test: Ensure CLI command is accessible and documented."""
    runner = CliRunner()
    result = runner.invoke(cli, ["command", "--help"])

    assert result.exit_code == 0, "Help should always succeed"
    assert "description text" in result.output
    assert "--option" in result.output
```

**Key Principles**:
- Smoke tests ensure commands exist and are callable
- Test `--help` output for documentation
- Don't test full functionality (that's integration tests)
- Fast, no file I/O or side effects

**Files**: `tests/test_cli.py:1-113`

### Preventing Regressions with Pre-commit Hooks

After fixing bugs, add pre-commit hooks to prevent similar issues:

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: validate-api-schemas
        name: Validate API Response Schemas
        entry: python scripts/validate_api_schemas.py
        language: python
        pass_filenames: false

      - id: check-parameter-types
        name: Check API Parameter Type Confusion
        entry: python scripts/check_parameter_types.py
        language: python
        types: [python]
```

### Summary Checklist

When writing regression tests:

- [ ] **Document the bug** in test docstring with "REGRESSION TEST" marker
- [ ] **Test at correct layer** (manager/service for contract bugs, not just API)
- [ ] **Validate ALL required fields** from schemas/contracts
- [ ] **Use real implementations** for critical contract validations
- [ ] **Avoid test time bombs** with obviously fake constants
- [ ] **Mock the right methods** and make wrong methods fail explicitly
- [ ] **Add pre-commit hooks** to prevent similar bugs
- [ ] **Update documentation** with lessons learned

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

**Last Updated**: 2025-11-10
**Status**: ✅ Complete and current

**Recent Updates**:
- 2025-11-10: Added comprehensive regression test patterns section documenting fixes for Codex findings
- 2025-01-05: Initial comprehensive testing guide
