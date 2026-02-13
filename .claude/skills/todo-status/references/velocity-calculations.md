# Velocity Calculations & Git History Analysis

Reference material for `/todo-status` Step 3 (Git History Analysis).

---

## Git History Script

Analyze TODO evolution using git:

```bash
# Count TODOs in recent commits (last 30 days)
git log --since="30.days.ago" --all --format="%H|%ad|%s" --date=short | while IFS='|' read hash date msg; do
    count=$(git show $hash:src/ 2>/dev/null | grep -r "TODO" | wc -l)
    echo "$date|$count|$msg"
done > ${TMPDIR:-/tmp}/todo_history.txt

# Calculate velocity (TODOs resolved per day)
# Parse history and compute trend
```

---

## Velocity Formulas

### Resolution Rate (TODOs/day)

```
velocity = (start_count - current_count) / days_elapsed
```

### Windowed Averages

Calculate velocity over different time windows to detect trends:

```
velocity_7d  = (count_7_days_ago - current_count) / 7
velocity_14d = (count_14_days_ago - current_count) / 14
velocity_30d = (count_30_days_ago - current_count) / 30
```

### Acceleration

```
acceleration = velocity_7d - velocity_30d
```

- Positive acceleration: velocity is increasing (improving)
- Zero acceleration: velocity is stable
- Negative acceleration: velocity is decreasing (worsening)

### Projected Completion

```
days_remaining = current_count / velocity_7d
projected_date = today + days_remaining

# Ideal velocity (for comparison)
ideal_velocity = start_count / planned_sprint_days
ideal_days_remaining = current_count / ideal_velocity
```

### Trend Direction

Determined by comparing windowed velocities:

| Condition | Trend | Indicator |
|-----------|-------|-----------|
| `velocity_7d > velocity_30d * 1.1` | Improving | Decreasing |
| `velocity_7d < velocity_30d * 0.9` | Worsening | Increasing |
| Otherwise | Stable | Stable |

---

## Historical Context Patterns

When generating the report, identify productive periods by grouping commits:

```
Historical Context:
- [date range]: [focus area] ([N] items)
- [date range]: [focus area] ([N] items)
- [date range]: [focus area] ([N] items)
```

### Commit Analysis Metrics

- **First TODO tracked**: Earliest date in history
- **Days active**: Span from first to current date
- **Most productive day**: Date with highest single-day resolution count
- **Average per commit**: Total resolved / commits that resolved TODOs
- **TODO-resolving commits**: Count of commits that reduced TODO count / total commits

### Categorizing Commits

Group commits by category based on files changed:

| File Pattern | Category |
|-------------|----------|
| `observability/`, `monitoring/` | Monitoring |
| `auth/`, `security/`, `compliance/` | Compliance |
| `tests/`, `test_*.py` | Testing |
| `core/`, `llm/`, `execution/` | Core Features |
| `docker/`, `scripts/`, CI files | Infrastructure |
