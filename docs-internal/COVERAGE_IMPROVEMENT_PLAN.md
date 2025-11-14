# Coverage Improvement Plan

**Status:** Current: 64% | Target: 80%+ | Gap: 16 percentage points
**Estimated Effort:** 12-16 hours
**Priority:** HIGH (enforced via CI/CD fail_under=80)

---

## Executive Summary

Following OpenAI Codex validation (2025-11-14), coverage threshold enforcement has been added to CI/CD. Current coverage at 64% will cause CI failures. This document outlines a systematic plan to reach 80%+ coverage.

**Immediate Changes (Completed):**
- ✅ Added `fail_under = 80` to pyproject.toml
- ✅ Added `--benchmark-disable` to suppress pytest-benchmark warnings
- ✅ Created validation tests to prevent configuration regression

**Remaining Work:**
- ⏳ Write comprehensive unit tests for high-impact modules
- ⏳ Achieve 80%+ coverage across all production code

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
