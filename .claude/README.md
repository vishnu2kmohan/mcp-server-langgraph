# Claude Code Workflow Resources

This directory contains optimized workflow resources for Claude Code sessions.

**Created**: 2025-10-20
**Purpose**: Streamline Claude Code workflows and reduce context loading time

---

## 📁 Directory Structure

```
.claude/
├── README.md                         # This file
├── WORKFLOW_OPTIMIZATION_SUMMARY.md  # Complete optimization overview
├── settings.local.json               # Claude settings (permissions)
├── templates/                        # Reusable templates
│   ├── sprint-planning.md           # Sprint initialization template
│   ├── technical-analysis.md        # Technical analysis framework
│   └── progress-tracking.md         # Sprint progress tracking
├── context/                          # Living context files
│   ├── recent-work.md               # Last 15 commits + current state
│   ├── testing-patterns.md          # All test patterns (437+ tests)
│   └── code-patterns.md             # Common code patterns
├── handoff/                          # Session continuity (Phase 3)
│   ├── last-session.md              # What we were working on
│   ├── next-steps.md                # Recommended next actions
│   └── blockers.md                  # Current blockers
└── commands/                         # Slash commands
    ├── start-sprint.md              # Initialize sprint workflow
    ├── progress-update.md           # Generate progress report
    ├── test-summary.md              # Comprehensive test analysis
    ├── validate.md                  # Run all validations (existing)
    ├── test-all.md                  # Run complete test suite (existing)
    ├── fix-issue.md                 # Fix GitHub issue (existing)
    ├── deploy-dev.md                # Development deployment (existing)
    ├── debug-auth.md                # Debug authentication (existing)
    └── setup-env.md                 # Environment setup (existing)
```

---

## 🚀 Quick Start

### Starting a New Sprint

```bash
# Use the start-sprint command
/start-sprint technical-debt

# Or manually with template
cp .claude/templates/sprint-planning.md docs-internal/SPRINT_PLAN_$(date +%Y%m%d).md
```

**What it does**:
1. Loads recent context from `context/recent-work.md`
2. Analyzes TODO_CATALOG.md with ultrathink
3. Creates sprint plan from template
4. Sets up progress tracking
5. Provides first task

### Tracking Sprint Progress

```bash
# Use the progress-update command
/progress-update

# Or manually update
cp .claude/templates/progress-tracking.md docs-internal/SPRINT_PROGRESS_$(date +%Y%m%d).md
```

**What it does**:
1. Collects git metrics (commits, files, lines)
2. Runs tests and captures results
3. Analyzes TodoWrite status
4. Assesses sprint health
5. Generates comprehensive update

### Analyzing Tests

```bash
# Use the test-summary command
/test-summary            # All tests
/test-summary unit       # Unit tests only
/test-summary integration # Integration tests
/test-summary failed     # Failed tests analysis
```

**What it does**:
1. Runs requested test scope
2. Analyzes pass/fail/skip counts
3. Calculates coverage
4. Categorizes by test type
5. Provides actionable recommendations

---

## 📚 Resource Guide

### Templates

Use these as starting points for sprint activities:

**`sprint-planning.md`** (350 lines):
- Sprint initialization checklist
- Backlog format (HIGH/MEDIUM/LOW)
- Success criteria framework
- Risk assessment matrix
- Type-specific guidance (technical-debt, feature, bug-fix, docs, refactoring)

**`technical-analysis.md`** (400 lines):
- Problem analysis framework
- Solution approach comparison (3 approaches)
- Implementation details planning
- Security and performance considerations
- Migration strategy template
- Decision documentation

**`progress-tracking.md`** (300 lines):
- Sprint overview tracking
- Completed/in-progress/blocked sections
- Sprint metrics (code, tests, quality)
- Daily standup format
- Sprint health indicators
- Burndown chart structure

### Context Files

Read these at session start for quick context:

**`recent-work.md`** (200 lines):
- Last 15 commits with categorization
- Recent sprint summary (89% success rate example)
- Recently modified files
- Current TODO status (24/30 resolved example)
- Quick wins and next sprint recommendations
- Patterns and conventions observed

**Purpose**: Provides instant understanding of what's been happening

**`testing-patterns.md`** (900 lines):
- 7 major test patterns with full examples
- Async tests, mocking, property-based, parametrized, integration, error handling
- Common mock patterns (Redis, OpenFGA, LLM, Prometheus)
- Test markers and naming conventions
- Given-When-Then structure
- Quick reference for all 437+ tests

**Purpose**: Write tests faster with proven patterns

**`code-patterns.md`** (700 lines):
- 10 core design patterns from codebase
- Pydantic settings, factory pattern, ABC with implementations
- Async context managers, feature flags, observability
- Error handling, batch operations, type-safe responses
- Coding conventions (imports, naming, docstrings, type hints)
- Common utilities

**Purpose**: Write code consistent with existing codebase

### Slash Commands

Use these for common workflows:

**New Commands**:
- `/start-sprint <type>` - Initialize sprint (types: technical-debt, feature, bug-fix, docs, refactoring)
- `/progress-update` - Generate comprehensive progress report
- `/test-summary [scope]` - Detailed test analysis (scopes: all, unit, integration, quality, failed)

**Existing Commands**:
- `/validate` - Run all validations (OpenAPI, deployments, Helm, Kustomize)
- `/test-all` - Run complete test suite with coverage
- `/fix-issue <number>` - Automated issue fixing workflow
- `/deploy-dev` - Development deployment workflow
- `/debug-auth` - Debug authentication and authorization
- `/setup-env` - Complete environment setup

---

## 💡 Usage Patterns

### Daily Development Workflow

**Morning** (Session start):
```bash
# 1. Load context
cat .claude/context/recent-work.md

# 2. Check test status
/test-summary unit

# 3. Review active sprint
cat docs-internal/SPRINT_PROGRESS_*.md
```

**During Work**:
```bash
# After each significant change
/test-summary unit

# When implementing new features
# Reference: .claude/context/code-patterns.md

# When writing tests
# Reference: .claude/context/testing-patterns.md
```

**End of Day**:
```bash
# Update sprint progress
/progress-update

# Review accomplishments
git log --oneline --since="today"
```

### Sprint Workflow

**Sprint Start**:
```bash
/start-sprint <type>
```

**During Sprint** (daily):
```bash
/progress-update
/test-summary
```

**Sprint End**:
```bash
/test-summary all
/validate
# Generate retrospective
```

---

## 🎯 Expected Benefits

### Time Savings

**Per Session**:
- Context loading: 10 min → 2 min (80% reduction)
- Test analysis: 20 min → 5 min (75% reduction)

**Per Sprint**:
- Sprint setup: 30 min → 10 min (67% reduction)
- Progress tracking: 30 min → 10 min (67% reduction)
- Documentation: 2 hrs → 1.2 hrs (40% reduction)

**Total**: 25-35% efficiency improvement

### Quality Improvements

- ✅ Consistent sprint structure
- ✅ Standardized documentation format
- ✅ Repeatable test patterns
- ✅ Complete code pattern library
- ✅ Always up-to-date context

---

## 🔄 Maintenance

### Auto-Update Context Files

**recent-work.md**:
```bash
# Run at sprint start/end or daily
git log --oneline -n 15 > /tmp/commits.txt
# Update recent-work.md with latest commits
```

**testing-patterns.md**:
```bash
# Run when new test patterns emerge
# (Phase 2: automated with scripts/analyze-test-patterns.py)
```

**code-patterns.md**:
```bash
# Run when new patterns emerge
# Manual review and update recommended
```

### Template Updates

Review and update templates when:
- New sprint types needed
- Success criteria change
- New quality gates added
- Process improvements identified

---

## 📊 Metrics

**Phase 1 Deliverables**:
- ✅ 3 templates (1,050 lines)
- ✅ 3 context files (1,800 lines)
- ✅ 3 new slash commands (1,700 lines)
- ✅ 1 comprehensive summary (350 lines)
- **Total**: 10 files, 4,900 lines

**Phase 2 (Planned)**:
- 🔄 4 automation scripts
- 🔄 5 additional slash commands
- **Total**: 9 additional files

**Phase 3 (Planned)**:
- ⏸️ 3 handoff files
- ⏸️ Additional templates
- ⏸️ Full automation

---

## 🔗 Related Documentation

- **Main Guide**: `../.github/CLAUDE.md` - Complete Claude Code integration guide
- **Optimization Summary**: `WORKFLOW_OPTIMIZATION_SUMMARY.md` - This optimization initiative
- **Testing Guide**: `../TESTING.md` - Full testing documentation
- **Developer Guide**: `../DEVELOPER_ONBOARDING.md` - Onboarding guide
- **Repository Structure**: `../REPOSITORY_STRUCTURE.md` - Project structure

---

## 📝 Contributing

To add new resources:

1. **Templates**: Add to `templates/` with descriptive filename
2. **Context**: Add to `context/` and update this README
3. **Commands**: Add to `commands/` following existing format
4. **Update**: Update `.github/CLAUDE.md` to reference new resources

---

## 🤝 Support

**Questions or Issues**:
- Check `.github/CLAUDE.md` for detailed guidance
- Review `WORKFLOW_OPTIMIZATION_SUMMARY.md` for context
- See examples in slash command files

**Feedback**:
- Document what works well
- Identify gaps or improvements needed
- Update templates based on real usage

---

**Version**: 1.0
**Last Updated**: 2025-10-20
**Status**: Phase 1 Complete ✅

🤖 **Optimized for Claude Code workflows**
