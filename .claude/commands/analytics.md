---
description: You are tasked with generating a comprehensive analytics dashboard for the Claude Code workflow opti
argument-hint: <args>
---
# Workflow Analytics Dashboard

You are tasked with generating a comprehensive analytics dashboard for the Claude Code workflow optimization. This command shows usage statistics, time savings, ROI, and recommendations.

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

**Dashboard Format**:
```
╔══════════════════════════════════════════════════════════════════╗
║              WORKFLOW ANALYTICS DASHBOARD                        ║
║              Last 30 Days | Auto-Generated                       ║
╠══════════════════════════════════════════════════════════════════╣
║  COMMAND USAGE STATISTICS                                        ║
╠══════════════════════════════════════════════════════════════════╣
║  Total Commands Used:      287                                   ║
║  Unique Commands:          15                                    ║
║  Most Used:                /test-summary (45 uses)               ║
║  Highest Value:            /create-adr (40 min/use)              ║
║  Total Time Saved:         42.5 hours                            ║
╠══════════════════════════════════════════════════════════════════╣
║  TOP 10 COMMANDS BY VALUE                                        ║
╠══════════════════════════════════════════════════════════════════╣
║  1. /test-summary          45 uses │ 3.8h saved │ 5 min/use     ║
║  2. /quick-debug           38 uses │ 7.6h saved │ 12 min/use    ║
║  3. /create-adr            12 uses │ 8.0h saved │ 40 min/use ⭐ ║
║  4. /improve-coverage      8 uses  │ 6.0h saved │ 45 min/use ⭐ ║
║  5. /coverage-gaps         18 uses │ 6.0h saved │ 20 min/use ⭐ ║
║  6. /ci-status             42 uses │ 3.2h saved │ 4.5 min/use   ║
║  7. /pr-checks             15 uses │ 2.5h saved │ 10 min/use    ║
║  8. /start-sprint          2 uses  │ 0.7h saved │ 20 min/use    ║
║  9. /progress-update       6 uses  │ 2.0h saved │ 20 min/use    ║
║  10. /deploy               5 uses  │ 2.1h saved │ 25 min/use ⭐ ║
╠══════════════════════════════════════════════════════════════════╣
║  RETURN ON INVESTMENT (ROI)                                      ║
╠══════════════════════════════════════════════════════════════════╣
║  Investment:               35 hours (one-time)                   ║
║  Return (30 days):         42.5 hours                            ║
║  ROI:                      1.2x (21% return) ✅                  ║
║  Break-Even:               ACHIEVED ✅                           ║
║                                                                  ║
║  Projected Annual:         510 hours saved                       ║
║  Work Weeks Saved:         12.8 weeks                            ║
║  Annualized ROI:           14.6x                                 ║
╠══════════════════════════════════════════════════════════════════╣
║  DEVELOPMENT VELOCITY                                            ║
╠══════════════════════════════════════════════════════════════════╣
║  Commits (30d):            47                                    ║
║  Contributors:             2                                     ║
║  Files Changed:            156                                   ║
║  Lines Added:              +2,847                                ║
║  Lines Removed:            -1,234                                ║
║  Net Change:               +1,613                                ║
║  Avg Commits/Day:          1.6                                   ║
╠══════════════════════════════════════════════════════════════════╣
║  QUALITY METRICS                                                 ║
╠══════════════════════════════════════════════════════════════════╣
║  Test Pass Rate:           99.3% (722/727) ✅                    ║
║  Test Coverage:            65% → 67% (+2%) 📈                    ║
║  Mypy Strict Modules:      3/11 → 5/11 (+2) 📈                   ║
║  Open TODOs:               34 → 28 (-6) 📉                       ║
║  Documentation:            39 ADRs (complete) ✅                 ║
╠══════════════════════════════════════════════════════════════════╣
║  EFFICIENCY GAINS (vs baseline)                                  ║
╠══════════════════════════════════════════════════════════════════╣
║  Sprint Setup:             67% faster (30min → 10min)            ║
║  Context Loading:          90% faster (10min → 1min)             ║
║  Test Analysis:            75% faster (20min → 5min)             ║
║  ADR Creation:             67% faster (60min → 20min) ⭐         ║
║  Coverage Analysis:        75% faster (60min → 15min) ⭐         ║
║  Debugging:                60% faster (20min → 8min)             ║
║  Deployment:               38% faster (40min → 25min) ⭐         ║
║  Overall:                  55-65% more efficient ✅              ║
╠══════════════════════════════════════════════════════════════════╣
║  RECOMMENDATIONS                                                 ║
╠══════════════════════════════════════════════════════════════════╣
║  🔥 High Impact:                                                 ║
║    • Use /create-adr more (only 12 uses, saves 40 min each)     ║
║    • Use /improve-coverage weekly (8 uses, saves 45 min each)   ║
║    • Use /deploy for all deployments (5 uses, saves 25 min)     ║
║                                                                  ║
║  ⚠️  Watch:                                                       ║
║    • Test coverage at 67% (target: 80%)                          ║
║    • Mypy strict rollout at 45% (5/11 modules)                   ║
║                                                                  ║
║  ✅ Celebrate:                                                   ║
║    • 99.3% test pass rate (excellent!)                           ║
║    • 287 command uses (workflow is being used!)                  ║
║    • ROI achieved in < 1 month                                   ║
╚══════════════════════════════════════════════════════════════════╝
```

### Step 5: Trend Analysis

Show trends over time:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  USAGE TRENDS (Last 4 Weeks)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Weekly Command Usage
  ─────────────────────────────────────────────────────────────────
  120 ┤                                          ╭───●
  100 ┤                                    ╭─────╯
   80 ┤                              ╭─────╯
   60 ┤                        ╭─────╯
   40 ┤                  ╭─────╯
   20 ┤            ╭─────╯
    0 └────────────┴──────┴──────┴──────┴──────┴──────────────────→
         Week 1   Week 2  Week 3  Week 4  Week 5         weeks

  Trend: 📈 INCREASING (+28% usage growth)
  Adoption: Strong (users embracing workflow)

  ─────────────────────────────────────────────────────────────────
  Weekly Time Saved
  ─────────────────────────────────────────────────────────────────
  15h ┤                                          ●
  12h ┤                                    ╭─────╯
  10h ┤                              ╭─────╯
   8h ┤                        ╭─────╯
   5h ┤                  ╭─────╯
   3h ┤            ╭─────╯
   0h └────────────┴──────┴──────┴──────┴──────┴──────────────────→
         Week 1   Week 2  Week 3  Week 4  Week 5         weeks

  Trend: 📈 ACCELERATING (+35% week-over-week)
  Value: Growing as adoption increases

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 6: Command-Specific Insights

For top commands, provide insights:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  COMMAND INSIGHTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  /test-summary (Most Used)
  ─────────────────────────────────────────────────────────────────
  Uses: 45 times (16% of all commands)
  Pattern: Used before commits and PRs (good practice!)
  Value: 3.8 hours saved
  Recommendation: Continue using before every commit ✓

  /create-adr (Highest Value)
  ─────────────────────────────────────────────────────────────────
  Uses: 12 times (saves 40 min each!)
  Pattern: Used for major decisions
  Value: 8.0 hours saved
  Opportunity: Use for all architectural decisions
  Potential: Could use 2-3x more often

  /quick-debug (Best ROI)
  ─────────────────────────────────────────────────────────────────
  Uses: 38 times
  Pattern: First response to errors (excellent!)
  Value: 7.6 hours saved (12 min per use)
  Recommendation: Keep as primary debugging tool ✓

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Step 7: Actionable Recommendations

Based on analytics, provide specific recommendations:

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  ACTIONABLE RECOMMENDATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  🎯 Quick Wins (High Impact, Low Effort)
  ─────────────────────────────────────────────────────────────────
  1. Use /create-adr for all architectural decisions
     Current: 12 uses
     Potential: 25 uses/month
     Additional savings: 8.7 hours/month

  2. Run /coverage-gaps weekly
     Current: 18 uses (occasional)
     Recommended: 4 uses/month (weekly)
     Impact: Better coverage tracking

  3. Use /improve-coverage for systematic coverage improvement
     Current: 8 uses
     Recommended: 2-3 uses/sprint
     Impact: Faster progress to 80% target

  💡 Optimization Opportunities
  ─────────────────────────────────────────────────────────────────
  1. Create pre-commit hook to log command usage automatically
     Impact: Better data collection

  2. Add /analytics to weekly sprint routine
     Impact: Data-driven workflow improvements

  3. Share time savings with team
     Impact: Demonstrate ROI, encourage adoption

  📊 Metrics to Track
  ─────────────────────────────────────────────────────────────────
  1. Command usage growth (target: +10%/month)
  2. Time savings per sprint (target: 8-10 hours)
  3. Coverage improvement (target: 80% by end of quarter)
  4. Type safety rollout (target: 11/11 modules strict)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Update Mechanism

To log commands automatically, add to each slash command:

```bash
# At the end of each command execution
uv run --frozen python scripts/workflow/track-command-usage.py --log "<command-name>"
```

Example integration in `/test-summary`:
```bash
# Run tests
pytest tests/ -v

# Log usage
uv run --frozen python scripts/workflow/track-command-usage.py --log "/test-summary"
```

## Export Options

### JSON Export
```bash
# Export usage data as JSON
uv run --frozen python scripts/workflow/track-command-usage.py --report --days 30 --format json > analytics-report.json
```

### CSV Export
```bash
# Export for spreadsheet analysis
uv run --frozen python scripts/workflow/track-command-usage.py --export-csv > usage-data.csv
```

## Integration with Other Tools

- **Sprint Planning**: Include analytics in `/start-sprint`
- **Progress Reports**: Include savings in `/progress-update`
- **Retrospectives**: Review analytics for continuous improvement
- **Documentation**: Update README with actual measured savings

## Notes

- **Automatic logging**: Best done via post-execution hooks
- **Privacy**: All data local, no external reporting
- **Accuracy**: Time savings are estimates, actual may vary
- **Trends**: Need >2 weeks of data for meaningful trends
- **ROI**: Measured from actual usage, not projections

---

**Success Criteria**:
- ✅ Usage statistics displayed
- ✅ ROI calculated from actual data
- ✅ Trends visualized
- ✅ Actionable recommendations provided
- ✅ Data-driven insights generated
- ✅ Export options available
