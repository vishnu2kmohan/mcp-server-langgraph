# Test Suite

Comprehensive test suite for MCP Server with LangGraph, following best practices for production Python applications.

## Directory Structure

```
tests/
├── test_*.py              # Unit & integration tests (mixed markers)
├── api/                   # API endpoint tests (NEW)
│   ├── test_api_keys_endpoints.py
│   └── test_service_principals_endpoints.py
├── e2e/                   # End-to-end user journey tests (NEW)
│   └── test_full_user_journey.py
├── unit/                  # Dedicated unit tests (NEW)
│   └── test_mcp_stdio_server.py
├── contract/              # Contract tests (MCP protocol, OpenAPI)
├── property/              # Property-based tests (Hypothesis)
├── performance/           # Performance benchmark tests
├── regression/            # Performance regression tests
└── conftest.py            # Shared test fixtures and configuration
```

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
def test_with_fixture(mock_llm_factory):
    """Test uses mock LLM factory from fixture."""
    assert mock_llm_factory is not None
```

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

### Common Issues

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
pytest tests/unit/test_mcp_stdio_server.py -v
pytest tests/unit/test_mcp_stdio_server.py -k "auth" -v  # Auth tests only
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
- API endpoints: ✅ 30+ test cases covering all routes
- MCP stdio server: ✅ 85%+ coverage target
- E2E workflows: ✅ 6 complete user journeys
- Test infrastructure: ✅ Fully isolated environment

### Implementation Status

✅ **Completed**:
- docker-compose.test.yml (isolated infrastructure)
- tests/api/test_api_keys_endpoints.py (15+ tests)
- tests/api/test_service_principals_endpoints.py (18+ tests)
- tests/unit/test_mcp_stdio_server.py (20+ tests)
- tests/e2e/test_full_user_journey.py (framework ready)
- Makefile targets (8 new commands)
- Tests README documentation

⚠️ **Pending** (marked with `pytest.skip()`):
- E2E test implementation (requires Keycloak fixtures)
- GDPR endpoints error case expansion
- MCP streamable server coverage expansion

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

**Last Updated**: 2025-10-31
