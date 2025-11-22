# Test Suite Reorganization Migration Guide

**Last Updated**: November 21, 2025
**Reorganization Date**: November 2025
**Impact**: 44 files relocated, 97% reduction in root directory clutter

This guide helps developers navigate the test suite reorganization completed in November 2025. If you're looking for a test file that used to be in `tests/`, this document shows you where it moved.

## Quick Summary

The test suite was reorganized to improve maintainability and reduce root directory clutter:

- **Before**: 55 files in `tests/` root
- **After**: 1 file in `tests/` root (98% reduction)
- **Relocated**: 44 files moved to logical subdirectories
- **New Structure**: 24 organized subdirectories by domain

## File Relocation Mapping

### Files Moved to `tests/meta/ci/`
CI/CD workflow validation tests (meta-validation - tests that test tests)

| Old Location | New Location | Purpose |
|-------------|--------------|---------|
| `test_workflow_dependencies.py` | `meta/ci/test_workflow_dependencies.py` | Workflow job dependency validation |
| `test_workflow_security.py` | `meta/ci/test_workflow_security.py` | Workflow secret security patterns |
| `test_workflow_syntax.py` | `meta/ci/test_workflow_syntax.py` | Actionlint syntax validation |

**Impact**: If you reference these files in CI/CD configs, update paths to include `meta/ci/` prefix.

### Files Moved to `tests/meta/infrastructure/`
Infrastructure configuration validation tests

| Old Location | New Location | Purpose |
|-------------|--------------|---------|
| `test_docker_paths.py` | `meta/infrastructure/test_docker_paths.py` | Docker Python path validation |

### Files Moved to `tests/meta/validation/`
Test suite validation and enforcement

| Old Location | New Location | Purpose |
|-------------|--------------|---------|
| `test_fixture_organization.py` | `meta/validation/test_fixture_organization.py` | Fixture organization enforcement |
| `test_test_organization.py` | `meta/validation/test_test_organization.py` | Test file organization validation |

### Files Moved to `tests/integration/`
Integration tests organized by domain (14 subdirectories)

#### `tests/integration/api/`
| Old Location | New Location |
|-------------|--------------|
| `test_agent_api_integration.py` | `integration/api/test_agent_api_integration.py` |
| `test_conversation_api_integration.py` | `integration/api/test_conversation_api_integration.py` |

#### `tests/integration/compliance/`
| Old Location | New Location |
|-------------|--------------|
| `test_gdpr_compliance.py` | `integration/compliance/test_gdpr_compliance.py` |

#### `tests/integration/contract/`
| Old Location | New Location |
|-------------|--------------|
| `test_mcp_contract.py` | `integration/contract/test_mcp_contract.py` |

#### `tests/integration/core/`
| Old Location | New Location |
|-------------|--------------|
| `test_agent_integration.py` | `integration/core/test_agent_integration.py` |
| `test_graph_builder_integration.py` | `integration/core/test_graph_builder_integration.py` |

#### `tests/integration/deployment/`
| Old Location | New Location |
|-------------|--------------|
| `test_docker_deployment.py` | `integration/deployment/test_docker_deployment.py` |
| `test_kubernetes_integration.py` | `integration/deployment/test_kubernetes_integration.py` |

#### `tests/integration/execution/`
| Old Location | New Location |
|-------------|--------------|
| `test_execution_integration.py` | `integration/execution/test_execution_integration.py` |
| `test_workflow_execution.py` | `integration/execution/test_workflow_execution.py` |

#### `tests/integration/health/`
| Old Location | New Location |
|-------------|--------------|
| `test_health_check_integration.py` | `integration/health/test_health_check_integration.py` |

#### `tests/integration/infrastructure/`
| Old Location | New Location |
|-------------|--------------|
| `test_database_integration.py` | `integration/infrastructure/test_database_integration.py` |
| `test_redis_integration.py` | `integration/infrastructure/test_redis_integration.py` |
| `test_openfga_integration.py` | `integration/infrastructure/test_openfga_integration.py` |

#### `tests/integration/patterns/`
| Old Location | New Location |
|-------------|--------------|
| `test_dependency_injection.py` | `integration/patterns/test_dependency_injection.py` |

#### `tests/integration/property/`
| Old Location | New Location |
|-------------|--------------|
| `test_property_integration.py` | `integration/property/test_property_integration.py` |

#### `tests/integration/regression/`
| Old Location | New Location |
|-------------|--------------|
| `test_regression_prevention.py` | `integration/regression/test_regression_prevention.py` |

#### `tests/integration/resilience/`
| Old Location | New Location |
|-------------|--------------|
| `test_circuit_breaker_integration.py` | `integration/resilience/test_circuit_breaker_integration.py` |
| `test_retry_integration.py` | `integration/resilience/test_retry_integration.py` |

#### `tests/integration/security/`
| Old Location | New Location |
|-------------|--------------|
| `test_auth_integration.py` | `integration/security/test_auth_integration.py` |
| `test_authorization_integration.py` | `integration/security/test_authorization_integration.py` |
| `test_api_key_integration.py` | `integration/security/test_api_key_integration.py` |

### Files Moved to `tests/unit/`
Pure unit tests organized by domain (12 subdirectories)

#### `tests/unit/auth/`
| Old Location | New Location |
|-------------|--------------|
| `test_auth_unit.py` | `unit/auth/test_auth_unit.py` |
| `test_jwt_validation.py` | `unit/auth/test_jwt_validation.py` |

#### `tests/unit/config/`
| Old Location | New Location |
|-------------|--------------|
| `test_config_management.py` | `unit/config/test_config_management.py` |

#### `tests/unit/core/`
| Old Location | New Location |
|-------------|--------------|
| `test_agent_unit.py` | `unit/core/test_agent_unit.py` |
| `test_graph_builder_unit.py` | `unit/core/test_graph_builder_unit.py` |

#### `tests/unit/execution/`
| Old Location | New Location |
|-------------|--------------|
| `test_execution_engine.py` | `unit/execution/test_execution_engine.py` |

#### `tests/unit/health/`
| Old Location | New Location |
|-------------|--------------|
| `test_health_check_unit.py` | `unit/health/test_health_check_unit.py` |

#### `tests/unit/llm/`
| Old Location | New Location |
|-------------|--------------|
| `test_llm_provider_unit.py` | `unit/llm/test_llm_provider_unit.py` |

#### `tests/unit/observability/`
| Old Location | New Location |
|-------------|--------------|
| `test_logging_unit.py` | `unit/observability/test_logging_unit.py` |
| `test_metrics_unit.py` | `unit/observability/test_metrics_unit.py` |

#### `tests/unit/resilience/`
| Old Location | New Location |
|-------------|--------------|
| `test_circuit_breaker_unit.py` | `unit/resilience/test_circuit_breaker_unit.py` |
| `test_retry_unit.py` | `unit/resilience/test_retry_unit.py` |

#### `tests/unit/session/`
| Old Location | New Location |
|-------------|--------------|
| `test_session_management.py` | `unit/session/test_session_management.py` |

#### `tests/unit/storage/`
| Old Location | New Location |
|-------------|--------------|
| `test_conversation_store_unit.py` | `unit/storage/test_conversation_store_unit.py` |
| `test_redis_store_unit.py` | `unit/storage/test_redis_store_unit.py` |

#### `tests/unit/tools/`
| Old Location | New Location |
|-------------|--------------|
| `test_tool_implementation_unit.py` | `unit/tools/test_tool_implementation_unit.py` |

### Files Remaining in Root

Only **1 test file** remains in the root directory:

| File | Reason |
|------|--------|
| `test_app_factory.py` | Application factory initialization test - foundational test that should remain at root level |

## Update Checklist for Developers

If you have code or documentation referencing the old test structure, update these areas:

### 1. Import Statements
If you import test utilities or fixtures from moved files:

```python
# ❌ OLD
from tests.test_workflow_dependencies import extract_needs_references

# ✅ NEW
from tests.meta.ci.test_workflow_dependencies import extract_needs_references
```

### 2. CI/CD Configuration
If your CI/CD workflows reference specific test files:

```yaml
# ❌ OLD
pytest tests/test_workflow_syntax.py

# ✅ NEW
pytest tests/meta/ci/test_workflow_syntax.py
```

### 3. Documentation Links
If you link to test files in documentation:

```markdown
<!-- ❌ OLD -->
See [workflow tests](../tests/test_workflow_dependencies.py)

<!-- ✅ NEW -->
See [workflow tests](../tests/meta/ci/test_workflow_dependencies.py)
```

### 4. Git History
To find the old location of a file and its history:

```bash
# Find where a file moved from
git log --follow --all -- tests/meta/ci/test_workflow_syntax.py

# See file history across the move
git log --follow --stat -- tests/meta/ci/test_workflow_syntax.py
```

### 5. IDE/Editor Configuration
Update test runner configurations if you have file-specific run configs:

- **PyCharm**: Update run configurations in `.idea/runConfigurations/`
- **VS Code**: Update `launch.json` test configurations
- **vim/emacs**: Update test runner keybindings/commands

## Running Tests After Reorganization

All pytest commands continue to work without changes due to pytest's automatic test discovery:

```bash
# Run all tests (discovers tests in all subdirectories)
pytest tests/

# Run specific categories using markers (unchanged)
pytest -m unit
pytest -m integration
pytest -m e2e

# Run tests in specific directory (new structure)
pytest tests/meta/ci/                    # All CI workflow tests
pytest tests/integration/security/       # All security integration tests
pytest tests/unit/auth/                  # All auth unit tests

# Run specific test file (use new path)
pytest tests/meta/ci/test_workflow_syntax.py
```

## Fixture Organization Changes (Phase 3)

In addition to test file reorganization, fixtures were modularized in Phase 3:

### Extracted Fixtures

| Old Location | New Location | Content |
|-------------|--------------|---------|
| `conftest.py` (lines 521-720) | `fixtures/docker_fixtures.py` | Docker Compose lifecycle, health checks (183 lines) |
| `conftest.py` (lines 1172-1197) | `fixtures/time_fixtures.py` | Time freezing for deterministic tests (42 lines) |

### Autouse Fixtures

**Important**: Autouse fixtures remain in `conftest.py` per enforcement rules:
- `init_test_observability()` - Observability initialization
- `reset_singletons()` - Singleton state reset between tests
- `test_infrastructure()` - Test infrastructure management

See `tests/fixtures/__init__.py` for complete fixture organization documentation.

## Benefits of Reorganization

### Before
- 🔴 55 files in root directory
- 🔴 Difficult to navigate
- 🔴 No clear categorization
- 🔴 Mixed concerns (unit + integration + meta)
- 🔴 Hard to maintain

### After
- ✅ 1 file in root (98% reduction)
- ✅ 24 logical subdirectories
- ✅ Clear domain separation
- ✅ Easy to find related tests
- ✅ Scalable structure for growth

## Common Migration Issues

### Issue 1: "Module not found" errors

**Symptom**: `ModuleNotFoundError: No module named 'tests.test_workflow_syntax'`

**Solution**: Update import to new location:
```python
from tests.meta.ci.test_workflow_syntax import ...
```

### Issue 2: Test not discovered by pytest

**Symptom**: `collected 0 items` when running `pytest tests/test_something.py`

**Solution**: File was moved. Check this migration guide or use:
```bash
find tests -name "test_something.py"
```

### Issue 3: Git shows file as deleted

**Symptom**: `git diff` shows file deletion but it still exists

**Solution**: File was moved with `git mv`. Check new location:
```bash
git log --follow --all -- tests/**/test_something.py
```

### Issue 4: Pre-commit hook failing after reorganization

**Symptom**: `FileNotFoundError` in pre-commit hooks

**Solution**:
1. Check if hook references old test paths
2. Update hook to use new paths
3. See `.git/hooks/pre-commit` and `.git/hooks/pre-push`

### Issue 5: Path calculation errors in moved tests

**Symptom**: `AssertionError: Workflows directory not found: /path/to/tests/meta/.github/`

**Solution**: Tests moved deeper in directory tree. Update path calculations:
```python
# OLD (2 levels up from tests/)
Path(__file__).parent.parent / ".github"

# NEW (4 levels up from tests/meta/ci/)
Path(__file__).parent.parent.parent.parent / ".github"
```

This was fixed in commit "fix(tests): correct path calculations in moved workflow tests".

## Need Help?

- **Test organization questions**: See `tests/README.md`
- **Fixture usage**: See `tests/fixtures/__init__.py`
- **Migration issues**: Check `docs-internal/TESTING_STRATEGY_VALIDATION_REPORT.md`
- **Pre-commit hook errors**: Run `pytest tests/meta/validation/` to validate organization

## Validation

To verify your migration is correct, run the meta-validation tests:

```bash
# Validate test organization
pytest tests/meta/validation/test_test_organization.py -v

# Validate fixture organization
pytest tests/meta/validation/test_fixture_organization.py -v

# Validate all meta tests
pytest tests/meta/ -v
```

All meta-validation tests should pass, confirming the reorganization is correct.

---

**Reorganization completed**: November 2025
**Documented in**: `docs-internal/TESTING_STRATEGY_VALIDATION_REPORT.md`
**Validation**: `pytest tests/meta/ -v`
