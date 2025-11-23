# Pytest Markers Reference

**Last Updated**: 2025-11-23
**Purpose**: Complete catalog of pytest markers for mcp-server-langgraph
**Total Markers**: 67 registered markers

---

## Quick Reference

```bash
# Run specific test categories
pytest -m unit                    # Fast unit tests only
pytest -m integration            # Integration tests (requires infrastructure)
pytest -m "unit and not slow"    # Unit tests excluding slow ones
pytest -m "api and unit"         # API unit tests (no external deps)
pytest -m property               # Property-based tests (Hypothesis)

# Run compliance tests
pytest -m gdpr                   # GDPR compliance tests
pytest -m soc2                   # SOC 2 compliance tests
pytest -m sla                    # SLA monitoring tests

# Run by feature
pytest -m auth                   # Authentication/authorization
pytest -m llm                    # LLM API tests (expensive)
pytest -m openfga                # OpenFGA integration
pytest -m mcp                    # MCP protocol tests
```

---

## Core Test Categories

### `unit`
**Purpose**: Fast tests with no external dependencies
**Characteristics**:
- No network calls
- No database access
- Uses mocks for external services
- Typically < 1 second per test

**Usage**:
```python
@pytest.mark.unit
async def test_session_creation(self, store):
    """Test in-memory session creation"""
    session_id = await store.create(
        user_id="user:alice",
        username="alice",
        roles=["admin"]
    )
    assert session_id is not None
```

**Run**: `pytest -m unit`

---

### `integration`
**Purpose**: Tests requiring real infrastructure (Redis, PostgreSQL, OpenFGA, etc.)
**Characteristics**:
- Requires docker-compose services
- Tests actual integration between components
- May be slower (1-5 seconds per test)

**Usage**:
```python
@pytest.mark.integration
async def test_redis_session_lifecycle(self, redis_store):
    """Test with real Redis instance"""
    session_id = await redis_store.create(...)
    # Verify with actual Redis
```

**Run**: `pytest -m integration` (after `make test-infra-up`)

---

### `e2e`
**Purpose**: End-to-end full system tests
**Characteristics**:
- Tests complete user workflows
- Requires full infrastructure stack
- Slowest tests (5-30 seconds)

**Usage**:
```python
@pytest.mark.e2e
@pytest.mark.asyncio
async def test_full_user_journey(self, test_client):
    """Test complete authentication flow"""
    # Login → Get token → Access resource → Logout
```

**Run**: `pytest -m e2e` (requires `make test-e2e`)

---

### `smoke`
**Purpose**: Critical path validation tests
**Characteristics**:
- Tests most important functionality
- Should always pass
- Run before deployments

**Usage**:
```python
@pytest.mark.smoke
@pytest.mark.unit
def test_server_starts():
    """Verify MCP server can start"""
```

**Run**: `pytest -m smoke`

---

### `slow`
**Purpose**: Tests taking > 1 second
**Characteristics**:
- Long-running operations
- May involve retries, timeouts, or large datasets
- Excluded from fast dev workflows

**Usage**:
```python
@pytest.mark.slow
@pytest.mark.integration
async def test_circuit_breaker_recovery(self):
    """Test circuit breaker opens after 5 failures (45s)"""
```

**Run**: `pytest -m slow` (or exclude with `-m "not slow"`)

---

## Feature-Based Markers

### `auth`
**Purpose**: Authentication and authorization tests
**Examples**: JWT validation, session management, OpenFGA checks

```python
@pytest.mark.auth
@pytest.mark.unit
async def test_jwt_token_validation(self):
    """Test JWT signature verification"""
```

---

### `api`
**Purpose**: REST API endpoint tests
**Examples**: FastAPI route testing, request validation, response schemas

```python
@pytest.mark.api
@pytest.mark.unit
async def test_health_endpoint_returns_200(self, client):
    """Test /health endpoint"""
    response = await client.get("/health")
    assert response.status_code == 200
```

**Tip**: Combine with `unit` for fast API tests: `-m "api and unit"`

---

### `openfga`
**Purpose**: OpenFGA authorization integration tests
**Requires**: OpenFGA service running

```python
@pytest.mark.openfga
@pytest.mark.integration
async def test_permission_check(self, openfga_client):
    """Test OpenFGA permission checking"""
```

---

### `infisical`
**Purpose**: Infisical secrets management tests
**Requires**: Infisical service or mock

---

### `mcp`
**Purpose**: Model Context Protocol compliance tests
**Examples**: Protocol validation, message formats, tool schemas

```python
@pytest.mark.mcp
@pytest.mark.contract
def test_mcp_tool_schema_valid(self):
    """Verify MCP tool schema compliance"""
```

---

### `llm`
**Purpose**: LLM API integration tests
**Characteristics**:
- Expensive (real API calls)
- Requires API keys
- May be slow (network latency)

```python
@pytest.mark.llm
@pytest.mark.integration
async def test_openai_completion(self):
    """Test OpenAI API integration"""
    # Requires OPENAI_API_KEY
```

**Note**: Often skipped in CI to save costs

---

### `observability`
**Purpose**: OpenTelemetry, metrics, logging tests
**Examples**: Trace propagation, metric export, log formatting

---

### `scim`
**Purpose**: SCIM 2.0 user provisioning tests
**Examples**: User CRUD, group management, SCIM protocol compliance

---

## Testing Methodology Markers

### `property`
**Purpose**: Property-based tests using Hypothesis
**Characteristics**:
- Tests invariants (properties that should always hold)
- Generates random test data
- Excellent for edge case discovery

**Usage**:
```python
from hypothesis import given, settings
from hypothesis import strategies as st

@pytest.mark.property
@pytest.mark.unit
@given(username=st.sampled_from(["alice", "bob"]))
@settings(max_examples=50)
def test_jwt_roundtrip(self, username):
    """Property: JWT encode/decode should be reversible"""
    token = create_token(username)
    payload = verify_token(token)
    assert payload["username"] == username
```

**Profiles**:
- Dev: 25 examples, 2000ms deadline
- CI: 100 examples, no deadline

**Run**: `pytest -m property`

---

### `contract`
**Purpose**: Contract/protocol compliance tests
**Examples**: MCP protocol, OpenAPI schema, SCIM spec

```python
@pytest.mark.contract
def test_openapi_schema_valid(self):
    """Verify OpenAPI schema is valid"""
```

---

### `benchmark`
**Purpose**: Performance benchmark tests
**Characteristics**:
- Disabled by default (`--benchmark-disable`)
- Measures latency, throughput
- Tracks regressions

**Usage**:
```python
@pytest.mark.benchmark
def test_session_creation_performance(self, benchmark):
    """Benchmark session creation"""
    benchmark(lambda: create_session())
```

**Run**: `pytest --benchmark-only` (or `make benchmark`)

---

### `mutation`
**Purpose**: Mutation testing (code quality)
**Characteristics**:
- Extremely slow (tests effectiveness of test suite)
- Runs on schedule, not in CI

**Run**: `make test-mutation` (uses mutmut)

---

### `regression`
**Purpose**: Performance regression tests
**Examples**: Detect slowdowns, memory leaks

---

## Compliance & Quality Markers

### `gdpr`
**Purpose**: GDPR compliance tests
**Examples**: Data subject rights (access, deletion, portability)

```python
@pytest.mark.gdpr
@pytest.mark.integration
async def test_user_data_export(self):
    """Test GDPR data export functionality"""
```

---

### `soc2`
**Purpose**: SOC 2 compliance tests
**Examples**: Access logging, audit trails, encryption

---

### `sla`
**Purpose**: SLA monitoring tests
**Examples**: Uptime checks, latency requirements

```python
@pytest.mark.sla
@pytest.mark.integration
async def test_api_latency_under_200ms(self):
    """Verify p95 latency < 200ms"""
```

---

### `security`
**Purpose**: Security tests (OWASP Top 10)
**Examples**: SQL injection, XSS, CSRF, authentication bypass

---

### `documentation`
**Purpose**: Documentation validation tests
**Examples**: MDX syntax, broken links, version consistency

---

### `precommit`
**Purpose**: Pre-commit hook validation tests
**Examples**: Hook configuration, script execution

---

## Infrastructure & Deployment Markers

### `kubernetes`
**Purpose**: Kubernetes integration tests
**Requires**: kubectl access or mock

---

### `deployment`
**Purpose**: Deployment configuration tests
**Examples**: Helm charts, Kustomize overlays

```python
@pytest.mark.deployment
def test_helm_chart_renders():
    """Verify Helm chart renders without errors"""
```

---

### `infrastructure`
**Purpose**: Infrastructure configuration tests
**Examples**: Docker Compose, Terraform validation

---

### `database`
**Purpose**: Database integration tests
**Requires**: PostgreSQL running

---

### `staging`
**Purpose**: Staging environment tests
**Characteristics**: Run against staging, not dev

---

### `terraform`
**Purpose**: Terraform configuration tests
**Examples**: tfplan validation, state file checks

---

### `ci`
**Purpose**: CI/CD pipeline tests
**Examples**: GitHub Actions workflow validation

```python
@pytest.mark.ci
def test_workflow_syntax_valid(self):
    """Verify GitHub Actions YAML is valid"""
```

---

### `validation`
**Purpose**: Validation tests for config/deployments
**Examples**: OpenAPI, Helm, Kustomize validation

---

## Technical Control Markers

### `asyncio`
**Purpose**: Async tests (pytest-asyncio)
**Auto-Applied**: By pytest-asyncio plugin
**Characteristics**: Enables async/await in tests

```python
@pytest.mark.asyncio
async def test_async_operation(self):
    """Test async function"""
    result = await async_function()
    assert result is not None
```

**Config**: `asyncio_mode = "auto"` (auto-detects async tests)

---

### `xdist_isolation`
**Purpose**: Tests requiring strict worker isolation
**Characteristics**:
- Prevents test interference in parallel execution
- May disable worker optimizations

---

### `xdist_group`
**Purpose**: Group related tests in same pytest-xdist worker
**Characteristics**:
- Improves fixture reuse
- Reduces memory fragmentation
- Prevents cache misses

**Usage**:
```python
@pytest.mark.xdist_group(name="testapiversionmetadata")
class TestAPIVersioning:
    """All tests run in same worker"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation"""
        gc.collect()
```

**Why**: Prevents memory explosion (217GB → 1.8GB observed)

---

### `skip_resilience_reset`
**Purpose**: Opt-out of autouse resilience fixture
**Use Case**: Tests that need persistent circuit breaker state

```python
@pytest.mark.skip_resilience_reset
def test_circuit_breaker_persistence(self):
    """Test circuit breaker state across requests"""
```

---

### `timeout`
**Purpose**: Custom timeout override
**Default**: 60 seconds (pytest-timeout)

```python
@pytest.mark.timeout(120)  # 2 minutes
async def test_long_running_operation(self):
    """Test that takes > 60s"""
```

---

### Tool Requirement Markers

#### `requires_kustomize`
**Purpose**: Test requires kubectl kustomize CLI
**Behavior**: Skipped if kustomize not installed

#### `requires_kubectl`
**Purpose**: Test requires kubectl CLI
**Behavior**: Skipped if kubectl not installed

#### `requires_helm`
**Purpose**: Test requires helm CLI
**Behavior**: Skipped if helm not installed

**Implementation**: Checked in `pytest_collection_modifyitems` hook

---

### `external_deps`
**Purpose**: Tests requiring external services
**Examples**: Third-party APIs, cloud resources

---

### `meta`
**Purpose**: Meta-tests (test suite validation)
**Examples**: Fixture organization, marker registration, pre-commit hooks

```python
@pytest.mark.meta
def test_all_markers_registered(self):
    """Verify all used markers are registered in pyproject.toml"""
```

**Location**: `tests/meta/`
**Count**: 90+ meta-tests

---

### `diagnostic`
**Purpose**: Diagnostic and troubleshooting tests
**Characteristics**: May not assert, just print diagnostic info

---

### `cli`
**Purpose**: CLI tool tests
**Examples**: Scaffolding, code generation

---

## Marker Combinations (Advanced)

### Fast Development Workflow
```bash
# Fast unit tests only (exclude slow, integration, LLM)
pytest -m "unit and not slow and not llm"
```

### Pre-Deployment Validation
```bash
# Smoke + integration tests
pytest -m "smoke or (integration and not slow)"
```

### Compliance Suite
```bash
# All compliance tests
pytest -m "gdpr or soc2 or sla or security"
```

### Quality Gates
```bash
# Property + contract + regression
pytest -m "property or contract or regression"
```

### API Testing
```bash
# API unit tests (fast)
pytest -m "api and unit"

# API integration tests
pytest -m "api and integration"
```

---

## Marker Registration

All markers are registered in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
markers = [
    "unit: Unit tests (fast, no external dependencies)",
    "integration: Integration tests (may require external services)",
    # ... 65 more markers
]
```

**Strict Mode**: Enabled (`--strict-markers`)
**Validation**: Pre-commit hook enforces marker registration
**Meta-Test**: `tests/meta/test_pytest_markers.py` validates consistency

---

## Best Practices

### 1. Always Use Multiple Markers
```python
@pytest.mark.unit          # Category
@pytest.mark.auth          # Feature
@pytest.mark.asyncio       # Technical
async def test_auth_feature(self):
    """Test description"""
```

### 2. Use xdist_group for Related Tests
```python
@pytest.mark.xdist_group(name="auth_tests")
class TestAuthentication:
    """Group related tests together"""
```

### 3. Mark Expensive Tests Appropriately
```python
@pytest.mark.llm           # Expensive
@pytest.mark.slow          # Long-running
@pytest.mark.integration   # Requires services
async def test_llm_call(self):
    """Only run when needed"""
```

### 4. Use Marker Logic for Smart Filtering
```bash
# Unit tests, but exclude slow ones
pytest -m "unit and not slow"

# Integration tests, but not LLM (save API costs)
pytest -m "integration and not llm"
```

---

## Common Workflows

### Daily Development
```bash
make test-dev              # Fast: unit + no slow
make test-fast             # All tests, no coverage
pytest -x --lf             # Stop on first failure, last-failed
```

### Pre-Commit
```bash
pytest -m "unit and not slow"  # Fast validation
```

### Pre-Push
```bash
make validate-pre-push     # Full validation (8-12 min)
pytest -m "unit or integration"  # Most tests
```

### CI/CD
```bash
pytest -m "unit and not llm"              # Unit tests (no API costs)
pytest -m integration                      # Integration tests
pytest -m "property or contract"          # Quality tests
pytest -m "gdpr or soc2 or sla"           # Compliance tests
```

---

## Troubleshooting

### Unknown Marker Warning
```
PytestUnknownMarkWarning: Unknown pytest.mark.my_marker
```

**Fix**: Add to `pyproject.toml` → `[tool.pytest.ini_options] markers`

### Tests Not Running
```bash
# Verify marker exists
pytest --markers | grep my_marker

# List tests with marker
pytest --collect-only -m my_marker
```

### Marker Combination Issues
```bash
# Use parentheses for complex logic
pytest -m "(unit or integration) and not slow"
```

---

## Quick Marker Lookup

| Marker | Purpose | Speed | Requires |
|--------|---------|-------|----------|
| `unit` | Fast isolated tests | < 1s | Nothing |
| `integration` | Real infrastructure | 1-5s | Docker |
| `e2e` | Full workflows | 5-30s | Full stack |
| `property` | Hypothesis tests | Varies | Nothing |
| `llm` | LLM API calls | 2-10s | API keys |
| `slow` | Long-running | > 1s | Varies |
| `gdpr` | GDPR compliance | Varies | Database |
| `mcp` | MCP protocol | < 1s | Nothing |

---

## Related Files

- Marker definitions: `pyproject.toml` → `[tool.pytest.ini_options] markers`
- Marker validation: `tests/meta/test_pytest_markers.py`
- Pre-commit hook: `validate-pytest-markers` in `.pre-commit-config.yaml`
- CLI detection: `tests/conftest.py` → `pytest_collection_modifyitems()`

---

**Auto-Generated**: This file should be updated when new markers are added
**Validation**: Run `pytest --markers` to see all registered markers
**Last Audit**: 2025-11-23 (67 markers documented)
