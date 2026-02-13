# Burndown Templates & Example Output

Reference material for `/todo-status` Step 4 (Enhanced Burndown Analysis).

---

## Enhanced Burndown Analysis

### ASCII Burndown Chart

Generate visual ASCII burndown chart:

```bash
# Generate burndown visualization
uv run --frozen python scripts/workflow/generate-burndown.py --days 30 --output ${TMPDIR:-/tmp}/burndown.txt
```

**Burndown Chart** (ASCII visualization):
```
TODOs Over Time (Last 30 Days)

30 |                                *
   |                           *
25 |                      *
   |                 *
20 |            *
   |       *
15 |  *
   |*
10 |
   +-------------------------------------
     Oct 1      Oct 15      Oct 20   Today

* Actual    - - - Ideal Burndown    --- Target

Current: 6 TODOs
Started: 30 TODOs (Oct 1)
Resolved: 24 TODOs (80%)
Velocity: 1.2 TODOs/day
ETA: Oct 25 (5 days)
```

### Comparison Metrics

- TODOs in source code: X (current)
- Items in catalog: Y (documented)
- New since last scan: Z
- Resolved since last scan: W

**Status Indicators**:
- Catalog up to date (source == catalog)
- New TODOs found (source > catalog)
- TODOs resolved (source < catalog)

### Burndown Metrics

```
Total Remaining: X items
Started with: Y items (Z days ago)
Resolved: W items (resolution rate: N%)

By Priority:
  CRITICAL: A items (target: 0, current progress: X%)
  HIGH: B items (target: < 5, current progress: Y%)
  MEDIUM: C items (as time permits)
  LOW: D items (backlog)

Velocity:
  Last 7 days: X.X TODOs/day
  Last 14 days: Y.Y TODOs/day
  Last 30 days: Z.Z TODOs/day

Trend: Decreasing (-24 in 30 days) | Stable | Increasing

Projected Completion:
  At current velocity: YYYY-MM-DD (N days remaining)
  At ideal velocity: YYYY-MM-DD (M days remaining)
```

---

## Example Output (Enhanced)

```
=== TODO Status Report (Enhanced) ===

Generated: 2025-10-20 14:30:00
Tracking Mode: Git History Enabled

Current Status:
- TODOs in code: 6
- Cataloged items: 30
- Status: 24 TODOs resolved! (80% reduction)

Burndown Chart (Last 30 Days):

30 |                                *
   |                           *
25 |                      *
   |                 *
20 |            *
   |       *
15 |  *
   |*                        * * * <- Current: 6
10 |
   +-------------------------------------
     Oct 1      Oct 15      Oct 20   Today

Velocity Analysis:
- Resolution rate: 1.2 TODOs/day (last 20 days)
- Acceleration: +0.3 TODOs/day (improving!)
- Projected completion: Oct 25 (5 days at current rate)

Priority Breakdown:
- CRITICAL: 0 (All resolved! -18 from start)
- HIGH: 3 (Storage backend items, -9 from start)
- MEDIUM: 2 (-5 from start)
- LOW: 1 (-2 from start)

Category Breakdown:
- Monitoring: 0 (Complete, was 8)
- Compliance: 3 (Storage integration, was 10)
- Core Features: 2 (was 5)
- Infrastructure: 1 (was 4)

Git History Insights:
- First TODO tracked: Oct 1, 2025
- Days active: 20 days
- Most productive day: Oct 18 (15 TODOs resolved)
- Average per commit: 0.9 TODOs resolved
- Commits resolving TODOs: 18/256 (7%)

Progress Since Last Scan:
- Resolved: 24 items (80%)
- New: 0 items
- Net improvement: -24 (Major cleanup!)
- Velocity trend: Accelerating (from 0.8 to 1.2 per day)

Quality Metrics:
- Test coverage maintained: 69%
- No new TODOs added
- All CRITICAL items resolved

Recommendations:
- Excellent progress - 80% reduction achieved
- Velocity increasing - maintain momentum
- Plan storage backend sprint for remaining 3 HIGH items
- Target: Complete sprint in 2-3 days (achievable at current rate)
- Current velocity supports Oct 25 completion

Next Sprint Focus:
- 3 HIGH priority items (storage backend)
- Estimated: 14 hours (2 days)
- Sprint type: technical-debt
- Success criteria: All HIGH items resolved
- Stretch goal: Clear MEDIUM items too

Historical Context:
- Oct 1-10: Monitoring focus (8 items)
- Oct 11-18: Compliance sprint (7 items)
- Oct 19-20: Mixed cleanup (9 items)

Full Reports:
- Current scan: ${TMPDIR:-/tmp}/todo_scan.md
- Burndown chart: ${TMPDIR:-/tmp}/burndown.txt
- Git history: ${TMPDIR:-/tmp}/todo_history.txt
```
