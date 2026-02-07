---
purpose: Tool selection patterns and efficiency guidelines
priority: high
category: efficiency
last-updated: 2026-02-07
---

# Tool Selection Patterns

## Decision Matrix

| Task | Tool | Why |
|------|------|-----|
| Find files by name/pattern | `Glob` | Fast pattern matching, no content read |
| Find files by content | `Grep` | Optimized ripgrep, sandboxed |
| Read 1-5 specific files | `Read` | Direct, parallel capable |
| Explore unknown structure | `Task(Explore)` | Multi-step search agent |
| Edit 1-2 files | `Edit` | Precise, tracked changes |
| Edit 3+ files same pattern | Script via `Bash` | Bulk operation efficiency |
| Create new file | `Write` | Single operation |
| Run commands | `Bash` | System operations |

---

## Parallel Operations

### Independent Reads

```
# CORRECT - Single message, parallel execution
Read file1.py
Read file2.py
Read file3.py

# WRONG - Sequential round-trips
Read file1.py → wait → Read file2.py → wait → Read file3.py
```

### Independent Bash Commands

```
# CORRECT - Multiple Bash in single message (parallel)
Bash(timeout=300000): uv run pytest -m unit
Bash(timeout=300000): npm test

# WRONG - run_in_background + TaskOutput polling
Bash(run_in_background=true): pytest ...  # Creates orphaned notifications
```

---

## Bulk Operations

### When to Use Scripts (3+ File Threshold)

| Files | Approach |
|-------|----------|
| 1-2 | `Edit` tool |
| 3-9 | Script (single pattern) |
| 10+ | Script with validation |

### Cross-Platform Script Patterns

```bash
# Find and replace (perl, not sed)
rg -l0 -e "old_pattern" --type py | xargs -0 perl -pi -e 's/\Qold_pattern\E/new_pattern/g'

# Rename symbol with escaping
source .claude/lib/bulk_edit_utils.sh
rename_symbol "OldClass" "NewClass" py

# Update imports
update_imports "old.module.path" "new.module.path"
```

### Safety Patterns

```bash
# Preview changes first
rg -l "pattern" --type py  # See which files match

# Use -e for patterns starting with -
rg -l0 -e "-pattern" --type py

# Use \Q..\E for literal matching in perl
perl -pi -e 's/\Qexact.match\E/replacement/g'
```

---

## Script Reuse

### Before Creating New Scripts

1. **Read inventory**: `scripts/SCRIPT_INVENTORY.md` (192 scripts)
2. **Search existing**: `Glob scripts/**/*.py` or `Grep "pattern" path=scripts/`
3. **Check archived**: `scripts/archive/unused/` for reusable scripts
4. **Check hooks**: `.pre-commit-config.yaml` for existing validation

### Key Script Categories

| Category | Location | Purpose |
|----------|----------|---------|
| Validators | `scripts/validators/` | Pre-commit checks |
| Bulk fixes | `scripts/archive/unused/` | Codebase-wide fixes |
| Dev tools | `scripts/dev/` | Development utilities |
| CI/CD | `scripts/ci/` | Pipeline scripts |

---

## Context Efficiency

### Never Re-Read Pattern

```
# File read 10 messages ago
# WRONG: Read file.py  # "Let me check again..."
# CORRECT: "Based on file.py read earlier, line 25 shows..."
```

### Batch Independent Calls

```
# CORRECT - One round-trip
Glob "**/*.py"
Grep "pattern" path=src/
Read requirements.txt

# WRONG - Three round-trips
Glob "**/*.py" → wait → Grep "pattern" → wait → Read requirements.txt
```

---

## Tool-Specific Tips

### Grep

```
# Use output_mode for efficiency
Grep pattern output_mode=files_with_matches  # Just file paths
Grep pattern output_mode=content -C 3        # With context
Grep pattern output_mode=count               # Match counts

# File type filtering
Grep pattern type=py           # Python files
Grep pattern glob="*.test.ts"  # Test files
```

### Glob

```
# Specific patterns
Glob "src/**/*.py"           # All Python in src/
Glob "**/test_*.py"          # All test files
Glob "**/*.{ts,tsx}"         # TypeScript files
```

### Bash

```
# Always include timeout
Bash(timeout=60000): short_command
Bash(timeout=300000): test_suite

# Chain dependent commands
Bash: mkdir -p dir && cd dir && git init

# Parallel independent commands - multiple Bash calls in same message
```

---

## Anti-Pattern Quick Reference

| Anti-Pattern | Correct Approach |
|--------------|------------------|
| `Bash: grep -r` | `Grep` tool |
| `Bash: cat file` | `Read` tool |
| 10 sequential Edits | Script with `rg | xargs perl` |
| `run_in_background` + `TaskOutput` | Multiple blocking `Bash(timeout=)` |
| Re-reading recent files | Use context from earlier |

---

**Key Insight**: Context tokens are the scarcest resource. Choose tools that minimize round-trips and maximize parallel execution.
