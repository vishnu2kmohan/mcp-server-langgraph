# TODO Status Report

**Usage**: `/todo-status`

**Purpose**: Generate current TODO status from catalog and source code

---

## 📊 TODO Status Generation

### Step 1: Run TODO Tracker

Execute the automated TODO tracker script:

```bash
python scripts/workflow/todo-tracker.py --output /tmp/todo_scan.md
```

**Captures**:
- All TODO comments in src/
- Grouped by priority (CRITICAL/HIGH/MEDIUM/LOW)
- Categorized by type (monitoring, compliance, testing, etc.)
- File locations with line numbers

### Step 2: Read TODO Catalog

Read the current TODO catalog:

```bash
cat docs-internal/TODO_CATALOG.md
```

**Analyzes**:
- Total items cataloged
- Items by priority
- Items by category
- Implementation status
- Deferred items

### Step 3: Compare and Report

Generate comparison report:

**Metrics**:
- TODOs in source code: X
- Items in catalog: Y
- New since last catalog: Z
- Resolved since last catalog: W

**Status**:
- 🟢 Catalog up to date (source == catalog)
- 🟡 New TODOs found (source > catalog)
- 🟢 TODOs resolved (source < catalog)

### Step 4: Burndown Analysis

Calculate sprint burndown:

```
Total Remaining: X items

By Priority:
  CRITICAL: A items (target: 0)
  HIGH: B items (target: < 5)
  MEDIUM: C items (as time permits)
  LOW: D items (backlog)

Trend: ↓ Decreasing | → Stable | ↑ Increasing
```

### Step 5: Generate Report

Create comprehensive status report:

```markdown
# TODO Status Report

**Generated**: YYYY-MM-DD HH:MM

## 📊 Current Status

- **TODOs in code**: X
- **Cataloged items**: Y
- **Status**: 🟢/🟡/🔴

## 🔥 Priority Breakdown

| Priority | Count | % of Total |
|----------|-------|------------|
| CRITICAL | X | XX% |
| HIGH | Y | YY% |
| MEDIUM | Z | ZZ% |
| LOW | W | WW% |

## 📁 Category Breakdown

| Category | Count | Top Priority |
|----------|-------|--------------|
| Monitoring | X | CRITICAL |
| Compliance | Y | HIGH |
| Testing | Z | MEDIUM |
| ... | ... | ... |

## 📈 Progress Since Last Sprint

- TODOs resolved: X
- New TODOs added: Y
- Net change: Z

## 💡 Recommendations

- [Based on analysis]

## 🎯 Next Sprint Focus

- Recommend tackling: [X CRITICAL, Y HIGH items]
- Estimated effort: [XX hours]
```

---

## 🔗 Integration

**With sprint planning**:
```bash
# During sprint setup
/todo-status

# Use output to populate sprint backlog
```

**With progress tracking**:
```bash
# Mid-sprint check
/todo-status

# Compare against sprint goals
```

---

## 📝 Example Output

```
=== TODO Status Report ===

Current Status:
- TODOs in code: 6
- Cataloged items: 30
- Status: 🟢 24 TODOs resolved!

Priority Breakdown:
- CRITICAL: 0 (✅ All resolved!)
- HIGH: 3 (Storage backend items)
- MEDIUM: 2
- LOW: 1

Category Breakdown:
- Monitoring: 0 (✅ Complete)
- Compliance: 3 (Storage integration)
- Core Features: 2
- Infrastructure: 1

Progress Since Last Catalog:
- Resolved: 24 items (80%)
- New: 0 items
- Net improvement: -24 (🎉 Major cleanup!)

Recommendations:
- ✅ Excellent progress - 80% reduction
- 📋 Plan storage backend sprint for remaining 3 HIGH items
- 🎯 Target: Complete sprint in 2-3 days

Next Sprint Focus:
- 3 HIGH priority items (storage backend)
- Estimated: 14 hours (2 days)
- Sprint type: technical-debt

Full Report: /tmp/todo_scan.md
```

---

**Related Commands**:
- `/start-sprint technical-debt` - Plan sprint to address TODOs
- `/progress-update` - Track TODO resolution during sprint

---

**Last Updated**: 2025-10-20
