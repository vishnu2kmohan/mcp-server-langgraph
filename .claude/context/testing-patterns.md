# Testing Patterns Context

**Last Updated**: 2025-10-20
**Purpose**: Reference guide for writing tests in mcp-server-langgraph
**Test Count**: 437+ tests across multiple categories

---

## 📊 Test Suite Overview

**Test Categories**:
- **Unit Tests**: 350+ tests (fast, no external dependencies)
- **Integration Tests**: 50+ tests (requires infrastructure)
- **Property Tests**: 27+ tests (Hypothesis-based edge case discovery)
- **Contract Tests**: 20+ tests (MCP protocol compliance)
- **Performance Tests**: 10+ tests (regression tracking)

**Coverage**: 69% (maintained after recent additions)
**Pass Rate**: 99.3% (722/727 passing)

---

## 🎯 Testing Philosophy

### Core Principles
1. **Mock external dependencies** - Don't rely on real services in unit tests
2. **Test behavior, not implementation** - Focus on what, not how
3. **Comprehensive edge cases** - Test happy path + error cases
4. **Property-based testing** - Use Hypothesis for invariants
5. **Clear test names** - `test_<what>_<condition>_<expected>`

### Test Organization
```python
"""
Comprehensive tests for <Component>

Tests cover:
- <Category 1>
- <Category 2>
- <Category 3>
- Edge cases and error handling
"""

class Test<Component>Name:
    """Tests for <specific aspect>"""

    @pytest.fixture
    def component(self):
        """Create component with test config"""
        return Component(param1=value1, param2=value2)

    @pytest.mark.asyncio  # For async tests
    @pytest.mark.unit     # Test category marker
    async def test_operation_success(self, component):
        """Test successful operation"""
        # Given
        input_data = {...}

        # When
        result = await component.operation(input_data)

        # Then
        assert result.success is True
        assert result.data == expected
```

---

## 🧪 Common Test Patterns

### Pattern 1: Async Tests with Fixtures

**Use Case**: Testing async components (sessions, API calls, LLM invocations)

```python
import pytest
from unittest.mock import AsyncMock, patch

class TestAsyncComponent:
    """Tests for async component"""

    @pytest.fixture
    def store(self):
        """Create test instance"""
        return SessionStore(default_ttl=3600, max_sessions=3)

    @pytest.mark.asyncio
    async def test_create_session(self, store):
        """Test creating a session"""
        # Given
        user_id = "user:alice"
        username = "alice"
        roles = ["admin", "user"]

        # When
        session_id = await store.create(
            user_id=user_id,
            username=username,
            roles=roles,
            metadata={"ip": "192.168.1.1"}
        )

        # Then
        assert session_id is not None
        assert len(session_id) > 0

        # Verify session exists
        session = await store.get(session_id)
        assert session is not None
        assert session.user_id == user_id
        assert session.username == username
        assert session.roles == roles
```

**Key Points**:
- Use `@pytest.mark.asyncio` for async tests
- Use fixtures for component setup
- Use `AsyncMock` for mocking async methods
- Test both operation + verification

---

### Pattern 2: Mocking External Dependencies

**Use Case**: Testing components that depend on external services (LLM, database, APIs)

```python
from unittest.mock import AsyncMock, MagicMock, patch

class TestAgentGraph:
    """Test LangGraph agent"""

    @patch("mcp_server_langgraph.llm.factory.create_llm_from_config")
    async def test_route_input(self, mock_create_llm):
        """Test routing logic"""
        from mcp_server_langgraph.core.agent import create_agent_graph

        # Given - Mock the LLM
        mock_model = MagicMock()
        mock_model.ainvoke = AsyncMock(
            return_value=AIMessage(content="Hello!")
        )
        mock_create_llm.return_value = mock_model

        graph = create_agent_graph()

        initial_state = {
            "messages": [HumanMessage(content="Hello")],
            "next_action": "",
            "user_id": "user:alice",
            "request_id": "req-123"
        }

        # When
        result = await graph.ainvoke(
            initial_state,
            config={"configurable": {"thread_id": "test-1"}}
        )

        # Then
        assert result is not None
        assert "messages" in result
        assert len(result["messages"]) > 1
        assert result["next_action"] == "end"
```

**Key Points**:
- Use `@patch` decorator for module-level mocks
- Mock at the import point (where code imports from)
- Use `MagicMock` for sync, `AsyncMock` for async
- Configure return values before use

---

### Pattern 3: Property-Based Testing (Hypothesis)

**Use Case**: Testing invariants and edge cases automatically

```python
import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

# Define strategies
valid_usernames = st.sampled_from(["alice", "bob", "admin"])
user_ids = st.builds(lambda name: f"user:{name}", valid_usernames)
expiration_seconds = st.integers(min_value=1, max_value=86400)

@pytest.mark.property
@pytest.mark.unit
class TestJWTProperties:
    """Property-based tests for JWT"""

    @given(username=valid_usernames, expiration=expiration_seconds)
    @settings(max_examples=50, deadline=2000)
    def test_jwt_encode_decode_roundtrip(self, username, expiration):
        """Property: JWT encode/decode should be reversible"""
        from mcp_server_langgraph.auth.middleware import AuthMiddleware

        auth = AuthMiddleware(secret_key="test-secret")

        # Create token
        token = auth.create_token(username, expires_in=expiration)

        # Verify token
        result = run_async(auth.verify_token(token))

        # Property: Should always be valid and preserve data
        assert result.valid is True
        assert result.payload["username"] == username
        assert "exp" in result.payload
        assert "iat" in result.payload
```

**Key Points**:
- Use `@given` with Hypothesis strategies
- Use `@settings` to control example count and timeout
- Test invariants (properties that should always hold)
- Use `@pytest.mark.property` marker

---

### Pattern 4: Parametrized Tests

**Use Case**: Testing multiple scenarios with same logic

```python
@pytest.mark.parametrize("username,expected_roles", [
    ("alice", ["user", "premium"]),
    ("bob", ["user"]),
    ("admin", ["admin"]),
])
async def test_user_roles(username, expected_roles):
    """Test user role assignment"""
    from mcp_server_langgraph.auth.user_provider import InMemoryUserProvider

    provider = InMemoryUserProvider()
    user = await provider.get_user(username)

    assert user is not None
    assert set(user.roles) == set(expected_roles)


@pytest.mark.parametrize("error_type,expected_status", [
    (ValueError, "validation_error"),
    (KeyError, "not_found"),
    (PermissionError, "forbidden"),
])
def test_error_handling(error_type, expected_status):
    """Test error mapping"""
    result = map_exception_to_status(error_type())
    assert result.status == expected_status
```

**Key Points**:
- Use `@pytest.mark.parametrize` for multiple test cases
- Provide list of tuples for parameters
- Test name will include parameter values
- Great for testing boundaries and categories

---

### Pattern 5: Integration Tests

**Use Case**: Testing with real infrastructure (Redis, OpenFGA, etc.)

```python
@pytest.mark.integration
class TestRedisSessionStore:
    """Integration tests requiring real Redis"""

    @pytest.fixture(scope="class")
    async def redis_store(self):
        """Create Redis session store (requires Redis running)"""
        store = RedisSessionStore(
            redis_url="redis://localhost:6379",
            default_ttl_seconds=3600
        )
        yield store
        # Cleanup after all tests
        await store.cleanup()

    @pytest.mark.asyncio
    async def test_redis_session_lifecycle(self, redis_store):
        """Test full session lifecycle with Redis"""
        # Create
        session_id = await redis_store.create(
            user_id="user:test",
            username="test",
            roles=["user"]
        )

        # Read
        session = await redis_store.get(session_id)
        assert session is not None

        # Update
        success = await redis_store.update(
            session_id,
            metadata={"updated": True}
        )
        assert success is True

        # Delete
        success = await redis_store.delete(session_id)
        assert success is True

        # Verify deletion
        session = await redis_store.get(session_id)
        assert session is None
```

**Key Points**:
- Use `@pytest.mark.integration` marker
- Use fixtures with appropriate scope (class, session)
- Include cleanup logic (yield pattern)
- Document infrastructure requirements

---

### Pattern 6: Error Handling Tests

**Use Case**: Testing error cases and exception handling

```python
@pytest.mark.asyncio
async def test_get_nonexistent_session(self, store):
    """Test retrieving a non-existent session"""
    session = await store.get("nonexistent-session-id")
    assert session is None


@pytest.mark.asyncio
async def test_create_session_exceeds_limit(self, store):
    """Test exceeding concurrent session limit"""
    # Given - Store with max 3 sessions
    store = InMemorySessionStore(
        default_ttl_seconds=3600,
        max_concurrent_sessions=3
    )

    # Create 3 sessions (at limit)
    for i in range(3):
        await store.create(
            user_id=f"user:test{i}",
            username=f"test{i}",
            roles=["user"]
        )

    # When - Try to create 4th session
    with pytest.raises(ValueError, match="Maximum concurrent sessions"):
        await store.create(
            user_id="user:test4",
            username="test4",
            roles=["user"]
        )


@pytest.mark.asyncio
async def test_invalid_input_raises_exception(self):
    """Test that invalid input raises appropriate exception"""
    with pytest.raises(ValidationError):
        await component.process(invalid_data)
```

**Key Points**:
- Test None returns for missing resources
- Test exception raising with `pytest.raises`
- Use `match=` parameter to verify error message
- Test boundary conditions (limits, empty, null)

---

### Pattern 7: Mock Configuration

**Use Case**: Testing with different configuration scenarios

```python
@patch.dict(os.environ, {
    "FEATURE_FLAG_ENABLED": "true",
    "MAX_RETRIES": "5",
    "TIMEOUT_SECONDS": "30"
})
def test_feature_with_config():
    """Test feature behavior with specific config"""
    from mcp_server_langgraph.core.config import Settings

    settings = Settings()
    assert settings.feature_flag_enabled is True
    assert settings.max_retries == 5


@patch("mcp_server_langgraph.secrets.manager.InfisicalClient")
def test_fallback_to_env_vars(mock_infisical):
    """Test fallback when Infisical unavailable"""
    # Mock Infisical failure
    mock_infisical.side_effect = Exception("Connection failed")

    # Should fallback to env vars
    with patch.dict(os.environ, {"API_KEY": "test-key"}):
        manager = SecretsManager()
        key = manager.get_secret("API_KEY")
        assert key == "test-key"
```

**Key Points**:
- Use `@patch.dict(os.environ, {})` for env vars
- Test different configuration scenarios
- Test fallback behavior
- Verify graceful degradation

---

## 🔄 Advanced Async Test Patterns

### Event Loop Management for Property Tests

**Problem**: Hypothesis property tests with async operations can leak event loop descriptors

**Solution**: Custom `run_async()` helper with proper cleanup

**Pattern** (from `tests/integration/property/test_auth_properties.py`):
```python
import asyncio

def run_async(coro):
    """
    Run async coroutine with proper event loop cleanup.

    CRITICAL: Prevents event loop descriptor leaks in property tests.
    Hypothesis runs tests multiple times, so proper cleanup is essential.
    """
    # Create fresh event loop for each property test
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        result = loop.run_until_complete(coro)
        return result
    finally:
        # CRITICAL: Always close to free file descriptors
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        # Wait for cancellation to complete
        loop.run_until_complete(
            asyncio.gather(*pending, return_exceptions=True)
        )

        # Close loop and free resources
        loop.close()
```

**Why it's needed**:
- Hypothesis runs each property test multiple times (25-100 examples)
- Each run creates new event loop if not managed
- Unclosed loops leak file descriptors
- Eventually hits OS file descriptor limit
- Prevents "Too many open files" errors

**Usage**:
```python
from hypothesis import given, settings
from hypothesis import strategies as st

@pytest.mark.property
@pytest.mark.unit
class TestAuthProperties:
    @given(username=st.sampled_from(["alice", "bob"]))
    @settings(max_examples=50)
    def test_jwt_roundtrip(self, username):
        """Property: JWT encode/decode should be reversible"""
        async def test_logic():
            token = await create_token(username)
            payload = await verify_token(token)
            return payload["username"]

        result = run_async(test_logic())
        assert result == username
```

---

### Async Fixture Loop Scope Pattern

**Problem**: "Future attached to different loop" errors in async fixtures

**Solution**: Explicit `loop_scope` parameter

**Pattern** (from `tests/conftest.py`):
```python
@pytest.fixture(scope="session", loop_scope="session")
async def postgres_connection_pool():
    """
    Session-scoped PostgreSQL connection pool.

    CRITICAL: loop_scope="session" prevents ScopeMismatch errors.
    Without this, pytest-asyncio creates new loop for function-scoped tests,
    but fixture is bound to different loop from session scope.
    """
    import asyncpg

    pool = await asyncpg.create_pool(
        host="localhost",
        port=5432,
        user="test",
        password="test",
        database="test_db",
        min_size=2,
        max_size=10,
    )

    yield pool

    # Cleanup
    await pool.close()


@pytest.fixture
async def db_connection(postgres_connection_pool):
    """
    Function-scoped clean database connection.

    Inherits loop from pool (both session-scoped loop).
    """
    async with postgres_connection_pool.acquire() as conn:
        # Start transaction for test isolation
        async with conn.transaction():
            yield conn
            # Transaction auto-rolls back after test
```

**Why it's needed**:
- Pytest-asyncio creates event loops based on fixture scope
- Session fixture with function loop → "Future attached to different loop"
- Explicit `loop_scope` ensures fixture uses correct loop
- Prevents asyncio.InvalidStateError

**Global Configuration** (in `pyproject.toml`):
```toml
[tool.pytest.ini_options]
asyncio_default_fixture_loop_scope = "session"
```

**Effect**: All async fixtures default to session loop scope (prevents most errors)

---

### AsyncMock Configuration Best Practices

**Problem**: Unconfigured AsyncMock returns truthy `<AsyncMock>` object, causing logic bugs

**Pattern**:
```python
from unittest.mock import AsyncMock

# ❌ WRONG - Unconfigured mock
mock_openfga = AsyncMock()
result = await mock_openfga.check_permission("user", "resource")
if result:  # Always True! (AsyncMock is truthy)
    grant_access()  # Security bypass!

# ✅ CORRECT - Explicit return value
mock_openfga = AsyncMock()
mock_openfga.check_permission.return_value = False  # Explicit False

result = await mock_openfga.check_permission("user", "resource")
if result:  # Correctly evaluates to False
    grant_access()  # Not called
```

**Rule**: ALWAYS configure return values explicitly

**Spec Pattern** (type-safe mocking):
```python
from mcp_server_langgraph.auth.openfga import OpenFGAClient

# Use spec to enforce type safety
mock_openfga = AsyncMock(spec=OpenFGAClient)

# IDE autocomplete works
mock_openfga.check_permission.return_value = True
mock_openfga.write_tuples.return_value = None
mock_openfga.list_objects.return_value = ["tool:agent_chat"]

# Attempting to mock non-existent method raises AttributeError
# mock_openfga.nonexistent_method  # AttributeError!
```

**Benefits**:
- Type safety (catches typos at mock creation time)
- IDE autocomplete for mock configuration
- Prevents accidental truthy evaluations
- Clear documentation of mocked interface

---

## 🧪 Meta-Test Patterns

**Purpose**: Tests that validate the test suite itself

**Category**: Quality assurance for testing infrastructure

**Location**: `tests/meta/` (90+ meta-tests)

---

### Pattern 1: Pytest Configuration Validation

**File**: `tests/meta/test_pytest_markers.py`

**Purpose**: Ensure all markers used in tests are registered in `pyproject.toml`

**Pattern**:
```python
import pytest
import ast
import glob

@pytest.mark.meta
def test_all_markers_registered():
    """Verify all pytest markers used in tests are registered"""
    import toml

    # Load registered markers from pyproject.toml
    with open("pyproject.toml") as f:
        config = toml.load(f)

    registered_markers = set()
    for marker_def in config["tool"]["pytest"]["ini_options"]["markers"]:
        # Extract marker name (before colon)
        marker_name = marker_def.split(":")[0].strip()
        registered_markers.add(marker_name)

    # Find all markers used in test files
    used_markers = set()
    for test_file in glob.glob("tests/**/*.py", recursive=True):
        with open(test_file) as f:
            tree = ast.parse(f.read())

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check for @pytest.mark.* decorator
                if hasattr(node.func, "attr") and node.func.attr == "mark":
                    # Get marker name from decorator
                    # ... parsing logic ...
                    used_markers.add(marker_name)

    # Verify all used markers are registered
    unregistered = used_markers - registered_markers
    assert not unregistered, f"Unregistered markers: {unregistered}"
```

**Benefit**: Catches typos in marker names before CI

---

### Pattern 2: Fixture Organization Validation

**File**: `tests/meta/test_fixture_organization.py`

**Purpose**: Prevent duplicate autouse fixtures across test modules

**Pattern**:
```python
import pytest
import ast
import glob

@pytest.mark.meta
def test_no_duplicate_autouse_fixtures():
    """Verify no duplicate session/module-scoped autouse fixtures"""
    autouse_fixtures = {}

    for test_file in glob.glob("tests/**/*.py", recursive=True):
        if "conftest.py" not in test_file:
            with open(test_file) as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check for @pytest.fixture decorator
                    for decorator in node.decorator_list:
                        if is_autouse_fixture(decorator):
                            fixture_name = node.name

                            if fixture_name in autouse_fixtures:
                                pytest.fail(
                                    f"Duplicate autouse fixture '{fixture_name}':\n"
                                    f"  - {autouse_fixtures[fixture_name]}\n"
                                    f"  - {test_file}\n"
                                    f"All session/module autouse fixtures must be in "
                                    f"tests/conftest.py only!"
                                )

                            autouse_fixtures[fixture_name] = test_file
```

**Benefit**: Enforces fixture organization best practices

---

### Pattern 3: Memory Safety Validation

**File**: `tests/meta/test_memory_safety.py`

**Purpose**: Ensure all tests using AsyncMock/MagicMock have proper cleanup

**Pattern**:
```python
import pytest
import ast
import glob

@pytest.mark.meta
def test_async_tests_have_teardown():
    """Verify async tests using mocks have gc.collect() teardown"""
    violations = []

    for test_file in glob.glob("tests/**/*.py", recursive=True):
        with open(test_file) as f:
            content = f.read()
            tree = ast.parse(content)

        # Check if file uses AsyncMock or MagicMock
        uses_mocks = "AsyncMock" in content or "MagicMock" in content

        if uses_mocks:
            # Find test classes
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                    # Check for teardown_method
                    has_teardown = any(
                        method.name == "teardown_method"
                        for method in node.body
                        if isinstance(method, ast.FunctionDef)
                    )

                    if not has_teardown:
                        violations.append(
                            f"{test_file}::{node.name} uses mocks but missing "
                            f"teardown_method with gc.collect()"
                        )

    assert not violations, "\n".join(violations)
```

**Benefit**: Prevents memory leaks before they reach CI

---

### Pattern 4: CI/CD Configuration Validation

**File**: `tests/meta/ci/test_workflow_parity.py`

**Purpose**: Ensure local validation matches CI validation exactly

**Pattern**:
```python
import pytest
import yaml

@pytest.mark.meta
@pytest.mark.ci
def test_pre_push_matches_ci():
    """Verify pre-push hooks run same validation as CI"""
    # Load GitHub Actions workflow
    with open(".github/workflows/ci.yaml") as f:
        ci_workflow = yaml.safe_load(f)

    # Extract test commands from CI
    ci_test_steps = ci_workflow["jobs"]["test"]["steps"]
    ci_commands = [
        step["run"]
        for step in ci_test_steps
        if "run" in step and "pytest" in step["run"]
    ]

    # Load pre-push hook
    with open(".git/hooks/pre-push") as f:
        pre_push_content = f.read()

    # Verify pre-push runs same tests
    for ci_command in ci_commands:
        assert ci_command in pre_push_content, (
            f"CI runs '{ci_command}' but pre-push hook doesn't. "
            f"Update scripts/run_pre_push_tests.py"
        )
```

**Benefit**: Catches CI/local validation drift

---

### Pattern 5: Documentation Consistency Validation

**File**: `tests/meta/validation/test_documentation.py`

**Purpose**: Ensure documentation examples are valid and up-to-date

**Pattern**:
```python
import pytest
import re
import glob

@pytest.mark.meta
@pytest.mark.documentation
def test_code_examples_are_valid():
    """Verify code examples in documentation are syntactically valid"""
    violations = []

    for doc_file in glob.glob("docs/**/*.md", recursive=True):
        with open(doc_file) as f:
            content = f.read()

        # Extract Python code blocks
        code_blocks = re.findall(r"```python\n(.*?)\n```", content, re.DOTALL)

        for idx, code in enumerate(code_blocks):
            try:
                # Attempt to parse as Python
                compile(code, f"{doc_file}:block-{idx}", "exec")
            except SyntaxError as e:
                violations.append(
                    f"{doc_file} code block {idx} has syntax error: {e}"
                )

    assert not violations, "\n".join(violations)
```

**Benefit**: Prevents broken documentation examples

---

### Pattern 6: Dependency Version Validation

**File**: `tests/meta/test_dependencies.py`

**Purpose**: Ensure dependency versions are synchronized across configuration files

**Pattern**:
```python
import pytest
import toml

@pytest.mark.meta
def test_python_version_consistency():
    """Verify Python version consistent across pyproject.toml, Dockerfile, CI"""
    # pyproject.toml
    with open("pyproject.toml") as f:
        pyproject = toml.load(f)

    pyproject_python = pyproject["project"]["requires-python"]

    # Dockerfile
    with open("Dockerfile") as f:
        dockerfile = f.read()

    dockerfile_python = re.search(r"FROM python:([\d.]+)", dockerfile).group(1)

    # CI workflow
    with open(".github/workflows/ci.yaml") as f:
        ci = yaml.safe_load(f)

    ci_python = ci["jobs"]["test"]["strategy"]["matrix"]["python-version"]

    # Verify consistency
    # (implementation depends on version format)
```

**Benefit**: Catches version mismatches before deployment

---

## 🛠️ Common Mock Patterns

### Redis Mock
```python
@pytest.fixture
def mock_redis():
    """Mock Redis client"""
    with patch("redis.asyncio.from_url") as mock:
        redis_client = AsyncMock()
        redis_client.get = AsyncMock(return_value=None)
        redis_client.set = AsyncMock(return_value=True)
        redis_client.delete = AsyncMock(return_value=1)
        redis_client.expire = AsyncMock(return_value=True)
        mock.return_value = redis_client
        yield redis_client
```

### OpenFGA Mock
```python
@pytest.fixture
def mock_openfga():
    """Mock OpenFGA client"""
    with patch("mcp_server_langgraph.auth.openfga.OpenFGAClient") as mock:
        client = mock.return_value
        client.check_permission = AsyncMock(return_value=True)
        client.write_tuples = AsyncMock(return_value=True)
        client.list_objects = AsyncMock(return_value=["tool:agent_chat"])
        yield client
```

### LLM Mock
```python
@pytest.fixture
def mock_llm():
    """Mock LLM for agent tests"""
    with patch("mcp_server_langgraph.llm.factory.create_llm_from_config") as mock:
        llm = MagicMock()
        llm.ainvoke = AsyncMock(
            return_value=AIMessage(content="Mock response")
        )
        mock.return_value = llm
        yield llm
```

### Prometheus Mock
```python
@pytest.fixture
def mock_prometheus():
    """Mock Prometheus API client"""
    with patch("prometheus_api_client.PrometheusConnect") as mock:
        prom = mock.return_value
        prom.custom_query = MagicMock(return_value=[
            {"metric": {}, "value": [1234567890, "0.95"]}
        ])
        yield prom
```

---

## 📝 Test Markers

**Available Markers** (defined in `pyproject.toml`):
```python
@pytest.mark.unit          # Fast tests, no external dependencies
@pytest.mark.integration   # Requires infrastructure (Redis, OpenFGA, etc.)
@pytest.mark.e2e           # End-to-end tests
@pytest.mark.property      # Property-based tests (Hypothesis)
@pytest.mark.contract      # Contract/protocol compliance tests
@pytest.mark.regression    # Performance regression tests
@pytest.mark.asyncio       # Async tests (pytest-asyncio)
```

**Running Specific Markers**:
```bash
pytest -m unit                  # Unit tests only
pytest -m integration          # Integration tests only
pytest -m "unit and not slow"  # Unit tests excluding slow ones
pytest -m property             # Property-based tests
```

---

## 🎯 Test Naming Conventions

### Format: `test_<what>_<condition>_<expected>`

**Good Examples**:
```python
test_create_session_success()                    # Happy path
test_get_session_nonexistent_returns_none()      # Error case
test_update_session_with_metadata_succeeds()     # Specific scenario
test_jwt_encode_decode_roundtrip()               # Property/invariant
test_route_input_with_keyword_uses_tool()        # Conditional behavior
```

**Avoid**:
```python
test_session()              # Too vague
test_1()                    # Meaningless
test_it_works()             # Not descriptive
test_bug_fix()              # Doesn't explain what
```

---

## 🧩 Test Structure (Given-When-Then)

```python
async def test_feature_behavior(self):
    """Test feature does X when Y"""
    # Given - Setup/preconditions
    user = create_user("alice")
    session = await create_session(user)

    # When - Execute the operation
    result = await feature.execute(session, params)

    # Then - Assert expectations
    assert result.success is True
    assert result.data["user_id"] == user.id
    assert result.metadata["timestamp"] is not None
```

---

## 📊 Common Assertions

### Success Cases
```python
assert result is not None
assert result.success is True
assert isinstance(result, ExpectedType)
assert len(result.items) == expected_count
assert result.value == expected_value
```

### Error Cases
```python
assert result is None
assert result.success is False
with pytest.raises(ExpectedException):
    await operation()
with pytest.raises(ValueError, match="expected message"):
    validate(bad_input)
```

### Collections
```python
assert len(items) == 3
assert item in collection
assert set(actual) == set(expected)  # Order-independent
assert all(x > 0 for x in values)
```

### Async Results
```python
result = await async_operation()
assert result is not None

# For multiple async calls
results = await asyncio.gather(
    async_op1(),
    async_op2(),
    async_op3()
)
assert all(r.success for r in results)
```

---

## 🚀 Running Tests

### All Tests
```bash
pytest                          # All tests
pytest -v                       # Verbose
pytest --tb=short               # Short traceback
pytest -x                       # Stop on first failure
pytest -vv --tb=long            # Maximum verbosity
```

### By Marker
```bash
pytest -m unit                  # Unit tests only
pytest -m integration          # Integration tests
pytest -m "not integration"    # Exclude integration
```

### Specific Tests
```bash
pytest tests/test_session.py                        # File
pytest tests/test_session.py::TestInMemorySessionStore  # Class
pytest tests/test_session.py::test_create_session      # Function
```

### With Coverage
```bash
pytest --cov=src --cov-report=html
pytest --cov=src --cov-report=term-missing
```

### Parallel Execution
```bash
pytest -n auto          # Use all CPUs
pytest -n 4             # Use 4 workers
```

---

## 📖 Quick Reference

**Test a new auth feature**:
1. Create test class: `class TestNewFeature:`
2. Add fixture: `@pytest.fixture def component():`
3. Mock dependencies: `@patch("module.Dependency")`
4. Write happy path: `test_feature_success()`
5. Write error cases: `test_feature_invalid_input()`
6. Add markers: `@pytest.mark.unit`, `@pytest.mark.asyncio`

**Test a new API endpoint**:
1. Use contract tests pattern from `tests/contract/`
2. Test request validation
3. Test response schema
4. Test error responses (400, 401, 403, 500)
5. Test auth/authz integration

**Test a new compliance feature**:
1. Unit test core logic with mocks
2. Integration test with real data sources
3. Test edge cases (empty data, missing fields)
4. Test error handling and fallbacks

---

**Related Files**:
- Test Configuration: `pyproject.toml` (pytest settings)
- Test Requirements: `requirements-dev.txt`
- Testing Guide: `TESTING.md`
- CI Test Workflow: `.github/workflows/ci.yaml`

---

**Auto-Generated**: This file should be updated when new test patterns emerge
**Last Review**: 2025-10-20
