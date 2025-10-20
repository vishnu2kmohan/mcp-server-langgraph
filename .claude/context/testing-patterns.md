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
