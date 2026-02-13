# Visualization Scripts & Options

Reference material for coverage-trend skill: module breakdown visualization, report options, improvement strategies, and troubleshooting.

---

## Module Breakdown

Show coverage by module:

```
Module Coverage Breakdown:

+----------------------------+----------+--------+-----------+
| Module                     | Coverage | Change | Trend     |
+----------------------------+----------+--------+-----------+
| src/core/agent.py          |   92%    |  +2%   | Up        |
| src/auth/middleware.py     |   88%    |  +5%   | Up        |
| src/llm/factory.py         |   85%    |   0%   | Stable    |
| src/monitoring/sla.py      |   45%    |  -3%   | Down      |
| src/api/server.py          |   78%    |  +1%   | Up        |
+----------------------------+----------+--------+-----------+

Coverage Gaps (< 60%):
  WARNING src/monitoring/sla.py: 45% (-3% this week)
  WARNING src/schedulers/compliance.py: 52% (new file)

Recently Improved (> +5%):
- src/auth/middleware.py: +5%
- src/core/feature_flags.py: +8%
```

---

## Options

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

## Coverage Improvement Strategies

### Strategy 1: Target Low-Hanging Fruit

Focus on modules with:
- Low coverage (< 60%)
- High importance (critical paths)
- Easy to test (pure functions)

### Strategy 2: Test New Code First

Enforce coverage on new code:
- Pre-commit hooks check coverage delta
- PR checks require coverage maintenance
- New files must have >= 80% coverage

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

## Troubleshooting

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

*Last Updated: 2025-10-20*
