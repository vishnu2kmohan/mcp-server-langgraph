---
name: type-safety-status
description: Track mypy strict type checking rollout progress. Use when monitoring type safety migration, planning next module to convert, or reviewing type error patterns.
allowed-tools:
  - Bash(uv:*)
  - Read
  - Glob
  - Grep
---
# Type Safety Status Tracker

**Usage**: `/type-safety-status`

**Purpose**: Track mypy strict type checking rollout progress for the mcp-server-langgraph project. Manages the gradual migration to full type safety.

## Project Type Safety Context

**Current Status**: 3/11 core modules with strict mypy
**Target**: 11/11 modules with strict type checking
**Strategy**: Gradual rollout, module by module
**Tool**: mypy with strict mode

**Strict Mode Benefits**:
- Catch type errors before runtime
- Better IDE autocomplete
- Self-documenting code
- Easier refactoring

## Your Task

### Step 1: Analyze Current mypy Configuration

1. **Read mypy configuration**:
   ```bash
   # Check mypy config
   cat pyproject.toml | grep -A 20 "\[tool.mypy\]"
   ```

2. **Identify strict modules**:
   Look for `[[tool.mypy.overrides]]` sections with `strict = true`

3. **Count total modules**:
   ```bash
   find src/mcp_server_langgraph -name "*.py" -type f | wc -l
   ```

### Step 2: Run mypy Analysis

1. **Run mypy on all code**:
   ```bash
   uv run --frozen mypy src/mcp_server_langgraph --show-error-codes --pretty
   ```

2. **Parse mypy output**:
   - Count total errors
   - Group by error code
   - Group by file
   - Identify patterns

3. **Run mypy with strict on non-strict modules**:
   ```bash
   uv run --frozen mypy src/mcp_server_langgraph/<module>.py --strict --show-error-codes
   ```

### Step 3: Generate Type Safety Dashboard

**Dashboard Format**:
```
+==================================================================+
|              TYPE SAFETY STATUS                                    |
|              mcp-server-langgraph                                  |
+==================================================================+
|  Strict Modules:     3/11  [###.......................]  27%       |
|  Target:            11/11  [########################]  100%       |
|  Progress:            +8   [!! 8 modules remaining]               |
|  mypy Errors:         47   [XX Need fixing before strict]         |
|  Error Types:          9   [Most common: type-arg, no-untyped]    |
+------------------------------------------------------------------+
|  Trend:                ^   [+1 module/sprint]                     |
|  ETA to Full Strict: 8wk   [At current pace]                     |
+==================================================================+
```

For detailed error breakdown and common type patterns, read [references/mypy-patterns.md](references/mypy-patterns.md).

For module-by-module breakdown, migration plan, and migration checklist, read [references/migration-checklist.md](references/migration-checklist.md).

## Commands to Run

```bash
# Check current strict module status
grep -A 2 "tool.mypy.overrides" pyproject.toml | grep "strict = true" | wc -l

# Run mypy on all code
uv run --frozen mypy src/mcp_server_langgraph --show-error-codes --pretty

# Test strict mode on specific module
uv run --frozen mypy src/mcp_server_langgraph/<module>.py --strict --show-error-codes

# Check which errors are most common (cross-platform: grep -oE instead of grep -oP)
uv run --frozen mypy src/ --show-error-codes 2>&1 | grep -oE '\[[^]]+\]' | sort | uniq -c | sort -rn

# Verify migration successful
uv run --frozen pytest tests/ -v && uv run --frozen mypy src/mcp_server_langgraph --strict
```

## Integration with Other Commands

- `/lint` - Run all linters including mypy
- `/validate` - Full validation including type checking
- `/progress-update` - Include type safety in sprint progress

## Notes

- **Gradual is better** than trying to fix everything at once
- **Test after each migration** to catch regressions early
- **Commit frequently** during migration
- **Don't use Any everywhere** - that defeats the purpose
- **Type stubs** may be needed for third-party libraries

---

**Success Criteria**:
- Current strict status displayed
- Remaining modules identified
- Migration plan with priorities
- Error breakdown and common patterns
- Detailed checklist for next module
- Commands to run for migration
