# Test Suite

Comprehensive test suite for MCP Server with LangGraph, following best practices for production Python applications.

## Directory Structure

**🎉 Restructured November 2025** - Test suite reorganized from 55 files in root to 1 file, with logical categorization into 24 subdirectories for improved maintainability. See `TESTING_STRATEGY_VALIDATION_REPORT.md` for full details.

```
tests/
├── conftest.py                    # Shared fixtures (2400 lines, -9% from modularization)
│
├── test_app_factory.py            # Only remaining root test (app factory initialization)
│
├── fixtures/                      # 📦 Modular fixture packages (Phase 3)
│   ├── __init__.py               #     Package initialization with loading rules
│   ├── docker_fixtures.py        #     Docker Compose lifecycle, health checks (183 lines)
│   └── time_fixtures.py          #     Time freezing for deterministic tests (42 lines)
│
├── api/                           # REST API endpoint tests
│   ├── test_api_keys_endpoints.py
│   ├── test_conversation_api.py
│   ├── test_execution_api.py
│   ├── test_monitoring_api.py
│   └── test_service_principals_endpoints.py
│
├── benchmarks/                    # Performance benchmarking
│   ├── scenarios/                #     Benchmark scenario definitions
│   └── test_*.py                 #     Pytest-benchmark performance tests
│
├── builder/                       # Graph builder tests
│   ├── api/                      #     Builder API tests
│   └── test_*.py                 #     Builder logic tests
│
├── cli/                           # CLI command tests
│   └── test_*.py                 #     Command-line interface tests
│
├── contract/                      # Contract testing (MCP, OpenAPI)
│   ├── test_mcp_protocol_contract.py
│   └── test_openapi_spec.py
│
├── core/                          # Core functionality tests
│   ├── interrupts/               #     Interrupt handling tests
│   └── test_*.py                 #     Core logic tests
│
├── deployment/                    # Deployment configuration validation
│   └── test_*.py                 #     Terraform, K8s manifest tests
│
├── deployments/                   # Deployment-specific tests
│   └── test_*.py                 #     Environment-specific deployment tests
│
├── e2e/                           # 🚀 End-to-end user journey tests
│   ├── test_full_user_journey.py #     Complete user workflows (6 journeys)
│   ├── test_real_clients.py      #     Real infrastructure integration
│   ├── test_scim_provisioning.py #     SCIM provisioning workflows
│   ├── real_clients.py           #     Real Keycloak/MCP clients
│   └── helpers.py                #     E2E test helpers (mock clients)
│
├── helpers/                       # Test helper utilities
│   └── test_*.py                 #     Shared test utilities
│
├── infrastructure/                # Infrastructure tests (non-K8s)
│   └── test_*.py                 #     Docker, database, cache tests
│
├── integration/                   # 🔗 Integration test suites (by domain)
│   ├── api/                      #     API integration tests
│   ├── compliance/               #     GDPR, SOC2 compliance tests
│   ├── contract/                 #     Contract integration tests
│   ├── core/                     #     Core integration tests
│   ├── deployment/               #     Deployment integration tests
│   ├── execution/                #     Execution engine integration
│   ├── health/                   #     Health check integration
│   ├── infrastructure/           #     Infrastructure integration
│   ├── patterns/                 #     Design pattern tests
│   ├── property/                 #     Property-based integration
│   ├── regression/               #     Regression prevention tests
│   ├── resilience/               #     Resilience pattern tests
│   └── security/                 #     Security integration tests
│
├── kubernetes/                    # Kubernetes-specific tests
│   └── test_*.py                 #     K8s manifest validation
│
├── llm/                           # LLM provider tests
│   └── test_*.py                 #     LangChain, Pydantic AI tests
│
├── meta/                          # 🔍 Meta-validation (tests that test tests)
│   ├── ci/                       #     CI/CD workflow validation
│   │   ├── test_workflow_dependencies.py  # Workflow job dependency validation
│   │   ├── test_workflow_security.py      # Workflow secret security patterns
│   │   └── test_workflow_syntax.py        # Actionlint syntax validation
│   ├── infrastructure/           #     Infrastructure configuration tests
│   │   └── test_docker_paths.py  #     Docker Python path validation
│   └── validation/               #     Test suite validation scripts
│       └── test_*.py             #     Test organization enforcement
│
├── middleware/                    # Middleware component tests
│   └── test_*.py                 #     Middleware logic tests
│
├── monitoring/                    # Observability tests
│   └── test_*.py                 #     Metrics, tracing, logging tests
│
├── performance/                   # 📊 Performance regression tests
│   ├── test_*.py                 #     Percentile-based performance validation
│   └── *.ipynb                   #     Jupyter notebook analysis
│
├── property/                      # 🎲 Property-based tests (Hypothesis)
│   └── test_*.py                 #     Generative testing with Hypothesis
│
├── regression/                    # Regression prevention tests
│   └── test_*.py                 #     Regression test suite
│
├── resilience/                    # Resilience pattern tests
│   └── test_*.py                 #     Circuit breaker, retry, timeout tests
│
├── scripts/                       # Test automation scripts
│   └── *.py                      #     CI/CD helper scripts
│
├── security/                      # 🔒 Security testing
│   ├── test_api_key_*.py         #     API key security tests
│   ├── test_authorization_*.py   #     OpenFGA authorization tests
│   ├── test_rbac_*.py            #     RBAC implementation tests
│   └── test_secrets_*.py         #     Secret management tests
│
├── smoke/                         # 💨 Smoke tests (fast validation)
│   └── test_*.py                 #     Quick sanity checks
│
├── terraform/                     # Terraform IaC tests
│   └── test_*.py                 #     Terraform plan validation
│
├── tools/                         # Tool implementation tests
│   └── test_*.py                 #     MCP tool logic tests
│
├── unit/                          # ⚡ Pure unit tests (no dependencies)
│   ├── auth/                     #     Authentication logic
│   ├── config/                   #     Configuration management
│   ├── core/                     #     Core business logic
│   ├── documentation/            #     Documentation generation
│   ├── execution/                #     Execution engine
│   ├── health/                   #     Health check logic
│   ├── llm/                      #     LLM integration
│   ├── observability/            #     Observability logic
│   ├── resilience/               #     Resilience patterns
│   ├── session/                  #     Session management
│   ├── storage/                  #     Storage layer
│   └── tools/                    #     Tool implementations
│
├── utils/                         # Test utilities
│   └── *.py                      #     Helper functions
│
└── validation_lib/                # Validation library tests
    └── test_*.py                 #     Input validation tests
```

### Reorganization Impact

**Before (Phase 1 baseline)**:
- 55 test files in root directory
- Difficult to navigate
- No clear categorization
- Mixed concerns (unit, integration, meta-validation)

**After (Phase 2 completed November 2025)**:
- **1 test file in root** (98% reduction)
- **24 logical subdirectories**
- **44 files relocated** to appropriate categories
- Clear separation of concerns
- Easier navigation and maintenance

**Key Improvements**:
1. **97% root directory reduction** - Only `test_app_factory.py` remains in root
2. **Logical categorization** - Tests grouped by domain (api, core, security, etc.)
3. **Meta-validation separation** - CI/infrastructure tests in `tests/meta/`
4. **Integration test organization** - 14 subdirectories under `tests/integration/`
5. **Modular fixtures** - Extracted into `tests/fixtures/` package (Phase 3)

See `docs-internal/TESTING_STRATEGY_VALIDATION_REPORT.md` and `tests/MIGRATION_GUIDE.md` for complete reorganization details and file relocation mappings.

## 🎯 Quick Start - Testing the New Features

### Test Infrastructure Setup

We now have a dedicated test environment using **docker-compose.test.yml** with isolated services (offset ports):

```bash
# Start test infrastructure (PostgreSQL, Redis, OpenFGA, Keycloak, Qdrant)
make test-infra-up

# Run new tests
make test-new

# Run specific test suites
make test-api           # API endpoint tests
make test-mcp-server    # MCP server unit tests
make test-e2e           # End-to-end user journeys (requires infrastructure)

# Stop test infrastructure
make test-infra-down
```

### New Test Categories Added

1. **API Endpoint Tests** (`tests/api/`): REST API contract testing
2. **E2E Tests** (`tests/e2e/`): Complete user journey testing
3. **MCP Server Unit Tests** (`tests/unit/`): Comprehensive server coverage
4. **Performance Benchmarks** (`tests/performance/`): Percentile-based performance validation
5. **Meta-Validation Tests** (`tests/meta/`): Test suite structure validation
6. **Deployment Tests** (`tests/deployment/`): K8s manifest and Helm chart validation

**CODEX Findings Addressed (2025-11-09)**:
- ✅ CLI tool guards for kustomize/helm/kubectl (Finding #1)
- ✅ Timeout test performance optimization (Finding #2)
- ✅ E2E tests auto-run with docker (Finding #3)
- ✅ Benchmarks opt-in by default (Finding #4)
- ✅ Meta-validation script for maintainability (Finding #5)
- ✅ Enabled skipped singleton tests (Finding #6)
- ✅ Helm tests use xfail(strict=True) (Finding #7)

See [New Testing Features](#new-testing-features) section below for details.

---

## Test Categories

### Unit Tests (`@pytest.mark.unit`)

**Purpose**: Fast, isolated tests with no external dependencies

**Characteristics**:
- Use mocks for LLM, OpenFGA, Infisical
- No network calls
- No Docker containers required
- Execute in <5 seconds total

**Run**:
```bash
pytest -m unit -v
make test-unit
```

**Files**:
- `test_agent.py` - Agent routing and message handling (mocked)
- `test_auth.py` - Authentication logic (mocked JWT)
- `test_feature_flags.py` - Feature flag configuration
- `test_health_check.py` - Health endpoint logic
- `test_openfga_client.py` - Authorization client logic (mocked)
- `test_pydantic_ai.py` - Pydantic AI integration (mocked)
- `test_secrets_manager.py` - Secret management (mocked Infisical)

### Integration Tests (`@pytest.mark.integration`)

**Purpose**: Test interactions with real external services

**Characteristics**:
- Require Docker infrastructure (`make setup-infra`)
- Real OpenFGA, observability stack
- May use real LLM APIs (if configured)
- Execute in 10-60 seconds

**Prerequisites**:
```bash
# Start infrastructure
make setup-infra

# Initialize OpenFGA
make setup-openfga
```

**Run**:
```bash
pytest -m integration -v
make test-integration
```

**Files** (same files as unit, different marker):
- `test_agent.py` - End-to-end agent execution
- `test_mcp_streamable.py` - MCP server integration
- `test_openfga_client.py` - Real OpenFGA authorization
- `test_pydantic_ai.py` - Real Pydantic AI routing
- `test_secrets_manager.py` - Real Infisical secret retrieval

### Contract Tests (`@pytest.mark.contract`)

**Location**: `contract/`

**Purpose**: Verify external API contracts (MCP protocol, OpenAPI)

**Run**:
```bash
pytest -m contract -v
make test-contract
```

**Files**:
- `test_mcp_protocol.py` - MCP JSON-RPC compliance
- `test_openapi_compliance.py` - OpenAPI schema validation

### Property-Based Tests (`@pytest.mark.property`)

**Location**: `property/`

**Purpose**: Test invariants with generated inputs (Hypothesis)

**Run**:
```bash
pytest -m property -v
make test-property
```

**Files**:
- `test_llm_properties.py` - LLM factory properties
- `test_auth_properties.py` - Authentication invariants

**Configuration**: See `pyproject.toml` `[tool.hypothesis]`

### Performance Tests (`@pytest.mark.benchmark`)

**Location**: `performance/`

**Purpose**: Measure and track performance metrics

**Run**:
```bash
pytest -m benchmark -v --benchmark-only
make benchmark
```

**Files**:
- `test_agent_benchmarks.py` - Agent response time
- `test_auth_benchmarks.py` - Authorization overhead

**Reports**: Saved to `.benchmarks/`

### Regression Tests (`@pytest.mark.regression`)

**Location**: `regression/`

**Purpose**: Detect performance regressions over time

**Run**:
```bash
pytest -m regression -v
make test-regression
```

**Files**:
- `test_response_time.py` - Response time regression detection

## Test Markers

All available markers are defined in `pyproject.toml`:

```python
@pytest.mark.unit          # Unit tests (fast, no deps)
@pytest.mark.integration   # Integration tests (require infra)
@pytest.mark.e2e          # End-to-end tests
@pytest.mark.slow         # Tests > 1 second
@pytest.mark.auth         # Authentication/authorization
@pytest.mark.openfga      # OpenFGA-specific
@pytest.mark.infisical    # Infisical-specific
@pytest.mark.mcp          # MCP protocol
@pytest.mark.observability # OpenTelemetry/metrics
@pytest.mark.benchmark    # Performance benchmarks
@pytest.mark.property     # Property-based tests
@pytest.mark.contract     # Contract tests
@pytest.mark.regression   # Regression tests
@pytest.mark.mutation     # Mutation testing
```

## Running Tests

### Quick Commands

```bash
# All tests
make test
pytest -v

# By category
make test-unit
make test-integration
make test-contract
make test-property
make test-regression

# Specific file
pytest tests/test_agent.py -v

# Specific test
pytest tests/test_agent.py::test_create_agent -v

# With coverage
make test-coverage
pytest --cov=. --cov-report=html
# View: htmlcov/index.html

# With output
pytest -v -s

# Stop on first failure
pytest -x

# Last failed tests only
pytest --lf
```

### Advanced Usage

```bash
# Run tests in parallel (requires pytest-xdist)
pytest -n auto

# Run tests with specific marker
pytest -m "unit and not slow"

# Run tests matching pattern
pytest -k "test_auth"

# Verbose output with trace
pytest -vv --tb=long

# Collect only (don't run)
pytest --collect-only

# List all markers
pytest --markers
```

## Test Configuration

### pytest Configuration

**Location**: `pyproject.toml` `[tool.pytest.ini_options]`

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]
addopts = "-v --strict-markers --tb=short"
```

### Coverage Configuration

**Location**: `pyproject.toml` `[tool.coverage.run]`

**Exclusions**:
- Tests themselves
- MCP server entry points (tested via integration)
- Examples and scripts

**Target**: 80%+ coverage for core modules

### Hypothesis Configuration

**Location**: `pyproject.toml` `[tool.hypothesis]`

```toml
max_examples = 100
deadline = 5000  # ms
database = ".hypothesis/examples"
```

## Writing Tests

### Test Structure

```python
import pytest
from unittest.mock import Mock, patch, AsyncMock

@pytest.mark.unit
def test_feature_name():
    """
    Test description.

    Verifies:
    - Expected behavior 1
    - Expected behavior 2
    """
    # Arrange
    input_data = {"key": "value"}

    # Act
    result = function_under_test(input_data)

    # Assert
    assert result == expected_output
```

### Async Tests

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_feature():
    """Test async function."""
    result = await async_function()
    assert result is not None
```

### Integration Tests with Fixtures

```python
@pytest.mark.integration
@pytest.mark.openfga
async def test_with_openfga(openfga_client, openfga_store_id):
    """Test with real OpenFGA."""
    # Use real client from fixture
    allowed = await openfga_client.check_permission(
        user="user:test",
        relation="viewer",
        object="conversation:1"
    )
    assert allowed is False  # No tuple written yet
```

### Property-Based Tests

```python
from hypothesis import given, strategies as st

@pytest.mark.property
@given(
    message=st.text(min_size=1, max_size=1000),
    user_id=st.from_regex(r"^user:[a-z]+$")
)
def test_agent_properties(message, user_id):
    """Test agent with generated inputs."""
    # Hypothesis generates many test cases
    result = agent.process(message, user_id)
    assert result is not None
```

## Fixtures

### Common Fixtures (conftest.py)

```python
# FastAPI Application Fixtures (Reusable)
@pytest.fixture
def test_app_settings()         # Test-specific application settings
@pytest.fixture
def test_fastapi_app()          # Configured FastAPI app with test dependencies
@pytest.fixture
def test_client()               # Synchronous TestClient (use for most API tests)
@pytest.fixture
def test_async_client()         # Async HTTPX client for async endpoint testing

# Mock fixtures
@pytest.fixture
def mock_llm_factory()
@pytest.fixture
def mock_openfga_client()
@pytest.fixture
def mock_infisical_client()
@pytest.fixture
def mock_pydantic_agent()

# Real service fixtures (integration)
@pytest.fixture
def openfga_store_id()
@pytest.fixture
def openfga_client()

# Test data fixtures
@pytest.fixture
def sample_messages()
@pytest.fixture
def sample_user_id()
```

### Using Fixtures

```python
# Using FastAPI TestClient (recommended for API tests)
def test_api_endpoint(test_client):
    """Test API endpoint using shared TestClient fixture."""
    response = test_client.get("/health/")
    assert response.status_code == 200

# Using async client for async endpoints
async def test_async_endpoint(test_async_client):
    """Test async API endpoint."""
    response = await test_async_client.get("/api/v1/users")
    assert response.status_code == 200

# Using mock fixtures
def test_with_mock(mock_llm_factory):
    """Test uses mock LLM factory from fixture."""
    assert mock_llm_factory is not None
```

**Benefits of using shared fixtures:**
- No need to create TestClient in each test file
- Consistent dependency overrides across all tests
- Easier to add authentication/authorization test permutations
- Reduces boilerplate code

### Fixture Organization Best Practices (CRITICAL)

**⚠️ IMPORTANT**: Session/module-scoped autouse fixtures MUST be in `tests/conftest.py`

This rule is enforced automatically via:
- Pre-commit hook: `validate-fixture-organization`
- Runtime plugin: `tests/conftest_fixtures_plugin.py`
- Test validation: `tests/test_fixture_organization.py`

**✅ CORRECT** - Autouse fixture in conftest.py:
```python
# tests/conftest.py
@pytest.fixture(scope="session", autouse=True)
def init_test_observability():
    """Initialize observability for all tests."""
    # Runs once per session automatically
    yield
```

**❌ INCORRECT** - Duplicate autouse fixtures:
```python
# tests/some_module/test_feature.py
@pytest.fixture(scope="module", autouse=True)  # ❌ DON'T DO THIS!
def init_test_observability():
    # This creates duplicates and causes issues
    yield
```

**Why this matters:**
- **Performance**: Duplicates cause unnecessary re-initialization (25× observed)
- **Maintainability**: Changes needed in multiple places
- **Reliability**: Potential race conditions and state pollution

**Test-specific fixtures should NOT be autouse:**
```python
# ✅ GOOD - Explicit fixture usage
def test_my_feature(test_circuit_breaker_config):
    # Fixture only used when needed
    pass

# ✅ GOOD - Module-wide fixture usage
pytestmark = pytest.mark.usefixtures("test_circuit_breaker_config")

def test_feature_a():
    pass

def test_feature_b():
    pass
```

**References:**
- ADR-0043: Pytest Fixture Consolidation (`adr/adr-0043-pytest-fixture-consolidation.md`)
- Evidence Report: `docs-internal/CODEX_FINDINGS_VALIDATION_REPORT.md`
- Global Guidelines: `~/.claude/CLAUDE.md` (Pytest Fixture Best Practices)

## Test Environment Variables

For integration tests, configure via `.env`:

```bash
# LLM Provider (for integration tests)
GOOGLE_API_KEY=your-key-here
# OR
ANTHROPIC_API_KEY=your-key-here

# OpenFGA (for integration tests)
OPENFGA_STORE_ID=from-setup-script
OPENFGA_MODEL_ID=from-setup-script

# Disable observability in tests (optional)
ENABLE_TRACING=false
ENABLE_METRICS=false
ENABLE_CONSOLE_EXPORT=false
```

**Never commit API keys to version control!**

## Continuous Integration

### GitHub Actions

Tests run automatically on:
- Pull requests
- Pushes to main

**Workflow**: `.github/workflows/test.yaml`

**Matrix Testing**: Python 3.10, 3.11, 3.12

### Pre-commit Hooks

Install pre-commit hooks to run tests locally:

```bash
pre-commit install
```

**Config**: `.pre-commit-config.yaml`

## Troubleshooting

### Common Integration Test Issues (Updated 2025-11-21)

**IMPORTANT**: Recent fixes addressed 7 major failure buckets affecting 78+ tests. If experiencing failures, review the CODEX FINDING FIX comments in the code for context.

#### 1. RuntimeError: Future attached to a different loop (34 tests)

**Symptom**: `RuntimeError: Future <Future pending> attached to a different loop than the current one`

**Root Cause**: Session-scoped async fixtures using function-scoped event loop

**Fix Applied**: Added explicit `loop_scope="session"` to async fixtures in `tests/conftest.py`:
- `postgres_connection_real` (line 1424)
- `redis_client_real` (line 1487)
- `openfga_client_real` (line 1524)

**Validation**: Run postgres compliance tests:
```bash
pytest tests/integration/compliance/test_postgres_*.py -v
```

**Prevention**: Pre-commit hook validates `asyncio_default_fixture_loop_scope="session"` in `pyproject.toml`

---

#### 2. GDPR Endpoint 401 Unauthorized (6 tests)

**Symptom**: All GDPR endpoint tests fail with 401 Unauthorized

**Root Cause**: Missing authentication middleware in test fixture. Endpoints check `request.state.user` (set by middleware), but test only overrode dependencies.

**Fix Applied**: Added mock auth middleware to `tests/integration/test_gdpr_endpoints.py:109-118`:
```python
@app.middleware("http")
async def mock_auth_middleware(request_obj: Request, call_next):
    request_obj.state.user = mock_auth_user
    response = await call_next(request_obj)
    return response
```

**Validation**: Run GDPR endpoint tests:
```bash
pytest tests/integration/test_gdpr_endpoints.py -v
```

---

#### 3. Docker Health-Check Tests Kill Main Infrastructure (8 tests)

**Symptom**: OSError: [Errno 111] Connect call failed ('127.0.0.1', 9432) after health check tests run

**Root Cause**: `docker compose down --remove-orphans` from health check tests tears down shared network containers

**Fix Applied**: Removed `--remove-orphans` flag from cleanup in `tests/integration/test_docker_health_checks.py` (lines 361, 427)

**Validation**: Run health checks then schema tests:
```bash
pytest tests/integration/test_docker_health_checks.py::TestDockerComposeHealthChecksIntegration::test_qdrant_health_check_works -v
pytest tests/integration/test_schema_initialization_timing.py -v
```

**Prevention**: Tests use isolated `COMPOSE_PROJECT_NAME` but share network

---

#### 4. Qdrant Port Already Allocated (3 tests)

**Symptom**: `Bind for 0.0.0.0:9333 failed: port is already allocated`

**Root Cause**: Health check tests try to start Qdrant on port already used by main infrastructure

**Fix Applied**: Added port-in-use check to `tests/integration/test_docker_health_checks.py:289-294`:
```python
if is_port_in_use(QDRANT_TEST_PORT):
    pytest.skip(f"Qdrant test port {QDRANT_TEST_PORT} already in use...")
```

**Validation**: Run health check test with main infrastructure running:
```bash
docker compose -f docker-compose.test.yml up -d
pytest tests/integration/test_docker_health_checks.py::TestDockerComposeHealthChecksIntegration::test_qdrant_health_check_works -v
```

---

#### 5. OpenFGA Initialization Timeout (3 tests)

**Symptom**: `pytest.skip: Failed to initialize OpenFGA after 3 attempts`

**Root Cause**: PostgreSQL migrations take >14s in slow CI environments

**Fix Applied**: Increased retry logic in `tests/conftest.py:1563-1564`:
- `max_retries`: 3 → 5
- `retry_delay`: 2.0 → 3.0
- Max wait time: 14s → 93s

**Validation**: Run OpenFGA-dependent tests:
```bash
pytest tests/integration/api/test_scim_security.py::test_openfga_admin_relation_check -v
```

---

#### 6. Kubernetes Health Probe Tests Run Unconditionally

**Symptom**: Tests fail when `HEALTH_CHECK_URL` not set

**Root Cause**: Incomplete `pytestmark = pytest.mark.skipif` (missing condition)

**Fix Applied**: Added proper skip condition to `tests/integration/test_kubernetes_health_probes.py:29-33`:
```python
pytestmark = pytest.mark.skipif(
    os.getenv("HEALTH_CHECK_URL") is None,
    reason="Kubernetes health probe tests require HEALTH_CHECK_URL..."
)
```

**Validation**: Tests should skip gracefully:
```bash
pytest tests/integration/test_kubernetes_health_probes.py -v
# Should see: SKIPPED (Kubernetes health probe tests require...)
```

---

#### 7. E2E Tests Missing MCP Server

**Symptom**: E2E tests marked xfail with "MCP server not running"

**Root Cause**: No MCP server in test infrastructure

**Fix Applied**:
1. Added `mcp-server-test` service to `docker-compose.test.yml` (lines 274-354)
2. Configured Keycloak confidential client in `tests/e2e/default-realm.json`
   (NOTE: Keycloak 26.x --import-realm requires filename to match realm name "default")
3. Updated `scripts/test-integration.sh` to start MCP server (line 220)

**Validation**: Check MCP server starts correctly:
```bash
docker compose -f docker-compose.test.yml up -d
docker compose -f docker-compose.test.yml ps mcp-server-test
curl http://localhost:8000/health
```

**E2E Test Status**:
- ✅ Infrastructure ready (6 tests passing: login, init, list_tools, chat, continue, get_conversation)
- ⏳ 23 tests remain xfail (features not yet implemented: search, token refresh, GDPR, service principals, API keys)

---

### Common Issues (General)

**Import errors**:
```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall in editable mode
pip install -e .
```

**OpenFGA connection errors** (integration tests):
```bash
# Start infrastructure
make setup-infra

# Initialize OpenFGA
make setup-openfga

# Update .env with OPENFGA_STORE_ID and OPENFGA_MODEL_ID
```

**Hypothesis flaky tests**:
```bash
# Increase deadline in pyproject.toml
[tool.hypothesis]
deadline = 10000  # 10 seconds
```

**Coverage not 100%**:
- Some modules intentionally excluded (see pyproject.toml)
- MCP entry points tested via integration tests
- Target is 80%+, not 100%

**Docker Compose services won't start**:
```bash
# Clean up all test containers and networks
docker compose -f docker-compose.test.yml down -v --remove-orphans

# Rebuild images
docker compose -f docker-compose.test.yml build --no-cache

# Start fresh
docker compose -f docker-compose.test.yml up -d
```

**Port conflicts**:
```bash
# Check what's using test ports
lsof -i :9432  # PostgreSQL
lsof -i :9080  # OpenFGA
lsof -i :9082  # Keycloak
lsof -i :9333  # Qdrant
lsof -i :8000  # MCP Server

# Stop conflicting processes or use different ports
```

### Debug Tests

```bash
# Print output (disable capture)
pytest -s

# Enter debugger on failure
pytest --pdb

# Run single test with full trace
pytest tests/test_agent.py::test_create_agent -vv --tb=long -s
```

## Best Practices

1. **Test Naming**: Use descriptive names - `test_feature_with_condition_expects_result`
2. **One Assert Per Test**: Focus tests on single behavior
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Use Fixtures**: Avoid code duplication
5. **Mock External Services**: Keep unit tests fast
6. **Test Edge Cases**: Empty inputs, None values, exceptions
7. **Use Markers**: Categorize tests properly
8. **Document**: Add docstrings explaining what's tested
9. **Async Tests**: Mark with `@pytest.mark.asyncio`
10. **Clean Up**: Use fixtures to ensure cleanup (yield pattern)

## Test Utilities and Helpers

### Mock Factories (`tests/utils/mock_factories.py`)

Reusable mock factories to prevent common test failures:

```python
from tests.utils.mock_factories import (
    create_mock_openfga_client,
    create_mock_llm_environment,
    create_isolated_circuit_breaker,
    verify_dependency_overrides,
)

# Create OpenFGA mock
mock_openfga = create_mock_openfga_client(authorized=True)

# Mock LLM environment variables
with create_mock_llm_environment(provider="azure"):
    factory = LLMFactory(provider="azure", ...)

# Isolated circuit breaker for testing
with create_isolated_circuit_breaker("openfga") as cb:
    # Test circuit breaker behavior
    ...

# Verify all dependencies are overridden
verify_dependency_overrides(
    app.dependency_overrides,
    [get_current_user, get_openfga_client, get_sp_manager],
)
```

**Use cases**:
- Prevent 401 errors from missing dependency overrides
- Avoid credential validation errors in LLM tests
- Test circuit breaker behavior without state pollution

### Shared API Fixtures (`tests/fixtures/api_fixtures.py`)

Reusable fixtures for FastAPI endpoint testing:

```python
from tests.fixtures.api_fixtures import mock_openfga_client, create_api_test_client

@pytest.fixture
def test_client(mock_openfga_client):
    """Create test client with OpenFGA mock"""
    return create_api_test_client(
        router=my_router,
        dependency_overrides={
            get_openfga_client: lambda: mock_openfga_client,
        },
    )
```

**Benefits**:
- Standardized test client setup
- Prevents async/sync dependency mismatch
- Automatic cleanup for xdist isolation

### API Testing Guide (`tests/API_TESTING.md`)

Comprehensive guide for testing FastAPI endpoints:
- Common issues and solutions (401 errors, async/sync mismatch)
- Dependency override patterns and checklists
- Troubleshooting guide with examples
- Required dependencies by endpoint type

**Must-read for**:
- Writing new API endpoint tests
- Debugging 401/403 errors in tests
- Understanding FastAPI dependency injection

## Coverage Reports

### Generate Coverage

```bash
# HTML report
pytest --cov=. --cov-report=html
open htmlcov/index.html

# Terminal report
pytest --cov=. --cov-report=term-missing

# XML report (for CI)
pytest --cov=. --cov-report=xml
```

### Coverage Targets

- **Core modules** (agent, auth, config): 90%+
- **LLM factory**: 85%+
- **Observability**: 80%+
- **Overall**: 80%+

## Mutation Testing

**Purpose**: Test the quality of tests themselves

**Run**:
```bash
make test-mutation
mutmut run
mutmut results
mutmut html
```

**Config**: `pyproject.toml` `[tool.mutmut]`

**Note**: Slow (30+ minutes), run periodically or in CI

## Test Infrastructure with Docker Compose

### Quick Start

We provide a lightweight `docker-compose.test.yml` for running integration tests with real services:

```bash
# Start test infrastructure
docker compose -f docker-compose.test.yml up -d

# Run integration tests
pytest -m integration

# Stop and clean up
docker compose -f docker-compose.test.yml down
```

### Services Included

- **Qdrant** (port 6333): Vector database for semantic search and dynamic context loading tests
- **Redis** (port 6379): For session management and conversation checkpoint tests
- **Postgres** (port 5432): For database integration tests

All services use `tmpfs` for faster performance and don't persist data between runs.

### Qdrant Integration Tests

The `qdrant_client` fixture enables previously-skipped Qdrant tests:

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_qdrant(qdrant_client):
    """Test using real Qdrant instance."""
    loader = DynamicContextLoader(
        qdrant_url="localhost",
        qdrant_port=6333,
        collection_name="test_my_collection",
    )
    # Test code...
```

**Enabled tests**:
- `test_dynamic_context_loader.py::test_full_workflow`
- `test_anthropic_enhancements_integration.py::test_index_search_load_workflow`
- `test_anthropic_enhancements_integration.py::test_progressive_discovery`

### Environment Variables

Override default ports if needed:

```bash
export QDRANT_URL=localhost
export QDRANT_PORT=6333
export REDIS_HOST=localhost
export REDIS_PORT=6379
export POSTGRES_HOST=localhost
export POSTGRES_PORT=5432
```

### Troubleshooting Test Infrastructure

**Qdrant not responding**:
```bash
# Check if running
curl http://localhost:6333/

# View logs
docker compose -f docker-compose.test.yml logs qdrant-test

# Restart
docker compose -f docker-compose.test.yml restart qdrant-test
```

**Redis connection issues**:
```bash
# Test connection
redis-cli -h localhost -p 6379 ping

# View logs
docker compose -f docker-compose.test.yml logs redis-test
```

**Clean slate**:
```bash
# Remove all test containers and volumes
docker compose -f docker-compose.test.yml down -v

# Start fresh
docker compose -f docker-compose.test.yml up -d
```

---

## 🆕 New Testing Features

### 1. API Endpoint Tests (`tests/api/`)

**Purpose**: Unit tests for REST API endpoints with comprehensive coverage.

**Files**:
- **`test_api_keys_endpoints.py`** - API key management endpoints
  - Create, list, rotate, revoke API keys
  - Kong validation endpoint (API key → JWT exchange)
  - Authorization and error handling
  - Coverage: 15+ test cases

- **`test_service_principals_endpoints.py`** - Service principal management endpoints
  - Create, list, get, delete service principals
  - Secret rotation
  - User association for permission inheritance
  - Authorization checks (owner verification)
  - Coverage: 18+ test cases

**Run**:
```bash
make test-api                           # Run all API tests
pytest tests/api/ -v                    # Verbose output
pytest tests/api/test_api_keys_endpoints.py -k "create"  # Specific tests
```

**Key Features**:
- FastAPI TestClient for HTTP testing
- Mocked dependencies (Keycloak, OpenFGA)
- Request/response schema validation
- Authentication/authorization testing
- Error case coverage

### 2. End-to-End Tests (`tests/e2e/`)

**Purpose**: Test complete user workflows from authentication to data management.

**File**: `test_full_user_journey.py`

**Test Journeys**:
1. **Standard User Flow**: Login → MCP Init → Chat → Search → Get Conversation → Token Refresh
2. **GDPR Compliance Flow**: Access Data → Export → Update Profile → Consent → Delete Account
3. **Service Principal Flow**: Create → Authenticate → Use → Associate → Rotate → Delete
4. **API Key Flow**: Create → Validate → Use → Rotate → Revoke
5. **Error Recovery**: Expired tokens, invalid credentials, authorization failures, rate limiting
6. **Multi-User Collaboration**: Share conversation, grant permissions, revoke access

**Prerequisites**:
```bash
# Start test infrastructure with isolated services
make test-infra-up

# Verify services are healthy
docker compose -f docker-compose.test.yml ps
```

**Run**:
```bash
make test-e2e                           # Run all E2E tests (auto-starts infrastructure)
TESTING=true pytest -m e2e -v           # Manual run with TESTING env var
pytest tests/e2e/ -k "journey" -v       # Run specific journey
```

**Infrastructure**:
- Uses **docker-compose.test.yml** (test-specific ports)
- PostgreSQL (9432), Redis (9379), OpenFGA (9080), Keycloak (9082), Qdrant (9333)
- Isolated from development environment
- Ephemeral storage (tmpfs) for speed

**Status**: ⚠️ Framework ready, tests marked with `pytest.skip()` pending infrastructure integration

### 3. MCP Server Unit Tests (`tests/unit/`)

**Purpose**: Comprehensive unit tests for MCP stdio server implementation.

**File**: `test_mcp_stdio_server.py`

**Coverage Areas**:
- Server initialization (with/without OpenFGA, fail-closed security)
- JWT authentication (missing token, invalid token, expired token)
- OpenFGA authorization (tool executor, conversation editor/viewer)
- Chat handler (new conversation, existing conversation, authorization checks)
- Response formatting (concise vs detailed)
- Error handling (agent failures, validation errors)
- Tool listing

**Run**:
```bash
make test-mcp-server                    # Run MCP server tests
pytest tests/unit/mcp/test_mcp_stdio_server.py -v
pytest tests/unit/mcp/test_mcp_stdio_server.py -k "auth" -v  # Auth tests only
```

**Key Features**:
- Mock OpenFGA, Keycloak, LangGraph
- Test fail-closed security patterns
- Production environment validation
- Conversation authorization logic
- Response optimization testing

**Target Coverage**: 85%+ on `src/mcp_server_langgraph/mcp/server_stdio.py`

### 4. Test Infrastructure (`docker-compose.test.yml`)

**Purpose**: Isolated test environment preventing interference with development services.

**Key Features**:
- **Port Offset**: All ports offset by 1000 (9432, 9379, 9080, 9082, 9333)
- **Ephemeral Storage**: tmpfs for speed, no persistent volumes
- **Fast Healthchecks**: 2-3s intervals vs 5-10s in dev
- **Reduced Resources**: Optimized limits for parallel execution
- **Test-Specific Config**: `TESTING=true`, reduced logging

**Services**:
| Service | Port | Usage |
|---------|------|-------|
| PostgreSQL | 9432 | OpenFGA + Keycloak database |
| Redis (checkpoints) | 9379 | LangGraph checkpointing |
| Redis (sessions) | 9380 | Session storage |
| OpenFGA | 9080 | Authorization service |
| Keycloak | 9082 | Authentication/SSO |
| Qdrant | 9333 | Vector database |

**Commands**:
```bash
# Lifecycle
make test-infra-up          # Start all test services
make test-infra-down        # Stop and clean (removes volumes)
make test-infra-logs        # View logs

# Manual control
docker compose -f docker-compose.test.yml up -d
docker compose -f docker-compose.test.yml ps
docker compose -f docker-compose.test.yml logs -f openfga-test
docker compose -f docker-compose.test.yml down -v
```

### 5. New Makefile Targets

**Test Infrastructure**:
```bash
make test-infra-up          # Start test infrastructure
make test-infra-down        # Stop and clean
make test-infra-logs        # View logs
```

**New Test Suites**:
```bash
make test-e2e               # End-to-end tests (auto-starts infrastructure)
make test-api               # API endpoint tests (unit)
make test-mcp-server        # MCP server unit tests
make test-new               # All newly added tests
make test-quick-new         # Quick parallel check
```

**Integration**:
- All new targets use `OTEL_SDK_DISABLED=true` for clean output
- Parallel execution where applicable (`-n auto`)
- Verbose output for debugging (`-v`)

### Test Coverage Improvements

**Before**:
- API endpoints: ❌ No dedicated tests
- MCP stdio server: ⚠️ Partial coverage
- E2E workflows: ❌ None
- Test infrastructure: ⚠️ Shared with dev

**After**:
- API endpoints: ✅ 33+ test cases covering all routes
- MCP stdio server: ✅ 85%+ coverage target
- E2E workflows: ✅ 7 implemented scenarios (39 total planned)
- Test infrastructure: ✅ Fully isolated environment

### Implementation Status (Updated After Codex Remediation)

- ✅ **Completed**:
  - docker-compose.test.yml (isolated infrastructure)
  - tests/api/ (33+ tests for all API endpoints)
  - tests/unit/mcp/test_mcp_stdio_server.py (20+ tests)
  - tests/e2e/test_full_user_journey.py:
    - ✅ Infrastructure tests (3/3): login, init, list_tools
    - ✅ Standard user journey (3/3): chat, continue, retrieve conversation
    - ✅ GDPR compliance (1/7): data export
    - ✅ API key lifecycle (3/7): create, list, revoke
  - tests/meta/ (3 meta-test suites, 10 tests for quality validation)
  - Agent edge case tests (3 tests): empty content, missing fields, long history
  - Makefile targets (8 new commands)

⚠️ **Pending** (marked with `@pytest.mark.xfail(strict=True)`):
- E2E scenarios: 29/39 remaining (74%)
  - Standard user: 2 tests (search conversations, token refresh)
  - GDPR: 6 tests (access data, update profile, delete account, etc.)
  - Service principals: 7 tests (full OAuth2 client credentials flow)
  - API keys: 4 tests (validation, usage, rotation)
  - Error recovery: 6 tests (token expiration, rate limiting, etc.)
  - Multi-user: 5 tests (collaboration scenarios)
  - Performance: 4 tests (load testing)

**E2E Implementation Progress**: 10/39 tests (26% → target: 80%)

### Best Practices Implemented

1. **Test Isolation**: Dedicated infrastructure prevents flaky tests
2. **Mocking Strategy**: Unit tests mock external dependencies
3. **Parallel Execution**: Most tests run in parallel for speed
4. **Clear Markers**: `@pytest.mark.e2e`, `@pytest.mark.api`, etc.
5. **FastAPI TestClient**: Proper HTTP testing for API endpoints
6. **Comprehensive Coverage**: Happy path + error cases + edge cases
7. **Documentation**: Each test has descriptive docstrings
8. **Fixtures**: Reusable test data in conftest.py

---

## Additional Resources

- **pytest Documentation**: https://docs.pytest.org/
- **Hypothesis Guide**: https://hypothesis.readthedocs.io/
- **FastAPI Testing**: https://fastapi.tiangolo.com/tutorial/testing/
- **Project Testing Guide**: `../docs/development/testing.md`
- **Contributing Guide**: `../.github/CONTRIBUTING.md`

**Last Updated**: 2025-11-07 (Fixture Organization Best Practices added)
