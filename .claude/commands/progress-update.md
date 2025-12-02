---
description: Generate comprehensive progress update for active sprint
argument-hint: <type>
---
# Generate Sprint Progress Update

**Usage**: `/progress-update` or `/progress-update <sprint-date>`

**Purpose**: Generate comprehensive progress update for active sprint

---

## 📊 Progress Update Generation

### Step 1: Identify Active Sprint

Find the most recent sprint tracking document:

```bash
# Find latest sprint progress file
ls -t docs-internal/SPRINT_PROGRESS_*.md | head -1

# Or use provided date
SPRINT_FILE=docs-internal/SPRINT_PROGRESS_$ARGUMENTS.md
```

**If no sprint file found**:
- Check if sprint was started with `/start-sprint`
- Look for sprint plan: `docs-internal/SPRINT_PLAN_*.md`
- Ask user which sprint to update

---

### Step 2: Collect Sprint Metrics

Gather current metrics from repository:

**Code Metrics**:
```bash
# Recent commits since sprint start
git log --oneline --since="$(date -d 'sprint start date' +%Y-%m-%d)" | wc -l

# Files modified
git diff --name-only <sprint-start-commit>..HEAD | wc -l

# Lines changed
git diff --stat <sprint-start-commit>..HEAD
```

**Test Metrics**:
```bash
# Run tests and capture results
pytest --collect-only -q | tail -1  # Total test count

# Run tests with verbose output
pytest -v --tb=short 2>&1 | tee /tmp/test_results.txt

# Parse results
grep -E "(passed|failed|skipped)" /tmp/test_results.txt | tail -1
```

**Coverage Metrics**:
```bash
# Generate coverage report
pytest --cov=src --cov-report=term-missing 2>&1 | grep "TOTAL"
```

**TODO Status**:
```bash
# Count remaining TODOs in source code
grep -r "TODO" src/ | wc -l

# Compare with catalog
cat docs-internal/TODO_CATALOG.md | grep -E "^(###|####)" | wc -l
```

---

### Step 3: Analyze TodoWrite Status

Check current todo list status:

**From TodoWrite tool**:
- Total items created
- Completed count
- In progress count
- Blocked count
- Pending count

**Calculate**:
- Completion rate: (completed / total) * 100%
- Velocity: completed items / days elapsed

---

### Step 4: Check Git Activity

Review git activity since sprint start:

```bash
# Commits per day
git log --since="sprint start" --pretty=format:"%ad" --date=short | sort | uniq -c

# Commit types (feat, fix, docs, test, refactor)
git log --oneline --since="sprint start" | grep -oE "^[a-z0-9]+ (feat|fix|docs|test|refactor|chore)" | cut -d' ' -f2 | sort | uniq -c

# Files most modified
git log --since="sprint start" --name-only --pretty=format: | sort | uniq -c | sort -rn | head -10
```

---

### Step 5: Assess Sprint Health

Determine sprint health based on:

**Indicators**:
| Indicator | Status | Criteria |
|-----------|--------|----------|
| On schedule | 🟢/🟡/🔴 | Completion rate vs time elapsed |
| Scope stable | 🟢/🟡/🔴 | No major scope changes |
| Quality maintained | 🟢/🟡/🔴 | Tests passing, coverage maintained |
| Blockers | 🟢/🟡/🔴 | Number of blocked items |

**Overall Health**:
- 🟢 Healthy: On track, no blockers, quality maintained
- 🟡 At Risk: Behind schedule or quality issues
- 🔴 Critical: Major blockers or significant delays

---

### Step 6: Generate Progress Report

Create or update progress tracking document:

**Include**:

1. **Sprint Overview** (updated)
   - Total items: X (Y completed, Z in progress, W pending)
   - Completion rate: XX%
   - Days elapsed: Y / Z total
   - Estimated completion: Date

2. **Completed Items** (since last update)
   - List each completed item with:
     - Priority
     - Actual hours
     - Completion timestamp
     - Related commits
     - Notes

3. **In Progress** (currently active)
   - Current item
   - Progress percentage
   - ETA
   - Next steps
   - Blockers (if any)

4. **Sprint Metrics** (updated)
   - Commits: X total
   - Files modified: Y
   - Lines added/removed: +X / -Y
   - Tests: X/Y passing (Z%)
   - Coverage: XX%

5. **Sprint Health** (assessment)
   - Overall status: 🟢/🟡/🔴
   - Health indicators (table)
   - Risks identified
   - Mitigation actions

6. **Daily Standup** (add new entry)
   - Date
   - Yesterday's accomplishments
   - Today's plan
   - Blockers
   - Metrics (hours, items, tests)

7. **Sprint Burndown** (updated)
   - Remaining hours estimate
   - Trend analysis
   - Projected completion date

---

### Step 7: Identify Issues and Recommendations

Based on metrics, identify:

**Issues**:
- Behind schedule: If completion rate < (days elapsed / total days)
- Quality degradation: If test pass rate < 95% or coverage dropped
- Scope creep: If total items increased significantly
- Blockers: List any blocked items

**Recommendations**:
- Adjust scope if behind schedule
- Focus on quality if test failures
- Address blockers immediately
- De-prioritize low-value items
- Request help if needed

---

### Step 8: Update Progress Tracking File

Write updates to sprint progress file:

```bash
# Update progress tracking document
# Location: docs-internal/SPRINT_PROGRESS_YYYYMMDD.md

# Update sections:
# - Sprint Overview (metrics)
# - Completed Items (add new completions)
# - In Progress (current status)
# - Daily Standup (new entry)
# - Sprint Health (current assessment)
# - Sprint Burndown (updated)
```

---

### Step 9: Summary Output

Provide user with summary:

```
=== Sprint Progress Update ===

Sprint: [Type] - [Date]
Status: 🟢 On Track | 🟡 At Risk | 🔴 Critical

Progress:
- Completed: X/Y items (Z%)
- In Progress: N items
- Blocked: M items (list if > 0)

Velocity:
- Items per day: X.X
- Estimated completion: YYYY-MM-DD

Recent Wins:
- [Item 1 completed]
- [Item 2 completed]

Next Focus:
- [Current/next item]

Blockers:
- [None | List blockers]

Full Report: docs-internal/SPRINT_PROGRESS_YYYYMMDD.md
```

---

## 📈 Progress Update Schedule

**Daily During Sprint**:
- End of each day
- After completing major items
- When blockers encountered
- Before daily standup (if team sprint)

**At Key Milestones**:
- 25% completion
- 50% completion (mid-sprint review)
- 75% completion
- Sprint completion

---

## 🎯 Automated Metrics Collection

**Metrics to Auto-Collect**:
1. Git commits (count, types, files changed)
2. Test results (pass/fail/skip counts)
3. Code coverage percentage
4. TODO count (source code vs catalog)
5. Lines of code (added/removed)

**Metrics to Manually Track**:
1. Hours spent (from TodoWrite actuals)
2. Blockers and resolutions
3. Quality issues encountered
4. Lessons learned

---

## 💡 Tips for Effective Progress Updates

**Be Honest**:
- Report actual status, not desired status
- Highlight blockers immediately
- Admit when behind schedule

**Be Specific**:
- List actual completed items (not "made progress")
- Quantify metrics (not "many tests added")
- Reference file names and line numbers

**Be Forward-Looking**:
- Identify next steps clearly
- Flag upcoming risks
- Adjust plans based on learnings

**Be Consistent**:
- Update at same time daily
- Use same format/template
- Track same metrics throughout sprint

---

## 🔗 Related Commands

- `/start-sprint <type>` - Initialize sprint
- `/test-summary` - Detailed test report
- `/validate` - Run all validations
- `/todo-status` - TODO catalog status (Phase 2)

---

## 📝 Example Output

```
=== Sprint Progress Update ===

Sprint: Technical Debt - 2025-10-18
Status: 🟢 On Track

Progress:
- Completed: 24/27 items (89%)
- In Progress: 0 items
- Blocked: 0 items

Velocity:
- Items per day: 24
- Sprint duration: 1 day
- Efficiency: 8x faster than estimated

Recent Wins:
- ✅ CI/CD workflows fixed
- ✅ Prometheus monitoring integrated
- ✅ Alerting system wired to all modules
- ✅ Search tools implemented

Deferred (properly documented):
- Storage backend implementation (3 items)
- Spec created: STORAGE_BACKEND_REQUIREMENTS.md

Metrics:
- Commits: 18
- Files modified: 25+
- Lines added: +2,500
- Tests: 722/727 passing (99.3%)
- Coverage: 69%

Next Steps:
1. Deploy to production
2. Schedule storage backend sprint
3. Fix remaining 5 test assertions

Full Report: docs-internal/SPRINT_PROGRESS_20251018.md
```

---

**Last Updated**: 2025-10-20
**Command Version**: 1.0
