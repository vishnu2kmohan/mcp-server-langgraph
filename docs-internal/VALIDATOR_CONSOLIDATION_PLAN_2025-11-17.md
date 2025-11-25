# Validator Consolidation Implementation Plan
## Remaining High-Priority Consolidations

**Date**: 2025-11-17
**Status**: PLANNING PHASE
**Reference**: [DUPLICATE_VALIDATOR_ANALYSIS_2025-11-16.md](./DUPLICATE_VALIDATOR_ANALYSIS_2025-11-16.md)

---

## Executive Summary

This document provides an implementation plan for the two remaining high-priority validator consolidations identified in the duplicate validator analysis:

1. **Documentation Validation Consolidation** (~300-400 lines savings, HIGH PRIORITY)
2. **GitHub Workflow Validation Consolidation** (~100-150 lines savings, HIGH PRIORITY)

**Work Completed** (2025-11-17):
- ✅ ADR Synchronization consolidation (~40 lines saved)
- ✅ CLI availability guards added to 5 external tool hooks
- ✅ CONTRIBUTING.md updated with validation tier guide

**Remaining Work**: ~400-550 lines of duplicate code across 2 consolidations

---

## Consolidation #1: Documentation Validation (HIGH PRIORITY)

### Current State

**Problem**: Documentation validation logic scattered across 6 hooks, 7 scripts, and 3 test files with significant overlap.

**Affected Components**:

#### Pre-commit Hooks (6 hooks):
1. `validate-adr-sync` → calls `scripts/validators/adr_sync_validator.py` (✅ DONE - consolidated with test)
2. `validate-documentation-integrity` → runs pytest on `tests/test_documentation_integrity.py`
3. `validate-documentation-structure` → runs pytest on `tests/regression/test_documentation_structure.py`
4. `check-frontmatter-quotes` → validation logic in hook itself
5. `check-mermaid-styling` → validation logic in hook itself
6. `validate-mdx-extensions` → calls `scripts/validators/mdx_extension_validator.py`

#### Validation Scripts (7 scripts):
1. `scripts/validators/adr_sync_validator.py` (7902 bytes) - ✅ CONSOLIDATED
2. `scripts/validators/validate_docs.py` (7948 bytes)
3. `scripts/validators/mdx_extension_validator.py` (5908 bytes)
4. `scripts/validators/frontmatter_validator.py` (8830 bytes)
5. `scripts/validators/todo_audit.py` (validation logic)
6. `scripts/validators/orphaned_mdx_validator.py` (validation logic)
7. `scripts/standardize_frontmatter.py` (fix script)

#### Meta-Tests (3 test files):
1. `tests/test_documentation_integrity.py` (ADRs, docs.json, HTML comments, Mermaid)
2. `tests/regression/test_documentation_structure.py` (orphaned files, numbering, TODOs)
3. Various validators called from tests

**Duplication Level**: ~40% overlap (300-400 lines)

### Consolidation Strategy

#### Phase 1: Create Comprehensive Documentation Validator

**New Script**: `scripts/validators/validate_documentation_comprehensive.py`

**Features**:
```python
class DocumentationValidator:
    """Comprehensive documentation validation suite."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.docs_dir = repo_root / "docs"
        self.adr_dir = repo_root / "adr"

    def validate_all(self) -> ValidationResult:
        """Run all documentation validations."""
        results = []

        # ADR sync (reuse existing validator)
        results.append(self.validate_adr_sync())

        # docs.json integrity
        results.append(self.validate_docs_json())

        # MDX syntax and extensions
        results.append(self.validate_mdx_syntax())

        # Frontmatter consistency
        results.append(self.validate_frontmatter())

        # Mermaid diagrams
        results.append(self.validate_mermaid())

        # Orphaned files
        results.append(self.validate_orphaned_files())

        # Navigation links
        results.append(self.validate_navigation())

        return ValidationResult.combine(results)

    def validate_adr_sync(self) -> ValidationResult:
        """Validate ADR synchronization (calls existing validator)."""
        from scripts.validators.adr_sync_validator import AdrSyncValidator
        validator = AdrSyncValidator(self.repo_root)
        return validator.validate()

    # ... other validation methods ...
```

**CLI Interface**:
```bash
# Run all validations
python scripts/validators/validate_documentation_comprehensive.py

# Run specific validation
python scripts/validators/validate_documentation_comprehensive.py --check=adr-sync
python scripts/validators/validate_documentation_comprehensive.py --check=mdx-syntax

# Fix mode (for auto-fixable issues)
python scripts/validators/validate_documentation_comprehensive.py --fix

# CI mode (stricter validation)
python scripts/validators/validate_documentation_comprehensive.py --strict
```

#### Phase 2: Consolidate Hooks

**Before** (6 hooks):
```yaml
- id: validate-adr-sync
- id: validate-documentation-integrity
- id: validate-documentation-structure
- id: check-frontmatter-quotes
- id: check-mermaid-styling
- id: validate-mdx-extensions
```

**After** (2 hooks):
```yaml
# Hook 1: Fast validation (pre-commit)
- id: validate-documentation-syntax
  name: Validate Documentation Syntax (MDX, Frontmatter, Mermaid)
  entry: python scripts/validators/validate_documentation_comprehensive.py --check=syntax
  stages: [pre-commit]

# Hook 2: Comprehensive validation (pre-push)
- id: validate-documentation-comprehensive
  name: Validate Documentation Comprehensive (ADR sync, links, integrity)
  entry: python scripts/validators/validate_documentation_comprehensive.py --all
  stages: [pre-push]
```

#### Phase 3: Update Tests to Call Validator

**Pattern**: Meta-tests validate that the comprehensive validator works correctly.

```python
# tests/test_documentation_integrity.py

def test_documentation_validation_comprehensive():
    """
    Test comprehensive documentation validation.

    NOTE: This test calls the validation script
    (scripts/validators/validate_documentation_comprehensive.py)
    instead of duplicating validation logic.
    """
    script_path = PROJECT_ROOT / "scripts" / "validators" / "validate_documentation_comprehensive.py"

    result = subprocess.run(
        [sys.executable, str(script_path)],
        capture_output=True,
        text=True,
        timeout=120,
    )

    assert result.returncode == 0, (
        f"Documentation validation failed:\n\n"
        f"{result.stdout}\n\n"
        f"Fix: Follow the recommendations in the report above"
    )
```

### Implementation Estimate

| Phase | Task | Time Estimate |
|-------|------|---------------|
| 1.1 | Create `validate_documentation_comprehensive.py` skeleton | 1 hour |
| 1.2 | Integrate existing validators (ADR, MDX, frontmatter) | 2 hours |
| 1.3 | Add new validations (orphaned files, navigation) | 2 hours |
| 1.4 | Add CLI interface and reporting | 1 hour |
| 2.1 | Update `.pre-commit-config.yaml` hooks | 30 min |
| 2.2 | Test hook integration | 30 min |
| 3.1 | Refactor `test_documentation_integrity.py` | 1 hour |
| 3.2 | Refactor `test_documentation_structure.py` | 1 hour |
| 3.3 | Run full test suite validation | 30 min |
| **TOTAL** | | **~10 hours** |

### Expected Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Hooks** | 6 hooks | 2 hooks | 67% reduction |
| **Scripts** | 7 scripts | 1 comprehensive | Single source of truth |
| **Duplicate lines** | ~300-400 | < 50 | ~90% reduction |
| **Maintenance burden** | HIGH (sync 6 places) | LOW (1 comprehensive validator) | Major simplification |

---

## Consolidation #2: GitHub Workflow Validation (HIGH PRIORITY)

### Current State

**Problem**: 4 different hooks validate GitHub workflows with overlapping concerns.

**Affected Components**:

#### Pre-commit Hooks (4 hooks):
1. `check-github-workflows` → External action (python-jsonschema/check-jsonschema) - basic YAML syntax
2. `actionlint-workflow-validation` → actionlint CLI - advanced workflow linting
3. `validate-github-workflows` → Python script (scripts/validate_github_workflows.py) - context usage validation
4. `validate-github-action-versions` → Pytest test (tests/meta/test_github_actions_validation.py) - action version validation

**Duplication Level**: ~35% overlap (100-150 lines)

### Consolidation Strategy

#### Phase 1: Separate Concerns

**Keep (Tier 1: Syntax Validation)**:
- `check-github-workflows` (basic YAML syntax)
- `actionlint-workflow-validation` (advanced linting)

**Consolidate (Tier 2: Comprehensive Validation)**:
- Merge `validate-github-workflows` + `validate-github-action-versions` into single comprehensive validator

#### Phase 2: Create Comprehensive Workflow Validator

**New Script**: `scripts/validators/validate_github_workflows_comprehensive.py`

**Features**:
```python
class GitHubWorkflowValidator:
    """Comprehensive GitHub Actions workflow validation."""

    def validate_all(self) -> ValidationResult:
        """Run all workflow validations."""
        results = []

        # Context usage (secrets.* in job-level if conditions)
        results.append(self.validate_context_usage())

        # Action versions (major version pinning, SHA pinning)
        results.append(self.validate_action_versions())

        # Permissions (GITHUB_TOKEN permissions)
        results.append(self.validate_permissions())

        # Workflow dependencies
        results.append(self.validate_dependencies())

        return ValidationResult.combine(results)

    def validate_context_usage(self) -> ValidationResult:
        """Validate GitHub context usage (existing logic)."""
        # Reuse logic from scripts/validate_github_workflows.py
        pass

    def validate_action_versions(self) -> ValidationResult:
        """Validate action version pinning (existing logic)."""
        # Reuse logic from tests/meta/test_github_actions_validation.py
        pass
```

#### Phase 3: Consolidate Hooks

**Before** (4 hooks):
```yaml
- id: check-github-workflows        # Syntax
- id: actionlint-workflow-validation # Linting
- id: validate-github-workflows     # Context usage
- id: validate-github-action-versions # Action versions
```

**After** (2 hooks):
```yaml
# Hook 1: Syntax validation (pre-commit, fast)
- id: validate-github-workflows-syntax
  name: Validate GitHub Workflows Syntax
  # Runs: check-jsonschema + actionlint
  entry: bash -c 'check-jsonschema && actionlint'

# Hook 2: Comprehensive validation (pre-push)
- id: validate-github-workflows-comprehensive
  name: Validate GitHub Workflows Comprehensive
  entry: python scripts/validators/validate_github_workflows_comprehensive.py
```

### Implementation Estimate

| Phase | Task | Time Estimate |
|-------|------|---------------|
| 1.1 | Analyze existing validators for overlap | 30 min |
| 2.1 | Create comprehensive validator skeleton | 1 hour |
| 2.2 | Integrate context usage validation | 1 hour |
| 2.3 | Integrate action version validation | 1 hour |
| 2.4 | Add CLI interface and reporting | 30 min |
| 3.1 | Update `.pre-commit-config.yaml` hooks | 30 min |
| 3.2 | Test hook integration | 30 min |
| 3.3 | Update meta-tests to call validator | 1 hour |
| **TOTAL** | | **~6 hours** |

### Expected Impact

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| **Hooks** | 4 hooks | 2 hooks | 50% reduction |
| **Scripts** | 2 scripts/tests | 1 comprehensive | Single source of truth |
| **Duplicate lines** | ~100-150 | < 30 | ~80% reduction |
| **Clarity** | Unclear separation | Clear (syntax vs comprehensive) | Better architecture |

---

## Overall Consolidation Impact

### Combined Metrics

| Metric | Current | After Consolidation | Improvement |
|--------|---------|---------------------|-------------|
| **Total Hooks** | 10 hooks | 4 hooks | 60% reduction |
| **Total Scripts** | 9 scripts/tests | 2 comprehensive | Massive simplification |
| **Duplicate Lines** | ~400-550 | < 80 | ~85% reduction |
| **Maintenance Points** | 10+ places to update | 2 validators | 80% less maintenance |

### Development Productivity Impact

**Before Consolidation**:
- Changing validation logic requires updates in 3-4 places (hook + script + test)
- High risk of inconsistency
- Unclear which validator is authoritative
- Difficult to understand validation coverage

**After Consolidation**:
- Single source of truth for each validation domain
- Clear architectural pattern (Script → Hook → Meta-test)
- Easy to extend with new validations
- Clear separation of concerns

---

## Recommended Implementation Order

### Sprint 1 (Week 1): Documentation Consolidation
**Priority**: HIGH
**Effort**: ~10 hours
**Impact**: 300-400 lines savings, 6 hooks → 2 hooks

**Rationale**: Documentation has the highest duplication (40%) and most complex overlap.

### Sprint 2 (Week 2): Workflow Consolidation
**Priority**: HIGH
**Effort**: ~6 hours
**Impact**: 100-150 lines savings, 4 hooks → 2 hooks

**Rationale**: Workflow consolidation is simpler and builds on patterns from documentation consolidation.

### Sprint 3 (Week 3): Validation & Testing
**Priority**: MEDIUM
**Effort**: ~4 hours
**Impact**: Ensure all consolidations work correctly

**Activities**:
- Run complete test suite
- Verify pre-commit/pre-push hooks
- Test CI/CD integration
- Update documentation

---

## Architecture Pattern (Established)

Following the pattern successfully applied to pytest config and ADR synchronization:

```
┌─────────────────────────────────────────────────────────┐
│ Validation Architecture Pattern                         │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Script (Source of Truth)                              │
│    ↓                                                     │
│  Pre-commit Hook (Trigger)                             │
│    ↑                                                     │
│  Meta-Test (Validator of Validator)                    │
│                                                          │
│  Benefits:                                              │
│  • Single source of truth                              │
│  • No duplicate logic                                  │
│  • Clear separation of concerns                        │
│  • Easy to maintain and extend                         │
└─────────────────────────────────────────────────────────┘
```

**Principles**:
1. **Script = Source of Truth**: Validation logic lives ONLY in scripts
2. **Hook = Trigger**: Hooks call scripts, contain minimal logic
3. **Meta-Test = Validator**: Tests verify validators work correctly (call script via subprocess)
4. **No Duplication**: Logic appears exactly once in the codebase

---

## Success Criteria

### Technical Metrics
- [ ] Total hooks reduced from 10 to 4 (60% reduction)
- [ ] Duplicate lines reduced from ~400-550 to < 80 (85% reduction)
- [ ] All tests passing after consolidation
- [ ] Pre-commit/pre-push hooks working correctly
- [ ] CI/CD pipelines unaffected

### Quality Metrics
- [ ] Clear architectural pattern followed
- [ ] Comprehensive documentation updated
- [ ] Easy to extend with new validations
- [ ] Single source of truth for each domain

### Developer Experience
- [ ] Faster pre-push hooks (less redundant validation)
- [ ] Clear error messages from consolidated validators
- [ ] Easy to understand validation coverage
- [ ] Reduced maintenance burden

---

## Risks & Mitigations

### Risk: Breaking existing workflows
**Mitigation**:
- Comprehensive testing before consolidation
- Parallel validation (old + new) during transition
- Rollback plan if issues detected

### Risk: Test failures during consolidation
**Mitigation**:
- Consolidate one validator at a time
- Run full test suite after each change
- Keep old tests alongside new until verified

### Risk: Performance degradation
**Mitigation**:
- Benchmark pre/post consolidation
- Optimize hot paths in comprehensive validators
- Cache validation results where appropriate

---

## Next Steps

1. **Review & Approval**: Get stakeholder approval for consolidation plan
2. **Sprint Planning**: Schedule documentation consolidation for Sprint 1
3. **Implementation**: Follow phased approach (1 consolidation at a time)
4. **Testing**: Comprehensive validation after each consolidation
5. **Documentation**: Update guides and architecture docs

---

## References

- [Duplicate Validator Analysis](./DUPLICATE_VALIDATOR_ANALYSIS_2025-11-16.md)
- [Codex Findings Remediation Report](./CODEX_FINDINGS_REMEDIATION_REPORT_2025-11-16.md)
- [Testing Strategy](testing/TESTING.md)

---

**Report Generated**: 2025-11-17
**Next Review**: After Sprint 1 completion
**Owner**: Infrastructure Team
