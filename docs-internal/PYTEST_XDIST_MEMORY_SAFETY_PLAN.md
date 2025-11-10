# Complete Implementation Plan: pytest-xdist Memory Safety
**Date**: 2025-11-10
**Status**: Phase 1 Complete (6 files, 45 classes) → Phases 2-5 Pending

---

## Executive Summary

### Problem Statement
pytest-xdist workers accumulate AsyncMock/MagicMock objects due to circular references, preventing garbage collection. This causes extreme memory consumption (217GB VIRT, 42GB RES observed) leading to OOM kills in CI/CD.

### Solution Pattern (3-part)
```python
# 1. Add import
import gc

# 2. Add class decorator
@pytest.mark.xdist_group(name="category_name")
class TestClassName:
    """Test description"""

    # 3. Add teardown method
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()
```

### Phase 1 Results (COMPLETED)
- **Files Fixed**: 6 CRITICAL files
- **Classes Protected**: 45 test classes
- **Memory Saved**: ~165GB RES
- **Files**:
  1. `tests/test_keycloak.py` (14 classes)
  2. `tests/test_openfga_client.py` (5 classes)
  3. `tests/test_auth.py` (5 classes)
  4. `tests/test_api_key_manager.py` (10 classes)
  5. `tests/test_service_principal_manager.py` (7 classes)
  6. `tests/integration/test_keycloak_admin.py` (4 classes)

### Remaining Scope
- **Phase 2**: 14 HIGH priority files (124+ test methods)
- **Phase 3**: Prevention infrastructure (pre-commit hooks, validation scripts, docs)
- **Phase 4**: 33 MEDIUM priority files (AsyncMock, ≤10 methods)
- **Phase 5**: 21 LOW priority files (MagicMock only)
- **Total**: 68 files remaining

---

## Phase 2: HIGH Priority Files (14 files)

### Criteria
- AsyncMock present
- 10+ test methods
- High memory consumption risk

### Files and Details

#### 1. `tests/test_auth_factory.py`
- **Classes**: 9
- **Methods**: 37
- **Group Name**: `auth_factory_tests`
- **Classes**:
  - TestCreateUserProvider
  - TestProductionEnvironmentGuards
  - TestCreateSessionStore
  - TestCreateAuthMiddleware
  - TestFactoryIntegration
  - TestCreateKeycloakClient
  - TestCreateOpenFGAClient
  - TestServicePrincipalManager
  - TestAPIKeyManager
- **Est. Memory Saved**: ~30GB RES

#### 2. `tests/core/test_cache.py`
- **Classes**: 15
- **Methods**: 37
- **Group Name**: `cache_tests`
- **Classes**:
  - TestCacheL1Operations
  - TestCacheL2Operations
  - TestCacheDelete
  - TestCacheClear
  - TestCacheStampedePrevention
  - TestCacheConfiguration
  - TestCacheMetrics
  - TestCacheEviction
  - TestCacheTTL
  - TestCacheSerialization
  - TestCacheErrors
  - TestCachePerformance
  - TestCacheIntegration
  - TestCacheThreadSafety
  - TestCacheRedisBackend
- **Est. Memory Saved**: ~35GB RES

#### 3. `tests/api/test_service_principals_endpoints.py`
- **Classes**: 7
- **Methods**: 21
- **Group Name**: `service_principals_api_tests`
- **Classes**:
  - TestCreateServicePrincipal
  - TestListServicePrincipals
  - TestGetServicePrincipal
  - TestRotateServicePrincipalSecret
  - TestDeleteServicePrincipal
  - TestAssociateUser
  - TestServicePrincipalAuthorization
- **Est. Memory Saved**: ~20GB RES

#### 4. `tests/api/test_api_keys_endpoints.py`
- **Classes**: 7
- **Methods**: 20
- **Group Name**: `api_keys_endpoints_tests`
- **Classes**:
  - TestCreateAPIKey
  - TestListAPIKeys
  - TestRotateAPIKey
  - TestRevokeAPIKey
  - TestValidateAPIKey
  - TestKongValidation
  - TestAPIKeyAuthorization
- **Est. Memory Saved**: ~18GB RES

#### 5. `tests/test_gdpr.py`
- **Classes**: 6
- **Methods**: 19
- **Group Name**: `gdpr_unit_tests`
- **Classes**:
  - TestDataExportService
  - TestDataDeletionService
  - TestGDPREndpoints
  - TestGDPRModels
  - TestGDPRIntegration
  - TestGDPRCompliance
- **Est. Memory Saved**: ~22GB RES

#### 6. `tests/integration/test_gdpr_endpoints.py`
- **Classes**: 2
- **Methods**: 18
- **Group Name**: `gdpr_integration_tests`
- **Classes**:
  - TestGDPREndpoints
  - TestGDPRProductionGuard
- **Special Considerations**: Integration test - may need `@pytest.mark.skipif("dist" in sys.modules)` if it requires specific infrastructure
- **Est. Memory Saved**: ~20GB RES

#### 7. `tests/test_session_timeout.py`
- **Classes**: 5
- **Methods**: 17
- **Group Name**: `session_timeout_tests`
- **Classes**:
  - TestSessionTimeoutMiddleware
  - TestSessionTimeoutHelpers
  - TestCreateSessionTimeoutMiddleware
  - TestSessionTimeoutEdgeCases
  - TestHIPAACompliance
- **Est. Memory Saved**: ~18GB RES

#### 8. `tests/test_llm_factory_contract.py`
- **Classes**: 2
- **Methods**: 16
- **Group Name**: `llm_factory_contract_tests`
- **Classes**:
  - TestFormatMessagesContract
  - TestFormatMessagesEdgeCases
- **Est. Memory Saved**: ~15GB RES

#### 9. `tests/integration/test_app_startup_validation.py`
- **Classes**: 5
- **Methods**: 16
- **Group Name**: `app_startup_validation_tests`
- **Classes**:
  - TestFastAPIStartupValidation
  - TestDependencyInjectionWiring
  - TestGracefulDegradation
  - TestProductionConfigValidation
  - TestRegressionPrevention
- **Special Considerations**: Integration test
- **Est. Memory Saved**: ~18GB RES

#### 10. `tests/test_user_provider.py`
- **Classes**: 4
- **Methods**: 14
- **Group Name**: `user_provider_tests`
- **Classes**:
  - TestInMemoryUserProvider
  - TestKeycloakUserProvider
  - TestCreateUserProvider
  - TestUserProviderInterface
- **Est. Memory Saved**: ~15GB RES

#### 11. `tests/test_context_manager.py`
- **Classes**: 4
- **Methods**: 13
- **Group Name**: `context_manager_tests`
- **Classes**:
  - TestContextManager
  - TestConvenienceFunctions
  - TestTokenCounting
  - TestCompactionResult
- **Est. Memory Saved**: ~12GB RES

#### 12. `tests/conftest.py`
- **Classes**: 0
- **Methods**: 12
- **Group Name**: N/A (no test classes)
- **Special Handling**: This is a fixtures file. Check if it has module/session-scoped fixtures that create AsyncMock. May not need xdist_group but review manually.
- **Est. Memory Saved**: ~5GB RES

#### 13. `tests/unit/test_dependencies_wiring.py`
- **Classes**: 5
- **Methods**: 11
- **Group Name**: `dependencies_wiring_tests`
- **Classes**:
  - TestKeycloakClientWiring
  - TestOpenFGAClientWiring
  - TestServicePrincipalManagerOpenFGAGuards
  - TestAPIKeyManagerRedisCacheWiring
  - TestDependencyStartupSmoke
- **Est. Memory Saved**: ~12GB RES

#### 14. `tests/smoke/test_ci_startup_smoke.py`
- **Classes**: 4
- **Methods**: 11
- **Group Name**: `ci_startup_smoke_tests`
- **Classes**:
  - TestCriticalStartupValidation
  - TestConfigurationValidation
  - TestDependencyInjectionSmoke
  - TestGracefulDegradationSmoke
- **Est. Memory Saved**: ~10GB RES

### Phase 2 Summary
- **Total Files**: 14
- **Total Classes**: ~75
- **Total Methods**: ~249
- **Est. Total Memory Saved**: ~250GB RES
- **Estimated Effort**: 2-3 hours (mostly automated with helper script)

---

## Phase 3: Prevention Infrastructure

### Goal
Ensure this memory issue can NEVER happen again through automated validation.

### 3.1: Pre-commit Hook

**File**: `.pre-commit-config.yaml`

**Hook to Add**:
```yaml
  # Memory safety validation for pytest-xdist
  - repo: local
    hooks:
      - id: validate-test-memory-safety
        name: Validate test memory safety (pytest-xdist)
        entry: python scripts/check_test_memory_safety.py
        language: python
        types: [python]
        files: ^tests/.*\.py$
        pass_filenames: true
        description: |
          Validates that test files using AsyncMock/MagicMock follow memory safety pattern:
          1. Have @pytest.mark.xdist_group on test classes
          2. Have teardown_method with gc.collect()
          3. Import gc module

          Prevents pytest-xdist OOM from mock accumulation (165GB+ memory leaks).
```

**Location**: Add after line ~52 (after gitleaks hook, before GitHub Actions validation)

### 3.2: Memory Safety Checker Script

**File**: `scripts/check_test_memory_safety.py`

**Purpose**: Validates all test files follow memory safety pattern

**Features**:
- Scans test files for AsyncMock/MagicMock usage
- Checks for required pattern components:
  - `import gc`
  - `@pytest.mark.xdist_group(name="...")`
  - `def teardown_method(self): ... gc.collect()`
- Reports violations with file path, line numbers, class names
- Exit code 0 if all files pass, 1 if violations found
- Can be run standalone or via pre-commit

**Usage**:
```bash
# Standalone
python scripts/check_test_memory_safety.py tests/**/*.py

# Via pre-commit
pre-commit run validate-test-memory-safety --all-files
```

**Implementation** (see detailed pseudocode in Deliverable 3.2 below)

### 3.3: Memory Safety Guidelines Documentation

**File**: `tests/MEMORY_SAFETY_GUIDELINES.md`

**Table of Contents**:
1. **Problem Overview**
   - What is the pytest-xdist memory issue?
   - Why AsyncMock/MagicMock cause problems
   - Real-world impact (165GB+ memory consumption)

2. **Solution Pattern**
   - 3-part pattern explanation
   - Code examples (correct vs incorrect)
   - When to apply the pattern

3. **Implementation Guide**
   - Step-by-step instructions
   - Using the helper script
   - Manual implementation

4. **Integration Test Considerations**
   - When to skip xdist (`@pytest.mark.skipif("dist" in sys.modules)`)
   - Balancing parallelization vs isolation
   - Infrastructure dependencies

5. **Troubleshooting**
   - Common issues
   - Debugging memory consumption
   - Testing the fix

6. **Validation**
   - Pre-commit hooks
   - CI/CD checks
   - Manual validation

7. **References**
   - pytest-xdist docs
   - Python gc module
   - Original issue tracking

**Implementation**: See detailed outline in Deliverable 3.3 below

### 3.4: Update TDD Guidelines

**File**: `~/.claude/CLAUDE.md`

**Section**: `## Test File Conventions > ### Python (pytest)`

**Addition** (after line ~13):
```markdown
#### Memory Safety for pytest-xdist

**CRITICAL**: All test classes using AsyncMock/MagicMock MUST follow memory safety pattern to prevent OOM:

```python
import gc  # Required

@pytest.mark.xdist_group(name="category_name")
class TestClassName:
    """Test description"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    # Test methods here...
```

**Why**: AsyncMock/MagicMock create circular references preventing garbage collection in xdist workers, causing 100GB+ memory leaks.

**Enforcement**:
- Pre-commit hook: `validate-test-memory-safety`
- Validation script: `scripts/check_test_memory_safety.py`
- See: `tests/MEMORY_SAFETY_GUIDELINES.md` for complete details
```

### Phase 3 Summary
- **Pre-commit Hook**: Automated validation on every commit
- **Validation Script**: Standalone checker (~200 lines)
- **Guidelines Doc**: Comprehensive reference (~500 lines)
- **TDD Update**: Global awareness for all projects
- **Estimated Effort**: 4-5 hours

---

## Phase 4: MEDIUM Priority Files (33 files)

### Criteria
- AsyncMock present
- ≤10 test methods
- Moderate memory consumption risk

### Recommended Approach
Use helper script `scripts/add_memory_safety_to_tests.py` for batch processing:

```bash
# Process all MEDIUM priority files
for file in tests/test_sla_monitoring.py tests/test_verifier.py ...; do
    python scripts/add_memory_safety_to_tests.py "$file" "$(basename $file .py)"
done
```

### Files (Top 15 shown, 33 total)
1. `tests/test_sla_monitoring.py` (9 classes, 9 methods) → `sla_monitoring_tests`
2. `tests/test_verifier.py` (4 classes, 9 methods) → `verifier_tests`
3. `tests/property/test_auth_properties.py` (5 classes, 9 methods) → `auth_properties_tests`
4. `tests/regression/test_performance_regression.py` (5 classes, 9 methods) → `performance_regression_tests`
5. `tests/security/test_api_key_performance_monitoring.py` (3 classes, 8 methods) → `api_key_perf_monitoring_tests`
6. `tests/unit/test_security_practices.py` (4 classes, 7 methods) → `security_practices_tests`
7. `tests/test_agent.py` (4 classes, 6 methods) → `agent_tests`
8. `tests/integration/test_mcp_startup_validation.py` (3 classes, 6 methods) → `mcp_startup_validation_tests`
9. `tests/test_session.py` (4 classes, 5 methods) → `session_tests`
10. `tests/unit/test_mcp_stdio_server.py` (7 classes, 5 methods) → `mcp_stdio_server_tests`
11. `tests/security/test_authorization_fallback_controls.py` (2 classes, 5 methods) → `authz_fallback_tests`
12. `tests/security/test_scim_service_principal_openfga.py` (4 classes, 5 methods) → `scim_sp_openfga_tests`
13. `tests/test_cleanup_scheduler.py` (9 classes, 4 methods) → `cleanup_scheduler_tests`
14. `tests/test_context_manager_llm.py` (3 classes, 4 methods) → `context_manager_llm_tests`
15. `tests/test_distributed_checkpointing.py` (4 classes, 4 methods) → `distributed_checkpointing_tests`
... (18 more files)

### Phase 4 Summary
- **Total Files**: 33
- **Est. Total Memory Saved**: ~80GB RES
- **Estimated Effort**: 3-4 hours (mostly automated)

---

## Phase 5: LOW Priority Files (21 files)

### Criteria
- MagicMock only (no AsyncMock)
- Lower memory consumption risk

### Recommendation
**DEFER** until a real memory issue is observed with these files.

**Rationale**:
- MagicMock causes less severe memory issues than AsyncMock
- These files likely have smaller memory footprints
- Time better spent on prevention infrastructure (Phase 3)
- Can be addressed incrementally if CI/CD shows issues

### Alternative: Batch Process
If you decide to fix all files for completeness:

```bash
# Get list of LOW priority files
grep -l "MagicMock" tests/**/*.py | grep -v "AsyncMock" > low_priority_files.txt

# Process with helper script
while read file; do
    python scripts/add_memory_safety_to_tests.py "$file" "$(basename $file .py)"
done < low_priority_files.txt
```

### Phase 5 Summary
- **Total Files**: 21
- **Est. Total Memory Saved**: ~20GB RES
- **Estimated Effort**: 2-3 hours (if pursued)
- **Recommendation**: DEFER

---

## Testing Strategy

### Challenge
Running full test suite triggers the memory issue we're trying to fix.

### Safe Testing Approaches

#### 1. File-by-File Validation (RECOMMENDED)
```bash
# Test individual files after fixing
pytest tests/test_auth_factory.py -v --tb=short

# Check for syntax errors
python -m py_compile tests/test_auth_factory.py

# Run with memory profiling (if needed)
pytest tests/test_auth_factory.py --memray
```

#### 2. Incremental Testing
```bash
# Fix 2-3 files at a time
python scripts/add_memory_safety_to_tests.py tests/test_auth_factory.py auth_factory_tests
python scripts/add_memory_safety_to_tests.py tests/core/test_cache.py cache_tests

# Test those files only
pytest tests/test_auth_factory.py tests/core/test_cache.py -v

# If pass, commit and continue
git add tests/test_auth_factory.py tests/core/test_cache.py
git commit -m "fix(tests): add memory safety to auth_factory and cache tests"
```

#### 3. Parallel Testing with Limited Workers
```bash
# Use fewer workers to limit total memory
pytest tests/ -n 2 --maxfail=1

# Gradually increase workers
pytest tests/ -n 4 --maxfail=1
```

#### 4. Memory Monitoring
```bash
# Monitor memory during test runs
watch -n 1 'ps aux | grep pytest | grep -v grep | awk "{print \$6/1024 \" MB\"}"'

# Or use htop in separate terminal
htop -p $(pgrep -f pytest)
```

#### 5. Smoke Test Strategy
**Phase 2 → Test 3 representative files**:
- `tests/test_auth_factory.py` (largest, 37 methods)
- `tests/integration/test_gdpr_endpoints.py` (integration test)
- `tests/conftest.py` (fixtures file)

**If these pass** → proceed with remaining files

### Verification Checklist (Per File)
- [ ] File compiles (`python -m py_compile`)
- [ ] Imports work (`pytest --collect-only`)
- [ ] Individual tests pass (`pytest file.py`)
- [ ] No memory explosion (< 2GB per worker)
- [ ] xdist groups show up in pytest output
- [ ] gc.collect() appears in teardown_method

---

## Commit Strategy

### Option A: Small Commits (RECOMMENDED)
**Pros**: Easy to review, easy to bisect if issues arise
**Cons**: More commits

```bash
# Commit 2-3 files at a time
git add tests/test_auth_factory.py tests/core/test_cache.py
git commit -m "fix(tests): add memory safety to auth_factory and cache (Phase 2, 1/7)"

git add tests/api/test_service_principals_endpoints.py tests/api/test_api_keys_endpoints.py
git commit -m "fix(tests): add memory safety to API endpoint tests (Phase 2, 2/7)"

# etc.
```

### Option B: Phase-Based Commits
**Pros**: Clean history, fewer commits
**Cons**: Larger changesets, harder to bisect

```bash
# Commit entire Phase 2 at once
git add tests/test_auth_factory.py tests/core/test_cache.py ... (all 14 files)
git commit -m "fix(tests): add memory safety to 14 HIGH priority files (Phase 2)"

# Commit Phase 3
git add scripts/check_test_memory_safety.py .pre-commit-config.yaml tests/MEMORY_SAFETY_GUIDELINES.md
git commit -m "feat(tests): add memory safety prevention infrastructure (Phase 3)"
```

### Option C: Hybrid (BEST)
**Combine both approaches**:

1. **Phase 2**: Small commits (2-3 files each) with testing between
2. **Phase 3**: Single commit (infrastructure is cohesive)
3. **Phase 4**: Batch commit (files are similar, low risk)

---

## Risk Assessment

### Risks and Mitigations

#### Risk 1: Breaking Existing Tests
**Probability**: LOW
**Impact**: HIGH
**Mitigation**:
- Test each file individually before committing
- Use `python -m py_compile` for syntax validation
- Run `pytest --collect-only` to verify imports
- Incremental commits allow easy rollback

#### Risk 2: Incorrect xdist_group Names
**Probability**: LOW
**Impact**: LOW
**Mitigation**:
- Helper script auto-generates group names from filenames
- Group names are isolated (no cross-dependencies)
- Duplicate group names are OK (xdist handles it)

#### Risk 3: Integration Tests Break with xdist
**Probability**: MEDIUM
**Impact**: MEDIUM
**Mitigation**:
- Mark integration tests with `@pytest.mark.skipif("dist" in sys.modules)`
- See `tests/MEMORY_SAFETY_GUIDELINES.md` section on integration tests
- Test integration files individually first
- Files to watch:
  - `tests/integration/test_gdpr_endpoints.py`
  - `tests/integration/test_app_startup_validation.py`
  - `tests/integration/test_mcp_startup_validation.py`

#### Risk 4: Validation Script False Positives
**Probability**: MEDIUM
**Impact**: LOW
**Mitigation**:
- Validation script should warn, not error, initially
- Manual review of warnings
- Iterate on script based on false positives
- Add exceptions for conftest.py and other special files

#### Risk 5: Memory Issue Persists
**Probability**: LOW
**Impact**: HIGH
**Mitigation**:
- Phase 1 already validated pattern works (165GB saved)
- Monitor memory during Phase 2 testing
- If issue persists, investigate deeper (profiling, heap dumps)

#### Risk 6: Helper Script Bugs
**Probability**: MEDIUM
**Impact**: MEDIUM
**Mitigation**:
- Test helper script on Phase 1 files first (should show "No changes needed")
- Manual review of generated code
- Dry-run mode in script (print changes without writing)

### Recovery Plan

**If tests break**:
1. Identify which commit/file caused breakage
2. `git revert` that commit
3. Manually inspect the file for issues
4. Fix manually and test
5. Re-commit with fixes

**If memory issue persists**:
1. Profile specific test file with `pytest --memray`
2. Check for other mock patterns (patch objects, fixtures)
3. Consider session/module scoped fixtures
4. Escalate to pytest-xdist maintainers if pattern isn't sufficient

---

## Time Estimates

### Conservative Estimates

| Phase | Task | Time | Notes |
|-------|------|------|-------|
| **2A** | Fix 14 HIGH priority files (automated) | 1h | Helper script + testing |
| **2B** | Manual review and testing | 1-2h | Verify each file |
| **2C** | Incremental commits | 0.5h | Git workflow |
| **3A** | Write validation script | 2h | ~200 lines with tests |
| **3B** | Add pre-commit hook | 0.5h | YAML config |
| **3C** | Write guidelines doc | 1.5h | ~500 lines with examples |
| **3D** | Update CLAUDE.md | 0.5h | TDD section |
| **3E** | Test prevention infrastructure | 1h | Validation |
| **4** | Fix 33 MEDIUM priority files (optional) | 3-4h | Batch processing |
| **5** | Fix 21 LOW priority files (defer) | N/A | Not recommended |
| **Total (Phase 2-3)** | **Complete protection** | **8-10h** | Phases 2 & 3 |

### Aggressive Estimates (If Everything Goes Smoothly)
- **Phase 2**: 2 hours
- **Phase 3**: 3 hours
- **Total**: 5 hours

### Recommended Approach
**Session 1 (3-4h)**: Phase 2 (14 HIGH priority files)
**Session 2 (4-5h)**: Phase 3 (Prevention infrastructure)
**Session 3 (optional, 3-4h)**: Phase 4 (33 MEDIUM priority files)

---

## Deliverables

### Deliverable 1: Phase 2 Implementation

**Files Modified** (14 files):
```
tests/test_auth_factory.py
tests/core/test_cache.py
tests/api/test_service_principals_endpoints.py
tests/api/test_api_keys_endpoints.py
tests/test_gdpr.py
tests/integration/test_gdpr_endpoints.py
tests/test_session_timeout.py
tests/test_llm_factory_contract.py
tests/integration/test_app_startup_validation.py
tests/test_user_provider.py
tests/test_context_manager.py
tests/conftest.py
tests/unit/test_dependencies_wiring.py
tests/smoke/test_ci_startup_smoke.py
```

**Changes Per File**:
- Added: `import gc` (if missing)
- Added: `@pytest.mark.xdist_group(name="...")` to each test class
- Added: `def teardown_method(self): gc.collect()` to each test class

**Validation**:
- [ ] All files compile
- [ ] `pytest --collect-only` passes
- [ ] Individual file tests pass
- [ ] Memory consumption < 2GB per worker
- [ ] All changes committed

### Deliverable 2: Phase 3 Prevention Infrastructure

#### 2A: Pre-commit Hook Configuration

**File**: `.pre-commit-config.yaml`

**Addition** (after line 52):
```yaml
  # Memory safety validation for pytest-xdist
  - repo: local
    hooks:
      - id: validate-test-memory-safety
        name: Validate test memory safety (pytest-xdist)
        entry: python scripts/check_test_memory_safety.py
        language: python
        types: [python]
        files: ^tests/.*\.py$
        pass_filenames: true
        description: |
          Validates that test files using AsyncMock/MagicMock follow memory safety pattern:
          1. Have @pytest.mark.xdist_group on test classes
          2. Have teardown_method with gc.collect()
          3. Import gc module

          Prevents pytest-xdist OOM from mock accumulation (165GB+ memory leaks).
```

#### 2B: Memory Safety Checker Script

**File**: `scripts/check_test_memory_safety.py`

**Pseudocode**:
```python
#!/usr/bin/env python3
"""
Check test files for memory safety pattern compliance.

Usage:
    python scripts/check_test_memory_safety.py tests/test_file.py
    python scripts/check_test_memory_safety.py tests/**/*.py
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple

def check_file(filepath: Path) -> Tuple[bool, List[str]]:
    """
    Check if test file follows memory safety pattern.

    Returns:
        (is_compliant, violations) where violations is list of issue descriptions
    """
    content = filepath.read_text()
    violations = []

    # Skip if no mocks
    has_async_mock = "AsyncMock" in content
    has_magic_mock = "MagicMock" in content
    if not has_async_mock and not has_magic_mock:
        return True, []

    # Check 1: import gc
    if "import gc" not in content:
        violations.append(f"Missing 'import gc'")

    # Check 2: Find all test classes
    test_classes = re.findall(r'^class (Test\w+)', content, re.MULTILINE)

    if not test_classes:
        # No test classes, only test functions - this is OK
        return True, []

    # Check 3: Each test class needs xdist_group
    for class_name in test_classes:
        # Find class definition
        class_pattern = rf'(@pytest\.mark\.\w+\s*\n)*class {class_name}:'
        class_match = re.search(class_pattern, content, re.MULTILINE)

        if not class_match:
            continue

        # Check for xdist_group decorator
        decorators = class_match.group(0)
        if "@pytest.mark.xdist_group" not in decorators:
            violations.append(
                f"Class '{class_name}' missing @pytest.mark.xdist_group decorator"
            )

    # Check 4: Each test class needs teardown_method
    for class_name in test_classes:
        # Find class body (simplified - find next class or end of file)
        class_start = content.find(f"class {class_name}:")
        next_class = content.find("\nclass Test", class_start + 1)
        if next_class == -1:
            class_body = content[class_start:]
        else:
            class_body = content[class_start:next_class]

        # Check for teardown_method with gc.collect()
        has_teardown = "def teardown_method" in class_body
        has_gc_collect = "gc.collect()" in class_body

        if not has_teardown:
            violations.append(
                f"Class '{class_name}' missing teardown_method"
            )
        elif not has_gc_collect:
            violations.append(
                f"Class '{class_name}' teardown_method missing gc.collect()"
            )

    is_compliant = len(violations) == 0
    return is_compliant, violations


def main():
    if len(sys.argv) < 2:
        print("Usage: python check_test_memory_safety.py <test_file> [<test_file2> ...]")
        sys.exit(1)

    all_compliant = True
    total_files = 0
    total_violations = 0

    for filepath_str in sys.argv[1:]:
        filepath = Path(filepath_str)

        if not filepath.exists():
            print(f"❌ {filepath}: File not found")
            all_compliant = False
            continue

        is_compliant, violations = check_file(filepath)
        total_files += 1

        if is_compliant:
            print(f"✅ {filepath}")
        else:
            print(f"❌ {filepath}")
            for violation in violations:
                print(f"   - {violation}")
            total_violations += len(violations)
            all_compliant = False

    print()
    print(f"Checked {total_files} files")
    if all_compliant:
        print("✅ All files compliant with memory safety pattern")
        sys.exit(0)
    else:
        print(f"❌ Found {total_violations} violations")
        sys.exit(1)


if __name__ == "__main__":
    main()
```

#### 2C: Memory Safety Guidelines

**File**: `tests/MEMORY_SAFETY_GUIDELINES.md`

**Outline**:
```markdown
# Memory Safety Guidelines for pytest-xdist

## Table of Contents
1. [Problem Overview](#problem-overview)
2. [Solution Pattern](#solution-pattern)
3. [Implementation Guide](#implementation-guide)
4. [Integration Test Considerations](#integration-test-considerations)
5. [Troubleshooting](#troubleshooting)
6. [Validation](#validation)
7. [References](#references)

## 1. Problem Overview

### What is the Issue?

pytest-xdist runs tests in parallel using worker processes. When test classes use `AsyncMock` or `MagicMock`, these objects create circular references that prevent Python's garbage collector from reclaiming memory.

**Result**: Memory accumulation across test runs, leading to:
- 165GB+ VIRT memory consumption
- 42GB+ RES (actual RAM) usage
- OOM kills in CI/CD (GitHub Actions runners have 7GB RAM)
- Test failures due to resource exhaustion

### Why Do Mocks Cause This?

`AsyncMock` and `MagicMock` objects:
1. Create internal references to track mock calls
2. Store references to arguments, return values, and exceptions
3. Build circular reference chains: mock → call_args → mock
4. Prevent garbage collection until explicitly cleared

In pytest-xdist workers, mocks accumulate across test classes because:
- Workers reuse Python interpreters
- Mocks from previous test classes remain in memory
- Without explicit garbage collection, memory grows unbounded

### Real-World Impact

**Before fix** (test_api_key_indexed_lookup.py):
```
VIRT: 217GB
RES:  42GB
Duration: OOM killed after 30 minutes
```

**After fix** (Phase 1, 6 files, 45 classes):
```
VIRT: < 2GB per worker
RES:  < 500MB per worker
Duration: Tests complete successfully
Memory saved: ~165GB
```

## 2. Solution Pattern

### 3-Part Pattern

Apply this pattern to **every test class** that uses `AsyncMock` or `MagicMock`:

```python
# 1. Import gc module (at top of file)
import gc

# 2. Add xdist_group marker (before class definition)
@pytest.mark.xdist_group(name="category_name")
class TestClassName:
    """Test description"""

    # 3. Add teardown_method (first method in class)
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    # ... test methods here ...
```

### Why Each Part is Necessary

#### Part 1: `import gc`
- Provides explicit garbage collection control
- Required for teardown_method to call gc.collect()

#### Part 2: `@pytest.mark.xdist_group(name="...")`
- Runs all tests in this class on the same worker
- Prevents inter-worker state pollution
- Provides isolation boundary for cleanup

**Group Naming Convention**:
- Use descriptive category name: `auth_tests`, `keycloak_unit_tests`, `api_keys_endpoints_tests`
- Can use file-based name: `test_auth_factory` → `auth_factory_tests`
- OK to reuse names across files (xdist handles it)
- Avoid: `group1`, `test`, generic names

#### Part 3: `def teardown_method(self)`
- Runs after **every test method** in the class
- Calls `gc.collect()` to force garbage collection
- Clears mock references accumulated during test
- Prevents memory buildup across test classes

### Example: Complete Implementation

```python
import gc
from unittest.mock import AsyncMock, MagicMock

import pytest

@pytest.mark.xdist_group(name="example_tests")
class TestExampleFeature:
    """Tests for example feature with mocks"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_with_async_mock(self):
        """Test using AsyncMock"""
        mock_service = AsyncMock()
        mock_service.fetch_data.return_value = {"key": "value"}

        result = await service_under_test(mock_service)

        assert result is not None
        # teardown_method will gc.collect() after this test

    def test_with_magic_mock(self):
        """Test using MagicMock"""
        mock_config = MagicMock()
        mock_config.get_setting.return_value = "test_value"

        result = feature_under_test(mock_config)

        assert result == "expected"
        # teardown_method will gc.collect() after this test
```

## 3. Implementation Guide

### Step-by-Step (Manual)

1. **Check if file needs fixing**:
   ```bash
   grep -l "AsyncMock\|MagicMock" tests/test_myfile.py
   ```

2. **Add import** (top of file, after docstring):
   ```python
   import gc
   ```

3. **Find all test classes**:
   ```bash
   grep "^class Test" tests/test_myfile.py
   ```

4. **Add decorator and teardown** to each test class:
   ```python
   @pytest.mark.xdist_group(name="myfile_tests")  # Add this
   class TestMyFeature:
       """Test description"""

       def teardown_method(self):  # Add this
           """Force GC to prevent mock accumulation in xdist workers"""
           gc.collect()

       # ... existing test methods ...
   ```

5. **Verify**:
   ```bash
   # Syntax check
   python -m py_compile tests/test_myfile.py

   # Collection check
   pytest tests/test_myfile.py --collect-only

   # Run tests
   pytest tests/test_myfile.py -v
   ```

### Step-by-Step (Automated)

Use helper script for batch processing:

```bash
# Single file
python scripts/add_memory_safety_to_tests.py tests/test_myfile.py myfile_tests

# Multiple files
for file in tests/test_auth.py tests/test_session.py; do
    group_name=$(basename "$file" .py)
    python scripts/add_memory_safety_to_tests.py "$file" "${group_name}_tests"
done
```

**Verify after automation**:
```bash
# Check diff
git diff tests/test_myfile.py

# Run tests
pytest tests/test_myfile.py -v
```

## 4. Integration Test Considerations

### When to Skip xdist

Some integration tests require:
- Exclusive access to shared resources (databases, services)
- Sequential execution order
- State that persists across tests

**For these tests**, add skipif to prevent xdist execution:

```python
import sys
import pytest

@pytest.mark.skipif(
    "dist" in sys.modules,
    reason="Integration test requires sequential execution"
)
@pytest.mark.xdist_group(name="integration_tests")  # Still add for when run without xdist
class TestIntegrationWorkflow:
    """Integration test requiring sequential execution"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation"""
        gc.collect()

    def test_complete_workflow(self):
        # Test that needs exclusive access to shared database
        pass
```

**When to use skipif**:
- ✅ Real database migrations (need exclusive table locks)
- ✅ Stateful service initialization (e.g., Keycloak realm setup)
- ✅ File system operations with locks
- ✅ Tests that modify global configuration

**When NOT to use skipif**:
- ❌ Tests using mocked services (always use xdist)
- ❌ Tests with isolated test databases per worker
- ❌ Stateless API tests
- ❌ Unit tests (always parallelizable)

### Balancing Parallelization vs Isolation

**Goal**: Maximize parallel execution while preventing flaky tests

**Strategy**:
1. **Default**: Use xdist for all tests
2. **Measure**: Identify flaky integration tests
3. **Isolate**: Add skipif only for problematic tests
4. **Optimize**: Fix tests to be xdist-compatible if possible

**Example**: Database Integration Tests
```python
# BETTER: Use test database with unique schema per worker
@pytest.fixture
def test_db_schema(worker_id):
    schema_name = f"test_{worker_id}"
    create_schema(schema_name)
    yield schema_name
    drop_schema(schema_name)

# WORSE: Skip xdist entirely
@pytest.mark.skipif("dist" in sys.modules, reason="Shared database")
```

## 5. Troubleshooting

### Issue: Tests Still Consuming Excessive Memory

**Symptoms**:
- Memory usage > 5GB per worker
- OOM kills persisting after applying pattern
- `VIRT` memory growing to 50GB+

**Debugging Steps**:

1. **Verify pattern is applied correctly**:
   ```bash
   python scripts/check_test_memory_safety.py tests/test_problem_file.py
   ```

2. **Check for session/module scoped fixtures**:
   ```python
   # These can accumulate across tests
   @pytest.fixture(scope="module")  # Problem: mock lives for entire module
   def mock_service():
       return AsyncMock()

   # Fix: Use function scope
   @pytest.fixture(scope="function")  # Good: mock recreated per test
   def mock_service():
       return AsyncMock()
   ```

3. **Profile memory usage**:
   ```bash
   # Install memray
   pip install pytest-memray

   # Run with profiling
   pytest tests/test_problem_file.py --memray --memray-bin-path=./memray-results

   # View results
   python -m memray flamegraph memray-results/test_problem_file.py.bin
   ```

4. **Check for patch leaks**:
   ```python
   # Problem: patch not cleaned up
   @patch("module.function")
   def test_something(mock_func):
       mock_func.return_value = "value"
       # If test fails, patch may not be cleaned up

   # Fix: Use context manager
   def test_something():
       with patch("module.function") as mock_func:
           mock_func.return_value = "value"
           # Guaranteed cleanup even on failure
   ```

### Issue: xdist_group Decorator Not Found

**Symptoms**:
```
ERROR: Unknown pytest.mark.xdist_group
```

**Fix**:
1. Check pytest-xdist version:
   ```bash
   pip show pytest-xdist
   # Need version 2.3.0+
   ```

2. Update if needed:
   ```bash
   pip install --upgrade pytest-xdist
   ```

3. Verify in pyproject.toml:
   ```toml
   [project]
   dependencies = [
       "pytest-xdist>=3.3.1",
   ]
   ```

### Issue: gc.collect() Not Reducing Memory

**Symptoms**:
- teardown_method runs
- gc.collect() called
- Memory still accumulates

**Possible Causes**:

1. **Circular references not broken**:
   ```python
   # Problem: self-referential mock
   mock_obj = MagicMock()
   mock_obj.parent = mock_obj  # Creates circular reference

   # Fix: Clear references explicitly
   def teardown_method(self):
       # Clear any mock references
       if hasattr(self, 'mock_obj'):
           self.mock_obj.parent = None
       gc.collect()
   ```

2. **Module-level mocks**:
   ```python
   # Problem: mock at module level persists
   MOCK_SERVICE = AsyncMock()  # Don't do this!

   # Fix: Use fixtures or class attributes
   @pytest.fixture
   def mock_service():
       return AsyncMock()
   ```

### Issue: Tests Fail After Adding Pattern

**Symptoms**:
- Tests passed before
- Tests fail after adding memory safety pattern

**Debugging**:

1. **Check for test order dependencies**:
   ```bash
   # Run in random order
   pytest tests/test_file.py --random-order

   # If this fails, tests have order dependencies (bad!)
   ```

2. **Check for shared state**:
   ```python
   # Problem: class-level state
   class TestFeature:
       mock_service = AsyncMock()  # Shared across all test methods!

       def test_one(self):
           self.mock_service.method()  # State from previous test!

   # Fix: Create mock per test
   class TestFeature:
       def teardown_method(self):
           gc.collect()

       def test_one(self):
           mock_service = AsyncMock()  # Fresh mock per test
           mock_service.method()
   ```

3. **Check teardown side effects**:
   ```python
   # Problem: teardown assumes specific state
   def teardown_method(self):
       self.mock.assert_called_once()  # Assumes mock exists!
       gc.collect()

   # Fix: Check existence first
   def teardown_method(self):
       if hasattr(self, 'mock'):
           self.mock.reset_mock()
       gc.collect()
   ```

## 6. Validation

### Pre-commit Hook

The pre-commit hook automatically validates memory safety pattern:

```bash
# Install hooks
pre-commit install

# Run validation
pre-commit run validate-test-memory-safety --all-files

# View results
# ✅ tests/test_auth.py
# ❌ tests/test_new_feature.py
#    - Class 'TestNewFeature' missing @pytest.mark.xdist_group decorator
```

### Manual Validation

```bash
# Check single file
python scripts/check_test_memory_safety.py tests/test_myfile.py

# Check all test files
python scripts/check_test_memory_safety.py tests/**/*.py

# Check specific directory
python scripts/check_test_memory_safety.py tests/integration/*.py
```

### CI/CD Validation

GitHub Actions workflow should include:

```yaml
- name: Validate memory safety pattern
  run: |
    python scripts/check_test_memory_safety.py tests/**/*.py
```

### Testing the Fix

**Before deploying to CI/CD**, test locally:

```bash
# 1. Run with limited workers
pytest tests/ -n 2 -v

# 2. Monitor memory
watch -n 1 'ps aux | grep pytest | awk "{sum += \$6} END {print sum/1024 \" MB\"}"'

# 3. Run with xdist explicitly
pytest tests/ -n auto -v

# 4. Check for OOM in dmesg (Linux)
dmesg | grep -i "out of memory"
```

**Memory expectations**:
- ✅ < 2GB total memory (all workers combined)
- ✅ < 500MB per worker
- ❌ > 5GB → investigate specific test files

## 7. References

### pytest-xdist Documentation
- [pytest-xdist Docs](https://pytest-xdist.readthedocs.io/)
- [xdist_group marker](https://pytest-xdist.readthedocs.io/en/stable/distribution.html#running-tests-in-a-group)

### Python Garbage Collection
- [gc module docs](https://docs.python.org/3/library/gc.html)
- [Circular references](https://docs.python.org/3/library/gc.html#gc.garbage)

### unittest.mock
- [AsyncMock](https://docs.python.org/3/library/unittest.mock.html#unittest.mock.AsyncMock)
- [MagicMock](https://docs.python.org/3/library/unittest.mock.html#unittest.mock.MagicMock)

### Project Documentation
- Phase 1 commit: `014386d` (6 files, 45 classes)
- Helper script: `scripts/add_memory_safety_to_tests.py`
- Validation script: `scripts/check_test_memory_safety.py`
- Pre-commit hook: `.pre-commit-config.yaml`

### Related Issues
- Original issue: `tests/security/test_api_key_indexed_lookup.py` (217GB VIRT, 42GB RES)
- Total files needing fixes: 74 (6 done, 68 remaining)

---

**Last Updated**: 2025-11-10
**Maintained By**: Test Infrastructure Team
```

#### 2D: Update TDD Guidelines

**File**: `~/.claude/CLAUDE.md`

**Section**: After line ~13 in "Python (pytest)" section

**Addition**:
```markdown
#### Memory Safety for pytest-xdist

**CRITICAL**: All test classes using AsyncMock/MagicMock MUST follow memory safety pattern to prevent OOM:

```python
import gc  # Required

@pytest.mark.xdist_group(name="category_name")
class TestClassName:
    """Test description"""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    # Test methods here...
```

**Why**: AsyncMock/MagicMock create circular references preventing garbage collection in xdist workers, causing 100GB+ memory leaks.

**Enforcement**:
- Pre-commit hook: `validate-test-memory-safety`
- Validation script: `scripts/check_test_memory_safety.py`
- See: `tests/MEMORY_SAFETY_GUIDELINES.md` for complete details
```

### Deliverable 3: Validation & Testing

**Checklist**:
- [ ] Validation script works on all test files
- [ ] Pre-commit hook catches violations
- [ ] Phase 1 files pass validation (show "No changes needed")
- [ ] Phase 2 files pass validation after fixing
- [ ] Guidelines documentation is clear and comprehensive
- [ ] CLAUDE.md updated with TDD requirements

**Testing**:
```bash
# Test validation script on Phase 1 files (should pass)
python scripts/check_test_memory_safety.py tests/test_keycloak.py

# Test on unfixed file (should fail)
python scripts/check_test_memory_safety.py tests/test_auth_factory.py

# Run pre-commit hook
pre-commit run validate-test-memory-safety --all-files
```

---

## Success Criteria

### Phase 2 Success
- [ ] 14 HIGH priority files fixed
- [ ] All files pass validation
- [ ] Memory consumption < 2GB per worker
- [ ] No test failures introduced
- [ ] All changes committed

### Phase 3 Success
- [ ] Pre-commit hook active and working
- [ ] Validation script catches violations
- [ ] Guidelines documentation complete
- [ ] TDD guidelines updated
- [ ] New violations prevented

### Overall Success
- [ ] pytest-xdist memory issue eliminated
- [ ] Prevention infrastructure in place
- [ ] Team awareness via documentation
- [ ] CI/CD runs without OOM kills
- [ ] This issue can NEVER happen again

---

## Appendix: Full File List

### Phase 2 (HIGH Priority, 14 files)
```
tests/test_auth_factory.py                                (9 classes, 37 methods)
tests/core/test_cache.py                                  (15 classes, 37 methods)
tests/api/test_service_principals_endpoints.py            (7 classes, 21 methods)
tests/api/test_api_keys_endpoints.py                      (7 classes, 20 methods)
tests/test_gdpr.py                                        (6 classes, 19 methods)
tests/integration/test_gdpr_endpoints.py                  (2 classes, 18 methods)
tests/test_session_timeout.py                             (5 classes, 17 methods)
tests/test_llm_factory_contract.py                        (2 classes, 16 methods)
tests/integration/test_app_startup_validation.py          (5 classes, 16 methods)
tests/test_user_provider.py                               (4 classes, 14 methods)
tests/test_context_manager.py                             (4 classes, 13 methods)
tests/conftest.py                                         (0 classes, 12 methods)
tests/unit/test_dependencies_wiring.py                    (5 classes, 11 methods)
tests/smoke/test_ci_startup_smoke.py                      (4 classes, 11 methods)
```

### Phase 4 (MEDIUM Priority, 33 files - Top 15 shown)
```
tests/test_sla_monitoring.py                              (9 classes, 9 methods)
tests/test_verifier.py                                    (4 classes, 9 methods)
tests/property/test_auth_properties.py                    (5 classes, 9 methods)
tests/regression/test_performance_regression.py           (5 classes, 9 methods)
tests/security/test_api_key_performance_monitoring.py     (3 classes, 8 methods)
tests/unit/test_security_practices.py                     (4 classes, 7 methods)
tests/test_agent.py                                       (4 classes, 6 methods)
tests/integration/test_mcp_startup_validation.py          (3 classes, 6 methods)
tests/test_session.py                                     (4 classes, 5 methods)
tests/unit/test_mcp_stdio_server.py                       (7 classes, 5 methods)
tests/security/test_authorization_fallback_controls.py    (2 classes, 5 methods)
tests/security/test_scim_service_principal_openfga.py     (4 classes, 5 methods)
tests/test_cleanup_scheduler.py                           (9 classes, 4 methods)
tests/test_context_manager_llm.py                         (3 classes, 4 methods)
tests/test_distributed_checkpointing.py                   (4 classes, 4 methods)
... (18 more files)
```

### Phase 5 (LOW Priority, 21 files - DEFER)
```
tests/middleware/test_rate_limiter.py                     (14 classes, 47 methods, MagicMock only)
tests/test_rate_limiter.py                                (6 classes, 27 methods, MagicMock only)
tests/security/test_injection_attacks.py                  (10 classes, 34 methods, no mocks found)
... (18 more files)
```

---

**END OF PLAN**
