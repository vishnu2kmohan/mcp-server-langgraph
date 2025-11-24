# Remaining xdist Marker Work

## Status: 2 of 6 files complete

✅ Completed:
1. tests/unit/core/test_cache_isolation.py (commit aaecf8be)
2. tests/unit/execution/test_network_mode_logic.py (commit b81109a4)

## Remaining: 4 files (10 test classes total)

### File 1: tests/meta/test_integration_script_args.py
**Classes**: 3
**Status**: Partially done (added import gc + marker to class 1)

**Remaining work**:
```python
# Add to TestIntegrationScriptArgPropagation (line 31):
def teardown_method(self):
    """Force GC to prevent mock accumulation in xdist workers"""
    gc.collect()

# Add to TestIntegrationScriptCoverageWorkflow (line ~178):
@pytest.mark.xdist_group(name="integration_script_coverage")
class TestIntegrationScriptCoverageWorkflow:
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

# Add to TestIntegrationScriptDocumentation (line ~228):
@pytest.mark.xdist_group(name="integration_script_docs")
class TestIntegrationScriptDocumentation:
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()
```

### File 2: tests/meta/test_precommit_cross_platform.py
**Classes**: 2

**Work needed**:
```python
# Add at top:
import gc

# Add to TestPreCommitCrossPlatformCompatibility (line ~27):
@pytest.mark.xdist_group(name="precommit_cross_platform")
class TestPreCommitCrossPlatformCompatibility:
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

# Add to TestPreCommitEnvironmentIsolation (line ~315):
@pytest.mark.xdist_group(name="precommit_env_isolation")
class TestPreCommitEnvironmentIsolation:
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()
```

### File 3: tests/meta/test_validate_prepush_efficiency.py
**Classes**: 3

**Work needed**:
```python
# Add at top:
import gc

# Add to TestValidatePrePushEfficiency (line ~33):
@pytest.mark.xdist_group(name="validate_prepush_efficiency")
class TestValidatePrePushEfficiency:
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

# Add to TestValidatePrePushPerformance (line ~345):
@pytest.mark.xdist_group(name="validate_prepush_performance")
class TestValidatePrePushPerformance:
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

# Add to TestValidatePrePushDocumentation (line ~435):
@pytest.mark.xdist_group(name="validate_prepush_docs")
class TestValidatePrePushDocumentation:
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()
```

### File 4: tests/meta/test_validation_optimization.py
**Classes**: 2

**Work needed**:
```python
# Add at top:
import gc

# Add to TestValidatorDeduplication (line ~24):
@pytest.mark.xdist_group(name="validator_deduplication")
class TestValidatorDeduplication:
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

# Add to TestMakefilePrePushParity (line ~141):
@pytest.mark.xdist_group(name="makefile_prepush_parity")
class TestMakefilePrePushParity:
    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()
```

### File 5: tests/unit/storage/test_conversation_store_async.py
**Functions**: 1 (needs function-to-class conversion)

**Work needed**: This one is more complex - single function needs conversion to class. Can use the pattern from test_network_mode_logic.py as reference.

## Automation Script

Use `scripts/dev/add_xdist_markers_bulk.py` (already created) to automate this:

```bash
# Dry-run to preview changes
python scripts/dev/add_xdist_markers_bulk.py tests/meta/*.py --dry-run

# Apply changes
python scripts/dev/add_xdist_markers_bulk.py tests/meta/*.py
```

## Verification

After adding markers, verify with:

```bash
# Check individual files
.venv/bin/python scripts/validators/check_test_memory_safety.py tests/meta/test_integration_script_args.py

# Check all meta tests
.venv/bin/python scripts/validators/check_test_memory_safety.py tests/meta/test_*.py

# Run pre-push hook to verify all issues resolved
git push --dry-run  # Triggers pre-push hooks without actually pushing
```

## Expected Impact

Once complete, this will fix the "Validate Pytest-xdist Isolation" CI check which is currently failing due to missing markers.

## References

- Memory safety pattern: `.claude/context/xdist-safety-patterns.md`
- Validator: `scripts/validators/check_test_memory_safety.py`
- Pre-push hook: `.pre-commit-config.yaml` (check-test-memory-safety)
- Example implementation: `tests/unit/execution/test_network_mode_logic.py` (commit b81109a4)
