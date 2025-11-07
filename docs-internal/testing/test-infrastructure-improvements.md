# Test Infrastructure Improvements

## Overview

This document describes the comprehensive test infrastructure improvements implemented to address critical gaps identified by OpenAI Codex analysis.

**Date:** November 5, 2024
**Status:** ✅ Phase 1-3 Complete
**Impact:** Critical improvements to test reliability, coverage visibility, and determinism

---

## Changes Summary

### Phase 1: Automated Infrastructure Management

#### 1.1 Docker Compose Lifecycle Automation
- **Added:** `pytest-docker-compose-v2>=0.1.2` dependency
- **Created:** `test_infrastructure` fixture for automated service management
- **Benefit:** Eliminates manual `docker compose up/down` commands

**Before:**
```bash
# Manual setup required
docker compose -f docker-compose.test.yml up -d
export TESTING=true
pytest tests/e2e/
docker compose -f docker-compose.test.yml down -v
```

**After:**
```python
@pytest.mark.e2e
def test_with_infrastructure(test_infrastructure):
    # All services automatically started and healthy
    assert test_infrastructure["ready"]
```

#### 1.2 Comprehensive Health Checks
- PostgreSQL (port 9432)
- Redis checkpoints (port 9379)
- Redis sessions (port 9380)
- OpenFGA (port 9080)
- Keycloak (port 9082)
- Qdrant (port 9333)

Each service waits for both TCP port availability AND HTTP health endpoint readiness.

### Phase 2: Test Coverage Visibility

#### 2.1 Skip → XFail(strict=True) Conversion

Converted strategic test skips to `@pytest.mark.xfail(strict=True)` to maintain visibility:

| File | Test | Previous | Current | Impact |
|------|------|----------|---------|--------|
| `test_performance_regression.py:144` | Performance regression | `@skip` | `@xfail(strict=True)` | CRITICAL - Will XPASS when blocker fixed |
| `test_service_principals_endpoints.py:665` | Service principal lifecycle | `@skip` | `@xfail(strict=True)` | HIGH - E2E coverage gap visibility |
| `test_cost_tracker.py:454` | Cost API endpoints | `@skip` | `@xfail(strict=True)` | MEDIUM - Feature not implemented |
| `test_health_check.py:239` | Infrastructure health | `@skip` | `@xfail(strict=True)` | LOW - Integration testing |

**Benefit:** When someone fixes the underlying blocker or implements the feature, the test will XPASS and fail CI, forcing the developer to:
1. Remove the `@xfail` marker
2. Verify the test passes
3. Activate the regression/coverage test

### Phase 3: Deterministic Testing

#### 3.1 Time Freezing with Freezegun
- **Added:** `freezegun>=1.5.1` dependency
- **Created:** `frozen_time` fixture for reproducible timestamps
- **Fixed:** Non-deterministic test data in API tests

**Before:**
```python
"created": datetime.now(timezone.utc).isoformat(),  # Changes every test run!
```

**After:**
```python
FIXED_TIME = datetime(2024, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
"created": FIXED_TIME.isoformat(),  # Always 2024-01-01T00:00:00Z
```

#### 3.2 Files Updated
- `tests/conftest.py` - Added `frozen_time` fixture
- `tests/api/test_api_keys_endpoints.py` - Fixed timestamps in mock_api_key_manager
- `tests/api/test_service_principals_endpoints.py` - Fixed timestamp at line 636
- `tests/conftest.py` - Fixed mock_jwt_token to use deterministic time

**Benefit:**
- Test output is now reproducible
- Snapshot testing becomes feasible
- Debugging is easier (consistent logs)
- No timestamp drift in CI reruns

### Phase 4: Code Organization

#### 4.1 Directory Consolidation
- **Removed:** `tests/integrations/` (single file orphan)
- **Consolidated:** All integration tests now in `tests/integration/`
- **Moved:** `test_alerting.py` from `tests/integrations/` to `tests/integration/`

**Benefit:** Clear, consistent test discovery and organization

---

## Usage Guide

### Running Tests with New Infrastructure

#### Unit Tests (No Infrastructure)
```bash
pytest tests/ -m unit
```

#### Integration Tests (Automated Infrastructure)
```bash
pytest tests/ -m integration
# Infrastructure automatically starts, waits for health, tears down
```

#### E2E Tests
```bash
pytest tests/e2e/
# Full docker-compose stack managed automatically
```

### Using Frozen Time

#### Method 1: Fixture Decorator
```python
@pytest.mark.usefixtures("frozen_time")
def test_with_fixed_time():
    assert datetime.now(timezone.utc).isoformat() == "2024-01-01T00:00:00+00:00"
```

#### Method 2: Fixture Parameter
```python
def test_with_fixed_time(frozen_time):
    # Time is frozen to 2024-01-01T00:00:00Z
    assert datetime.now(timezone.utc).year == 2024
```

#### Method 3: Manual Control
```python
from freezegun import freeze_time

@freeze_time("2025-03-15 10:30:00")
def test_specific_time():
    assert datetime.now(timezone.utc).hour == 10
```

---

## Validation & Testing

### Validation Checklist

- [x] Docker infrastructure fixtures implemented
- [x] Health check waiters for all 6 services
- [x] XFail markers converted (4 strategic tests)
- [x] Time freezing implemented
- [x] Directory structure consolidated
- [ ] CI pipeline validation (pending)
- [ ] Full E2E test suite activation (Phase 2 work)

### Expected Behavior

#### When Infrastructure is Available
```bash
$ pytest tests/integration/ -v
...
Starting test infrastructure via docker-compose...
Waiting for test infrastructure health checks...
✓ PostgreSQL ready
✓ Redis (checkpoints) ready
✓ Redis (sessions) ready
✓ OpenFGA ready
✓ Keycloak ready
✓ Qdrant ready
✅ All test infrastructure services ready
...
PASSED tests/integration/test_foo.py::test_bar
...
Tearing down test infrastructure...
✅ Test infrastructure cleaned up
```

#### When Docker is Not Available
```bash
$ pytest tests/integration/ -v
SKIPPED [1] Docker daemon not available
```

---

## Remaining Work (Future Phases)

### Phase 2: E2E Test Implementation (Week 3-4)
- [ ] Create `mcp_server_fixture` in conftest.py
- [ ] Boot actual API + MCP stack via test_infrastructure
- [ ] Implement user journey tests 04-12 (currently skipped)
- [ ] SCIM provisioning automation with Keycloak fixture

### Phase 3: Performance Testing (Week 5)
- [ ] Research LangGraph-compatible LLM mocking patterns
- [ ] Implement serializable mock factory for msgpack
- [ ] Enable `test_agent_response_time_p95` (line 144)
- [ ] Add performance baseline metrics to CI

### Phase 4: Settings Refactoring (Week 5)
- [ ] Refactor `server_stdio.py:138` for dependency injection
- [ ] Update `_create_openfga_client()` to accept settings parameter
- [ ] Remove late monkeypatching from integration tests
- [ ] Update all tests to use constructor injection

---

## Best Practices

### DO

✅ Use `test_infrastructure` fixture for integration/E2E tests
✅ Use `frozen_time` for any test involving timestamps
✅ Use `@xfail(strict=True)` for tests blocked on unimplemented features
✅ Document why tests are xfailed with clear "when this is fixed..." instructions
✅ Use deterministic test data (fixed UUIDs, timestamps, etc.)

### DON'T

❌ Use `@skip` for tests that WILL be implemented (use `@xfail(strict=True)`)
❌ Use `datetime.now()` in test fixtures (use fixed time)
❌ Use random UUIDs in test data
❌ Manually start/stop docker-compose (use fixtures)
❌ Use late monkeypatching (inject at construction time)

---

## References

- **Pytest XFail Documentation:** https://docs.pytest.org/en/stable/how-to/skipping.html
- **Freezegun GitHub:** https://github.com/spulec/freezegun
- **pytest-docker-compose-v2:** https://pypi.org/project/pytest-docker-compose-v2/
- **OpenAI Codex Analysis:** (Internal validation report)

---

## Change Log

| Date | Author | Change |
|------|--------|--------|
| 2024-11-05 | vishnu2kmohan (via Claude Code) | Initial implementation of Phases 1-3 |
