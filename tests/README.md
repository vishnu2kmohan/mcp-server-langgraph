# Test Suite

Comprehensive test suite for MCP Server with LangGraph, following best practices for production Python applications.

## Directory Structure

```
tests/
├── test_*.py              # Unit & integration tests (mixed markers)
├── api/                   # API contract compliance tests
├── contract/              # Contract tests (MCP protocol, OpenAPI)
├── property/              # Property-based tests (Hypothesis)
├── performance/           # Performance benchmark tests
├── regression/            # Performance regression tests
└── conftest.py            # Shared test fixtures and configuration
```

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

## Additional Resources

- **pytest Documentation**: https://docs.pytest.org/
- **Hypothesis Guide**: https://hypothesis.readthedocs.io/
- **Project Testing Guide**: `../docs/development/testing.md`
- **Contributing Guide**: `../.github/CONTRIBUTING.md`

**Last Updated**: 2025-10-20
