---
name: todo-status
description: Generate TODO status report with git tracking and burndown analytics. Use when reviewing TODO progress, velocity, and projected completion dates.
allowed-tools:
  - Bash(git:*)
  - Read
  - Glob
  - Grep
---
# TODO Status Report (Enhanced)

**Usage**: `/todo-status` or `/todo-status --burndown`

**Purpose**: Generate comprehensive TODO status with git tracking and burndown analytics

**Features**: Git-based historical tracking, burndown chart visualization, velocity calculation, trend analysis, predicted completion dates.

---

## Step 1: Run Enhanced TODO Tracker

```bash
# Standard scan
uv run --frozen python scripts/workflow/todo-tracker.py --output ${TMPDIR:-/tmp}/todo_scan.md

# With historical tracking (recommended)
uv run --frozen python scripts/workflow/todo-tracker.py --output ${TMPDIR:-/tmp}/todo_scan.md --track-history
```

**Captures**: All TODO comments in src/ grouped by priority (CRITICAL/HIGH/MEDIUM/LOW), categorized by type, with file locations, git history of changes, and historical counts by commit.

## Step 2: Read TODO Catalog

```bash
cat docs-internal/TODO_CATALOG.md
```

**Analyzes**: Total items cataloged, items by priority/category, implementation status, deferred items.

## Step 3: Git History Analysis

Analyze TODO evolution using git.

For detailed git history scripts, velocity formulas, and historical context patterns, see [references/velocity-calculations.md](references/velocity-calculations.md).

**Metrics**: TODOs resolved per day (velocity), average resolution rate (7/14/30 days), trend direction (improving/stable/worsening), projected completion date.

## Step 4: Burndown Analysis

Generate visual burndown chart, comparison metrics, and burndown metrics.

For ASCII chart templates, comparison metrics format, burndown metrics format, and example output, see [references/burndown-templates.md](references/burndown-templates.md).

## Step 5: Generate Report

Create comprehensive status report:

```markdown
# TODO Status Report

**Generated**: YYYY-MM-DD HH:MM

## Current Status

- **TODOs in code**: X
- **Cataloged items**: Y
- **Status**: (up-to-date / new TODOs found / TODOs resolved)

## Priority Breakdown

| Priority | Count | % of Total |
|----------|-------|------------|
| CRITICAL | X | XX% |
| HIGH | Y | YY% |
| MEDIUM | Z | ZZ% |
| LOW | W | WW% |

## Category Breakdown

| Category | Count | Top Priority |
|----------|-------|--------------|
| Monitoring | X | CRITICAL |
| Compliance | Y | HIGH |
| Testing | Z | MEDIUM |
| ... | ... | ... |

## Progress Since Last Sprint

- TODOs resolved: X
- New TODOs added: Y
- Net change: Z

## Recommendations

- [Based on analysis]

## Next Sprint Focus

- Recommend tackling: [X CRITICAL, Y HIGH items]
- Estimated effort: [XX hours]
```

---

## Integration

- **Sprint planning**: Run `/todo-status` during sprint setup, use output to populate backlog
- **Progress tracking**: Run `/todo-status` mid-sprint, compare against sprint goals

**Related Commands**: `/start-sprint technical-debt` (plan sprint), `/progress-update` (track resolution)

---

**Last Updated**: 2025-10-20
