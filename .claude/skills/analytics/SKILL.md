---
name: analytics
description: Generate workflow analytics dashboard with usage statistics and ROI metrics. Use when reviewing command usage, time savings, and workflow efficiency.
argument-hint: <args>
allowed-tools:
  - Bash(git:*)
  - Bash(uv:*)
  - Read
  - Glob
  - Grep
context: fork
---
# Workflow Analytics Dashboard

**Usage**: `/analytics` or `/analytics <args>`

**Purpose**: Generate a comprehensive analytics dashboard for the Claude Code workflow optimization showing usage statistics, time savings, ROI, and recommendations.

---

## Analytics Context

**Data Sources**:
- Command usage log (`.claude/analytics/command-usage.jsonl`)
- Git commit history
- Test execution history
- Coverage reports
- Benchmark results

**Tracked Metrics**:
- Command usage frequency
- Time savings per command
- Overall ROI
- Sprint velocity
- Test pass rate
- Coverage trends

---

## Your Task

### Step 1: Generate Usage Report

Run the usage tracking script:

```bash
uv run --frozen python scripts/workflow/track-command-usage.py --report --days 30
```

### Step 2: Calculate ROI

Run the ROI calculation:

```bash
uv run --frozen python scripts/workflow/track-command-usage.py --roi
```

### Step 3: Gather Additional Metrics

**Git Metrics** (last 30 days):
```bash
# Commit count
git log --since="30 days ago" --oneline | wc -l

# Contributors
git log --since="30 days ago" --format="%an" | sort -u | wc -l

# Files changed
git log --since="30 days ago" --name-only | sort -u | wc -l

# Lines changed
git log --since="30 days ago" --numstat | awk '{add+=$1; del+=$2} END {print add, del}'
```

**Test Metrics**:
```bash
# Run tests and capture results (cross-platform using mktemp)
TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT
pytest tests/ -v --tb=no 2>&1 | tee "$TMPFILE"

# Parse pass rate
grep "passed" "$TMPFILE"
```

**Coverage Metrics**:
```bash
# Get coverage percentage (cross-platform, uses grep -oE instead of GNU-only -oP)
if [ -f "htmlcov/index.html" ]; then
    grep -oE 'pc_cov">[0-9]+' htmlcov/index.html | head -1 | grep -oE '[0-9]+'
fi
```

### Step 4: Generate Comprehensive Dashboard

Generate a box-drawn dashboard with these sections (populate from Steps 1-3):

| Section | Key Fields |
|---------|-----------|
| **Command Usage Statistics** | Total commands, unique commands, most used, highest value, total time saved |
| **Top 10 Commands by Value** | Rank, command name, uses, time saved, min/use |
| **Return on Investment (ROI)** | Investment, return (30d), ROI ratio, break-even status, projected annual, annualized ROI |
| **Development Velocity** | Commits, contributors, files changed, lines added/removed, avg commits/day |
| **Quality Metrics** | Test pass rate, coverage, mypy strict modules, open TODOs, documentation |
| **Efficiency Gains** | Per-task improvement vs baseline (sprint setup, context loading, test analysis, ADR creation, coverage analysis, debugging, deployment) |
| **Recommendations** | High impact actions, items to watch, wins to celebrate |

> For the full box-drawn dashboard template and command-specific insight templates, read [references/dashboard-templates.md](references/dashboard-templates.md).

> For trend analysis charts, actionable recommendations, and metric formulas, read [references/metric-formulas.md](references/metric-formulas.md).

---

## Notes

- **Automatic logging**: Best done via post-execution hooks
- **Privacy**: All data local, no external reporting
- **Accuracy**: Time savings are estimates, actual may vary
- **Trends**: Need >2 weeks of data for meaningful trends
- **ROI**: Measured from actual usage, not projections
