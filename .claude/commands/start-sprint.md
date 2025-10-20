# Start Sprint Workflow

**Usage**: `/start-sprint <type>` or `/start-sprint $ARGUMENTS`

**Sprint Types**:
- `technical-debt` - Address TODO items and tech debt
- `feature` - Implement new features
- `bug-fix` - Fix bugs and issues
- `documentation` - Documentation improvements
- `refactoring` - Code refactoring sprint

---

## 📋 Sprint Initialization Workflow

### Step 1: Load Context

Read the following context files to understand current state:

```bash
# Recent work
cat .claude/context/recent-work.md

# Active TODOs
cat docs-internal/TODO_CATALOG.md

# Testing patterns
cat .claude/context/testing-patterns.md

# Code patterns
cat .claude/context/code-patterns.md
```

**Analyze**:
- Recent commits (last 15)
- Current TODO status
- Test coverage status
- Active work areas

---

### Step 2: Create Sprint Plan

Use the sprint planning template:

```bash
# Copy template to new sprint document
cp .claude/templates/sprint-planning.md docs-internal/SPRINT_PLAN_$(date +%Y%m%d).md
```

**Fill in Sprint Plan**:
1. **Sprint Type**: $ARGUMENTS (technical-debt, feature, etc.)
2. **Sprint Duration**: Based on scope (1-5 days)
3. **Primary Goal**: Clear, measurable objective
4. **Sprint Backlog**: Prioritized items (HIGH/MEDIUM/LOW)
5. **Success Criteria**: Specific, measurable criteria

---

### Step 3: Perform Ultrathink Analysis

For complex sprints, use extended thinking:

**For technical-debt sprints**:
```
ultrathink: Analyze all TODO items in docs-internal/TODO_CATALOG.md and recent code.
Create a comprehensive implementation plan with:
1. Categorization by priority (CRITICAL/HIGH/MEDIUM)
2. Effort estimation per item
3. Dependencies and blockers
4. Risk assessment
5. Recommended order of execution
```

**For feature sprints**:
```
ultrathink: Analyze the feature requirements and codebase.
Create a comprehensive technical design with:
1. Architecture approach (ADR if needed)
2. Files to modify vs create
3. Testing strategy
4. Migration/rollback plan
5. Performance and security considerations
```

**For bug-fix sprints**:
```
think hard: Analyze the bug reports and affected code.
Create a debugging and fix plan with:
1. Root cause analysis
2. Reproduction steps
3. Fix approach with alternatives
4. Test cases to prevent regression
5. Deployment strategy
```

---

### Step 4: Create Sprint Backlog

Based on analysis, create detailed backlog:

**Format**:
| Priority | Item | Description | Est. Hours | Dependencies | Status |
|----------|------|-------------|------------|--------------|--------|
| HIGH | Item 1 | Description | 4 | None | ⏸️ |
| HIGH | Item 2 | Description | 6 | Item 1 | ⏸️ |
| MEDIUM | Item 3 | Description | 2 | None | ⏸️ |

**Use TodoWrite tool** to track items:
```
Create todo items for each backlog item with:
- content: "Item description"
- activeForm: "Working on item description"
- status: "pending"
```

---

### Step 5: Setup Sprint Branch (Optional)

For feature sprints, create a feature branch:

```bash
# Create sprint branch
git checkout -b sprint/<type>-$(date +%Y%m%d)

# Verify branch
git branch --show-current
```

**For technical-debt/bug-fix**: Work on main with frequent commits

---

### Step 6: Pre-Sprint Validation

Run pre-sprint checks:

```bash
# 1. Ensure all tests pass
make test-unit

# 2. Check code quality
make lint

# 3. Verify infrastructure (if needed)
make health-check

# 4. Check dependencies
pip check
```

**Expected**: All checks passing before starting sprint work

---

### Step 7: Document Sprint Start

Create sprint tracking document:

```bash
# Copy progress tracking template
cp .claude/templates/progress-tracking.md docs-internal/SPRINT_PROGRESS_$(date +%Y%m%d).md
```

**Initialize tracking with**:
- Sprint overview (total items, dates)
- Empty completed/in-progress/blocked sections
- Baseline metrics (coverage, test count, etc.)

---

### Step 8: Sprint Kickoff Summary

Provide user with:

**Sprint Summary**:
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

---

## 📊 Sprint Type-Specific Guidance

### Technical Debt Sprint

**Focus**:
- Resolve TODO items from catalog
- Fix technical debt
- Improve code quality

**Key Activities**:
1. Read `docs-internal/TODO_CATALOG.md`
2. Prioritize by impact and effort
3. Group related items
4. Execute in phases (CRITICAL → HIGH → MEDIUM)
5. Document deferred items with rationale

**Success Metrics**:
- TODO items resolved (target: 80%+)
- Test coverage maintained or improved
- No new technical debt introduced

---

### Feature Sprint

**Focus**:
- Implement new functionality
- Comprehensive testing
- Documentation

**Key Activities**:
1. Create technical analysis (`.claude/templates/technical-analysis.md`)
2. Design API/interface
3. Implement core logic
4. Write comprehensive tests (follow `.claude/context/testing-patterns.md`)
5. Update documentation
6. Create ADR if architectural

**Success Metrics**:
- Feature implemented and tested
- Documentation complete
- Test coverage ≥ 80%
- CI/CD passing

---

### Bug-Fix Sprint

**Focus**:
- Fix reported bugs
- Add regression tests
- Root cause analysis

**Key Activities**:
1. Reproduce bugs
2. Root cause analysis
3. Fix with minimal impact
4. Add regression tests
5. Verify no other functionality broken

**Success Metrics**:
- All bugs fixed
- Regression tests added
- No new bugs introduced
- All tests passing

---

### Documentation Sprint

**Focus**:
- Improve documentation
- Update stale docs
- Create missing guides

**Key Activities**:
1. Audit existing documentation
2. Identify gaps and stale content
3. Update/create documentation
4. Verify examples work
5. Update Mintlify navigation if needed

**Success Metrics**:
- Documentation coverage ≥ 90%
- All examples working
- No broken links
- Mintlify build passing

---

### Refactoring Sprint

**Focus**:
- Improve code structure
- Reduce complexity
- Maintain functionality

**Key Activities**:
1. Identify refactoring candidates
2. Ensure comprehensive test coverage first
3. Refactor incrementally
4. Verify tests still pass
5. Update documentation

**Success Metrics**:
- Code quality improved (complexity, duplication)
- All tests still passing
- No functionality changes
- Performance maintained or improved

---

## 🎯 Quick Start Examples

### Example 1: Technical Debt Sprint
```
/start-sprint technical-debt

# Will:
1. Read TODO_CATALOG.md
2. Analyze with ultrathink
3. Create sprint plan
4. Set up tracking
5. Provide first task
```

### Example 2: Feature Sprint
```
/start-sprint feature

# Will:
1. Ask for feature description
2. Create technical analysis
3. Design implementation
4. Create sprint plan with tasks
5. Set up feature branch
```

### Example 3: Bug-Fix Sprint
```
/start-sprint bug-fix

# Will:
1. Read recent bug reports
2. Prioritize by severity
3. Create debugging plan
4. Set up tracking
5. Provide first bug to fix
```

---

## 🔗 Related Commands

- `/progress-update` - Update sprint progress
- `/test-summary` - Generate test summary
- `/validate` - Run all validations
- `/fix-issue <number>` - Fix specific issue

---

## 📝 Notes

- **Always start with analysis** - Don't rush into coding
- **Update progress daily** - Keep tracking document current
- **Communicate blockers** - Document any blockers immediately
- **Celebrate wins** - Mark completed items promptly
- **Retrospective** - Document lessons learned at end

---

**Last Updated**: 2025-10-20
**Template Version**: 1.0
