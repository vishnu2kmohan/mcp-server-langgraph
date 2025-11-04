# E2E Test Strategy

## Current State (Phase 4 - Pragmatic Implementation)

### Completed: HTTP Mock-Based E2E Tests ✅

Following the OpenAI Codex recommendation to "swap to HTTP mocks" for rapid E2E activation, we've implemented:

**Enabled Tests** (3/53):
1. ✅ `test_01_login` - User authentication with Keycloak mock
2. ✅ `test_02_mcp_initialize` - MCP protocol initialization
3. ✅ `test_03_list_tools` - MCP tool listing

**Test Infrastructure**:
- `tests/e2e/helpers.py` - HTTP mock helpers (MockKeycloakAuth, MockMCPClient)
- Mock-based fixtures for lightweight testing without infrastructure

**Running E2E Tests**:
```bash
# With HTTP mocks (no infrastructure required)
TESTING=true pytest tests/e2e/test_full_user_journey.py::TestStandardUserJourney::test_01_login -v
TESTING=true pytest tests/e2e/test_full_user_journey.py::TestStandardUserJourney::test_02_mcp_initialize -v
TESTING=true pytest tests/e2e/test_full_user_journey.py::TestStandardUserJourney::test_03_list_tools -v

# Run all enabled E2E tests
TESTING=true pytest tests/e2e/test_full_user_journey.py::TestStandardUserJourney -v -k "test_01 or test_02 or test_03"
```

---

## Remaining Work (50/53 tests)

### TDD RED Phase Status

The remaining 50 E2E tests are written but **intentionally skipped** pending implementation:

**Requires Keycloak Admin API Implementation** (15+ tests):
- SCIM provisioning tests (test_scim_provisioning.py)
- User management tests
- Service principal tests
- API key tests

**Requires MCP Protocol Implementation** (20+ tests):
- Agent chat conversations
- Conversation search/retrieval
- Multi-turn conversations
- Permission checks

**Requires GDPR Implementation** (5 tests):
- Data export
- Profile updates
- Consent management
- Account deletion

**Requires Full Integration** (10+ tests):
- Service principal authentication
- API key validation
- Multi-user collaboration
- Error recovery scenarios

---

## Full Implementation Roadmap

### Phase 4A: Keycloak Admin API (Estimated: 10-15 hours)

**Implement in** `src/mcp_server_langgraph/auth/keycloak.py`:

```python
class KeycloakClient:
    async def create_user(self, username: str, email: str, password: str) -> str
    async def update_user(self, user_id: str, updates: dict) -> None
    async def delete_user(self, user_id: str) -> None
    async def get_user(self, user_id: str) -> dict
    async def list_users(self, query: str = None) -> list
    async def create_group(self, name: str) -> str
    async def add_user_to_group(self, user_id: str, group_id: str) -> None
    async def remove_user_from_group(self, user_id: str, group_id: str) -> None
```

**Tests to Enable**:
- `tests/e2e/test_scim_provisioning.py` (20 tests)
- `tests/integration/test_keycloak_admin.py` (integration tests)

### Phase 4B: MCP Protocol Test Client (Estimated: 8-12 hours)

**Implement in** `tests/e2e/mcp_test_client.py`:

```python
class MCPTestClient:
    async def connect(self, url: str, auth_token: str) -> None
    async def initialize(self) -> dict
    async def list_tools(self) -> list
    async def call_tool(self, name: str, arguments: dict) -> dict
    async def disconnect(self) -> None
```

**Tests to Enable**:
- `test_04_agent_chat_create_conversation`
- `test_05_agent_chat_continue_conversation`
- `test_06_search_conversations`
- `test_07_get_conversation`
- (15+ tests total)

### Phase 4C: GDPR & API Integration (Estimated: 6-8 hours)

**Tests to Enable**:
- GDPR journey tests (5 tests)
- API key journey tests (5 tests)
- Service principal journey tests (7 tests)

### Phase 4D: Error Recovery & Multi-User (Estimated: 4-6 hours)

**Tests to Enable**:
- Error recovery scenarios (3 tests)
- Multi-user collaboration (3 tests)

---

## Infrastructure Requirements

### Docker Compose Test Infrastructure

**Already Complete** ✅:
- `docker-compose.test.yml` - Full test infrastructure
  - PostgreSQL (port 9432)
  - Redis (ports 9379, 9380)
  - OpenFGA (port 9080)
  - Keycloak (port 9082)
  - Qdrant (port 9333)

**To Run Infrastructure**:
```bash
# Start test infrastructure
docker compose -f docker-compose.test.yml up -d

# Verify services
docker compose -f docker-compose.test.yml ps

# Run E2E tests with real infrastructure
TESTING=true pytest tests/e2e/ -v

# Stop infrastructure
docker compose -f docker-compose.test.yml down -v
```

---

## Migration Path: Mocks → Real Infrastructure

### Current Approach (HTTP Mocks)

**Advantages**:
- ✅ Fast execution (<1s per test)
- ✅ No infrastructure dependencies
- ✅ Easy to run in CI/CD
- ✅ Validates test logic and assertions

**Limitations**:
- ❌ Doesn't catch integration bugs
- ❌ Doesn't test real Keycloak/OpenFGA behavior
- ❌ Doesn't validate network layer

### Future Approach (Real Infrastructure)

**When to Switch**:
1. Keycloak Admin API implemented
2. MCP protocol client implemented
3. CI runners configured with Docker support

**Migration Steps**:
1. Keep HTTP mock fixtures for unit-style E2E tests
2. Add `@pytest.mark.requires_infrastructure` decorator
3. Run both mock and real infrastructure tests
4. Gradually migrate critical paths to real infrastructure

**Example**:
```python
@pytest.mark.e2e
@pytest.mark.requires_infrastructure  # New marker
async def test_01_login_real_keycloak(test_infrastructure_check):
    """Test login with real Keycloak instance"""
    # Uses real KeycloakClient instead of mocks
    # Requires docker-compose.test.yml running
```

---

## Estimated Completion

**Current Progress**: 3/53 E2E tests enabled (5.7%)

**Phase 4 Full Implementation**:
- **Time Estimate**: 28-41 hours
- **Complexity**: High (requires Keycloak Admin API, MCP client)
- **Dependencies**: Infrastructure, authentication, protocols

**Recommendation**:
- ✅ Current mock-based approach validates test framework
- ✅ Enables gradual migration to real infrastructure
- ✅ Follows TDD principles (tests written first)
- 🔄 Full implementation should be prioritized based on project needs

---

## CI/CD Integration

### Current CI (Mock-Based)

```yaml
# .github/workflows/e2e-tests.yaml
- name: Run E2E tests (mocked)
  run: |
    TESTING=true pytest tests/e2e/ -v -k "test_01 or test_02 or test_03"
```

### Future CI (Infrastructure-Based)

```yaml
# Future: Full E2E with infrastructure
- name: Start test infrastructure
  run: docker compose -f docker-compose.test.yml up -d

- name: Wait for services
  run: docker compose -f docker-compose.test.yml ps --wait

- name: Run E2E tests (real infrastructure)
  run: |
    TESTING=true pytest tests/e2e/ -v -m "e2e and requires_infrastructure"

- name: Stop infrastructure
  if: always()
  run: docker compose -f docker-compose.test.yml down -v
```

---

## References

- **Infrastructure**: `/docker-compose.test.yml`
- **HTTP Mocks**: `/tests/e2e/helpers.py`
- **Integration Tests**: `/tests/integration/test_keycloak_admin.py`
- **Test Fixtures**: `/tests/e2e/test_full_user_journey.py:32-91`

**Last Updated**: 2025-11-04
**Status**: Phase 4 - Pragmatic Implementation (3/53 tests enabled with mocks)
