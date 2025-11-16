# Test Suite Statistics Report

**Generated:** 2025-11-15 19:33:44

---

## Test Counts by Category

| Category | Count |
|----------|-------|
| Unit | 0 |
| Integration | 0 |
| E2e | 0 |
| Smoke | 0 |
| Property | 0 |
| Regression | 0 |
| **Total** | **0** |

## Test Files

**Total test files:** 314

## Code Coverage

**Current coverage:** ~65-70% (based on recent runs)
**Target coverage:** 80%
**Gap:** ~15%

*Note: Run `make test-coverage` for exact coverage report*

## Test Infrastructure

- ✅ pytest-xdist (parallel execution)
- ✅ pytest-asyncio (async test support)
- ✅ pytest-timeout (timeout protection)
- ✅ pytest-rerunfailures (flaky test handling)
- ✅ Hypothesis (property-based testing)
- ✅ Memory safety patterns (AsyncMock, GC)
- ✅ Worker-safe ID helpers (xdist isolation)

## Recent Improvements

- 🔧 AsyncMock security helpers (2025-11-15)
- 🔧 Memory safety patterns enforcement
- 🔧 ID pollution prevention
- 🔧 Test sleep budget enforcement

## Meta-Tests (Quality Enforcement)

| Meta-Test | Purpose |
|-----------|---------|
| test_async_mock_configuration.py | Async Mock Configuration |
| test_pytest_xdist_enforcement.py | Pyxdist Enforcement |
| test_id_pollution_prevention.py | Id Pollution Prevention |
| test_test_sleep_budget.py | Sleep Budget |

---

**How to use this report:**
- Run `make generate-reports` to regenerate
- Updated weekly via CI (.github/workflows/weekly-reports.yaml)
- Validated by `tests/meta/test_report_freshness.py`
