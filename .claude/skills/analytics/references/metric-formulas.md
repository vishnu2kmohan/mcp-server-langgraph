# Metric Formulas & Trend Analysis Reference

Detailed metric formulas, trend charts, actionable recommendations, update mechanism, and export/integration options for the `/analytics` skill.

---

## Step 5: Trend Analysis

Show trends over time:

```
-------------------------------------------------------------------
  USAGE TRENDS (Last 4 Weeks)
-------------------------------------------------------------------

  Weekly Command Usage
  -----------------------------------------------------------------
  120 |                                          +----*
  100 |                                    +-----+
   80 |                              +-----+
   60 |                        +-----+
   40 |                  +-----+
   20 |            +-----+
    0 +------------+------+------+------+------+-------------------->
         Week 1   Week 2  Week 3  Week 4  Week 5         weeks

  Trend: INCREASING (+28% usage growth)
  Adoption: Strong (users embracing workflow)

  -----------------------------------------------------------------
  Weekly Time Saved
  -----------------------------------------------------------------
  15h |                                          *
  12h |                                    +-----+
  10h |                              +-----+
   8h |                        +-----+
   5h |                  +-----+
   3h |            +-----+
   0h +------------+------+------+------+------+-------------------->
         Week 1   Week 2  Week 3  Week 4  Week 5         weeks

  Trend: ACCELERATING (+35% week-over-week)
  Value: Growing as adoption increases

-------------------------------------------------------------------
```

---

## Step 7: Actionable Recommendations

Based on analytics, provide specific recommendations:

```
-------------------------------------------------------------------
  ACTIONABLE RECOMMENDATIONS
-------------------------------------------------------------------

  Quick Wins (High Impact, Low Effort)
  -----------------------------------------------------------------
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

  Optimization Opportunities
  -----------------------------------------------------------------
  1. Create pre-commit hook to log command usage automatically
     Impact: Better data collection

  2. Add /analytics to weekly sprint routine
     Impact: Data-driven workflow improvements

  3. Share time savings with team
     Impact: Demonstrate ROI, encourage adoption

  Metrics to Track
  -----------------------------------------------------------------
  1. Command usage growth (target: +10%/month)
  2. Time savings per sprint (target: 8-10 hours)
  3. Coverage improvement (target: 80% by end of quarter)
  4. Type safety rollout (target: 11/11 modules strict)

-------------------------------------------------------------------
```

---

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

---

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

---

## Integration with Other Tools

- **Sprint Planning**: Include analytics in `/start-sprint`
- **Progress Reports**: Include savings in `/progress-update`
- **Retrospectives**: Review analytics for continuous improvement
- **Documentation**: Update README with actual measured savings
