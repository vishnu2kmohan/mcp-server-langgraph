# Testing Guide

Comprehensive testing guide for the MCP Server with LangGraph.

## Quick Start

```bash
# Install test dependencies
make install-dev

# Run all tests
make test

# Run with coverage
make test-coverage
```

## Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures and configuration
├── test_src/mcp_server_langgraph/auth/middleware.py             # Authentication/authorization tests
├── test_openfga_client.py   # OpenFGA integration tests
├── test_secrets_manager.py  # Infisical secrets tests
├── test_src/mcp_server_langgraph/core/agent.py            # LangGraph agent tests
└── test_mcp_streamable.py   # MCP StreamableHTTP tests
```

## Test Categories

### Unit Tests (Fast, No External Dependencies)

```bash
# Run only unit tests
make test-unit

# Or with pytest directly
pytest -m unit -v
```

**Coverage:**
- ✅ `test_src/mcp_server_langgraph/auth/middleware.py` - 40+ tests for JWT and OpenFGA authorization
- ✅ `test_openfga_client.py` - 12+ tests for OpenFGA client
- ✅ `test_secrets_manager.py` - 15+ tests for Infisical integration
- ✅ `test_src/mcp_server_langgraph/core/agent.py` - 10+ tests for LangGraph agent

### Integration Tests (Require External Services)

```bash
# Run integration tests
make test-integration

# Or with pytest
pytest -m integration -v
```

**Requirements:**
- Running OpenFGA instance (localhost:8080)
- Running Infisical instance (if testing secrets)
- Docker Compose infrastructure

**Setup:**
```bash
# Start infrastructure
make setup-infra

# Run integration tests
make test-integration
```

### End-to-End Tests (Full System)

```bash
# Run e2e tests
pytest -m e2e -v
```

**Requirements:**
- All services running
- Valid API keys configured
- Network connectivity

## Test Markers

Tests are categorized using pytest markers:

```python
@pytest.mark.unit          # Fast unit tests
@pytest.mark.integration   # Integration tests
@pytest.mark.e2e          # End-to-end tests
@pytest.mark.auth         # Authentication tests
@pytest.mark.openfga      # OpenFGA tests
@pytest.mark.infisical    # Infisical tests
@pytest.mark.mcp          # MCP protocol tests
@pytest.mark.slow         # Slow tests (>1 second)
```

Run specific markers:
```bash
pytest -m "auth and unit" -v
pytest -m "not slow" -v
```

## Coverage Requirements

- **Minimum:** 70% overall coverage (enforced in CI)
- **Target:** 80%+ coverage
- **Goal:** 90%+ for critical paths

```bash
# Generate coverage report
make test-coverage

# View HTML report
open htmlcov/index.html
```

Current coverage:
- `src/mcp_server_langgraph/auth/middleware.py`: ~85%
- `openfga_client.py`: ~80%
- `secrets_manager.py`: ~90%
- `src/mcp_server_langgraph/core/agent.py`: ~75%
- `src/mcp_server_langgraph/mcp/server_streamable.py`: ~70%

## Writing Tests

### Unit Test Example

```python
import pytest
from mcp_server_langgraph.auth.middleware import AuthMiddleware

@pytest.mark.unit
@pytest.mark.auth
class TestAuthMiddleware:
    def test_create_token_success(self):
        """Test JWT token creation"""
        auth = AuthMiddleware(secret_key="test-secret")
        token = auth.create_token("alice", expires_in=3600)

        assert token is not None
        assert isinstance(token, str)
```

### Integration Test Example

```python
@pytest.mark.integration
@pytest.mark.openfga
class TestOpenFGAIntegration:
    @pytest.mark.skip(reason="Requires running OpenFGA instance")
    async def test_full_authorization_flow(self):
        """Test complete authorization flow with real OpenFGA"""
        client = OpenFGAClient(
            api_url="http://localhost:8080",
            store_id="test-store",
            model_id="test-model"
        )

        # Test write, check, list operations
        await client.write_tuples([...])
        allowed = await client.check_permission(...)
        assert allowed is True
```

## Fixtures

Common fixtures available in `conftest.py`:

```python
# Use in your tests
def test_with_mock_user(mock_user_alice):
    assert mock_user_alice["username"] == "alice"

def test_with_settings(mock_settings):
    assert mock_settings.service_name == "test-service"

async def test_with_client(mock_httpx_client):
    response = await mock_httpx_client.get("/test")
```

## Mocking

### Mocking OpenFGA

```python
@patch('openfga_client.OpenFgaClient')
async def test_check_permission(mock_sdk_client):
    mock_response = MagicMock()
    mock_response.allowed = True

    mock_instance = AsyncMock()
    mock_instance.check.return_value = mock_response
    mock_sdk_client.return_value = mock_instance

    # Test your code
```

### Mocking Anthropic API

```python
@patch('agent.ChatAnthropic')
def test_agent_graph(mock_anthropic):
    mock_model = MagicMock()
    mock_model.invoke.return_value = AIMessage(content="Response")
    mock_anthropic.return_value = mock_model

    # Test agent
```

## CI/CD Integration

Tests run automatically in GitHub Actions on:
- Push to `main` or `develop`
- Pull requests
- Release creation

**CI Pipeline:**
1. Unit tests (required to pass)
2. Integration tests (allowed to fail)
3. Coverage check (minimum 70%)
4. Linting (flake8, black, isort, mypy)
5. Security scan (bandit)

## Local Testing Best Practices

### Before Committing

```bash
# 1. Run unit tests
make test-unit

# 2. Check code formatting
make format

# 3. Run linters
make lint

# 4. Check coverage
make test-coverage

# 5. Run security scan
make security-check
```

### Full Pre-Commit Check

```bash
# Run everything
make install-dev && \
  make test-unit && \
  make format && \
  make lint && \
  make security-check
```

## Troubleshooting

### Tests Failing Due to Missing Dependencies

```bash
# Reinstall dependencies
make clean
make install-dev
```

### Integration Tests Failing

```bash
# Ensure infrastructure is running
make setup-infra

# Check service health
docker-compose ps
curl http://localhost:8080/healthz  # OpenFGA
```

### Coverage Too Low

```bash
# Find uncovered lines
pytest --cov=. --cov-report=term-missing

# Focus on specific file
pytest --cov=auth --cov-report=term-missing tests/test_src/mcp_server_langgraph/auth/middleware.py
```

### Slow Tests

```bash
# Run only fast tests
pytest -m "not slow" -v

# Identify slow tests
pytest --durations=10
```

## Test Data

Test data and fixtures:

**Users:**
- `alice`: Premium user, admin of org:acme
- `bob`: Standard user, member of org:acme
- `admin`: Admin user with elevated privileges

**JWT Secret (test only):**
- `test-secret-key-for-testing-only`

**OpenFGA:**
- Store ID: `test-store-id`
- Model ID: `test-model-id`

## Performance Testing

For load/performance testing:

```bash
# Install locust
pip install locust

# Run load tests (if implemented)
locust -f tests/performance/locustfile.py
```

## Future Improvements

- [ ] Add performance/load tests
- [ ] Increase unit test coverage to 90%
- [ ] Add mutation testing (mutmut)
- [ ] Implement property-based testing (hypothesis)
- [ ] Add contract tests for MCP protocol
- [ ] Set up test database fixtures
- [ ] Add visual regression tests for dashboards
- [ ] Implement chaos engineering tests

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [pytest-asyncio](https://pytest-asyncio.readthedocs.io/)
- [Coverage.py](https://coverage.readthedocs.io/)
- [Testing best practices](https://docs.python-guide.org/writing/tests/)
