---
name: start-sprint
description: Initialize sprint with planning, backlog creation, and tracking setup. Use when starting a new development sprint.
argument-hint: <type>
allowed-tools:
  - Bash(gh:*)
  - Bash(git:*)
  - Read
  - Glob
  - Grep
  - Write
disable-model-invocation: true
---
# Start Sprint Workflow

**Usage**: `/start-sprint <type>` or `/start-sprint $ARGUMENTS`

**Sprint Types**:
- `technical-debt` - Address TODO items and tech debt
- `feature` - Implement new features
- `bug-fix` - Fix bugs and issues
- `documentation` - Documentation improvements
- `refactoring` - Code refactoring sprint

---

## Sprint Initialization Workflow

### Step 1: Load Context

Read context files to understand current state:

```bash
cat .claude/context/recent-work.md
cat docs-internal/TODO_CATALOG.md
cat .claude/context/testing-patterns.md
cat .claude/context/code-patterns.md
```

**Analyze**: Recent commits (last 15), TODO status, test coverage, active work areas.

---

### Step 2: Create Sprint Plan

```bash
cp .claude/templates/sprint-planning.md docs-internal/SPRINT_PLAN_$(date +%Y%m%d).md
```

Fill in: Sprint Type ($ARGUMENTS), Duration (1-5 days), Primary Goal, Sprint Backlog (HIGH/MEDIUM/LOW), Success Criteria.

---

### Step 3: Perform Ultrathink Analysis

Use extended thinking based on sprint type:
- **technical-debt**: `ultrathink` - prioritize TODOs (CRITICAL/HIGH/MEDIUM), estimate effort, identify dependencies and risks
- **feature**: `ultrathink` - architecture approach, files to modify/create, testing strategy, migration/rollback plan
- **bug-fix**: `think hard` - root cause analysis, reproduction steps, fix alternatives, regression tests

For detailed analysis prompt templates per sprint type, read [references/sprint-templates.md](references/sprint-templates.md).

---

### Step 4: Create Sprint Backlog

Create detailed backlog from analysis:

| Priority | Item | Description | Est. Hours | Dependencies | Status |
|----------|------|-------------|------------|--------------|--------|
| HIGH | Item 1 | Description | 4 | None | Pending |
| HIGH | Item 2 | Description | 6 | Item 1 | Pending |
| MEDIUM | Item 3 | Description | 2 | None | Pending |

Use **TodoWrite** to track items (content, activeForm, status: "pending").

---

### Step 5: Setup Sprint Branch (Optional)

For feature sprints:
```bash
git checkout -b sprint/<type>-$(date +%Y%m%d)
git branch --show-current
```

For technical-debt/bug-fix: Work on main with frequent commits.

---

### Step 6: Pre-Sprint Validation and Sprint Tracking

Run validation checks and create tracking document. Read [references/sprint-templates.md](references/sprint-templates.md) for validation commands and tracking setup.

---

### Step 7: Sprint Type-Specific Guidance

For focus areas, key activities, and success metrics per sprint type, read [references/sprint-templates.md](references/sprint-templates.md).

---

### Step 8: Sprint Kickoff Summary

Provide user with:

```
Sprint Type: $ARGUMENTS
Duration: X days
Total Items: Y (Z high, W medium, V low)
Estimated Hours: XX

Sprint Plan: docs-internal/SPRINT_PLAN_YYYYMMDD.md
Progress Tracking: docs-internal/SPRINT_PROGRESS_YYYYMMDD.md

First Task: [Item name]
```

**Next Steps**:
1. Review sprint plan for approval
2. Adjust scope if needed
3. Begin with first HIGH priority item
4. Update progress tracking daily

For quick start examples, read [references/planning-checklists.md](references/planning-checklists.md).

---

## Related Commands

- `/progress-update` - Update sprint progress
- `/test-summary` - Generate test summary
- `/validate` - Run all validations
- `/fix-issue <number>` - Fix specific issue

---

## Notes

- **Always start with analysis** - Don't rush into coding
- **Update progress daily** - Keep tracking document current
- **Communicate blockers** - Document any blockers immediately
- **Celebrate wins** - Mark completed items promptly
- **Retrospective** - Document lessons learned at end

---

**Last Updated**: 2025-10-20
**Skill Version**: 1.0
