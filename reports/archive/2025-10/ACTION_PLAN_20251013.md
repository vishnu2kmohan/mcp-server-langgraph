# Prioritized Action Plan for Issue Remediation

**Generated:** October 13, 2025
**Status:** 96.3% test success rate (422/438 passing)
**Target:** 99%+ test success rate

---

## 🔴 Priority 1: Critical Issues (2-4 hours)

### 1. Fix GDPR Compliance Test Failures (8 tests)
**Estimated Time:** 1.5 hours
**Impact:** High - Compliance features not verified

**Tests to fix:**
- `test_export_user_data_basic`
- `test_export_user_data_no_sessions`
- `test_export_portable_json_format`
- `test_export_portable_csv_format`
- `test_export_handles_session_store_error`
- `test_delete_user_account_no_session_store`
- `test_full_data_lifecycle`
- `test_export_very_large_user_data`

**Root Cause:** Session store mock configuration
**Files:** `tests/test_gdpr.py`, `src/mcp_server_langgraph/api/gdpr.py`

**Steps:**
```bash
# 1. Run failing tests with detailed output
ENABLE_TRACING=false uv run pytest tests/test_gdpr.py::TestDataExportService -v --tb=long

# 2. Review test mocking for session store
# 3. Fix mock setup in tests or implementation
# 4. Verify fixes
ENABLE_TRACING=false uv run pytest tests/test_gdpr.py -v
```

---

### 2. Fix SLA Monitoring Test Failures (4 tests)
**Estimated Time:** 1 hour
**Impact:** High - SLA monitoring not verified

**Tests to fix:**
- `test_report_compliance_score_calculation`
- `test_alert_on_breach`
- `test_custom_sla_configuration`
- `test_missing_target`

**Root Cause:** Metric calculation or configuration logic
**Files:** `tests/test_sla_monitoring.py`, `src/mcp_server_langgraph/monitoring/sla.py`

**Steps:**
```bash
# 1. Run failing tests
ENABLE_TRACING=false uv run pytest tests/test_sla_monitoring.py -v --tb=long -k "compliance_score or alert_on_breach or custom_sla or missing_target"

# 2. Debug metric calculation logic
# 3. Fix implementation or test expectations
# 4. Verify fixes
```

---

### 3. Fix Performance Regression Test Failures (3 tests)
**Estimated Time:** 45 minutes
**Impact:** Medium - Performance monitoring not working

**Tests to fix:**
- `test_agent_response_time_p95`
- `test_llm_call_latency`
- `test_regression_detection_significant_slowdown`

**Root Cause:** Missing baseline metrics or mock timing
**Files:** `tests/regression/test_performance_regression.py`

**Steps:**
```bash
# 1. Check for baseline metrics file
ls tests/regression/baseline_metrics.json

# 2. Run tests with verbose output
ENABLE_TRACING=false uv run pytest tests/regression/ -v --tb=long

# 3. Update baseline metrics or fix timing mocks
# 4. Verify fixes
```

---

### 4. Fix SOC2 Scheduler Test (1 test)
**Estimated Time:** 30 minutes
**Impact:** Low - Single failing test

**Test to fix:**
- `test_scheduler_start_stop`

**Root Cause:** APScheduler lifecycle management
**Files:** `tests/test_soc2_evidence.py`, `src/mcp_server_langgraph/schedulers/compliance.py`

**Steps:**
```bash
# 1. Run specific test
ENABLE_TRACING=false uv run pytest tests/test_soc2_evidence.py::TestComplianceScheduler::test_scheduler_start_stop -v --tb=long

# 2. Debug scheduler startup/shutdown
# 3. Fix implementation or test
# 4. Verify fix
```

---

## 🟠 Priority 2: Medium Issues (2-3 hours)

### 5. Fix Flake8 Configuration
**Estimated Time:** 15 minutes
**Impact:** Medium - Blocks linting

**Error:**
```
Expected `per-file-ignores` to be a mapping from file exclude patterns to ignore codes.
```

**Steps:**
```bash
# 1. Locate flake8 configuration
grep -r "per-file-ignores" .flake8 setup.cfg pyproject.toml

# 2. Fix format (should be: pattern = codes)
# Example:
# [flake8]
# per-file-ignores =
#     __init__.py:F401,F403
#     tests/*:F401,F811,S101

# 3. Test configuration
flake8 --version
flake8 src/ --count

# 4. Verify
make lint
```

---

### 6. Install and Configure Type Checking & Security Scanning
**Estimated Time:** 30 minutes
**Impact:** Medium - Quality gates missing

**Steps:**
```bash
# 1. Install tools
uv pip install mypy bandit

# 2. Run type checking
mypy src/ --ignore-missing-imports

# 3. Run security scan
bandit -r src/ -ll

# 4. Address critical issues found

# 5. Add to CI/CD (already configured)
```

---

### 7. Fix Performance Benchmark Tests (5 setup errors)
**Estimated Time:** 1 hour
**Impact:** Medium - Performance monitoring unavailable

**Tests to fix:**
- All JWT benchmark tests
- All OpenFGA benchmark tests

**Root Cause:** pytest-benchmark fixture configuration
**Files:** `tests/performance/test_benchmarks.py`, `tests/conftest.py`

**Steps:**
```bash
# 1. Check pytest-benchmark installation
uv pip list | grep benchmark

# 2. Run with detailed output
ENABLE_TRACING=false uv run pytest tests/performance/test_benchmarks.py -v --tb=long

# 3. Fix fixture setup in conftest.py
# 4. Verify benchmarks run
uv run pytest tests/performance/ -v --benchmark-only
```

---

### 8. Verify Python 3.12 Compatibility
**Estimated Time:** 30 minutes
**Impact:** Medium - Version mismatch risk

**Steps:**
```bash
# 1. Check if Python 3.12 available
python3.12 --version || echo "Need to install Python 3.12"

# 2. Create new virtual environment with Python 3.12
python3.12 -m venv .venv-312
source .venv-312/bin/activate

# 3. Install dependencies
uv pip install -r requirements.txt -r requirements-test.txt

# 4. Run test suite
ENABLE_TRACING=false pytest -v --tb=short

# 5. Document any issues
# 6. Update .python-version if needed
```

---

## 🟢 Priority 3: Low Issues (< 30 minutes)

### 9. Format Code with Black and isort
**Estimated Time:** 5 minutes
**Impact:** Low - Cosmetic consistency

**Steps:**
```bash
# 1. Format all code
make format

# Or manually:
black . --exclude venv
isort . --skip venv --profile black

# 2. Verify
black --check . --exclude venv
isort --check . --skip venv

# 3. Commit changes
git add .
git commit -m "style: format code with black and isort"
```

---

## Summary

### Time Estimates
```
Priority 1 (Critical):  2-4 hours
Priority 2 (Medium):    2-3 hours
Priority 3 (Low):       5 minutes
───────────────────────────────
Total:                  4-7 hours
```

### Impact on Test Success Rate
```
Current:                96.3% (422/438 passing)
After Priority 1:       99.5% (436/438 passing)
After Priority 2:       100%  (443/443 passing)
```

### Recommended Execution Order
1. Fix flake8 config (15 min) - Unblocks linting
2. Format code (5 min) - Clean baseline
3. Fix GDPR tests (1.5 hrs) - Highest count of failures
4. Fix SLA tests (1 hr) - Second highest
5. Fix regression tests (45 min) - Performance validation
6. Fix SOC2 test (30 min) - Complete P1
7. Install mypy/bandit (30 min) - Quality gates
8. Fix benchmark tests (1 hr) - Performance monitoring
9. Test Python 3.12 (30 min) - Version compatibility

### Success Criteria
- ✅ All 438 tests passing
- ✅ Zero flake8 errors
- ✅ Zero mypy type errors
- ✅ Zero bandit security issues
- ✅ All benchmarks running
- ✅ Python 3.12 compatibility verified

---

## Quick Commands Reference

### Run Full Analysis
```bash
# All tests
ENABLE_TRACING=false uv run pytest -v --tb=short

# With coverage
ENABLE_TRACING=false uv run pytest -v --cov=src --cov-report=html

# Specific categories
uv run pytest -m property -v    # Property tests
uv run pytest -m contract -v    # Contract tests
uv run pytest -m unit -v        # Unit tests
```

### Code Quality
```bash
make format           # Format code
make lint             # Run linters
make security-check   # Security scan
```

### Validation
```bash
python3 scripts/validation/validate_deployments.py
docker compose -f docker-compose.yml config --quiet
```

---

**Next Steps:**
1. Review this action plan
2. Start with Priority 1 items
3. Track progress with todo list
4. Re-run full test suite after each fix
5. Update COMPREHENSIVE_ANALYSIS_REPORT.md when complete
