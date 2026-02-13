---
name: fix-mypy
description: Fix MyPy type checking errors systematically. Use when mypy reports type errors and you need to fix them module by module.
allowed-tools:
  - Bash(uv:*)
  - Read
  - Glob
  - Grep
  - Edit
---
# Fix MyPy Type Errors

Systematic workflow for fixing MyPy type checking errors in the codebase.

## Usage

```bash
/fix-mypy
```

## Current Status

- **MyPy**: Currently DISABLED in pre-commit due to 145+ errors
- **Goal**: 0 errors (100% type safety), enable strict type checking
- **Checklist**: `.github/checklists/TYPE_SAFETY_MIGRATION.md`

## Quick Start

```bash
# See all errors
mypy src/ --show-error-codes

# Check specific module
mypy src/mcp_server_langgraph/core/config.py

# Save errors to file
mypy src/ --show-error-codes > mypy_errors.txt
```

## Systematic Fix Workflow

### Phase 1: Categorize Errors

```bash
mypy src/ --show-error-codes > mypy_errors.txt
cat mypy_errors.txt | grep "error:" | cut -d: -f4 | cut -d'[' -f2 | cut -d']' -f1 | sort | uniq -c | sort -rn
```

For error type explanations and fix examples, see [references/type-error-catalog.md](references/type-error-catalog.md).

### Phase 2: Fix by Module (Incremental)

**Fix ONE module at a time**:

```bash
# 1. Pick a module
mypy src/mcp_server_langgraph/core/config.py

# 2. Fix errors one by one
# 3. Run tests after each fix
pytest tests/test_config.py -xvs

# 4. Commit when module is clean
git add src/mcp_server_langgraph/core/config.py
git commit -m "fix(types): add type hints to core/config.py"
```

For common type hints, type stubs, and ignore patterns, see [references/fix-patterns.md](references/fix-patterns.md).

### Phase 3: Validate Progress

```bash
# Count remaining errors
mypy src/ --show-error-codes 2>&1 | grep "error:" | wc -l

# Track progress
echo "Baseline: 145 errors"
echo "Current: $(mypy src/ --show-error-codes 2>&1 | grep 'error:' | wc -l) errors"
```

## MyPy Configuration

Current config in `pyproject.toml`:

```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = false  # TODO: Enable after fixing errors
ignore_missing_imports = true  # TODO: Add type stubs for libraries
```

**Target config** (after fixes):

```toml
[tool.mypy]
python_version = "3.12"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true   # Enable strict mode
ignore_missing_imports = false  # Require type stubs
strict = true                   # Maximum strictness
```

## Validation Commands

```bash
mypy src/                                        # Basic check
mypy src/ --show-error-codes                     # With error codes
mypy src/ --strict                               # Strict mode
mypy src/ --html-report mypy-report              # HTML report
mypy src/mcp_server_langgraph/core/config.py     # Specific module
```

## Progress Tracking

```bash
/type-safety-status                              # Slash command

# Manual
mypy src/ --show-error-codes 2>&1 | grep "error:" | wc -l
mypy src/ --show-error-codes 2>&1 | grep "error:" | cut -d'[' -f2 | cut -d']' -f1 | sort | uniq -c | sort -rn
```

## Resources

- **MyPy Documentation**: https://mypy.readthedocs.io/
- **PEP 484** (Type Hints): https://peps.python.org/pep-0484/
- **Python Typing Module**: https://docs.python.org/3/library/typing.html
- **Error Catalog**: [references/type-error-catalog.md](references/type-error-catalog.md)
- **Fix Patterns**: [references/fix-patterns.md](references/fix-patterns.md)

---

**Goal**: Enable MyPy in pre-commit hooks after fixing all 145+ errors.
