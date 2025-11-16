# AsyncMock Security Remediation Guide

**Status:** 🔴 **CRITICAL - Security Vulnerability**
**Baseline:** 435 unconfigured AsyncMock violations (as of 2025-11-15)
**Priority:** P0 (Security)
**Estimated Effort:** 8-12 hours for complete remediation
**Phase 1 Complete:** ✅ Helper fixtures created and tested

---

## Executive Summary

Unconfigured `AsyncMock()` instances return truthy `MagicMock` objects when awaited, causing authorization checks to incorrectly pass. This was the root cause of a SCIM security vulnerability (commit abb04a6a).

**Impact:** 435 test files with potential security bypasses in authorization logic.

**Solution:** Use safe helper factories from `tests.helpers.async_mock_helpers` that enforce explicit configuration.

---

## The Vulnerability

### ❌ WRONG: Security Bypass Risk

```python
# Unconfigured AsyncMock returns truthy value
mock_openfga = AsyncMock()

# Authorization check ALWAYS passes (security bypass!)
if await mock_openfga.check_permission(user, relation, resource):
    grant_access()  # ← VULNERABILITY: Always grants access!
```

### ✅ CORRECT: Explicit Configuration

```python
from tests.helpers import configured_async_mock_deny

# Safe default: deny by default
mock_openfga = configured_async_mock_deny()

# Authorization check ALWAYS denies (security-safe)
if await mock_openfga.check_permission(user, relation, resource):
    grant_access()  # ← SAFE: Never reached unless explicitly granted
```

---

## Helper Fixtures

### `configured_async_mock(return_value=None)`

Safe default for general mocks - explicitly returns `None`.

```python
from tests.helpers import configured_async_mock

# Returns None by default
mock_api = configured_async_mock()
result = await mock_api.fetch_data()  # Returns None

# Custom return value
mock_api = configured_async_mock(return_value={"status": "ok"})
result = await mock_api.fetch_data()  # Returns {"status": "ok"}

# With spec for type safety
mock_api = configured_async_mock(
    return_value={"data": [1, 2, 3]},
    spec=APIClient
)
```

### `configured_async_mock_deny()`

**Use for all authorization mocks** - denies by default (security-safe).

```python
from tests.helpers import configured_async_mock_deny

# Authorization mock - denies by default
mock_authz = configured_async_mock_deny()

# Safe: Returns False
can_access = await mock_authz.check_permission(...)  # Returns False

# Explicit grant when needed
mock_authz.check_permission.return_value = True
can_access = await mock_authz.check_permission(...)  # Returns True
```

### `configured_async_mock_raise(exception)`

For error scenario testing.

```python
from tests.helpers import configured_async_mock_raise

# Simulate network error
mock_api = configured_async_mock_raise(ConnectionError("Service down"))

with pytest.raises(ConnectionError, match="Service down"):
    await mock_api.call()
```

---

## Remediation Pattern

### Pattern 1: Simple Unconfigured Mock

**Before:**
```python
mock_keycloak = AsyncMock()  # ❌ Unconfigured!
```

**After:**
```python
from tests.helpers import configured_async_mock

mock_keycloak = configured_async_mock(return_value=None)  # ✅ Safe default
```

### Pattern 2: Authorization Mock

**Before:**
```python
mock_openfga = AsyncMock()  # ❌ Bypasses authorization!
# Later...
mock_openfga.check_permission.return_value = False
```

**After:**
```python
from tests.helpers import configured_async_mock_deny

mock_openfga = configured_async_mock_deny()  # ✅ Denies by default
# Configuration on next line works too
mock_openfga.check_permission.return_value = False
```

### Pattern 3: Mock with Spec

**Before:**
```python
mock_client = AsyncMock(spec=KeycloakClient)  # ❌ Unconfigured!
```

**After:**
```python
from tests.helpers import configured_async_mock

mock_client = configured_async_mock(
    return_value=None,
    spec=KeycloakClient
)  # ✅ Safe + type-checked
```

### Pattern 4: Error Simulation

**Before:**
```python
mock_api = AsyncMock()
mock_api.side_effect = ConnectionError("Timeout")  # ❌ Unconfigured initially
```

**After:**
```python
from tests.helpers import configured_async_mock_raise

mock_api = configured_async_mock_raise(
    ConnectionError("Timeout")
)  # ✅ Explicit error
```

---

## Remediation Workflow

### Step 1: Run Validator

```bash
uv run python scripts/check_async_mock_configuration.py tests/**/*.py
```

Output shows files and line numbers with violations.

### Step 2: Fix Violations (Priority Order)

#### Priority 1: Auth/Authz Tests (Security-Critical)

- `tests/property/test_auth_properties.py` (2 violations)
- `tests/test_keycloak.py` (124 violations) 🔴 HIGH VOLUME
- `tests/test_service_principal_manager.py` (14 violations)
- `tests/test_session.py` (12 violations)
- `tests/test_auth.py`
- `tests/test_user_provider.py`

#### Priority 2: API/MCP Tests (User-Facing)

- `tests/api/test_scim_security.py` (5 violations)
- `tests/api/test_bearer_scheme_diagnostic.py` (6 violations)
- `tests/mcp/test_mcp_server.py`
- `tests/mcp/test_langgraph_graph.py`

#### Priority 3: Remaining Tests (Internal)

- All other test files

### Step 3: Apply Fixes

**Manual Approach (Recommended for Security Tests):**

1. Open file with violations
2. Locate bare `AsyncMock()` calls
3. Replace with appropriate helper:
   - Authorization → `configured_async_mock_deny()`
   - General → `configured_async_mock(return_value=None)`
   - Error → `configured_async_mock_raise(exception)`
4. Add import:
   ```python
   from tests.helpers import configured_async_mock, configured_async_mock_deny
   ```
5. Run tests: `uv run pytest tests/path/to/test_file.py -xvs`
6. Verify: `uv run python scripts/check_async_mock_configuration.py tests/path/to/test_file.py`

**Bulk Approach (For Non-Critical Tests):**

```bash
# Dry run first
uv run python scripts/bulk_fix_async_mock.py tests/some_test.py --dry-run

# Apply fixes
uv run python scripts/bulk_fix_async_mock.py tests/some_test.py

# Verify
uv run pytest tests/some_test.py
```

### Step 4: Verify Meta-Test Passes

```bash
uv run pytest tests/meta/test_async_mock_configuration.py -xvs
```

Should pass with 0 violations after all fixes applied.

### Step 5: Enable Pre-Commit Hook

Once all violations are fixed, move the hook from `manual` to `pre-push` in `.pre-commit-config.yaml`:

```yaml
# Move from line ~1160 (manual) to line ~440 (pre-push)
- id: check-async-mock-configuration
  name: Check AsyncMock Configuration
  entry: uv run python scripts/check_async_mock_configuration.py
  language: system
  files: ^tests/.*\.py$
  stages: [pre-push]  # ← Enable enforcement
```

---

## Validation

### Continuous Validation

```bash
# Check specific file
uv run python scripts/check_async_mock_configuration.py tests/test_example.py

# Check all test files
uv run python scripts/check_async_mock_configuration.py tests/**/*.py

# Run meta-test
uv run pytest tests/meta/test_async_mock_configuration.py -xvs
```

### Expected Output (After Remediation)

```
✅ AsyncMock Configuration Validation

All AsyncMock instances are properly configured!

Checked: 313 files
Violations: 0

✅ PASSED
```

---

## Enforcement

### Pre-Commit Hook

Located at `.pre-commit-config.yaml` lines ~1160-1190 (currently in `[manual]` stage).

**Enable after remediation:**
```yaml
stages: [pre-push]
```

### Meta-Test

`tests/meta/test_async_mock_configuration.py` runs the validator against all test files in CI.

**Current Status:** ❌ Failing (435 violations)
**Target:** ✅ Passing (0 violations)

---

## Progress Tracking

**Baseline (2025-11-15):** 435 violations

**Current Status:**
- ✅ Helper fixtures created (`tests/helpers/async_mock_helpers.py`)
- ✅ Helper tests passing (21 tests, 100% coverage)
- ✅ Bulk-fix script created (`scripts/bulk_fix_async_mock.py`)
- ⏳ Violations remaining: **435** (0% complete)

**Estimated Completion Time:** 8-12 hours
**Breakdown:**
- Priority 1 (Auth/Authz): 4-5 hours (152 violations)
- Priority 2 (API/MCP): 2-3 hours (~50 violations)
- Priority 3 (Remaining): 2-4 hours (~233 violations)

---

## References

- **Helper Fixtures:** `tests/helpers/async_mock_helpers.py`
- **Helper Tests:** `tests/helpers/test_async_mock_helpers.py`
- **Validator Script:** `scripts/check_async_mock_configuration.py`
- **Bulk-Fix Script:** `scripts/bulk_fix_async_mock.py`
- **Meta-Test:** `tests/meta/test_async_mock_configuration.py`
- **Pre-Commit Config:** `.pre-commit-config.yaml:1160-1190`
- **Historical Incident:** SCIM security bug (commit abb04a6a)

---

## Next Steps

1. ✅ **Complete:** Helper fixtures created and tested
2. 🔄 **In Progress:** Document remediation pattern (this guide)
3. ⏳ **Pending:** Fix Priority 1 violations (auth/authz tests)
4. ⏳ **Pending:** Fix Priority 2 violations (API/MCP tests)
5. ⏳ **Pending:** Fix Priority 3 violations (remaining tests)
6. ⏳ **Pending:** Enable pre-commit hook enforcement
7. ⏳ **Pending:** Verify meta-test passes in CI

**Recommendation:** Dedicate 1-2 focused sessions to complete remediation given security-critical nature.

---

**Last Updated:** 2025-11-15
**Owner:** Infrastructure Team
**Status:** Phase 1 Complete (Helpers), Phase 2 Pending (Mass Remediation)
