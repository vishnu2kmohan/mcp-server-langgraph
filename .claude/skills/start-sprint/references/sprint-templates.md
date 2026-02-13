# Sprint Templates Reference

Detailed templates for ultrathink analysis prompts, pre-sprint validation, sprint tracking setup, and sprint type-specific guidance.

---

## Ultrathink Analysis Prompt Templates (Step 3)

### For technical-debt sprints
```
ultrathink: Analyze all TODO items in docs-internal/TODO_CATALOG.md and recent code.
Create a comprehensive implementation plan with:
1. Categorization by priority (CRITICAL/HIGH/MEDIUM)
2. Effort estimation per item
3. Dependencies and blockers
4. Risk assessment
5. Recommended order of execution
```

### For feature sprints
```
ultrathink: Analyze the feature requirements and codebase.
Create a comprehensive technical design with:
1. Architecture approach (ADR if needed)
2. Files to modify vs create
3. Testing strategy
4. Migration/rollback plan
5. Performance and security considerations
```

### For bug-fix sprints
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

## Pre-Sprint Validation (Step 6)

Run pre-sprint checks:

```bash
# 1. Ensure all tests pass
make test-unit

# 2. Check code quality
make lint-check

# 3. Verify infrastructure (if needed)
make health-check

# 4. Check dependencies
pip check
```

**Expected**: All checks passing before starting sprint work

---

## Document Sprint Start (Step 7)

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

## Sprint Type-Specific Guidance

### Technical Debt Sprint

**Focus**:
- Resolve TODO items from catalog
- Fix technical debt
- Improve code quality

**Key Activities**:
1. Read `docs-internal/TODO_CATALOG.md`
2. Prioritize by impact and effort
3. Group related items
4. Execute in phases (CRITICAL -> HIGH -> MEDIUM)
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
- Test coverage >= 80%
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
- Documentation coverage >= 90%
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

**Last Updated**: 2025-10-20
