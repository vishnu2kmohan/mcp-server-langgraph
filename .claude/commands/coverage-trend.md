---
description: Track test coverage trends over time and identify patterns
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

## 📊 What This Command Does

Analyzes test coverage evolution over time by:

1. Running current coverage measurement
2. Reading historical coverage data
3. Computing trends and changes
4. Identifying coverage gaps
5. Generating trend visualization

---

## 🚀 Execution Steps

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
# Total coverage percentage
CURRENT_COV=$(grep -oP 'Total coverage: \K[0-9.]+' coverage.xml || \
              coverage report --format=total 2>/dev/null || \
              echo "unknown")

# Module-level coverage
coverage report --format=markdown > /tmp/coverage_by_module.md

# Or parse HTML
grep -A 5 "Total" htmlcov-combined/index.html
```

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

### Step 5: Generate Visualization

Create ASCII trend chart:

```
Coverage Trend (Last 30 Days)

75% │                                    ●
    │                               ●
70% │                          ●
    │                     ●
65% │                ●              ↗ Current: 69%
    │           ●                   ↗ Trend: +2.3%
60% │      ●                        ↗ Target: 80%
    │  ●
55% │
    └─────────────────────────────────────
      Sep 20    Oct 1      Oct 15    Today

● Actual    ─ ─ ─ Target (80%)    ─·─ 7-day avg

Statistics:
- Current: 69.0%
- 7-day avg: 68.5%
- 30-day avg: 66.2%
- Trend: ↑ Improving (+2.3% in 30 days)
- Target: 80% (11% gap)
- ETA to target: ~45 days at current rate
```

### Step 6: Module Breakdown

Show coverage by module:

```
Module Coverage Breakdown:

┌────────────────────────────┬──────────┬────────┬───────────┐
│ Module                     │ Coverage │ Change │ Trend     │
├────────────────────────────┼──────────┼────────┼───────────┤
│ src/core/agent.py          │   92%    │  +2%   │ ↑ Up      │
│ src/auth/middleware.py     │   88%    │  +5%   │ ↑ Up      │
│ src/llm/factory.py         │   85%    │   0%   │ → Stable  │
│ src/monitoring/sla.py      │   45%    │  -3%   │ ↓ Down    │
│ src/api/server.py          │   78%    │  +1%   │ ↑ Up      │
└────────────────────────────┴──────────┴────────┴───────────┘

Coverage Gaps (< 60%):
⚠️  src/monitoring/sla.py: 45% (-3% this week)
⚠️  src/schedulers/compliance.py: 52% (new file)

Recently Improved (> +5%):
- ✅ src/auth/middleware.py: +5%
- ✅ src/core/feature_flags.py: +8%
```

---

## 📈 Coverage Metrics

### Overall Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Total Coverage | 69% | 80% | 🟡 On track |
| Unit Coverage | 75% | 85% | 🟡 Improving |
| Integration Coverage | 62% | 75% | 🟡 Improving |
| Combined Coverage | 69% | 80% | 🟡 On track |

### Trend Indicators

**Improving** ↑:
- Coverage increased last 7 days
- More lines covered
- New tests added

**Stable** →:
- Coverage unchanged (±1%)
- Maintaining current level

**Declining** ↓:
- Coverage decreased
- Code added without tests
- Tests removed

### Module Categories

**High Coverage** (> 80%):
- Core modules
- Critical paths
- Well-tested features

**Medium Coverage** (60-80%):
- Most modules
- Good test coverage
- Room for improvement

**Low Coverage** (< 60%):
- New modules
- Complex/difficult to test
- Needs attention

**Untested** (0%):
- Dead code
- Generated files
- Test utilities

---

## 🎯 Coverage Goals

### Project Targets

From project configuration:

```toml
[tool.coverage.report]
fail_under = 80.0        # Long-term target
precision = 1

[tool.coverage.run]
source = ["src"]
omit = [
    "*/tests/*",
    "*/examples/*",
    "*/__init__.py"
]
```

### Sprint Goals

Typical sprint coverage goals:

**Short-term** (1 sprint):
- +2-3% coverage increase
- Cover 1-2 low-coverage modules
- No coverage regressions

**Medium-term** (1 month):
- +5-10% coverage increase
- All modules > 60%
- Critical paths > 90%

**Long-term** (3 months):
- 80%+ total coverage
- All modules > 70%
- Critical paths > 95%

---

## 📊 Trend Analysis Examples

### Healthy Trend

```
Coverage improving steadily:
- Oct 1: 60%
- Oct 10: 63% (+3%)
- Oct 20: 69% (+6%)
- Trend: +0.3%/day
- ETA to 80%: ~35 days
- Status: ✅ On track
```

### Concerning Trend

```
Coverage declining:
- Oct 1: 70%
- Oct 10: 68% (-2%)
- Oct 20: 65% (-5%)
- Trend: -0.25%/day
- Cause: New code without tests
- Action: Add tests before new features
```

### Plateau

```
Coverage stagnant:
- Oct 1: 69%
- Oct 10: 69% (0%)
- Oct 20: 69% (0%)
- Status: → Stable
- Action: Focus sprint on coverage improvement
```

---

## 🔧 Options

### Quick Check

Just show current coverage:

```bash
coverage report --format=total
```

### Detailed Analysis

Full trend report with 30-day history:

```bash
uv run --frozen python scripts/workflow/coverage-trend-analyzer.py --days 30 --detailed
```

### Module Focus

Analyze specific module:

```bash
coverage report --include="src/auth/*"
```

### Specialized Coverage Reports

**HTML Report Only** (fastest for browsing):
```bash
make test-coverage-html
# Opens: htmlcov/index.html
```

**XML Report Only** (for CI/coverage services):
```bash
make test-coverage-xml
# Generates: coverage.xml
```

**Terminal Report Only** (quick overview):
```bash
make test-coverage-terminal
```

**Incremental Coverage** (80-90% faster):
```bash
make test-coverage-changed
```
Only tests changed code since last run using pytest-testmon.
First run tests all files, subsequent runs only test changes.

**Fast Coverage** (unit tests only, 70-80% faster):
```bash
make test-coverage-fast
```
Parallel execution, unit tests only.

---

## 💡 Coverage Improvement Strategies

### Strategy 1: Target Low-Hanging Fruit

Focus on modules with:
- Low coverage (< 60%)
- High importance (critical paths)
- Easy to test (pure functions)

### Strategy 2: Test New Code First

Enforce coverage on new code:
- Pre-commit hooks check coverage delta
- PR checks require coverage maintenance
- New files must have ≥ 80% coverage

### Strategy 3: Incremental Improvement

Add 1-2% coverage per sprint:
- Sustainable pace
- Gradual improvement
- No burnout

### Strategy 4: Delete Dead Code

Remove untested, unused code:
- Improves coverage percentage
- Reduces maintenance burden
- Cleaner codebase

---

## 📝 Example Output

```
=== Coverage Trend Analysis ===

Generated: 2025-10-20 14:30:00
Period: Last 30 days

Current Coverage: 69.0%
Previous (7 days ago): 67.5%
Change: +1.5% ✅

Coverage Trend (30 Days):

75% │                                    ●
    │                               ●
70% │                          ●
    │                     ●
65% │                ●              ↗ Current: 69%
    │           ●                   ↗ 7-day avg: 68.5%
60% │      ●                        ↗ Target: 80%
    │  ●
55% │
    └─────────────────────────────────────
      Sep 20    Oct 1      Oct 15    Today

Velocity: +0.3%/day (last 7 days)
ETA to 80%: ~37 days (Nov 26, 2025)

Module Breakdown:
┌────────────────────────────┬──────────┬────────┐
│ Module                     │ Coverage │ Change │
├────────────────────────────┼──────────┼────────┤
│ src/core/agent.py          │   92%    │  +2%   │
│ src/auth/middleware.py     │   88%    │  +5%   │
│ src/llm/factory.py         │   85%    │   0%   │
│ src/api/server.py          │   78%    │  +1%   │
│ src/monitoring/sla.py      │   45%    │  -3%   │
└────────────────────────────┴──────────┴────────┘

Coverage Gaps (Priority):
1. ⚠️  src/monitoring/sla.py: 45% (needs +35% for target)
2. ⚠️  src/schedulers/compliance.py: 52% (+28% needed)
3. ⚠️  src/core/parallel_executor.py: 58% (+22% needed)

Recently Improved:
- ✅ src/auth/middleware.py: +5% (excellent progress!)
- ✅ src/core/feature_flags.py: +8% (great work!)

Recommendations:
1. 📈 Maintain current velocity - on track for 80% target
2. 🎯 Focus next sprint on src/monitoring/* (currently 45%)
3. ✅ Celebrate wins - 5 modules improved this week!
4. 📊 Consider adding integration tests for schedulers

Overall Status: ✅ HEALTHY TREND
Coverage improving steadily. Keep it up!

Full Reports:
- HTML: htmlcov-combined/index.html
- Trend: .coverage-history/trend.csv
- Details: /tmp/coverage_trend_full.md
```

---

## 🔗 Related Commands

- `/test-summary` - Test execution summary
- `/benchmark` - Performance trends
- `/progress-update` - Sprint progress with coverage

---

## 🛠️ Troubleshooting

### Issue: No historical data

```bash
# Create coverage history tracking
mkdir -p .coverage-history
echo "$(date +%Y-%m-%d),$(coverage report --format=total)" \
  >> .coverage-history/trend.csv
```

### Issue: Coverage calculation fails

```bash
# Ensure tests have run with coverage
make test-coverage-combined

# Check coverage files exist
ls -la coverage.xml .coverage
```

### Issue: Trend shows unexpected changes

```bash
# Check what files changed
git diff HEAD~7 --stat src/

# Review new files
git diff HEAD~7 --name-status | grep "^A"
```

---

**Last Updated**: 2025-10-20
**Command Version**: 1.0
**Coverage Tool**: pytest-cov, coverage.py
**Trend Tracking**: CSV-based history in .coverage-history/
