# Claude Code Integration Guide

**Purpose**: Quick start guide for using Claude Code with MCP Server LangGraph
**Comprehensive Documentation**: See `.claude/` directory for complete resources

---

## 🚀 Quick Start

### For New Claude Code Sessions

1. **Load mandatory context** (prevents common errors):
   ```bash
   # Read these FIRST in every session
   cat .claude/memory/python-environment-usage.md  # CRITICAL: Always use .venv
   cat .claude/memory/validation-strategy.md       # Hooks and validation reference
   cat .claude/memory/make-targets.md              # 161 Make targets reference
   ```

2. **Load project context** (understand recent work):
   ```bash
   cat .claude/context/recent-work.md             # Last 15 commits, sprint summary
   cat .claude/README.md                          # Complete workflow guide
   ```

3. **Use slash commands** for common workflows:
   ```bash
   /start-sprint <type>    # Initialize sprint with context
   /test-summary          # Analyze test suite
   /quick-debug <error>   # AI-assisted debugging
   /validate              # Run all validations
   ```

---

## 📚 Complete Documentation Structure

### `.claude/` Directory Organization

```
.claude/
├── README.md                          # 📖 Complete workflow automation guide
├── QUICK_REFERENCE.md                 # 📄 1-page command cheat sheet
├── SETTINGS.md                        # ⚙️ Configuration architecture
│
├── commands/                          # 44 slash commands (organized)
│   └── README.md                      # Command discovery guide
│
├── templates/                         # 8 professional templates
│   └── README.md                      # Template selection guide
│
├── context/                           # Living context files
│   ├── recent-work.md                 # Last 15 commits (auto-updated)
│   ├── testing-patterns.md            # 20,000+ test patterns
│   ├── code-patterns.md               # Design patterns library
│   ├── pytest-markers.md              # 168 markers catalog
│   ├── xdist-safety-patterns.md       # Memory safety (NEW)
│   └── test-constants-pattern.md      # Centralized constants (NEW)
│
└── memory/                            # Persistent guidance (MANDATORY)
    ├── python-environment-usage.md    # CRITICAL: Always use .venv
    ├── validation-strategy.md         # Consolidated hooks/validation reference
    ├── task-spawn-error-prevention-strategy.md  # Error patterns & solutions
    └── make-targets.md                # 161 Make targets reference
```

**Total**: 62+ files, ~20,000 lines of documentation & automation

---

## 🎯 Project Overview

### Architecture

**Technology Stack**:
- **Framework**: LangGraph >=1.0.4 (conversation state management)
- **Frontend**: Agent Studio (React 18 + Redux Toolkit + RTK Query + Vite)
- **LLM Support**: Multi-provider (OpenAI, Anthropic, Google Vertex AI, Azure)
- **Vertex AI**: Claude + Gemini via Workload Identity Federation (keyless auth)
- **Auth**: Keycloak SSO + OpenFGA authorization + DPoP token binding
- **Storage**: PostgreSQL + Redis (langgraph-checkpoint-redis for distributed state)
- **Execution**: Docker/Kubernetes sandbox code execution engine
- **Observability**: OpenTelemetry + Prometheus + Grafana
- **Deployment**: Kubernetes (Helm + Kustomize)

### Project Structure

```
mcp-server-langgraph/
├── src/mcp_server_langgraph/    # Main package
│   ├── core/                     # Agent, config, feature flags
│   ├── auth/                     # Authentication & authorization
│   ├── llm/                      # LLM factory & validators
│   ├── mcp/                      # MCP server implementations
│   ├── observability/            # Telemetry & metrics
│   ├── secrets/                  # Secrets management
│   ├── studio/                   # Agent Studio frontend (React + Redux)
│   ├── execution/                # Sandboxed code execution engine
│   └── security/                 # Prompt injection protection
├── tests/                        # 20,000+ comprehensive tests
├── deployments/                  # Kubernetes, Helm, Kustomize
├── monitoring/                   # Grafana dashboards
└── .claude/                      # Workflow automation
```

**Test Suite**: 20,000+ tests, 168 pytest markers, 99.3% pass rate
**Coverage**: 75% (targeting 80%+)

---

## Workflow Automation

### Efficiency Gains

**Measured Results**:
- **Time Saved**: 607 hours/year (~15 work weeks)
- **Efficiency**: 45-50% workflow improvement
- **ROI**: 45x return on investment

### Key Resources

1. **Commands** (`.claude/commands/`): 44 slash commands
   - `/start-sprint` - Sprint initialization
   - `/test-summary` - Detailed test analysis
   - `/quick-debug` - AI-assisted debugging
   - `/validate` - Complete validation
   - See `.claude/commands/README.md` for all commands

2. **Templates** (`.claude/templates/`): 8 professional templates
   - ADR template (650 lines) - 67% faster
   - API design template (1,400 lines) - 67% faster
   - Bug investigation template (1,250 lines) - 50% faster
   - See `.claude/templates/README.md` for all templates

3. **Context** (`.claude/context/`): Living documentation
   - Auto-updated from git history
   - Test patterns from 20,000+ tests
   - Design patterns from codebase
   - **NEW**: pytest markers, xdist safety, test constants

4. **Memory** (`.claude/memory/`): Persistent guidance (5 files)
   - Python environment usage (MANDATORY)
   - Lint workflow enforcement
   - Task spawn error prevention
   - Pre-commit hooks catalog (95 hooks)
   - Make targets guide (161 targets)

---

## Git Worktree Sessions (Isolated Work)

**NEW**: This project now supports automated git worktree creation for isolated Claude Code sessions.

### Why Use Worktrees?

Git worktrees allow you to have multiple working directories from the same repository, providing:
- **Session isolation**: Each Claude Code session works in its own directory
- **Branch safety**: No conflicts between concurrent work
- **Clean state**: Each session starts fresh from a base branch
- **Easy cleanup**: Auto-delete when no uncommitted changes

### Quick Start

**Starting a New Session**:
```bash
# Launch Claude Code in a new isolated worktree
./scripts/start-worktree-session.sh

# Or specify a different base branch
./scripts/start-worktree-session.sh feature-branch
```

This automatically:
1. Creates worktree in `../worktrees/mcp-server-langgraph-session-YYYYMMDD-HHMMSS/`
2. Based on your current branch (or specified branch)
3. Launches Claude Code in the new worktree
4. Sets up session tracking metadata

**During Session**:
- Claude Code detects worktree and shows session info at startup
- Work normally - all changes are isolated to the worktree
- Commit and push as usual

**Ending Session**:
- Exit Claude Code normally
- If worktree is clean (no uncommitted changes), prompted to delete
- Otherwise, worktree is preserved for later

**Manual Cleanup**:
```bash
# List all worktrees and cleanup options
./scripts/cleanup-worktrees.sh

# Auto-delete all clean worktrees
./scripts/cleanup-worktrees.sh --auto

# Preview without deleting
./scripts/cleanup-worktrees.sh --dry-run

# From within Claude Code
/cleanup-worktrees
```

### Worktree Detection

When running in a worktree, Claude Code automatically displays:
```
🌳 Git Worktree Session Active
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  SESSION_ID=mcp-server-langgraph-session-20250115-143022
  BASE_BRANCH=main
  CREATED_AT=20250115-143022
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Best Practices

**Use worktrees for**:
- ✅ Experimental features
- ✅ Bug investigation
- ✅ Major refactoring
- ✅ Testing different approaches
- ✅ Working on multiple issues simultaneously

**Don't use worktrees for**:
- ❌ Quick single-file edits (overhead not worth it)
- ❌ Documentation-only changes
- ❌ When you need to switch branches frequently (just use git switch)

### Troubleshooting

**Issue**: Worktree creation fails
- **Cause**: Branch doesn't exist or uncommitted changes in main repo
- **Solution**: Commit or stash changes first, verify branch exists

**Issue**: Can't delete worktree
- **Cause**: Worktree is locked or has uncommitted changes
- **Solution**:
  ```bash
  # Unlock and try again
  git worktree unlock /path/to/worktree
  ./scripts/cleanup-worktrees.sh --auto
  ```

**Issue**: Too many worktrees accumulating
- **Cause**: Not cleaning up after sessions
- **Solution**: Run cleanup regularly
  ```bash
  # Weekly cleanup of all clean worktrees
  ./scripts/cleanup-worktrees.sh --auto
  ```

---

## 🎨 Agent Studio (NEW)

### Overview

Unified frontend for AI agent development with visual workflow builder and real-time interaction:

**Features**:
- **Visual Workflow Builder**: Interactive agent graph design with React Flow
- **Real-time Streaming Chat**: Live conversation with agents
- **In-context Observability**: Embedded metrics and trace visualization
- **State Management**: Redux Toolkit + RTK Query for optimized data flow
- **Code Execution**: Sandboxed Python/JavaScript execution in Docker/Kubernetes
- **Security**: Prompt injection protection with content filtering

**Access**:
```bash
# Start the development server
make run-studio

# Access Agent Studio
http://localhost:8000/studio
```

**Architecture**:
- **Frontend**: React 18 + TypeScript + Vite
- **State**: Redux Toolkit with RTK Query for API caching
- **UI Components**: Shadcn/ui + Tailwind CSS
- **Visualization**: React Flow for graph editing
- **Backend API**: FastAPI with SSE for streaming

**Key Routes**:
- `/studio` - Main dashboard
- `/studio/agents` - Agent management
- `/studio/chat` - Interactive chat interface
- `/studio/traces` - Observability traces
- `/studio/workflows` - Workflow editor and management

**Development**:
```bash
# Install frontend dependencies
cd src/mcp_server_langgraph/studio/frontend
npm install

# Start development server with hot reload
npm run dev

# Build for production
npm run build

# Run frontend tests
npm test
```

**Integration with Backend**:
- WebSocket connections for real-time streaming
- RTK Query for automatic cache invalidation
- OpenTelemetry integration for distributed tracing
- Keycloak SSO for authentication

---

## 🔄 Recommended Workflow

**CRITICAL**: Always follow the Explore → Plan → Code → Commit workflow

**Complete Guide**: See `.github/CLAUDE.md` sections below for detailed workflow
**Quick Reference**: TDD principles in `~/.claude/CLAUDE.md` (global)

### Phase 1: EXPLORE (Research First) 🔍

**DO NOT jump to coding immediately**. Understanding the codebase is prerequisite to making good changes.

**Required Actions**:
1. **Read existing code**: Use `Read` and `Grep` tools to understand current implementation
2. **Review ADRs**: Check `/adr/` directory for architectural decisions (101 ADRs documented)
3. **Check tests**: Look at test files in `/tests/` to understand expected behavior
4. **Search for patterns**: Use `grep -r "pattern" src/` to find similar implementations
5. **Ask questions**: Clarify requirements before proposing solutions

**Success Criteria**:
- ✅ Read 5-10 related files minimum
- ✅ Identified existing patterns to follow
- ✅ Understood test coverage expectations
- ✅ Reviewed relevant ADRs (if architectural change)
- ✅ Can explain current implementation in detail

**Example - GOOD Exploration**:
```bash
User: "Add caching to the API endpoints"

Claude (Exploring first):
"Let me first understand the existing caching strategy:
1. Reading core/cache.py to see current implementation
2. Checking if OpenTelemetry metrics exist for cache hits/misses
3. Reading ADR-0030 (Resilience Patterns) for caching guidance
4. Examining tests/test_cache.py to understand test patterns
5. Searching for existing cache decorators: grep -r '@cache' src/

[After research]
I found you already have L1/L2 caching with Redis. Your current implementation uses..."
```yaml
**Example - BAD (Skipped Exploration)**:
```yaml
User: "Add caching to the API endpoints"

Claude (Jumping to code):
"I'll add Redis caching to the API endpoints..."
[Starts implementing without understanding existing patterns]
```python
### Phase 2: PLAN (Think Before Acting) 🧠

**Create a detailed plan** using the `TodoWrite` tool BEFORE writing any code.

**Required Actions**:
1. **Use TodoWrite**: Create task breakdown with 5-10 specific tasks
2. **Identify tests**: List which tests need to be written FIRST (TDD!)
3. **Consider edge cases**: Document error scenarios, validation, boundaries
4. **Estimate complexity**: Simple fix, moderate feature, or complex change?
5. **Get approval**: Wait for explicit user approval before proceeding

**Planning Depth** (use thinking keywords):
- **Simple bug fix**: Default thinking
- **New feature**: `"think hard"` - deeper analysis required
- **Complex feature**: `"think harder"` - comprehensive multi-angle analysis
- **Architectural change**: `"ultrathink"` - exhaustive analysis with alternatives

**Success Criteria**:
- ✅ Todo list created with specific, actionable tasks
- ✅ Tests identified and will be written FIRST (TDD compliance)
- ✅ Edge cases and error scenarios documented
- ✅ User explicitly approved the plan

**Example - GOOD Planning**:
```python
User: "Implement rate limiting for API endpoints"

Claude (Planning with TodoWrite):
[Creates comprehensive todo list:]
1. Write tests for rate limiting (RED phase: test 429 responses, reset headers)
2. Research existing rate limit middleware in auth/ directory
3. Implement RateLimitMiddleware with Redis backend
4. Add OpenTelemetry metrics (rate_limit_exceeded counter, rate_limit_remaining gauge)
5. Update deployment configs with RATE_LIMIT_* environment variables
6. Add configuration to core/config.py
7. Document in ADR-0055 (Rate Limiting Strategy)
8. Run integration tests
9. Update CHANGELOG.md

Estimated effort: 4-6 hours
Risk: Medium (new middleware, requires Redis)
[Waits for user approval before coding]
```yaml
**Example - BAD (No Planning)**:
```yaml
User: "Implement rate limiting"

Claude (No plan):
"I'll add rate limiting using Redis..."
[Starts coding immediately without structured plan]
```bash
### Phase 3: CODE (TDD Cycle) 💻

**Follow Test-Driven Development (TDD)** strictly. This is NON-NEGOTIABLE.

**🔴 RED Phase - Write Failing Tests First**:
```bash
# 1. Write test that defines expected behavior
# tests/test_rate_limit.py

def test_rate_limit_blocks_after_threshold():
    # GIVEN: User has exceeded rate limit
    # WHEN: Making additional request
    response = client.get("/api/endpoint")
    # THEN: Should return 429 Too Many Requests
    assert response.status_code == 429

# 2. Run test to confirm it FAILS
pytest tests/test_rate_limit.py -xvs
# ❌ FAILED (Expected - proves test is valid!)
```bash
**🟢 GREEN Phase - Implement Minimal Code**:
```bash
# 3. Write simplest code to make test pass
# src/mcp_server_langgraph/api/rate_limit.py

class RateLimitMiddleware:
    async def __call__(self, request):
        if rate_exceeded(request):
            return JSONResponse(status_code=429)
        return await self.app(request)

# 4. Run test to confirm it PASSES
pytest tests/test_rate_limit.py -xvs
# ✅ PASSED (GREEN achieved!)
```bash
**♻️ REFACTOR Phase - Improve Code Quality**:
```bash
# 5. Refactor while keeping tests green
# - Extract Redis logic to separate class
# - Add type hints
# - Improve error messages
# - Add docstrings

# 6. Run tests after EACH refactoring step
pytest tests/test_rate_limit.py -xvs
# ✅ PASSED (still green after refactoring)
```bash
**Critical TDD Rules**:
- ⚠️ **NEVER** write implementation before tests
- ⚠️ **NEVER** skip the RED phase (proves test works)
- ⚠️ **ALWAYS** commit tests separately from implementation
- ⚠️ **ALWAYS** verify tests fail before implementing

**Success Criteria**:
- ✅ Tests written FIRST (before any implementation)
- ✅ Tests failed initially (RED phase verified)
- ✅ Tests pass after implementation (GREEN phase achieved)
- ✅ Code refactored for quality (REFACTOR phase completed)
- ✅ All existing tests still pass (no regressions)

### Phase 4: COMMIT (Automated Validation) 🚀

**Two-stage git hook validation** ensures quality before merging.

**Pre-commit Hooks (< 30s - Fast Validation)**:
```bash
git commit -m "feat: implement rate limiting middleware"

# Automatically runs:
# - ruff format (auto-format code - replaces black)
# - ruff check --fix (auto-fix linting - replaces isort + flake8)
# - bandit (security scan)
# - shellcheck (bash scripts)
# Duration: 15-30 seconds (45% faster with Ruff consolidation)
```bash
**Pre-push Hooks (8-12 min - Comprehensive Validation)**:
```bash
git push

# Automatically runs (4 phases):
# Phase 1: Lockfile + workflow validation (< 30s)
# Phase 2: MyPy type checking (1-2 min, warning-only)
# Phase 3: Test suite - unit, smoke, integration, property (3-5 min)
# Phase 4: All pre-commit hooks on ALL files (5-8 min)
# Duration: 8-12 minutes (matches CI exactly!)
```sql
**Success Criteria**:
- ✅ Pre-commit hooks passed (code auto-formatted)
- ✅ Pre-push hooks passed (all tests green)
- ✅ Commit message follows conventional commits format
- ✅ Co-authored-by: Claude tag included (if applicable)

---

## Workflow Compliance Checklist

Before marking ANY task complete, verify ALL phases:

- [ ] **EXPLORE**: Did I read 5-10 related files? Review ADRs? Understand existing patterns?
- [ ] **PLAN**: Did I create TodoWrite task list? Get user approval? Identify tests to write?
- [ ] **CODE**: Did I write tests FIRST? Verify RED → GREEN → REFACTOR cycle?
- [ ] **COMMIT**: Did pre-commit pass? Did pre-push pass? All tests green?

**Enforcement**: This 4-phase workflow prevents 90% of implementation problems. Following it rigorously saves significant debugging time.

---

## Anti-Patterns to AVOID

**❌ Jumping Directly to Code**:
```python
User: "Fix the authentication bug"
Claude: "I'll update auth/middleware.py..." [WRONG - didn't explore first]
```python
**Fix**: Always start with exploration phase.

**❌ No Planning/TodoWrite**:
```text
Claude: [Starts writing code without creating todo list] [WRONG - no structured plan]
```rust
**Fix**: Use TodoWrite to create detailed plan before coding.

```rust
**Fix**: Use TodoWrite to create detailed plan before coding.

**❌ Implementation Before Tests**:
```yaml
Claude: [Writes feature.py, then test_feature.py] [WRONG - not TDD]
```yaml
**Fix**: Write tests FIRST, then implement.

**❌ Skipping RED Phase Verification**:
```yaml
Claude: [Writes test + implementation together without verifying test fails] [WRONG]
```bash
**Fix**: Run test before implementing to prove it fails (RED phase).

**❌ Committing Without Running Hooks**:
```bash
Claude: git commit --no-verify [WRONG - bypasses validation]
```bash
**Fix**: Let hooks run. They catch issues before CI.

---

## Best Practices for Claude Code

### 1. Task Decomposition

Claude Code excels when tasks are well-defined:

- ✅ **Good**: "Implement session management with Redis backend, including tests"
- Clear scope
- Testable outcome
- Well-defined deliverable

❌ **Avoid**: "Make the auth better"
- Vague requirements
- Unclear success criteria
- No measurable outcome

### 2. Incremental Development

Claude Code works best with incremental phases:

**Phase 1**: Core implementation
- Create interfaces and base classes
- Implement core functionality
- Add configuration support

**Phase 2**: Testing
- Unit tests for each component
- Integration tests
- Edge case coverage

**Phase 3**: Documentation
- Update ../CHANGELOG.md
- Add inline documentation
- Create usage examples

### 3. Testing Strategy

Claude Code can generate comprehensive test suites:

```python
# Claude Code generates tests with:
- Multiple test classes (by component)
- Comprehensive coverage (86%+ pass rate achieved)
- Mock-based testing (avoiding external dependencies)
- Integration scenarios (realistic use cases)
- Edge cases (error handling, validation)
```bash
Example from this project:
- **test_session.py**: 687 lines, 26 tests, full lifecycle coverage
- **test_role_mapper.py**: 712 lines, 23 tests, enterprise scenarios

### 4. Code Organization

Claude Code maintains clean code organization:

```python
# File structure Claude Code follows:
"""
Module docstring explaining purpose

Imports (grouped by: stdlib, third-party, local)

Constants and configuration

Classes (with comprehensive docstrings)

Helper functions

Main execution (if applicable)
"""
```bash
### 5. Documentation Standards

Claude Code generates documentation with:

- **Docstrings**: Comprehensive for all public APIs
- **Type hints**: Full type annotation throughout
- **../CHANGELOG.md**: Detailed with file references and line numbers
- **README updates**: Keep main README synchronized

## Working with Claude Code

### Starting a Task

```bash
# Launch Claude Code
claude

# Describe your task clearly
"Implement user profile management with the following requirements:
1. User CRUD operations
2. Profile photo upload to S3
3. Email verification workflow
4. Comprehensive tests
5. Update ../CHANGELOG.md"
```bash
### Reviewing Claude Code's Work

Claude Code provides:
- **Clear explanations**: What was implemented and why
- **File references**: Exact file paths and line numbers
- **Test results**: Pass/fail status with details
- **Next steps**: Recommendations for follow-up work

### Iterating with Claude Code

```bash
# If tests fail or adjustments needed:
"The session tests are failing due to Redis mock issues.
Please update the tests to properly mock the Redis client."

# Claude Code will:
1. Analyze the failure
2. Identify the root cause
3. Implement the fix
4. Verify with test execution
5. Report results
```bash
## Configuration for Claude Code

### Python Environment

**IMPORTANT**: Always use the project's virtual environment, never system Python.

**Virtual Environment**: `/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/.venv`
**Python Version**: 3.12
**Package Manager**: uv

**Approved Methods** (in order of preference):

1. **Use `uv run`** (preferred):
   ```bash
   uv run --frozen python script.py
   uv run --frozen pytest tests/
   uv run --frozen mypy src/
   ```

2. **Explicit venv path**:
   ```bash
   .venv/bin/python script.py
   .venv/bin/pytest tests/
   ```

3. **Activate first** (only for multiple commands):
   ```bash
   source .venv/bin/activate && .venv/bin/pytest && .venv/bin/mypy src/
   ```

**Never Use**: Bare `python`, `python3`, `pytest`, or `pip` commands (these use system Python).

**Full Documentation**: See `.claude/memory/python-environment-usage.md` for complete guidelines, troubleshooting, and examples.

### Environment Setup

Claude Code automatically detects:
- Python virtual environment (.venv)
- Package manager (uv, pip, poetry)
- Test framework (pytest)
- Code style tools (Ruff, mypy, bandit)

### Git Hooks Configuration

**Updated:** 2025-11-13 - Reorganized for developer productivity

This project uses a **two-stage hook validation strategy**:

#### Pre-commit Hooks (Fast - < 30s)
Auto-runs on `git commit` for changed files only.

**What Claude Code needs to know:**
- Commits are fast (15-30s) - no need to wait long
- Auto-fixers run automatically (Ruff format + auto-fix)
- Only changed files are validated
- Can commit frequently without performance penalty

```bash
# When Claude Code commits changes
git commit -m "feat: implement feature"
# Runs: ruff format, ruff check --fix, bandit, shellcheck, etc.
# Duration: < 30 seconds (45% faster with Ruff consolidation)
```bash
#### Pre-push Hooks (Comprehensive - 8-12 min)
Auto-runs on `git push` for all files. Matches CI exactly.

**4-Phase Validation:**
1. **Phase 1**: Lockfile + workflow validation (< 30s)
2. **Phase 2**: MyPy type checking (1-2 min, warning only)
3. **Phase 3**: Test suite (unit, smoke, integration, property) (3-5 min)
4. **Phase 4**: All pre-commit hooks on all files (5-8 min)

**What Claude Code needs to know:**
- Push takes 8-12 minutes - this is expected
- Matches CI validation exactly - prevents surprises
- All tests run before push (unit, smoke, integration, property)
- Cannot bypass without `--no-verify` (emergency only)

```bash
# When Claude Code pushes changes
git push
# Runs: Complete 4-phase validation
# Duration: 8-12 minutes (matches CI)
```bash
#### Hook Installation

```bash
# Install hooks (done during setup)
make git-hooks

# Verify hooks are configured
uv run --frozen python scripts/validators/validate_pre_push_hook.py
```python
#### When Claude Code Should Commit/Push

**Commit frequently** (fast, < 30s):
- After implementing a feature
- After writing tests
- After refactoring
- After documentation updates

**Push strategically** (comprehensive, 8-12 min):
- After completing a logical unit of work
- Before switching context
- At end of coding session
- When ready for CI validation

#### Performance Monitoring

Claude Code can measure hook performance:
```bash
uv run --frozen python scripts/dev/measure_hook_performance.py --stage all
```python
#### Documentation References

- Full guide: `TESTING.md#git-hooks-and-validation`
- Categorization: `docs-internal/HOOK_CATEGORIZATION.md`
- Migration guide: `docs-internal/PRE_COMMIT_PRE_PUSH_REORGANIZATION.md`

### Project-Specific Settings

From `pyproject.toml`:
```toml
[tool.pytest.ini_options]
asyncio_mode = "strict"
testpaths = ["tests"]
python_files = ["test_*.py"]
markers = ["unit", "integration", "e2e"]

[tool.ruff]
line-length = 127
target-version = "py310"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]  # pycodestyle, pyflakes, isort, pyupgrade, bugbear

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```bash
## Tips for Maximum Productivity

### 1. Use TodoWrite Tool
Claude Code tracks tasks with TodoWrite:
- ✅ Completed tasks
- 🔄 In-progress tasks
- ⏸️ Pending tasks

### 2. Provide Context
Give Claude Code context about:
- Related files to read
- Existing patterns to follow
- Integration points to consider

### 3. Request Comprehensive Tests
Always ask for "comprehensive tests" to get:
- Multiple test classes
- Edge case coverage
- Integration scenarios
- Mock-based isolation

### 4. Review Generated Code
Claude Code generates production-quality code, but review:
- Security implications
- Performance considerations
- Edge cases specific to your domain

### 5. Maintain Documentation
After each Claude Code session:
- Update ../CHANGELOG.md (Claude Code does this automatically)
- Review generated documentation
- Verify README is current

## Code Quality Standards

Claude Code maintains:
- **Type safety**: Full type hints with mypy validation
- **Test coverage**: 70%+ coverage target (achieved 86% in Phase 2)
- **Documentation**: Docstrings for all public APIs
- **Code style**: Ruff linting + formatting (10-100x faster than legacy tools)
- **Security**: Bandit scanning for vulnerabilities

## Example Claude Code Workflow

### Task: Add JWT Token Rotation

```python
User: "Implement automatic JWT token rotation with the following:
1. Detect tokens expiring within 5 minutes
2. Automatically refresh using refresh token
3. Update session with new tokens
4. Add metrics for rotation events
5. Comprehensive tests
6. Update ../CHANGELOG.md"

Claude Code Response:
- ✅ Created src/mcp_server_langgraph/auth/token_rotation.py (250 lines)
- ✅ Updated src/mcp_server_langgraph/auth/middleware.py (+80 lines)
- ✅ Added rotation metrics to src/mcp_server_langgraph/auth/metrics.py (+15 lines)
- ✅ Created tests/test_token_rotation.py (350 lines, 18 tests)
- ✅ Updated ../CHANGELOG.md with implementation details
- ✅ All 18 tests passing

Summary:
- Implemented TokenRotationManager with configurable thresholds
- Integrated with AuthMiddleware.verify_token()
- Added 3 new metrics: token_rotation_attempts, token_rotation_success, token_rotation_failures
- Comprehensive test coverage including edge cases
- Backward compatible (rotation disabled by default)
```bash
## Troubleshooting

### Common Issues

**Issue**: Tests failing after implementation
- **Solution**: Ask Claude Code to analyze and fix test failures
- **Prevention**: Request tests be run after each implementation

**Issue**: Mock objects not working correctly
- **Solution**: Provide examples of correct mock usage from existing tests
- **Prevention**: Reference similar test files for consistency

**Issue**: Type checking errors
- **Solution**: Run `mypy src/` and provide output to Claude Code
- **Prevention**: Request type hints during initial implementation

## Best Practices Summary

1. ✅ **Clear requirements**: Provide detailed, specific requirements
2. ✅ **Incremental development**: Break large tasks into phases
3. ✅ **Comprehensive tests**: Always request full test coverage
4. ✅ **Documentation**: Update ../CHANGELOG.md and docstrings
5. ✅ **Review**: Review generated code before deployment
6. ✅ **Iterate**: Use Claude Code for refinements and fixes
7. ✅ **Test-driven**: Run tests early and often
8. ✅ **Context**: Provide examples and existing patterns

## Makefile Commands Reference

This project includes 40+ custom Makefile commands for common development tasks. Claude Code can use these commands directly via the Bash tool.

### Testing Commands

```bash
make test                 # Run all automated tests (unit + integration)
make test-unit            # Run unit tests only (fast, no external deps)
make test-integration     # Run integration tests (requires infrastructure)
make test-coverage        # Generate comprehensive coverage report
make test-property        # Run property-based tests (Hypothesis)
make test-contract        # Run contract tests (MCP protocol compliance)
make test-regression      # Run performance regression tests
make test-mutation        # Run mutation tests (test effectiveness)
make test-all-quality     # Run all quality tests
```bash
### Infrastructure & Setup

```bash
make install              # Install production dependencies
make install-dev          # Install development + test dependencies
make setup-infra          # Start Docker infrastructure (all services)
make setup-openfga        # Initialize OpenFGA (authorization)
make setup-keycloak       # Initialize Keycloak (SSO)
make dev-setup            # Complete developer setup (install+infra+setup)
make quick-start          # Quick start with defaults
```bash
### Validation Commands

```bash
make validate-openapi         # Validate OpenAPI schema
make validate-deployments     # Validate all deployment configs
make validate-docker-compose  # Validate Docker Compose
make validate-helm            # Validate Helm chart
make validate-kustomize       # Validate Kustomize overlays
make validate-all             # Run all deployment validations
```bash
### Deployment Commands

```bash
make deploy-dev               # Deploy to development (Kustomize)
make deploy-staging           # Deploy to staging (Kustomize)
make deploy-production        # Deploy to production (Helm)
make deploy-rollback-dev      # Rollback development deployment
make deploy-rollback-staging  # Rollback staging deployment
make deploy-rollback-production  # Rollback production deployment
```bash
### Code Quality Commands

```bash
make lint-check           # Run Ruff linter (replaces flake8 + isort checks)
make lint-fix             # Auto-fix linting + format code (replaces black + isort)
make lint-format          # Format code only (replaces black)
make lint-type-check      # Run mypy type checking
make lint-security        # Run bandit security scan
make pre-commit-setup     # Setup pre-commit hooks
```bash
### Running & Monitoring

```bash
make run                  # Run stdio MCP server
make run-streamable       # Run StreamableHTTP server
make health-check         # Check system health
make monitoring-dashboard # Open Grafana dashboards
make logs                 # Show infrastructure logs
make logs-follow          # Follow all logs in real-time
```bash
### Documentation

```bash
make docs-serve           # Serve Mintlify docs locally
make docs-build           # Build Mintlify docs
make docs-deploy          # Deploy docs to Mintlify
```bash
### Usage Examples

When working on tasks, Claude Code should use these commands directly:

```bash
# Example: Testing workflow
"Run the unit tests to verify the changes"
→ make test-unit

# Example: Validation workflow
"Validate all deployment configurations"
→ make validate-all

# Example: Setup workflow
"Set up the complete development environment"
→ make dev-setup
```bash
**Tip**: Run `make help` to see all available commands with descriptions.

## Custom Slash Commands

This project includes custom slash commands in `.claude/commands/` for common workflows:

### Available Commands

- **`/test-all`** - Run complete test suite (unit, integration, property, contract, regression)
- **`/deploy-dev`** - Execute development deployment workflow
- **`/validate`** - Run all validations (OpenAPI, deployments, Helm, Kustomize)
- **`/debug-auth`** - Debug authentication and authorization issues
- **`/setup-env`** - Complete environment setup from scratch
- **`/fix-issue <number>`** - Automated issue debugging workflow

### Using Slash Commands

```bash
# Run all tests and generate coverage report
/test-all

# Deploy to development environment
/deploy-dev

# Debug authentication problems
/debug-auth

# Fix GitHub issue #42
/fix-issue 42
```bash
Each command includes:
- Comprehensive step-by-step instructions
- Common troubleshooting scenarios
- Expected outputs and verification steps
- Integration with Makefile commands

## Planning Strategies with Extended Thinking

Claude Code supports extended thinking modes for complex problems. Use these keywords to request different levels of planning depth:

### Thinking Modes

1. **`"think"`** - Basic planning (default)
   - Quick analysis
   - Simple task breakdown
   - Good for straightforward tasks

2. **`"think hard"`** - Enhanced planning
   - Deeper analysis
   - More detailed considerations
   - Better for moderately complex tasks

3. **`"think harder"`** - Advanced planning
   - Comprehensive analysis
   - Multiple approaches considered
   - Edge case identification
   - Good for complex features

4. **`"ultrathink"`** - Maximum planning depth
   - Exhaustive analysis
   - Architecture considerations
   - Security and performance implications
   - Multiple solution comparisons
   - Best for critical or complex architectural changes

### When to Use Each Mode

**Use `"think"`** for:
- Bug fixes with clear root cause
- Adding simple tests
- Documentation updates
- Minor refactoring

**Use `"think hard"`** for:
- New feature implementation
- Significant refactoring
- Integration with external systems
- Performance optimization

**Use `"think harder"`** for:
- Complex multi-component features
- Architectural changes
- Security-critical implementations
- Database schema changes

**Use `"ultrathink"`** for:
- Major architectural decisions
- Breaking changes requiring migration
- Complex distributed system features
- Critical security or compliance features

### Example Usage

**Simple bug fix**: Fix the session expiration bug in auth/middleware.py

**Complex feature**: "think hard: Implement distributed caching with Redis cluster support"

**Architectural change**: "ultrathink: Design and implement a plugin system for custom authentication providers"

### Planning Output

When using extended thinking, Claude Code will:
1. Analyze the problem from multiple angles
2. Consider edge cases and failure modes
3. Evaluate trade-offs between approaches
4. Provide a detailed implementation plan
5. Identify potential risks and mitigations
6. Suggest testing strategies

**Best Practice**: For tasks requiring significant code changes or architectural decisions, always use at least `"think hard"` to ensure thorough planning before implementation.

## Resources

- **Claude Code Documentation**: https://docs.claude.com/claude-code
- **Project README**: [../README.md](../README.md)
- **Mintlify Documentation**: See `docs/` directory - Comprehensive docs with 100% coverage
- **Testing Guide**: [../docs/advanced/testing.mdx](../docs/advanced/testing.mdx)
- **Development Guide**: [../docs/advanced/development-setup.mdx](../docs/advanced/development-setup.mdx)
- **CHANGELOG**: [../CHANGELOG.md](../CHANGELOG.md)
- **Contributing**: [../CONTRIBUTING.md](../CONTRIBUTING.md) - Contribution guidelines
- **Security**: [../SECURITY.md](../SECURITY.md) - Security policies and reporting
- **Frontend Style Guide**: `docs-internal/frontend/STYLE.md` - Design system (CVA, Radix colors, accessibility)
- **AI Agents**: [../AGENTS.md](../AGENTS.md) - Cross-tool AI assistant instructions (OpenAI Codex, Cursor, etc.)

## Support

For issues or questions about Claude Code integration:
1. Check the [Claude Code documentation](https://docs.claude.com/claude-code)
2. Review recent conversations in `.claude/` directory
3. Report issues at https://github.com/anthropics/claude-code/issues

---

**Last Updated**: 2026-01-28
**Claude Code Version**: Opus 4.5 (claude-opus-4-5-20251101)
**LangGraph Version**: >=1.0.4 (with langgraph-checkpoint-redis>=0.2.1 for distributed state)
