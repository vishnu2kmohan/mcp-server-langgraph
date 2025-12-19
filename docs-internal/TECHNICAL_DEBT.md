# Technical Debt Tracking

**Purpose:** Centralized tracking of known technical debt across the MCP Server LangGraph project.

**Last Updated:** 2025-12-19

**Owner:** Engineering Team

**Review Cadence:** Quarterly (Q1, Q2, Q3, Q4)

---

## Table of Contents

1. [Overview](#overview)
2. [Categories](#categories)
3. [Current Known Issues](#current-known-issues)
4. [Remediation Strategy](#remediation-strategy)
5. [Tracking Table](#tracking-table)
6. [Quarterly Review Process](#quarterly-review-process)
7. [References](#references)

---

## Overview

This document tracks technical debt that has been:

- **Acknowledged**: Identified through code analysis, Codex findings, or development experience
- **Documented**: Captured with inline comments, noqa markers, or ADRs
- **Deferred**: Intentionally postponed for valid reasons (time, priority, risk)
- **Trackable**: Can be measured and monitored over time

### Debt Philosophy

Technical debt is not inherently bad. Like financial debt, it can be a strategic tool when:

1. **Consciously Acquired**: Team knowingly accepts debt for valid reasons
2. **Well Documented**: Debt is tracked with context and remediation plans
3. **Actively Managed**: Regular review prevents debt from becoming unmanageable
4. **Time-Bounded**: Debt has clear repayment plan or acceptance criteria

### Debt vs. Quality Issues

**Technical Debt** (tracked here):
- Intentional shortcuts with documented trade-offs
- Pre-existing patterns marked for future improvement
- Known limitations with workarounds

**Quality Issues** (NOT tracked here):
- Bugs requiring immediate fixes
- Security vulnerabilities (handled via security process)
- Production incidents (tracked in incident management)

---

## Categories

### 1. Test Suite Debt

Technical debt in the test suite that affects maintainability, performance, or reliability.

**Examples:**
- AsyncMock configuration violations
- Excessive sleep durations
- pytest-xdist compatibility issues
- Test fixture organization
- Dead test code after return statements

**Impact:**
- Slower test execution
- Intermittent test failures
- Security vulnerabilities (unconfigured authorization mocks)
- Maintenance burden

### 2. Documentation Debt

Documentation that is incomplete, outdated, or needs synchronization.

**Examples:**
- ADR sync between `adr/` and `docs/architecture/`
- Placeholder URLs in documentation
- Missing API documentation
- Outdated architecture diagrams
- Incomplete user guides

**Impact:**
- Developer onboarding friction
- Incorrect implementation assumptions
- Lost architectural knowledge
- Poor user experience

### 3. Configuration Debt

Configuration files and infrastructure-as-code that need cleanup or modernization.

**Examples:**
- Pre-commit hook configurations
- Makefile pattern consolidation
- Docker Compose service definitions
- Helm chart placeholder values
- GitHub Actions workflow optimization

**Impact:**
- CI/CD pipeline complexity
- Deployment configuration drift
- Developer environment setup friction
- Inconsistent validation

### 4. Code Quality Debt

Code patterns that work but don't meet current standards.

**Examples:**
- Missing type annotations (`# type: ignore` markers)
- Deprecated import patterns
- TODO/FIXME comments in source code
- Code duplication
- Over-complex functions

**Impact:**
- Reduced code maintainability
- Type safety gaps
- Future refactoring burden
- Knowledge silos

### 5. Observability Backend Debt

Unimplemented observability backend integrations.

**Examples:**
- Jaeger backend (traces)
- AWS X-Ray backend (traces)
- Azure Application Insights backend (traces)
- Elasticsearch backend (logs)
- AWS CloudWatch integrations (logs, metrics, alerts)
- Datadog Metrics backend
- Azure Monitor Alerts backend

**Impact:**
- Limited multi-cloud observability
- Manual backend switching for different environments
- Incomplete monitoring coverage

---

## Current Known Issues

### Test Suite Debt

#### 1. AsyncMock Configuration Violations

**Status:** 🔴 CRITICAL (Security)

**Description:** 435+ unconfigured `AsyncMock()` instances that return truthy values when awaited, causing authorization checks to incorrectly pass.

**Files Affected:**
- 54 test files with `# async-mock-configured` markers
- Examples:
  - `tests/compliance/test_soc2_audit_requirements.py:168`
  - `tests/compliance/test_hipaa_audit_requirements.py:183`
  - `tests/compliance/test_gdpr_audit_requirements.py:197`
  - `tests/api/test_user_api.py:132`
  - `tests/unit/bootstrap/test_bootstrap_modules.py:242`

**Root Cause:** Unconfigured AsyncMock returns `<AsyncMock>` (truthy) instead of `False`, bypassing security checks.

**Security Impact:** Critical - authorization logic may incorrectly grant access.

**Remediation:** Use safe helper factories from `tests.helpers.async_mock_helpers`:
- `configured_async_mock_deny()` - Safe default for authorization
- `configured_async_mock_allow()` - Explicit permission grant
- `configured_async_mock_void()` - For void functions

**References:**
- `docs-internal/ASYNC_MOCK_REMEDIATION_GUIDE.md`
- `tests/ASYNC_MOCK_GUIDELINES.md`
- `.pre-commit-config.yaml` hook: `check-async-mock-configuration`
- Commit: `abb04a6a` (SCIM security vulnerability fix)

#### 2. Sleep Duration Violations

**Status:** 🟡 MEDIUM (Performance)

**Description:** 5 test files with sleep durations exceeding recommended limits, causing slow test execution.

**Files Affected:**
- `tests/unit/api/v1/test_streaming_outbound_rate_limit.py:132` - 1.1s sleep (rate limit window)
- `tests/unit/api/v1/test_mcp_websocket.py:777` - 1.1s sleep (rate limit window)
- `tests/unit/api/v1/test_mcp_websocket.py:1901` - 1.1s sleep (connection timeout)
- `tests/unit/execution/test_kubernetes_sandbox_async.py:365` - 10s sleep (timeout testing)
- `tests/unit/execution/test_docker_sandbox_async.py:317` - 10s sleep (timeout testing)

**Total Impact:** ~24s of wall-clock sleep in active tests (acceptable within 60s budget)

**Recommended Limits:**
- Unit tests: max 0.5s sleep
- Integration tests: max 2.0s sleep

**Remediation:**
- Use `VirtualClock` for instant time advancement (preferred)
- Document justification with `# noqa: sleep-duration` marker
- Consider alternative testing strategies (event-driven, mocking)

**References:**
- `.pre-commit-config.yaml` hook: `check-test-sleep-duration`
- `scripts/validators/check_test_sleep_budget.py` (60s max, 45s warning)

#### 3. pytest-xdist Memory Safety

**Status:** 🟢 RESOLVED (Documented Pattern)

**Description:** AsyncMock/MagicMock objects in pytest-xdist workers create circular references, causing memory explosion (217GB VIRT observed).

**Solution:** 3-part pattern enforced by pre-commit hooks:
1. `@pytest.mark.xdist_group(name="...")` - Group related tests
2. `teardown_method() + gc.collect()` - Force garbage collection
3. Performance tests skip xdist: `@pytest.mark.skipif(os.getenv("PYTEST_XDIST_WORKER")...)`

**Impact:** 98% memory reduction (217GB → 1.8GB), 40% faster test runs

**References:**
- `tests/MEMORY_SAFETY_GUIDELINES.md`
- `.claude/context/xdist-safety-patterns.md` (1,800 lines of examples)
- `.pre-commit-config.yaml` hook: `check-test-memory-safety`
- `scripts/validation/check_test_memory_safety.py`

### Documentation Debt

#### 4. Placeholder URLs in Deployment Configs

**Status:** 🟡 MEDIUM (Configuration)

**Description:** Unresolved placeholder URLs and project IDs in deployment configuration files.

**Files Affected:**
- `deployments/monitoring/slo-alerts.yaml`
- `deployments/helm/mcp-server-langgraph/values.yaml`
- `deployments/helm/values-production-gke.yaml`
- `config/alerts.yaml`
- `monitoring/prometheus/alerts/*.yaml`
- `deployments/overlays/production-gke/kustomization.yaml`

**Patterns to Fix:**
- `YOUR_STAGING_PROJECT_ID`
- `YOUR_GCP_PROJECT_ID`
- `@PROJECT_ID.iam.gserviceaccount.com` (not using variable substitution)
- `example.com` in alerting URLs

**Safe Patterns:**
- `${GCP_PROJECT_ID}` (variable substitution)
- Actual project IDs for specific environments
- `*.local.yaml` files for deployment-specific configs (gitignored)

**References:**
- `.pre-commit-config.yaml` hook: `check-helm-placeholders`
- Codex findings: `values-staging.yaml:108`, `values-production.yaml:139`

#### 5. ADR Synchronization

**Status:** 🟢 ACTIVE (Enforced)

**Description:** Architecture Decision Records must be synchronized between `adr/` (source) and `docs/architecture/` (published).

**Enforcement:**
- Pre-commit hook: `validate-adr-sync` (via `validate-docs`)
- ADR index validation: `validate-adr-index`
- Automated generation: `scripts/docs/generate_adr_index.py`

**Process:**
1. Create/update ADR in `adr/`
2. Run `make docs-sync-adr` (or let pre-commit hook validate)
3. Verify `docs/architecture/` is updated
4. Update `adr/README.md` index

**References:**
- `.pre-commit-config.yaml` hook: `validate-docs --adr`
- `scripts/validators/validate_docs.py`

### Configuration Debt

#### 6. Pre-Commit Hook Consolidation

**Status:** 🟢 RESOLVED (ADR-0052, ADR-0053)

**Description:** 69 pre-commit hooks consolidated from 21 separate pytest invocations to 1 unified test runner.

**Achievement:**
- Time savings: ~4 minutes per pre-push
- Single test discovery: ~13s (vs ~4.5 min for 21 sessions)
- Eliminated pytest cache/coverage lock contention
- Fail-fast across all test categories

**Current State:**
- `run-pre-push-tests` hook: Consolidated marker-based test execution
- `validate-fast` hook: Consolidated fast validators
- `validate-docs` hook: Consolidated documentation validators (7 → 1)

**References:**
- `docs-internal/ADR-0052-GIT-HOOKS-CI-PARITY.md`
- `docs-internal/ADR-0053-MAKEFILE-PREPUSH-PARITY-ENFORCEMENT.md`
- `.pre-commit-config.yaml` hook: `run-pre-push-tests`

#### 7. Makefile Pattern Standardization

**Status:** 🟢 RESOLVED (ADR-0053)

**Description:** 133 make targets with standardized patterns and CI parity enforcement.

**Patterns:**
- `make validate-*`: Validation targets (CI parity)
- `make test-*`: Test execution targets
- `make docs-*`: Documentation targets
- `make deploy-*`: Deployment targets

**References:**
- `.claude/memory/make-targets.md`
- `docs-internal/ADR-0053-MAKEFILE-PREPUSH-PARITY-ENFORCEMENT.md`

### Code Quality Debt

#### 8. Type Ignore Markers

**Status:** 🟡 MEDIUM (Type Safety)

**Description:** 303 `# type: ignore` markers across 83 source files.

**Top Files:**
- `src/mcp_server_langgraph/llm/factory.py` - 18 markers
- `src/mcp_server_langgraph/core/cache.py` - 15 markers
- `src/mcp_server_langgraph/core/agent_graph_builder.py` - 14 markers
- `src/mcp_server_langgraph/monitoring/prometheus_client.py` - 11 markers
- `src/mcp_server_langgraph/middleware/rate_limiter.py` - 9 markers

**Remediation Strategy:**
1. **Phase 1**: Add proper type annotations to eliminate markers
2. **Phase 2**: Use `typing.cast()` for unavoidable cases
3. **Phase 3**: Update mypy configuration for stricter checking

**References:**
- `.pre-commit-config.yaml` hook: `mypy` (pre-push stage)
- `pyproject.toml` - mypy configuration

#### 9. TODO/FIXME Comments

**Status:** 🟢 TRACKED (Informational)

**Description:** 18+ source files with TODO/FIXME comments, primarily in observability backends.

**Top Categories:**
1. **Observability Backends** (11 TODOs in `observability/query/factory.py`):
   - Jaeger backend (traces)
   - AWS X-Ray backend (traces)
   - Azure Application Insights backend (traces)
   - Elasticsearch backend (logs)
   - AWS CloudWatch Logs backend
   - AWS CloudWatch Metrics backend
   - Datadog Metrics backend
   - GCP Cloud Monitoring Alerting backend
   - AWS CloudWatch Alarms backend
   - Azure Monitor Alerts backend

2. **Frontend E2E Tests** (4 TODOs in `studio/frontend/e2e/artifact-rendering.spec.ts`):
   - Mermaid diagram rendering verification
   - Chart rendering verification
   - Artifact interactivity testing

3. **API Documentation** (scattered in `api/v1/*.py`):
   - OpenAPI schema enhancements
   - Example request/response documentation

**Strategy:** Track via `todo-audit.py` (manual stage), prioritize during feature development.

**References:**
- `.pre-commit-config.yaml` hook: `audit-todo-fixme-markers` (manual stage)
- `scripts/validators/todo_audit.py`

---

## Remediation Strategy

### Prioritization Framework

**P0 - CRITICAL** (Security, Production Blockers)
- **Timeline:** Immediate (within sprint)
- **Examples:** AsyncMock security violations, production deployment blockers
- **Approval:** Required before release

**P1 - HIGH** (Performance, Developer Experience)
- **Timeline:** Next quarter
- **Examples:** Sleep duration violations, type annotation gaps
- **Approval:** Include in quarterly planning

**P2 - MEDIUM** (Maintainability, Technical Excellence)
- **Timeline:** Within 6 months
- **Examples:** Documentation sync, placeholder cleanup
- **Approval:** Opportunistic during related work

**P3 - LOW** (Nice-to-Have, Future Improvements)
- **Timeline:** Backlog
- **Examples:** Observability backend implementations, code refactoring
- **Approval:** As capacity allows

### Remediation Approaches

#### 1. Incremental Improvement

**When:** Large-scale debt (e.g., 435 AsyncMock violations)

**Strategy:**
1. Stop adding new debt (enforced via pre-commit hooks)
2. Fix violations as you touch files (boy scout rule)
3. Dedicate 10% of sprint capacity to debt reduction
4. Track progress via metrics (violations count, coverage %)

**Example:** AsyncMock remediation
- Phase 1: Create safe helper fixtures ✅
- Phase 2: Fix high-risk authorization mocks (Q1 2026)
- Phase 3: Fix remaining violations (Q2 2026)

#### 2. Big Bang Migration

**When:** Architectural changes, dependency upgrades

**Strategy:**
1. Create comprehensive migration plan
2. Allocate dedicated sprint(s)
3. Use feature flags for gradual rollout
4. Comprehensive testing before/after

**Example:** Python 3.11 → 3.13 migration
- Week 1: Update dependencies, run compatibility tests
- Week 2: Fix deprecated patterns, update type hints
- Week 3: Comprehensive testing, CI/CD validation

#### 3. Opportunistic Fixes

**When:** Low-effort, localized improvements

**Strategy:**
1. Fix during related feature work
2. Include in code review checklist
3. Celebrate small wins

**Example:** Type ignore markers
- Touching `llm/factory.py`? Fix 2-3 type ignore markers
- Adding tests? Remove sleep() calls in favor of VirtualClock

#### 4. Acceptance (Conscious Debt)

**When:** Cost > benefit, strategic trade-offs

**Strategy:**
1. Document why debt is accepted
2. Define acceptance criteria
3. Review quarterly for re-evaluation

**Example:** Observability backend TODOs
- Cost: 80+ hours to implement all backends
- Benefit: Currently only use GCP backends
- Decision: Accept debt until multi-cloud deployment
- Review: Q3 2026 (re-evaluate based on roadmap)

---

## Tracking Table

| ID | Issue | Category | Priority | Status | Owner | Target | Notes |
|----|-------|----------|----------|--------|-------|--------|-------|
| TD-001 | AsyncMock Configuration (435 violations) | Test Suite | P0 | In Progress | @engineering | Q1 2026 | Helper fixtures created, enforcement active |
| TD-002 | Sleep Duration Violations (5 files) | Test Suite | P1 | Tracked | @qa | Q2 2026 | 24s total impact, within 60s budget |
| TD-003 | pytest-xdist Memory Safety | Test Suite | P0 | ✅ Resolved | @engineering | Complete | Pattern enforced via pre-commit hooks |
| TD-004 | Placeholder URLs (14 files) | Documentation | P1 | Tracked | @devops | Q1 2026 | Blocks production deployments |
| TD-005 | ADR Synchronization | Documentation | P2 | ✅ Enforced | @docs | Complete | Automated via pre-commit hooks |
| TD-006 | Pre-Commit Hook Consolidation | Configuration | P1 | ✅ Resolved | @engineering | Complete | ADR-0052, ADR-0053 |
| TD-007 | Makefile Pattern Standardization | Configuration | P2 | ✅ Resolved | @engineering | Complete | 133 targets standardized |
| TD-008 | Type Ignore Markers (303 instances) | Code Quality | P1 | Tracked | @engineering | Q2 2026 | Incremental reduction via boy scout rule |
| TD-009 | TODO/FIXME Comments (18+ files) | Code Quality | P2 | Tracked | @engineering | Q3 2026 | Prioritize based on feature work |
| TD-010 | Observability Backends (11 TODOs) | Code Quality | P3 | Accepted | @observability | Q4 2026 | Multi-cloud deployment trigger |
| TD-011 | Frontend E2E Tests (4 TODOs) | Test Suite | P2 | Tracked | @frontend | Q2 2026 | Artifact rendering verification |

### Metrics Dashboard

**Test Suite Health:**
- AsyncMock violations: 435 → Target: 0 (Q1 2026)
- Sleep budget: 24s/60s (40% utilization) ✅
- Memory safety: 98% reduction achieved ✅
- Coverage: 75% → Target: 80% (Q2 2026)

**Code Quality:**
- Type ignore markers: 303 → Target: 150 (Q2 2026)
- TODO comments: 18+ → Target: 10 (Q3 2026)

**Configuration:**
- Pre-commit hooks: 69 (consolidated from 90+) ✅
- Make targets: 133 (standardized) ✅

---

## Quarterly Review Process

### Q1 Review (January)

**Focus:** Security & Production Readiness
- Review P0 critical debt
- Validate remediation progress
- Update priorities based on roadmap

**Agenda:**
1. Review tracking table metrics
2. Identify new debt from previous quarter
3. Re-prioritize based on business impact
4. Assign ownership for Q1 remediation

### Q2 Review (April)

**Focus:** Developer Experience & Performance
- Review P1 high-priority debt
- Measure developer productivity impact
- Validate tooling improvements

### Q3 Review (July)

**Focus:** Maintainability & Documentation
- Review P2 medium-priority debt
- Audit documentation completeness
- Plan refactoring initiatives

### Q4 Review (October)

**Focus:** Strategic Planning & Roadmap Alignment
- Review P3 low-priority debt
- Re-evaluate accepted debt
- Plan next year's debt reduction goals

### Review Template

```markdown
# Technical Debt Quarterly Review - Q{X} {YEAR}

**Date:** {DATE}
**Participants:** {TEAM_MEMBERS}
**Previous Quarter Achievements:** {SUMMARY}

## Debt Metrics

| Metric | Last Quarter | Current | Target | Status |
|--------|--------------|---------|--------|--------|
| AsyncMock violations | {PREV} | {CURR} | {TARGET} | {STATUS} |
| Type ignore markers | {PREV} | {CURR} | {TARGET} | {STATUS} |
| Coverage % | {PREV} | {CURR} | {TARGET} | {STATUS} |

## New Debt Identified

| ID | Issue | Priority | Owner | Target |
|----|-------|----------|-------|--------|
| TD-{XXX} | {DESCRIPTION} | {P0/P1/P2/P3} | {@OWNER} | {QX YEAR} |

## Resolved Debt

- ✅ TD-{XXX}: {DESCRIPTION} (Resolved by @{OWNER})

## Re-Prioritization

- TD-{XXX}: {OLD_PRIORITY} → {NEW_PRIORITY} (Reason: {JUSTIFICATION})

## Action Items

- [ ] {OWNER}: {ACTION_ITEM_1}
- [ ] {OWNER}: {ACTION_ITEM_2}

## Next Review: Q{X+1} {YEAR}
```

---

## References

### Internal Documentation

**Architecture Decision Records:**
- `docs-internal/ADR-0052-GIT-HOOKS-CI-PARITY.md` - Hook consolidation
- `docs-internal/ADR-0053-codex-findings-validation.md` - Codex findings validation
- `docs-internal/ADR-0053-MAKEFILE-PREPUSH-PARITY-ENFORCEMENT.md` - Makefile standardization
- `docs-internal/ADR-0054-CODEX-INFRASTRUCTURE-DEPENDENCY-FINDINGS.md` - Infrastructure findings

**Remediation Guides:**
- `docs-internal/ASYNC_MOCK_REMEDIATION_GUIDE.md` - AsyncMock security fixes
- `docs-internal/CODEX_FINDINGS_VALIDATION_REPORT_2025-11-21.md` - Codex validation results

**Testing Guidelines:**
- `tests/ASYNC_MOCK_GUIDELINES.md` - AsyncMock best practices
- `tests/MEMORY_SAFETY_GUIDELINES.md` - pytest-xdist memory safety
- `tests/PYTEST_XDIST_BEST_PRACTICES.md` - Parallel test execution
- `TESTING.md` - Comprehensive testing guide

**Context Files:**
- `.claude/context/xdist-safety-patterns.md` - 1,800 lines of xdist patterns
- `.claude/memory/pre-commit-hooks-catalog.md` - 69 hooks reference
- `.claude/memory/make-targets.md` - 133 targets reference

### Validation Scripts

**Pre-Commit Hooks:**
- `.pre-commit-config.yaml` - 69 hooks enforcing debt prevention
- `scripts/validators/check_async_mock_configuration.py` - AsyncMock validation
- `scripts/validators/check_test_sleep_duration.py` - Sleep duration validation
- `scripts/validators/check_test_memory_safety.py` - Memory safety validation
- `scripts/validators/validate_docs.py` - Documentation validation
- `scripts/validators/todo_audit.py` - TODO/FIXME tracking

**Analysis Tools:**
- `scripts/validators/check_test_sleep_budget.py` - Wall-clock sleep budget (60s max)
- `scripts/validation/check_test_memory_safety.py` - Memory safety patterns

### External Resources

**Testing Best Practices:**
- pytest documentation: https://docs.pytest.org/
- pytest-xdist: https://pytest-xdist.readthedocs.io/
- Hypothesis property testing: https://hypothesis.readthedocs.io/

**Type Checking:**
- mypy documentation: https://mypy.readthedocs.io/
- typing module: https://docs.python.org/3/library/typing.html

**CI/CD:**
- GitHub Actions: https://docs.github.com/actions
- pre-commit framework: https://pre-commit.com/

---

## Maintenance

**Document Owner:** Engineering Team

**Update Triggers:**
1. Quarterly reviews (mandatory)
2. New debt identification (as discovered)
3. Debt resolution (when completed)
4. Priority changes (based on business impact)

**Version History:**
- 2025-12-19: Initial version
- {NEXT_UPDATE}: {SUMMARY}

**Feedback:** Submit issues or suggestions via GitHub Issues with label `technical-debt`.

---

**Remember:** Technical debt is not failure - it's a conscious trade-off. The key is transparency, tracking, and timely repayment.
