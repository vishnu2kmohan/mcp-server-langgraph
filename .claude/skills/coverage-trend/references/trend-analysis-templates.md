# Trend Analysis Templates

Reference material for coverage-trend skill: metrics definitions, goals, trend examples, and output templates.

---

## Coverage Metrics

### Overall Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| Total Coverage | 69% | 80% | On track |
| Unit Coverage | 75% | 85% | Improving |
| Integration Coverage | 62% | 75% | Improving |
| Combined Coverage | 69% | 80% | On track |

### Trend Indicators

**Improving** (Up):
- Coverage increased last 7 days
- More lines covered
- New tests added

**Stable** (Unchanged):
- Coverage unchanged (+/-1%)
- Maintaining current level

**Declining** (Down):
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

## Coverage Goals

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

## Trend Analysis Examples

### Healthy Trend

```
Coverage improving steadily:
- Oct 1: 60%
- Oct 10: 63% (+3%)
- Oct 20: 69% (+6%)
- Trend: +0.3%/day
- ETA to 80%: ~35 days
- Status: On track
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
- Status: Stable
- Action: Focus sprint on coverage improvement
```

---

## Example Output

```
=== Coverage Trend Analysis ===

Generated: 2025-10-20 14:30:00
Period: Last 30 days

Current Coverage: 69.0%
Previous (7 days ago): 67.5%
Change: +1.5%

Coverage Trend (30 Days):

75% |                                    *
    |                               *
70% |                          *
    |                     *
65% |                *              > Current: 69%
    |           *                   > 7-day avg: 68.5%
60% |      *                        > Target: 80%
    |  *
55% |
    +-------------------------------------
      Sep 20    Oct 1      Oct 15    Today

Velocity: +0.3%/day (last 7 days)
ETA to 80%: ~37 days (Nov 26, 2025)

Module Breakdown:
+----------------------------+----------+--------+
| Module                     | Coverage | Change |
+----------------------------+----------+--------+
| src/core/agent.py          |   92%    |  +2%   |
| src/auth/middleware.py     |   88%    |  +5%   |
| src/llm/factory.py         |   85%    |   0%   |
| src/api/server.py          |   78%    |  +1%   |
| src/monitoring/sla.py      |   45%    |  -3%   |
+----------------------------+----------+--------+

Coverage Gaps (Priority):
1. src/monitoring/sla.py: 45% (needs +35% for target)
2. src/schedulers/compliance.py: 52% (+28% needed)
3. src/core/parallel_executor.py: 58% (+22% needed)

Recently Improved:
- src/auth/middleware.py: +5% (excellent progress!)
- src/core/feature_flags.py: +8% (great work!)

Recommendations:
1. Maintain current velocity - on track for 80% target
2. Focus next sprint on src/monitoring/* (currently 45%)
3. Celebrate wins - 5 modules improved this week!
4. Consider adding integration tests for schedulers

Overall Status: HEALTHY TREND
Coverage improving steadily. Keep it up!

Full Reports:
- HTML: htmlcov-combined/index.html
- Trend: .coverage-history/trend.csv
- Details: ${TMPDIR:-/tmp}/coverage_trend_full.md
```

---

*Last Updated: 2025-10-20*
