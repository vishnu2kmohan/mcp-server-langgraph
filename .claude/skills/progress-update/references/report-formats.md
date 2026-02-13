# Report Formats & Progress Tracking

Reference material for full progress report sections, file update procedures, and scheduling guidance.

---

## Progress Report Sections (Step 6)

Create or update progress tracking document:

### 1. Sprint Overview (updated)
- Total items: X (Y completed, Z in progress, W pending)
- Completion rate: XX%
- Days elapsed: Y / Z total
- Estimated completion: Date

### 2. Completed Items (since last update)
- List each completed item with:
  - Priority
  - Actual hours
  - Completion timestamp
  - Related commits
  - Notes

### 3. In Progress (currently active)
- Current item
- Progress percentage
- ETA
- Next steps
- Blockers (if any)

### 4. Sprint Metrics (updated)
- Commits: X total
- Files modified: Y
- Lines added/removed: +X / -Y
- Tests: X/Y passing (Z%)
- Coverage: XX%

### 5. Sprint Health (assessment)
- Overall status: Green/Yellow/Red
- Health indicators (table)
- Risks identified
- Mitigation actions

### 6. Daily Standup (add new entry)
- Date
- Yesterday's accomplishments
- Today's plan
- Blockers
- Metrics (hours, items, tests)

### 7. Sprint Burndown (updated)
- Remaining hours estimate
- Trend analysis
- Projected completion date

---

## Update Progress Tracking File (Step 8)

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

## Progress Update Schedule

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

## Tips for Effective Progress Updates

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

*Last Updated: 2025-10-20*
