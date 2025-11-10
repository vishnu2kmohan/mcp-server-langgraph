# pytest-xdist Memory Safety - Quick Reference

**Full Plan**: See [PYTEST_XDIST_MEMORY_SAFETY_PLAN.md](./PYTEST_XDIST_MEMORY_SAFETY_PLAN.md)

## Status at a Glance

| Phase | Files | Classes | Methods | Status | Time Est. | Memory Impact |
|-------|-------|---------|---------|--------|-----------|---------------|
| **Phase 1** | 6 | 45 | ~165 | ✅ DONE | - | ~165GB saved |
| **Phase 2** | 14 | ~75 | ~249 | ❌ TODO | 2-3h | ~250GB saved |
| **Phase 3** | 4 infra | - | - | ❌ TODO | 4-5h | Prevention |
| **Phase 4** | 33 | ~100 | ~150 | ⏸️ DEFER | 3-4h | ~80GB saved |
| **Phase 5** | 21 | ~50 | ~100 | ⏸️ DEFER | 2-3h | ~20GB saved |
| **TOTAL** | **78** | **~270** | **~664** | **8%** | **9-15h** | **~515GB** |

## Phase 2: HIGH Priority (Next Step)

### Files to Fix (14 files, 2-3 hour effort)

```bash
# Batch 1: Core Authentication & Authorization (2 files)
tests/test_auth_factory.py                     (9 classes, 37 methods)
tests/core/test_cache.py                       (15 classes, 37 methods)

# Batch 2: API Endpoints (2 files)
tests/api/test_service_principals_endpoints.py (7 classes, 21 methods)
tests/api/test_api_keys_endpoints.py           (7 classes, 20 methods)

# Batch 3: GDPR Compliance (2 files)
tests/test_gdpr.py                             (6 classes, 19 methods)
tests/integration/test_gdpr_endpoints.py       (2 classes, 18 methods)

# Batch 4: Session & Auth (2 files)
tests/test_session_timeout.py                  (5 classes, 17 methods)
tests/test_llm_factory_contract.py             (2 classes, 16 methods)

# Batch 5: Startup & Validation (3 files)
tests/integration/test_app_startup_validation.py (5 classes, 16 methods)
tests/unit/test_dependencies_wiring.py           (5 classes, 11 methods)
tests/smoke/test_ci_startup_smoke.py             (4 classes, 11 methods)

# Batch 6: Core Services (3 files)
tests/test_user_provider.py                    (4 classes, 14 methods)
tests/test_context_manager.py                  (4 classes, 13 methods)
tests/conftest.py                              (0 classes, 12 methods - REVIEW MANUALLY)
```

### Quick Fix Command (per file)

```bash
# Template
python scripts/add_memory_safety_to_tests.py <FILE> <GROUP_NAME>

# Example
python scripts/add_memory_safety_to_tests.py tests/test_auth_factory.py auth_factory_tests

# Batch processing
for file in tests/test_auth_factory.py tests/core/test_cache.py; do
    group_name=$(basename "$file" .py | sed 's/test_//')_tests
    python scripts/add_memory_safety_to_tests.py "$file" "$group_name"
done
```

### Verification After Fix

```bash
# 1. Syntax check
python -m py_compile tests/test_auth_factory.py

# 2. Collection check (imports)
pytest tests/test_auth_factory.py --collect-only

# 3. Run tests
pytest tests/test_auth_factory.py -v

# 4. Memory check (optional)
pytest tests/test_auth_factory.py -v &
pid=$! && watch -n 1 "ps -p $pid -o rss | tail -1"
```

### Commit Template

```bash
git add tests/test_auth_factory.py tests/core/test_cache.py
git commit -m "fix(tests): add memory safety to auth_factory and cache tests (Phase 2, batch 1/6)

Apply pytest-xdist memory safety pattern to prevent OOM:
- Add @pytest.mark.xdist_group to 24 test classes
- Add teardown_method with gc.collect()
- Add import gc

Estimated memory saved: ~65GB RES

Part of Phase 2 (14 HIGH priority files, 75 classes total).
See docs-internal/PYTEST_XDIST_MEMORY_SAFETY_PLAN.md for details.

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Phase 3: Prevention Infrastructure (4-5 hours)

### Deliverables

1. **Pre-commit Hook** (`.pre-commit-config.yaml`)
   - Add `validate-test-memory-safety` hook
   - Runs automatically on commit
   - Blocks commits with violations

2. **Validation Script** (`scripts/check_test_memory_safety.py`)
   - ~200 lines Python
   - Checks for import gc, xdist_group, teardown_method
   - Standalone + pre-commit usage

3. **Guidelines Doc** (`tests/MEMORY_SAFETY_GUIDELINES.md`)
   - ~1500 lines comprehensive guide
   - Problem overview, solution pattern, troubleshooting
   - Integration test considerations

4. **TDD Update** (`~/.claude/CLAUDE.md`)
   - Add memory safety requirements
   - Global awareness for all projects

### Implementation Order

```bash
# 1. Create validation script (2h)
# - See plan for full implementation
scripts/check_test_memory_safety.py

# 2. Test validation script (0.5h)
python scripts/check_test_memory_safety.py tests/test_keycloak.py  # Should pass
python scripts/check_test_memory_safety.py tests/test_auth_factory.py  # Should fail (before fix)

# 3. Add pre-commit hook (0.5h)
# - Edit .pre-commit-config.yaml at line ~52

# 4. Write guidelines doc (1.5h)
# - Use template from plan

# 5. Update CLAUDE.md (0.5h)
# - Add memory safety section to pytest conventions

# 6. Test entire infrastructure (1h)
pre-commit run validate-test-memory-safety --all-files
```

## The 3-Part Pattern

### What to Add

```python
# 1. Import (top of file)
import gc

# 2. Decorator (before each test class)
@pytest.mark.xdist_group(name="descriptive_category_name")
class TestClassName:
    """Test description"""

    # 3. Teardown (first method in each test class)
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    # ... test methods ...
```

### Why It Works

- **xdist_group**: Runs all tests in class on same worker (isolation)
- **teardown_method**: Runs after every test method
- **gc.collect()**: Forces garbage collection to clear mock references
- **Result**: No circular reference accumulation → No memory leak

## Common Issues

### Issue: Helper Script Not Working

```bash
# Check the script exists
ls -la scripts/add_memory_safety_to_tests.py

# Make it executable
chmod +x scripts/add_memory_safety_to_tests.py

# Test on Phase 1 file (should say "No changes needed")
python scripts/add_memory_safety_to_tests.py tests/test_keycloak.py keycloak_tests
```

### Issue: Tests Fail After Adding Pattern

```bash
# Check syntax
python -m py_compile tests/test_file.py

# Check imports
pytest tests/test_file.py --collect-only

# Run single test to isolate issue
pytest tests/test_file.py::TestClass::test_method -v
```

### Issue: Memory Still High

```bash
# Profile memory usage
pip install pytest-memray
pytest tests/test_file.py --memray

# Check for session/module fixtures
grep "@pytest.fixture.*scope=" tests/test_file.py

# Look for module-level mocks (these accumulate)
grep "^[A-Z_].*Mock" tests/test_file.py
```

## Integration Test Special Cases

### When to Skip xdist

Some integration tests need sequential execution:

```python
import sys
import pytest

@pytest.mark.skipif(
    "dist" in sys.modules,
    reason="Integration test requires sequential execution"
)
@pytest.mark.xdist_group(name="integration_tests")
class TestDatabaseMigration:
    """Needs exclusive access to shared database"""

    def teardown_method(self):
        gc.collect()
```

**Use skipif for**:
- Real database migrations (table locks)
- Stateful service initialization
- File system operations with locks
- Global configuration changes

**Don't use skipif for**:
- Mocked services (always use xdist)
- Isolated test databases
- Stateless API tests
- Unit tests

## Quick Wins

### Find High-Risk Files

```bash
# Files with AsyncMock (highest risk)
grep -l "AsyncMock" tests/**/*.py | while read f; do
    classes=$(grep -c "^class Test" "$f")
    methods=$(grep -c "def test_" "$f")
    echo "$classes classes, $methods methods: $f"
done | sort -rn

# Files with most test methods
for f in tests/**/*.py; do
    [ -f "$f" ] && echo "$(grep -c 'def test_' "$f") $f"
done | sort -rn | head -20
```

### Batch Fix Multiple Files

```bash
# Fix batch of files
files=(
    tests/test_auth_factory.py
    tests/core/test_cache.py
    tests/test_gdpr.py
)

for file in "${files[@]}"; do
    group_name=$(basename "$file" .py | sed 's/test_//')_tests
    echo "Fixing $file → group: $group_name"
    python scripts/add_memory_safety_to_tests.py "$file" "$group_name"
done

# Test all fixed files
pytest "${files[@]}" -v
```

### Monitor Memory During Tests

```bash
# Terminal 1: Run tests
pytest tests/ -n 4 -v

# Terminal 2: Monitor memory
watch -n 1 'echo "Memory (MB):"; ps aux | grep pytest | grep -v grep | awk "{sum += \$6/1024} END {print sum}"'

# Expected: < 2000 MB total
# Problem: > 5000 MB → investigate specific files
```

## Resources

- **Full Plan**: [PYTEST_XDIST_MEMORY_SAFETY_PLAN.md](./PYTEST_XDIST_MEMORY_SAFETY_PLAN.md)
- **Helper Script**: `scripts/add_memory_safety_to_tests.py`
- **Validation**: `scripts/check_test_memory_safety.py` (Phase 3)
- **Guidelines**: `tests/MEMORY_SAFETY_GUIDELINES.md` (Phase 3)
- **Phase 1 Commit**: `014386d` (6 files, 45 classes, ~165GB saved)

## Next Steps

1. **Read full plan** to understand strategy and risks
2. **Fix Phase 2** (14 HIGH priority files, 2-3 hours)
3. **Build Phase 3** (prevention infrastructure, 4-5 hours)
4. **Consider Phase 4** (33 MEDIUM priority files, optional)
5. **Defer Phase 5** (21 LOW priority files, MagicMock only)

**Goal**: Ensure this memory issue can NEVER happen again.

---

**Last Updated**: 2025-11-10
**Status**: Phase 1 Complete (8%), Phase 2-3 Pending
