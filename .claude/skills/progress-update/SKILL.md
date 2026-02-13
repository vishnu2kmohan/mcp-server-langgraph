---
name: progress-update
description: Generate comprehensive sprint progress update with metrics and health assessment. Use during active sprints to track and report progress.
argument-hint: <type>
allowed-tools:
  - Bash(git:*)
  - Bash(gh:*)
  - Read
  - Glob
  - Grep
---
# Generate Sprint Progress Update

**Usage**: `/progress-update` or `/progress-update <sprint-date>`

**Purpose**: Generate comprehensive progress update for active sprint

---

## Progress Update Generation

### Step 1: Identify Active Sprint

Find the most recent sprint tracking document:

```bash
ls -t docs-internal/SPRINT_PROGRESS_*.md | head -1       # Find latest
SPRINT_FILE=docs-internal/SPRINT_PROGRESS_$ARGUMENTS.md   # Or use provided date
```

**If no sprint file found**:
- Check if sprint was started with `/start-sprint`
- Look for sprint plan: `docs-internal/SPRINT_PLAN_*.md`
- Ask user which sprint to update

### Step 2: Collect Sprint Metrics

Gather current metrics from repository:

```bash
# Code metrics
git log --oneline --since="$(date -d 'sprint start date' +%Y-%m-%d)" | wc -l  # Commits
git diff --name-only <sprint-start-commit>..HEAD | wc -l                        # Files modified
git diff --stat <sprint-start-commit>..HEAD                                     # Lines changed
# Test metrics
pytest --collect-only -q | tail -1                                              # Total tests
pytest -v --tb=short 2>&1 | tee ${TMPDIR:-/tmp}/test_results.txt
grep -E "(passed|failed|skipped)" ${TMPDIR:-/tmp}/test_results.txt | tail -1
# Coverage
pytest --cov=src --cov-report=term-missing 2>&1 | grep "TOTAL"
# TODO status
grep -r "TODO" src/ | wc -l
```

### Step 3: Analyze TodoWrite Status

Check current todo list status:

**From TodoWrite tool**: Total items, completed, in progress, blocked, pending counts.

**Calculate**:
- Completion rate: (completed / total) * 100%
- Velocity: completed items / days elapsed

### Step 4: Check Git Activity

Review git activity since sprint start:

```bash
git log --since="sprint start" --pretty=format:"%ad" --date=short | sort | uniq -c  # Commits/day
git log --oneline --since="sprint start" | grep -oE "^[a-z0-9]+ (feat|fix|docs|test|refactor|chore)" | cut -d' ' -f2 | sort | uniq -c  # By type
git log --since="sprint start" --name-only --pretty=format: | sort | uniq -c | sort -rn | head -10  # Hot files
```

### Step 5: Assess Sprint Health

> Read [references/metrics-templates.md](references/metrics-templates.md) for the health indicators table, overall health criteria, and automated metrics collection guidance.

### Step 6: Generate Progress Report

Create or update progress tracking document with the following sections:
1. Sprint Overview (metrics)
2. Completed Items (since last update)
3. In Progress (currently active)
4. Sprint Metrics (updated)
5. Sprint Health (assessment)
6. Daily Standup (new entry)
7. Sprint Burndown (updated)

> Read [references/report-formats.md](references/report-formats.md) for the full report section details, field definitions, and update procedures.

### Step 7: Identify Issues and Recommendations

> Read [references/metrics-templates.md](references/metrics-templates.md) for issue detection criteria (schedule, quality, scope, blockers) and recommendation templates.

### Step 8: Update Progress Tracking File

> Read [references/report-formats.md](references/report-formats.md) for file update procedures, progress tracking file structure, and update schedule guidance.

### Step 9: Summary Output

Provide user with summary:

```
=== Sprint Progress Update ===

Sprint: [Type] - [Date]
Status: On Track | At Risk | Critical

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

## Related Commands

- `/start-sprint <type>` - Initialize sprint
- `/test-summary` - Detailed test report
- `/validate` - Run all validations
- `/todo-status` - TODO catalog status (Phase 2)

---

**Last Updated**: 2025-10-20
**Command Version**: 1.0
