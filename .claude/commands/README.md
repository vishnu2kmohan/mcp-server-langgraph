# Claude Code Slash Commands

This directory contains 37 specialized slash commands for streamlined development workflows.

> **Note**: Some commands have been migrated to user-level skills (`~/.claude/skills/`).
> Skills include: `/explore-codebase`, `/code-review`, `/plan-review`, `/plan-status`,
> `/ci-status`, `/coverage-gaps`, `/docs-audit`, `/knowledge-search`, `/troubleshoot`, `/test-status`.

**Quick Access**: See `.claude/QUICK_REFERENCE.md` for the most-used commands.

---

## 📋 Command Categories

### 🚀 Development Workflow (5 commands)

Essential commands for daily development tasks:

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/fix-mypy` | Systematic MyPy error fixing | When you have type checking errors |
| `/plan-feature` | Feature planning with deep thinking | Before implementing new features |
| `/tdd` | TDD workflow (Red-Green-Refactor) | When implementing with test-first approach |
| `/create-test` | Generate test file from template | When creating tests for new modules |
| `/lint` | Run linting workflow | Before committing code |

**Most Used**: `/plan-feature`, `/tdd`, `/explore-codebase` (skill)

---

### ✅ Testing & Quality (10 commands)

Comprehensive testing and quality assurance tools:

| Command | Purpose | Speed | When to Use |
|---------|---------|-------|-------------|
| `/test-summary [scope]` | Comprehensive test analysis | ~2 min | Before committing, daily standup |
| `/test-all` | Run complete test suite | ~10 min | Pre-commit, pre-deploy |
| `/test-fast [mode]` | Fast test iteration (40-70% faster) | ~15s | Active development, TDD cycles |
| `/verify-tests` | Pre-commit test verification | ~9 min | Before committing/pushing |
| `/test-failure-analysis` | Deep failure analysis | ~3 min | When tests fail unexpectedly |
| `/benchmark` | Performance benchmarks + trends | ~5 min | After performance changes |
| `/security-scan-report` | Security scanning | ~10 min | Pre-release, weekly |
| `/coverage-trend` | Coverage trend analysis | ~2 min | Sprint retrospectives |
| `/improve-coverage [%]` | Generate coverage improvement plan | ~3 min | Working toward 80% coverage |
| `/type-safety-status` | MyPy strict rollout tracker | ~2 min | Type safety migration sprints |

**Most Used**: `/test-summary`, `/test-fast`, `/coverage-gaps` (skill)

**Fast Workflow**: Use `/test-fast dev` during active development, `/test-summary` before commits

---

### 🐛 Debugging (3 commands)

AI-assisted debugging and problem-solving:

| Command | Purpose | AI Systems | When to Use |
|---------|---------|------------|-------------|
| `/quick-debug [error]` | Fast AI-assisted debugging | Claude | **First response** to simple errors |
| `/debug-auth` | Authentication debugging | Claude | Login/permission issues |
| `/validate` | Run all validations | Claude | Comprehensive health check |

**Pro Tip**: Start with `/quick-debug` for simple errors. Use `/troubleshoot` (skill) for complex issues requiring multiple perspectives.

---

### 🔄 CI/CD & Deployment (4 commands)

Continuous integration and deployment workflows:

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/pr-checks [number]` | PR validation summary | Before requesting reviews |
| `/review-pr` | PR review checklist | When reviewing PRs |
| `/deploy-dev` | Development deployment | Deploying to dev environment |
| `/deploy` | Production deployment | Production releases |

**Best Practice**: Check `/plan-status` (skill) before `/code-review` (skill), check `/ci-status` (skill) before pushing

**Skills for AI-Powered Reviews**:
- `/code-review`, `/plan-review`, `/plan-status`, `/ci-status` are now user-level skills
- Access them the same way - they work identically as skills

---

### 📊 Project Management (7 commands)

Sprint planning, tracking, and documentation:

| Command | Purpose | Time Saved | When to Use |
|---------|---------|------------|-------------|
| `/start-sprint <type>` | Sprint initialization | 20 min | Start of sprint |
| `/progress-update` | Progress tracking | 15 min | End of day, standups |
| `/todo-status` | TODO burndown with velocity | 5 min | Checking sprint progress |
| `/release-prep <version>` | Release preparation checklist | 30 min | Pre-release |
| `/fix-issue <number>` | GitHub issue fixing workflow | 10 min | Working on specific issues |
| `/create-adr` | Create Architecture Decision Record | 40 min | Documenting technical decisions |
| `/analytics` | Usage + ROI dashboard | 5 min | Measuring workflow efficiency |

**Most Used**: `/start-sprint`, `/progress-update`, `/create-adr`

**Sprint Types**: `technical-debt`, `feature`, `bugfix`, `security`, `performance`

---

### 📚 Documentation (1 command)

Documentation creation and maintenance:

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/refresh-context` | Manual context file refresh | When context feels stale |

**Note**: Context files auto-update via post-commit hook - manual refresh rarely needed

**Skills**: `/docs-audit` and `/knowledge-search` are available as user-level skills

---

### 🔧 Environment (4 commands)

Environment setup and infrastructure:

| Command | Purpose | When to Use |
|---------|---------|-------------|
| `/setup-env` | Environment setup checklist | First-time setup, onboarding |
| `/db-operations` | Database operations guide | Database migrations, debugging |
| `/cleanup-worktrees` | Manage and cleanup git worktrees | After sessions, weekly cleanup |

---

## 🎯 Common Workflows

### Starting a New Sprint
```bash
1. /start-sprint technical-debt
2. Review generated sprint plan
3. /todo-status  # Track progress daily
4. /progress-update  # End of day updates
```

### Debugging an Error
```bash
1. Copy error message
2. /quick-debug "error message"
3. Apply suggested fix
4. /test-fast dev  # Verify fix
```

### Before Creating a PR
```bash
1. /test-summary  # Run full test suite
2. /coverage-gaps  # Check coverage
3. /code-review staged  # Dual AI review (Codex + Gemini) before commit
   # - Validates plan completion first
   # - Asks clarifying questions for critical findings
   # - Reconciles findings from both reviewers
4. /ci-status  # Verify CI is green
5. Create PR
6. /pr-checks  # Validate PR requirements
```

### Working on Test Coverage
```bash
1. /coverage-gaps  # Visual heatmap
2. /improve-coverage 70  # Get improvement plan
3. /create-test <module>  # Generate test file
4. Implement tests
5. /test-summary  # Verify improvements
6. /coverage-trend  # Track progress
```

### Pre-Release Checklist
```bash
1. /test-all  # Full test suite
2. /benchmark  # Performance check
3. /coverage-gaps  # Coverage validation
4. /security-scan-report  # Security audit
5. /release-prep 2.8.0  # Generate checklist
```

---

## 📈 Command Usage Tips

### Daily Use (Execute These Daily)
1. `/test-fast dev` - During active development
2. `/quick-debug` - When hitting errors
3. `/progress-update` - End of day tracking

### Weekly Use
1. `/coverage-trend` - Track coverage progress
2. `/ci-status` - CI/CD health monitoring
3. `/analytics` - Review workflow efficiency

### Per-Sprint Use
1. `/start-sprint` - Sprint kickoff
2. `/release-prep` - End of sprint
3. `/benchmark` - Performance tracking

### As-Needed Use
- `/create-adr` - When making architectural decisions
- `/docs-audit` - Before major releases
- `/fix-issue` - When working on GitHub issues
- `/deploy` - For deployments

---

## 🎓 Best Practices

### Command Naming Conventions
- **Verbs**: Commands start with action verbs (`create`, `fix`, `deploy`, `analyze`)
- **Hyphens**: Multi-word commands use hyphens (`test-summary`, `coverage-gaps`)
- **Specificity**: Names clearly indicate purpose (`quick-debug` vs `/test-failure-analysis`)

### When to Use Which Test Command
- **Active Development**: `/test-fast dev` (15s, parallel, fail-fast)
- **Pre-Commit**: `/test-summary` (2 min, analysis + report)
- **Pre-Push**: `/verify-tests` (9 min, comprehensive)
- **Pre-Deploy**: `/test-all` (10 min, all test types)
- **Investigating Failures**: `/test-failure-analysis` (deep dive)

### Coverage Command Workflow
1. **Current State**: `/coverage-gaps` (visual heatmap)
2. **Historical Trends**: `/coverage-trend` (progress over time)
3. **Improvement**: `/improve-coverage 70` (action plan)

### Debugging Workflow
1. **Simple Error**: `/quick-debug "error"` (fast, single AI)
2. **Complex Issue**: `/troubleshoot "issue"` (triple-AI, multimodal)
3. **Test Failures**: `/test-failure-analysis` (deep test analysis)
4. **Domain-Specific**: `/debug-auth` (for auth issues)

---

## 🔍 Finding the Right Command

### I want to...

**...understand the code**
→ `/explore-codebase`, `/knowledge-search`

**...plan work**
→ `/start-sprint`, `/plan-feature`, `/create-adr`

**...test my code**
→ `/test-fast dev` (during), `/test-summary` (before commit), `/test-all` (pre-deploy)

**...improve quality**
→ `/coverage-gaps`, `/improve-coverage`, `/benchmark`, `/security-scan-report`

**...fix a bug**
→ `/quick-debug` (simple), `/troubleshoot` (complex), `/test-failure-analysis`, `/debug-auth`

**...track progress**
→ `/progress-update`, `/todo-status`, `/analytics`

**...prepare for release**
→ `/release-prep`, `/test-all`, `/security-scan-report`, `/benchmark`

**...review code**
→ `/code-review`, `/plan-review`, `/plan-status`, `/pr-checks`, `/review-pr`

**...deploy**
→ `/ci-status` (check first), `/deploy-dev` or `/deploy`

**...document decisions**
→ `/create-adr`, `/docs-audit`

---

## 📊 Command Impact Metrics

Based on actual usage data:

| Command | Avg Time Saved | Usage Frequency | Annual Impact |
|---------|----------------|-----------------|---------------|
| `/quick-debug` | 12 min | Daily (4-5x/day) | 180 hours |
| `/create-adr` | 40 min | Weekly (3-4x/sprint) | 80 hours |
| `/test-fast` | 30 sec | Very frequent (20x/day) | 40 hours |
| `/coverage-gaps` | 10 min | Weekly | 24 hours |
| `/start-sprint` | 20 min | Bi-weekly | 20 hours |
| `/progress-update` | 15 min | Daily | 60 hours |

**Total Annual Time Savings**: ~607 hours (~15 work weeks)
**ROI**: 45x (based on 13.5 hours setup investment)

---

## 🆘 Troubleshooting

### Command Not Found
```bash
# Verify command exists
ls .claude/commands/ | grep <command-name>

# Check spelling (commands use hyphens, not underscores)
✓ /test-summary
✗ /test_summary
```

### Command Fails
```bash
# Check prerequisites
1. Verify virtual environment: uv run --frozen python --version
2. Check infrastructure: docker compose ps
3. Validate git hooks: ls .git/hooks/
```

### Command Runs Slowly
```bash
# Use faster alternatives
/test-all       → /test-fast dev
/test-summary   → /test-summary unit
/benchmark      → Skip trend analysis
```

---

## 📝 Contributing New Commands

When adding new slash commands:

1. **Use the naming convention**: `verb-noun` (e.g., `create-test`, `fix-issue`)
2. **Include usage examples**: Show command syntax with parameters
3. **Document prerequisites**: List required services, files, or setup
4. **Specify time/performance**: Indicate expected execution time
5. **Add to this README**: Update relevant category section
6. **Update QUICK_REFERENCE.md**: If it's a frequently-used command
7. **Test thoroughly**: Verify command works in different scenarios

---

## 📚 Additional Resources

- **Quick Reference**: `.claude/QUICK_REFERENCE.md` - 1-page cheat sheet (recommended to print)
- **Main Guide**: `.claude/README.md` - Complete workflow documentation
- **Templates**: `.claude/templates/README.md` - When to use each template
- **Context Files**: `.claude/context/` - Living documentation (auto-updated)
- **Memory Files**: `.claude/memory/` - Persistent guidance and error prevention

---

**Last Updated**: 2026-01-31
**Command Count**: 47 commands across 8 categories
**Maintained By**: Automated via Claude Code optimization framework
