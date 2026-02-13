---
name: coverage-trend
description: Track test coverage trends over time. Use when you need to analyze coverage evolution, identify gaps, and measure progress toward coverage targets.
allowed-tools:
  - Bash(uv:*)
  - Bash(python3:*)
  - Read
  - Glob
  - Grep
---
# Coverage Trend Analysis

**Usage**: `/coverage-trend` or `/coverage-trend --days 30`

**Purpose**: Track test coverage trends over time and identify patterns

## Efficiency Pattern: Script Reference

For detailed analysis, use the dedicated script instead of embedded bash:
```bash
uv run --frozen python scripts/workflow/coverage-trend-analyzer.py --days 30 --detailed
```

The script handles all the parsing, trend calculation, and visualization in a single command.

---

## What This Command Does

Analyzes test coverage evolution over time by:

1. Running current coverage measurement
2. Reading historical coverage data
3. Computing trends and changes
4. Identifying coverage gaps
5. Generating trend visualization

---

## Execution Steps

### Step 1: Run Current Coverage

Execute coverage measurement:

```bash
# Run combined coverage (unit + integration)
make test-coverage-combined

# This generates:
# - htmlcov-combined/index.html (HTML report)
# - coverage.xml (XML report)
# - .coverage (raw data)
```

### Step 2: Extract Coverage Metrics

Parse coverage results:

```bash
# Total coverage percentage (cross-platform: grep -oE instead of grep -oP)
CURRENT_COV=$(grep -oE 'Total coverage: [0-9.]+' coverage.xml | grep -oE '[0-9.]+' || \
              coverage report --format=total 2>/dev/null || \
              echo "unknown")

# Module-level coverage
coverage report --format=markdown > ${TMPDIR:-/tmp}/coverage_by_module.md

# Or parse HTML
grep -A 5 "Total" htmlcov-combined/index.html
```

For detailed coverage metrics definitions and goals, see [references/trend-analysis-templates.md](references/trend-analysis-templates.md).

### Step 3: Load Historical Data

Read stored coverage history:

```bash
# Coverage history stored in .coverage-history/
# Format: YYYY-MM-DD,coverage_percentage,modules_covered

# Create if doesn't exist
mkdir -p .coverage-history

# Append current measurement
echo "$(date +%Y-%m-%d),$CURRENT_COV" >> .coverage-history/trend.csv
```

### Step 4: Calculate Trends

Analyze coverage evolution:

```bash
# Last 7 days average
tail -7 .coverage-history/trend.csv | awk -F',' '{sum+=$2; count++} END {print sum/count}'

# Last 30 days average
tail -30 .coverage-history/trend.csv | awk -F',' '{sum+=$2; count++} END {print sum/count}'

# Trend direction
# Compare last 7 days vs previous 7 days
```

For trend analysis examples (healthy, concerning, plateau), see [references/trend-analysis-templates.md](references/trend-analysis-templates.md).

### Step 5: Generate Visualization

Create ASCII trend chart:

```
Coverage Trend (Last 30 Days)

75% |                                    *
    |                               *
70% |                          *
    |                     *
65% |                *              > Current: 69%
    |           *                   > Trend: +2.3%
60% |      *                        > Target: 80%
    |  *
55% |
    +-------------------------------------
      Sep 20    Oct 1      Oct 15    Today

* Actual    - - - Target (80%)    -.- 7-day avg

Statistics:
- Current: 69.0%
- 7-day avg: 68.5%
- 30-day avg: 66.2%
- Trend: Up Improving (+2.3% in 30 days)
- Target: 80% (11% gap)
- ETA to target: ~45 days at current rate
```

For module breakdown visualization and report options, see [references/visualization-scripts.md](references/visualization-scripts.md).

For full example output, see [references/trend-analysis-templates.md](references/trend-analysis-templates.md).

---

## Related Commands

- `/test-summary` - Test execution summary
- `/benchmark` - Performance trends
- `/progress-update` - Sprint progress with coverage

---

**Last Updated**: 2025-10-20
**Command Version**: 1.0
**Coverage Tool**: pytest-cov, coverage.py
**Trend Tracking**: CSV-based history in .coverage-history/
