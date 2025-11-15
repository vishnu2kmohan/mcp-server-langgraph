# Coverage Improvement Plan

**Status:** Current: 65.78% | Target: 80%+ | Gap: 14.22 percentage points
**Updated:** 2025-11-15 (Phase 1 Complete, Phase 2 In Progress)
**Estimated Effort:** 12-16 hours remaining
**Priority:** HIGH (enforced via CI/CD fail_under=64, target 80)

---

## Executive Summary

Following OpenAI Codex validation (2025-11-14), coverage threshold enforcement has been added to CI/CD. This document outlines a systematic plan to reach 80%+ coverage.

**Phase 1 (COMPLETED - 2025-11-15):**
- ✅ Added `fail_under = 64` to pyproject.toml (realistic threshold)
- ✅ Created 97 new tests for monitoring modules
- ✅ Improved coverage from 63.88% → 65.78% (+1.9%)
- ✅ prometheus_client.py: 44% → 87% (+43%)
- ✅ budget_monitor.py: 47% → 81% (+34%)
- ✅ cost_api.py: 55% → 91% (+36%)
- ✅ Excluded developer tools from coverage (quickstart.py, playground)
- ✅ Pushed to GitHub and validated CI/CD

**Phase 2 (IN PROGRESS - 2025-11-15):**
- ✅ Created fast_resilience_config fixture for faster tests
- ✅ Created meta-test for coverage enforcement (test_coverage_enforcement.py)
- ✅ Created meta-test for performance regression (test_performance_regression_suite.py)
- ✅ Created meta-test for slow test detection (test_slow_test_detection.py)
- ✅ Added 3 pre-commit hooks for regression prevention
- ⏳ Optimize slow tests (OpenFGA: 45s, Agent: 14-29s)
- ⏳ Improve test suite performance (current: 220s, target: <120s)

**Remaining Work (Phase 3+):**
- ⏳ Write comprehensive unit tests for high-impact modules
- ⏳ Achieve 80%+ coverage across all production code

---

## Phase 2: Performance Optimization & Regression Prevention (2025-11-15)

### Objectives
1. **Prevent coverage regression** below 64% minimum threshold
2. **Prevent performance regression** of test suite
3. **Detect slow individual tests** before they compound
4. **Create fast test execution infrastructure**

### Completed Work

#### 2.1 fast_resilience_config Fixture
**Location:** `tests/conftest.py:1750-1792`
**Purpose:** Reduce circuit breaker timeouts from 30-60s to 1s for faster tests

```python
@pytest.fixture
def fast_resilience_config():
    """Configure all circuit breakers with minimal timeouts for fast testing."""
    test_config = ResilienceConfig(
        enabled=True,
        circuit_breakers={
            "llm": CircuitBreakerConfig(name="llm", fail_max=3, timeout_duration=1),
            "openfga": CircuitBreakerConfig(name="openfga", fail_max=3, timeout_duration=1),
            # ... other services
        },
    )
    set_resilience_config(test_config)
    # Clear existing circuit breaker instances to force recreation
    # ...
```

**Impact:** Reduces circuit breaker test time from 30-60s → <2s

**Limitation Discovered:** OpenFGA tests still slow due to **retry logic**, not circuit breaker timeout
- 45s delay = 15 failed calls × 3 retries × ~1s per retry
- Retry decorator wraps circuit breaker, causing multiple retry attempts
- **Future optimization needed:** Configure retry attempts for tests

#### 2.2 Meta-Tests for Regression Prevention

Created 3 meta-tests to prevent quality regression:

**A. Coverage Enforcement** (`tests/meta/test_coverage_enforcement.py`)
- Runs full unit test suite with coverage measurement
- Enforces minimum 64% threshold (CI requirement)
- Warns if below 65% baseline (Phase 1 achievement)
- Documents Phase 1 improvements in error messages
- **Execution time:** ~2-3 minutes (runs full test suite)

**B. Performance Regression** (`tests/meta/test_performance_regression_suite.py`)
- Validates unit test suite completes in < 120 seconds
- Current: 220s (TOO SLOW, exceeds target)
- Target: < 120s for acceptable TDD workflow
- Ideal: < 60s for rapid iteration
- **Known slow tests documented for future optimization**

**C. Slow Test Detection** (`tests/meta/test_slow_test_detection.py`)
- Detects individual unit tests > 10 seconds
- Maintains KNOWN_SLOW_TESTS allowlist
- Fails if NEW slow tests are introduced
- Provides optimization strategies in error messages
- **Known slow tests:**
  - OpenFGA circuit breaker: 45s each (3 tests)
  - Agent tests: 14-29s each (8 tests)
  - Retry timing test: 14s (1 test)

#### 2.3 Pre-Commit Hooks

Added 3 new hooks to `.pre-commit-config.yaml`:

**A. validate-minimum-coverage** (pre-push stage)
- Runs: `pytest tests/meta/test_coverage_enforcement.py`
- Triggers: Changes to `src/**/*.py`, `tests/**/*.py`, `pyproject.toml`
- Prevents: Coverage dropping below 64%
- **Stage:** pre-push (slow: runs full test suite)

**B. validate-test-suite-performance** (manual stage)
- Runs: `pytest tests/meta/test_performance_regression_suite.py`
- Validates: Suite completes in < 120s
- **Stage:** manual (use for performance audits)
- **Usage:** `SKIP= pre-commit run validate-test-suite-performance`

**C. detect-slow-unit-tests** (manual stage)
- Runs: `pytest tests/meta/test_slow_test_detection.py`
- Detects: Individual tests > 10s
- **Stage:** manual (use for performance audits)
- **Usage:** `SKIP= pre-commit run detect-slow-unit-tests`

### Performance Analysis & Findings

#### Current Test Suite Performance
- **Total duration:** 220.72s (3m 40s)
- **Target:** < 120s (2 minutes)
- **Gap:** 100.72s (45% over target)

#### Root Causes of Slowness

**1. OpenFGA Circuit Breaker Tests (45s each × 3 tests = 135s)**
```python
# tests/test_openfga_client.py:518-676
# TestOpenFGACircuitBreakerCriticality

# Why slow?
# - Triggers circuit breaker to open (requires 15 failures)
# - Each failure retries 3 times (@retry_with_backoff decorator)
# - 15 calls × 3 retries × ~1s = 45s per test

# Optimization strategy:
# 1. Mock retry decorator configuration for tests
# 2. Reduce retry attempts to 1 for test scenarios
# 3. Alternative: Use fast_resilience_config + mock retries
```

**2. Agent Tests (14-29s each × 8 tests = 160s)**
```python
# tests/test_agent.py
# TestAgentGraph

# Why slow?
# - Actually executes full LangGraph workflow via graph.ainvoke()
# - Real ContextManager and OutputVerifier execution
# - LLM calls (even mocked) have overhead
# - State persistence and retrieval

# Optimization strategy:
# 1. Mock ContextManager to return immediately
# 2. Mock OutputVerifier to skip validation
# 3. Mock graph.ainvoke() to return predetermined state
# 4. Use unit tests for components, integration tests for full workflow
```

**3. Retry Timing Test (14s)**
```python
# tests/resilience/test_retry.py:118
# test_exponential_backoff_timing

# Why slow?
# - Actually sleeps for exponential backoff (1s, 2s, 4s, 8s)
# - Validates real time delays

# Optimization strategy:
# 1. Use freezegun to mock time.sleep()
# 2. Advance time instantly instead of actual sleeping
# 3. Validate backoff calculation without waiting
```

### Recommendations for Phase 3

#### Priority 1: Optimize OpenFGA Tests (High Impact)
- **Estimated effort:** 2-4 hours
- **Impact:** Reduce suite time by ~135s (61% improvement)
- **Approach:**
  1. Create test-specific retry configuration (max_attempts=1)
  2. Mock or configure retry decorator for tests
  3. Keep fail_max=3 but eliminate retry delays

#### Priority 2: Optimize Agent Tests (High Impact)
- **Estimated effort:** 4-6 hours
- **Impact:** Reduce suite time by ~160s (72% improvement)
- **Approach:**
  1. Split into unit tests (fast, mocked) and integration tests (slow, real)
  2. Mock ContextManager and OutputVerifier for unit tests
  3. Keep integration tests for E2E validation
  4. Run integration tests less frequently (nightly builds)

#### Priority 3: Optimize Retry Timing Test (Low Impact)
- **Estimated effort:** 1 hour
- **Impact:** Reduce suite time by ~14s (6% improvement)
- **Approach:**
  1. Use freezegun to mock time
  2. Validate backoff calculation without sleeping

### Success Metrics

**Phase 2 Achievements:**
- ✅ Coverage regression prevention in place (meta-test + hook)
- ✅ Performance regression detection in place (meta-tests)
- ✅ Slow test detection prevents new performance issues
- ✅ Fast test infrastructure available (fast_resilience_config)
- ✅ Documentation updated with findings and strategies

**Phase 3 Targets:**
- ⏳ Test suite duration < 120s (current: 220s)
- ⏳ No individual unit test > 5s (current: 3 tests at 45s, 8 tests at 14-29s)
- ⏳ Coverage ≥ 70% (after key modules tested)

---

## Coverage Analysis by Module

### Critical Gaps (Highest Priority)

| Module | Current | Target | Gap | Effort | Impact |
|--------|---------|--------|-----|--------|--------|
| `execution/kubernetes_sandbox.py` | 10% | 80% | 70% | 4-6h | 🔴 HIGH |
| `mcp/server_streamable.py` | 20% | 80% | 60% | 3-4h | 🔴 HIGH |
| `builder/codegen/generator.py` | 20% | 70% | 50% | 2-3h | 🟡 MEDIUM |
| `builder/importer/ast_parser.py` | 7% | 70% | 63% | 2-3h | 🟡 MEDIUM |
| `compliance/gdpr/postgres_storage.py` | 17% | 70% | 53% | 1-2h | 🟠 LOW |
| `observability/langsmith.py` | 26% | 60% | 34% | 1-2h | 🟠 LOW |

**Well-Covered Modules (Reference Examples):**
- ✅ `health/checks.py` (100%)
- ✅ `execution/resource_limits.py` (98%)
- ✅ `execution/code_validator.py` (94%)
- ✅ `auth/api_keys.py` (89%)

---

## Phase 1: kubernetes_sandbox.py (10% → 80%)

**Current Coverage:** 10% (13,916 statements total, 4,550 missed)
**Estimated Effort:** 4-6 hours
**Priority:** 🔴 CRITICAL (infrastructure safety)

### Test Categories Needed

#### 1.1 Pod Lifecycle Tests
```python
# tests/unit/execution/test_kubernetes_sandbox_lifecycle.py

@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesSandboxPodLifecycle:
    """Test pod creation, execution, and cleanup."""

    def test_create_pod_with_default_settings(self, mock_k8s_client):
        """Verify pod creation with default resource limits."""
        # TDD RED: Test currently fails (function not tested)
        # TDD GREEN: Implement test to verify pod spec
        pass

    def test_create_pod_with_custom_resources(self, mock_k8s_client):
        """Verify custom CPU/memory limits are applied."""
        pass

    def test_delete_pod_on_cleanup(self, mock_k8s_client):
        """Verify pod is deleted after execution."""
        pass

    def test_force_delete_on_timeout(self, mock_k8s_client):
        """Verify force deletion when pod hangs."""
        pass
```

#### 1.2 Error Handling Tests
```python
@pytest.mark.unit
@pytest.mark.kubernetes
class TestKubernetesSandboxErrorHandling:
    """Test error scenarios and recovery."""

    def test_pod_creation_failure_raises_error(self, mock_k8s_client):
        """Verify proper error when pod creation fails."""
        pass

    def test_pod_timeout_cleanup(self, mock_k8s_client):
        """Verify cleanup happens even on timeout."""
        pass

    def test_api_server_unavailable_handling(self, mock_k8s_client):
        """Verify graceful degradation when K8s API unavailable."""
        pass
```

#### 1.3 Security Context Tests
```python
@pytest.mark.unit
@pytest.mark.security
@pytest.mark.kubernetes
class TestKubernetesSandboxSecurity:
    """Test security controls and isolation."""

    def test_security_context_applied(self, mock_k8s_client):
        """Verify security context prevents privilege escalation."""
        pass

    def test_network_policy_isolation(self, mock_k8s_client):
        """Verify network isolation between pods."""
        pass

    def test_resource_quota_enforcement(self, mock_k8s_client):
        """Verify resource quotas prevent resource exhaustion."""
        pass
```

### Mock Strategy
```python
@pytest.fixture
def mock_k8s_client():
    """Mock Kubernetes client for unit tests."""
    with patch('kubernetes.client.CoreV1Api') as mock:
        mock.return_value.create_namespaced_pod.return_value = MagicMock(
            metadata=MagicMock(name='test-pod'),
            status=MagicMock(phase='Running')
        )
        yield mock
```

---

## Phase 2: server_streamable.py (20% → 80%)

**Current Coverage:** 20%
**Estimated Effort:** 3-4 hours
**Priority:** 🔴 CRITICAL (MCP protocol core)

### Test Categories Needed

#### 2.1 SSE Streaming Tests
```python
# tests/unit/mcp/test_server_streamable_sse.py

@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.asyncio
class TestServerStreamableSSE:
    """Test Server-Sent Events streaming behavior."""

    async def test_stream_response_chunks(self):
        """Verify response is streamed in chunks."""
        pass

    async def test_stream_error_propagation(self):
        """Verify errors are propagated through stream."""
        pass

    async def test_stream_backpressure_handling(self):
        """Verify backpressure when client is slow."""
        pass
```

#### 2.2 Connection Management Tests
```python
@pytest.mark.unit
@pytest.mark.mcp
@pytest.mark.asyncio
class TestServerStreamableConnections:
    """Test connection lifecycle and cleanup."""

    async def test_connection_established(self):
        """Verify connection is established correctly."""
        pass

    async def test_connection_closed_on_complete(self):
        """Verify connection cleanup on normal completion."""
        pass

    async def test_connection_closed_on_error(self):
        """Verify connection cleanup on error."""
        pass
```

---

## Phase 3: Builder/Codegen Modules (7-20% → 70%)

**Estimated Effort:** 4-6 hours
**Priority:** 🟡 MEDIUM (developer tools)

### Modules
1. `builder/codegen/generator.py` (20% → 70%)
   - Test code generation templates
   - Test variable substitution
   - Test edge cases (empty inputs, special characters)

2. `builder/importer/ast_parser.py` (7% → 70%)
   - Test AST parsing for different Python constructs
   - Test import graph extraction
   - Test error handling for malformed code

---

## Phase 4: Compliance & Observability (17-26% → 60-70%)

**Estimated Effort:** 2-4 hours
**Priority:** 🟠 LOW (can defer if needed)

### Modules
1. `compliance/gdpr/postgres_storage.py` (17% → 70%)
2. `observability/langsmith.py` (26% → 60%)

---

## Implementation Strategy

### TDD Workflow (CRITICAL)
```text
For each module:
1. 🔴 RED: Write test that fails (proves validation works)
2. 🟢 GREEN: Implement minimal code to pass test
3. ♻️ REFACTOR: Improve code quality while keeping tests green
4. 📊 VERIFY: Run coverage to confirm improvement
5. ✅ COMMIT: Commit tests + implementation together
```

### Test Organization
```text
tests/
├── unit/
│   ├── execution/
│   │   ├── test_kubernetes_sandbox_lifecycle.py  # New
│   │   ├── test_kubernetes_sandbox_errors.py     # New
│   │   └── test_kubernetes_sandbox_security.py   # New
│   └── mcp/
│       ├── test_server_streamable_sse.py         # New
│       └── test_server_streamable_connections.py # New
└── meta/
    └── test_codex_config_validation.py            # ✅ Done
```

### Mocking Guidelines
- **Mock external dependencies**: Kubernetes API, databases, HTTP clients
- **Test behavior, not implementation**: Focus on contracts and outcomes
- **Use realistic test data**: Representative of production scenarios
- **Test error paths**: 50% of coverage should be error handling

---

## Coverage Verification

### Before Each Commit
```bash
# Run tests with coverage
pytest tests/ -m unit --cov=src/mcp_server_langgraph --cov-report=term-missing

# Verify coverage meets threshold
# (CI will enforce fail_under=80)
```

### Coverage Targets by Phase
- **After Phase 1:** 70% overall (kubernetes_sandbox done)
- **After Phase 2:** 75% overall (server_streamable done)
- **After Phase 3:** 79% overall (builder modules done)
- **After Phase 4:** 80%+ overall (✅ meets threshold)

---

## Risks & Mitigation

### Risk 1: Coverage Enforcement Blocks CI
**Mitigation:**
- Temporarily lower threshold to 70% if needed
- Create tracking issue for 80% target
- Set deadline for completion

### Risk 2: Complex Modules Hard to Test
**Mitigation:**
- Focus on testable units (pure functions, clear interfaces)
- Use comprehensive mocking for external dependencies
- Refactor if needed to improve testability

### Risk 3: Time Estimation Too Optimistic
**Mitigation:**
- Start with highest-impact modules (kubernetes_sandbox, server_streamable)
- Re-evaluate after Phase 1 completion
- Adjust threshold if necessary

---

## Success Criteria

- ✅ Overall coverage ≥ 80%
- ✅ No module below 50% coverage (infrastructure critical)
- ✅ All tests follow TDD principles (RED-GREEN-REFACTOR)
- ✅ No skipped tests without documented reason
- ✅ CI/CD passes with coverage enforcement
- ✅ Test runtime remains under 5 minutes

---

## Timeline

**Optimistic:** 12 hours (3 workdays @ 4h/day)
**Realistic:** 16 hours (4 workdays @ 4h/day)
**Pessimistic:** 20 hours (5 workdays @ 4h/day)

**Recommendation:** Allocate 2 weeks for completion with buffer.

---

## References

- Codex Validation Summary: `docs-internal/CODEX_VALIDATION_SUMMARY_2025-11-14.md`
- Test Memory Safety Guidelines: `tests/MEMORY_SAFETY_GUIDELINES.md`
- Coverage Report (current): `htmlcov/index.html` (run `make test-unit` to generate)

---

**Document Created:** 2025-11-14
**Next Review:** After Phase 1 completion
**Owner:** Engineering Team
