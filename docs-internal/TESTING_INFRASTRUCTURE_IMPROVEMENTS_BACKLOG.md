# Testing Infrastructure Improvements - Implementation Backlog

**Date Created**: 2025-11-22
**Session**: mcp-server-langgraph-session-20251118-221044
**Status**: Phase 1 Complete, Phases 2-6 Planned

---

## Executive Summary

This document outlines the remaining testing infrastructure improvements identified in the comprehensive audit. **Phase 1 (Schema Management) is complete and committed**. This backlog provides detailed implementation plans for Phases 2-6.

### Completed Work ✅

- **Phase 1: Schema Management**
  - Created `tests/meta/test_alembic_schema_parity.py` (4/4 tests passing)
  - Validated Alembic migrations ↔ SQL schema parity
  - Documented findings in `SCHEMA_MANAGEMENT_VALIDATION_2025-11-22.md`
  - **Audit Finding #1 RESOLVED**

---

## Phase 2: Unit Test Refactoring (High Priority)

**Goal**: Eliminate brittle unit tests that couple to implementation details

### Current State

**Problem File**: `tests/unit/test_mcp_stdio_server.py`
- **627 lines** of test code
- **50 `@patch` decorators** - extremely brittle
- Tests break on internal refactoring even when behavior unchanged

**Example of Brittleness**:
```python
# Current approach - couples to implementation
@patch("mcp_server_langgraph.mcp.server_stdio.settings")
@patch("mcp_server_langgraph.mcp.server_stdio.create_auth_middleware")
@patch("mcp_server_langgraph.mcp.server_stdio.get_agent_graph")
@patch("mcp_server_langgraph.mcp.server_stdio.tracer")
@patch("mcp_server_langgraph.mcp.server_stdio.format_response")
async def test_handle_chat_new_conversation(
    self, mock_format, mock_tracer, mock_graph, mock_auth, mock_settings, ...
):
    # 5 patches! Refactoring any module breaks this
```

### Proposed Solution: Behavioral Mock Framework

Create behavioral mocks in `tests/utils/mock_factories.py`:

```python
def create_behavioral_auth_middleware(
    *,
    authorized: bool = True,
    user_id: str = "alice",
    token_valid: bool = True
) -> AuthMiddleware:
    """
    Behavioral mock: Tests WHAT happens, not HOW it's implemented.

    Args:
        authorized: Whether user is authorized
        user_id: User ID to return
        token_valid: Whether token validation succeeds

    Returns:
        Mock that behaves like real AuthMiddleware
    """
    mock = AsyncMock(spec=AuthMiddleware)

    if token_valid:
        verification = MagicMock()
        verification.valid = True
        verification.payload = {"sub": user_id}
        mock.verify_token.return_value = verification
    else:
        verification = MagicMock()
        verification.valid = False
        verification.error = "Invalid token"
        mock.verify_token.return_value = verification

    mock.authorize.return_value = authorized
    return mock


def create_behavioral_agent_graph(
    *,
    response_message: str = "Hello!",
    conversation_exists: bool = False,
    user_id: str = "alice"
) -> CompiledGraph:
    """
    Behavioral mock for LangGraph agent.

    Tests behavior: "When user sends message, agent responds"
    NOT implementation: "get_agent_graph returns graph with checkpointer"
    """
    mock = AsyncMock(spec=CompiledGraph)

    if conversation_exists:
        state_snapshot = MagicMock()
        state_snapshot.values = {
            "messages": [HumanMessage(content="Previous message")]
        }
        mock.aget_state.return_value = state_snapshot
    else:
        state_snapshot = MagicMock()
        state_snapshot.values = {"messages": []}
        mock.aget_state.return_value = state_snapshot

    mock.ainvoke.return_value = {
        "messages": [
            HumanMessage(content="User input"),
            AIMessage(content=response_message)
        ],
        "next_action": "",
        "user_id": user_id
    }

    return mock
```

### Refactored Test Example

```python
# After: Behavioral approach
async def test_handle_chat_new_conversation():
    """Test chat creates new conversation when none exists."""
    # Arrange: Create behavioral mocks
    auth = create_behavioral_auth_middleware(
        authorized=True,
        user_id="alice"
    )
    agent = create_behavioral_agent_graph(
        response_message="Hi! How can I help?",
        conversation_exists=False
    )

    # Act: Test public interface
    server = MCPAgentServer(auth_middleware=auth, agent_graph=agent)
    response = await server.handle_chat(
        message="Hello",
        user_id="alice",
        token="valid-token"
    )

    # Assert: Verify behavior
    assert "Hi! How can I help?" in response
    agent.ainvoke.assert_called_once()  # Behavior verification
```

**Benefits**:
- ✅ **0 `@patch` decorators** (down from 50)
- ✅ Tests survive refactoring (public interface unchanged)
- ✅ Self-documenting (behavioral intent clear)
- ✅ ~50% fewer lines (no patch setup boilerplate)

### Implementation Steps

1. **Create Behavioral Mock API** (`tests/utils/mock_factories.py`):
   - `create_behavioral_auth_middleware()`
   - `create_behavioral_agent_graph()`
   - `create_behavioral_llm_provider()`
   - `create_behavioral_checkpointer()`

2. **Write TDD Sample Test** (RED phase):
   - Create one test using new behavioral mocks
   - Verify it fails (no implementation yet)

3. **Refactor `test_mcp_stdio_server.py`**:
   - Replace all `@patch` decorators with behavioral mocks
   - Test via dependency injection, not module patching
   - Target: <10 patches (from 50)

4. **Apply to Other Files**:
   - Find other files with >5 `@patch` decorators
   - Apply same refactoring pattern

**Estimated Effort**: 8-10 hours

---

## Phase 3: E2E Coverage Expansion (Medium Priority)

**Goal**: Implement missing E2E tests for critical user journeys

### Current State

**File**: `tests/e2e/test_full_user_journey.py`
- **1196 lines total**
- **37 test scenarios** defined
- **13 implemented** (35.1% coverage) ✅
- **24 marked `@pytest.mark.xfail`** (64.9% incomplete) ❌

### Coverage Gaps by Journey

| Journey | Implemented | Xfail | Coverage |
|---------|-------------|-------|----------|
| Standard User Flow | 6/8 | 2/8 | 75% |
| GDPR Compliance | 5/5 | 0/5 | 100% ✅ |
| Service Principal | 2/7 | 5/7 | 28.6% ⚠️ |
| API Key Flow | 3/6 | 3/6 | 50% |
| Error Recovery | 1/5 | 4/5 | 20% ❌ |
| Multi-User Collaboration | 0/3 | 3/3 | 0% ❌ |
| Performance E2E | 0/3 | 3/3 | 0% ❌ |

### Priority Order (User-Journey Sequence)

#### Priority 0: Security-Critical (Immediate)

1. **`test_08_refresh_token`** (lines 307-316)
   - **Why**: Token refresh is security-critical
   - **Implementation**: Use real Keycloak `/auth/refresh` endpoint
   ```python
   async def test_08_refresh_token(self, authenticated_session):
       """Test JWT token refresh before expiration"""
       from tests.e2e.real_clients import real_keycloak_auth

       async with real_keycloak_auth() as auth:
           old_token = authenticated_session["access_token"]
           refresh_token = authenticated_session["refresh_token"]

           # Refresh token
           new_tokens = await auth.refresh(refresh_token)

           # Verify new token works
           introspection = await auth.introspect(new_tokens["access_token"])
           assert introspection["active"] is True

           # Verify old token eventually expires
           # (may still be valid during grace period)
   ```

2. **`test_03_unauthorized_resource_access`** (lines 1023-1031)
   - **Why**: Authorization bypass is critical security flaw
   - **Implementation**: Attempt to access another user's conversation
   ```python
   async def test_03_unauthorized_resource_access(self, authenticated_session):
       """Test accessing unauthorized conversation"""
       # Create conversation as alice
       conversation_id = await mcp.create_conversation(user_id="alice")

       # Try to access as bob (should fail)
       with pytest.raises(PermissionError):
           await mcp.get_conversation(conversation_id, user_id="bob")
   ```

3. **`test_04_rate_limiting_enforcement`** (lines 1033-1041)
   - **Why**: Rate limiting prevents DoS
   - **Implementation**: Send requests exceeding rate limit

#### Priority 1: Feature Completeness

4. **`test_06_search_conversations`** (lines 266-275)
   - **Why**: Core functionality
   - **Implementation**: Use real Qdrant vector search
   ```python
   async def test_06_search_conversations(self, authenticated_session):
       """Step 6: Search user's conversations"""
       from tests.e2e.real_clients import real_mcp_client

       async with real_mcp_client(access_token=access_token) as mcp:
           # Create conversations with searchable content
           conv1_id = await mcp.create_conversation(user_id=user_id)
           await mcp.send_message(conv1_id, "Tell me about Python")

           conv2_id = await mcp.create_conversation(user_id=user_id)
           await mcp.send_message(conv2_id, "Tell me about Java")

           # Search for Python-related conversations
           results = await mcp.search_conversations(query="Python programming")

           # Verify results
           assert len(results) > 0
           assert conv1_id in [r["conversation_id"] for r in results]
           assert conv2_id not in [r["conversation_id"] for r in results]
   ```

#### Priority 2: Service Principal & API Keys

5. **TestServicePrincipalJourney** (7 tests, lines 598-773)
   - Create service principal
   - Authenticate with service credentials
   - Use service principal for API calls
   - Revoke service principal

6. **API Key Tests** (lines 775-959)
   - `test_04_use_api_key_for_tools`
   - `test_05_rotate_api_key`

### Implementation Steps

1. **Security tests first** (Priority 0)
2. **Feature completeness** (Priority 1)
3. **Service principals & API keys** (Priority 2)
4. **Remove `@pytest.mark.xfail` markers** as tests pass

**Estimated Effort**: 6-8 hours

---

## Phase 4: Polyfactory Introduction (Medium Priority)

**Goal**: Replace manual test data fixtures with type-safe factories

### Current State

**Manual Fixtures** (`tests/conftest.py`):
```python
@pytest.fixture(scope="session")
def mock_user_alice():
    """Mock user alice (session-scoped for performance)"""
    return {
        "username": "alice",
        "tier": "premium",
        "organization": "acme",
        "roles": ["admin", "user"]
    }

@pytest.fixture(scope="session")
def mock_user_bob():
    """Mock user bob (session-scoped for performance)"""
    return {
        "username": "bob",
        "tier": "standard",
        "organization": "acme",
        "roles": ["user"]
    }
```

**Problems**:
- ❌ Repetitive (manual creation)
- ❌ Not type-safe (plain dicts)
- ❌ Hard to vary (need new fixture for each variation)
- ❌ Missing edge cases (empty values, boundaries)

### Proposed Solution: Polyfactory

**Add Dependency** (`pyproject.toml`):
```toml
[project.optional-dependencies]
dev = [
    # ... existing deps ...
    "polyfactory>=2.16.2",  # Type-safe test data factories
]
```

**Create Factories** (`tests/factories/__init__.py`):
```python
from polyfactory.factories.pydantic_factory import ModelFactory
from mcp_server_langgraph.models import UserProfile, MCPRequest, Conversation


class UserProfileFactory(ModelFactory):
    """Factory for UserProfile test data."""
    __model__ = UserProfile


class MCPRequestFactory(ModelFactory):
    """Factory for MCP request test data."""
    __model__ = MCPRequest


class ConversationFactory(ModelFactory):
    """Factory for Conversation test data."""
    __model__ = Conversation
```

**Usage in Tests**:
```python
# Before: Manual fixtures
def test_premium_user_access(mock_user_alice):
    assert mock_user_alice["tier"] == "premium"
    # ... test logic ...

# After: Polyfactory
def test_premium_user_access():
    user = UserProfileFactory.build(tier="premium")
    assert user.tier == "premium"
    # ... test logic ...

# Property-based testing with Hypothesis
from hypothesis import given
from hypothesis.strategies import builds

@given(user=builds(UserProfileFactory.build))
def test_user_authorization_logic(user):
    """Test authorization for ALL possible user configurations."""
    result = authorize_user(user)
    assert isinstance(result, bool)
```

**Benefits**:
- ✅ Type-safe (Pydantic validation)
- ✅ Auto-generates valid data
- ✅ Randomization for property-based testing
- ✅ Easy overrides (`UserProfileFactory.build(username="alice")`)
- ✅ Reduces fixture code by ~500 lines

### Implementation Steps

1. Add `polyfactory` to `pyproject.toml`
2. Create `tests/factories/__init__.py`
3. Create factories for core models:
   - `UserProfileFactory`
   - `MCPRequestFactory`
   - `ConversationFactory`
   - `MessageFactory`
4. Replace manual fixtures in `conftest.py`
5. Update all test files using old fixtures

**Estimated Effort**: 4-6 hours

---

## Phase 5: Code Organization (Low Priority)

**Goal**: Reduce `conftest.py` from 2042 → <1500 lines

### Current State

**`tests/conftest.py`**: 2042 lines, 48 fixtures

**Categories**:
1. **Autouse fixtures** (266-445) - MUST stay in conftest.py
2. **Pytest hooks** (147-259) - MUST stay in conftest.py
3. **Monkey patches** (20-59) - MUST stay in conftest.py
4. **Mock data fixtures** (1599-1722) - **CAN extract** → 124 lines
5. **Resilience fixtures** (1765-1963) - **CAN extract** → 199 lines
6. **Auth fixtures** (1365-1597) - **CAN extract** → 233 lines

**Total extractable**: ~556 lines

### Implementation Plan

**1. Extract Mock Data** (`tests/fixtures/mock_data_fixtures.py`):
```python
# Move from conftest.py
@pytest.fixture
def mock_agent_state():
    """Mock LangGraph agent state"""
    return {
        "messages": [HumanMessage(content="Hello, what can you do?")],
        "next_action": "respond",
        "user_id": "alice",
        "request_id": "test-request-123",
    }

@pytest.fixture
def mock_httpx_client():
    """Mock httpx.AsyncClient for API tests"""
    # ... implementation ...
```

**2. Extract Resilience** (`tests/fixtures/resilience_fixtures.py`):
```python
@pytest.fixture
def test_circuit_breaker_config():
    """Fast circuit breaker config for testing"""
    # ... implementation ...

@pytest.fixture(autouse=True)
def reset_resilience_state():
    """Reset circuit breakers between tests"""
    # ... implementation ...
```

**3. Extract Auth** (`tests/fixtures/auth_fixtures.py`):
```python
@pytest.fixture
def mock_current_user():
    """Mock current user for FastAPI dependency injection"""
    # ... implementation ...

@pytest.fixture
def register_mcp_test_users():
    """Register test users in auth provider"""
    # ... implementation ...
```

**4. Update conftest.py**:
```python
pytest_plugins = [
    "tests.conftest_fixtures_plugin",
    "tests.fixtures.docker_fixtures",
    "tests.fixtures.time_fixtures",
    "tests.fixtures.database_fixtures",
    "tests.fixtures.mock_data_fixtures",    # NEW
    "tests.fixtures.resilience_fixtures",   # NEW
    "tests.fixtures.auth_fixtures",         # NEW
]
```

**Target**: <1500 lines (from 2042)

**Estimated Effort**: 2-3 hours

---

## Phase 6: Final Validation & Integration

**Goal**: Ensure all changes integrate with CI/CD

### Checklist

1. **Pre-commit hooks** - All checks pass
2. **Unit tests** - 100% pass
3. **Integration tests** - 100% pass
4. **E2E tests** - >80% implemented (from 35%)
5. **Coverage** - Maintain ≥80%
6. **Pre-push hooks** - CI/CD sync validated
7. **GitHub Actions** - Workflows pass

**Estimated Effort**: 2-3 hours

---

## Total Effort Estimate

| Phase | Priority | Estimated Hours |
|-------|----------|----------------|
| Phase 1: Schema Management | P0 | ✅ **COMPLETE** |
| Phase 2: Unit Test Refactoring | P1 | 8-10 hours |
| Phase 3: E2E Coverage | P1 | 6-8 hours |
| Phase 4: Polyfactory | P2 | 4-6 hours |
| Phase 5: Code Organization | P3 | 2-3 hours |
| Phase 6: Final Validation | P0 | 2-3 hours |
| **TOTAL** | | **22-30 hours** |

---

## Recommended Implementation Order

### Sprint 1 (High Priority - 10-13 hours)
1. Phase 2: Unit test refactoring (eliminate brittleness)
2. Phase 3: Security-critical E2E tests (token refresh, unauthorized access)

### Sprint 2 (Medium Priority - 10-14 hours)
3. Phase 3: Feature E2E tests (search, service principals, API keys)
4. Phase 4: Polyfactory introduction

### Sprint 3 (Low Priority - 4-6 hours)
5. Phase 5: Code organization cleanup
6. Phase 6: Final validation

---

## Success Metrics

**Before** (Current State):
- ❌ Schema drift risk (unvalidated)
- ❌ 50 @patch decorators (brittle unit tests)
- ❌ 64.9% E2E tests incomplete (24/37 xfail)
- ❌ 2042-line conftest.py (poor organization)
- ❌ Manual test data fixtures (repetitive)

**After** (Target State):
- ✅ Automated schema parity validation (Phase 1 DONE)
- ✅ <10 @patch decorators (behavioral mocks)
- ✅ >80% E2E tests implemented (<8 xfail)
- ✅ <1500-line conftest.py (well-organized)
- ✅ Type-safe test data factories (polyfactory)

---

## References

- **Audit Document**: Original findings document
- **Phase 1 Report**: `SCHEMA_MANAGEMENT_VALIDATION_2025-11-22.md`
- **Test Organization**: `TESTING_INFRASTRUCTURE_IMPROVEMENTS_2025-11-21.md`
- **Exploration Report**: Comprehensive 6000+ line analysis

---

**Document Status**: Living backlog (updated as phases complete)
**Next Action**: Begin Sprint 1 (Phase 2: Unit Test Refactoring)
