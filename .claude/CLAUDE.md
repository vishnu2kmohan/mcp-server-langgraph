# MCP Server LangGraph - Claude Code Quick Start

**Purpose**: Essential context auto-loaded at session start
**Full Guide**: `.github/CLAUDE.md` (1,070 lines of comprehensive documentation)
**Last Updated**: 2025-12-07

---

## CRITICAL: Python Environment

**ALWAYS use the project virtual environment. NEVER use bare `python` commands.**

```bash
# PREFERRED: uv run (automatically uses .venv)
uv run --frozen pytest tests/
uv run --frozen python script.py
uv run --frozen mypy src/

# ALTERNATIVE: Explicit venv path
.venv/bin/python script.py
.venv/bin/pytest tests/

# NEVER USE (will use wrong Python):
# python script.py     <- WRONG
# pytest tests/        <- WRONG
# pip install foo      <- WRONG
```

---

## TDD Mode Active

**Write tests FIRST, then implementation (Red-Green-Refactor):**

1. **RED**: Write failing test that defines expected behavior
2. **GREEN**: Write minimal code to make test pass
3. **REFACTOR**: Improve code while keeping tests green

```python
# Test structure: GIVEN-WHEN-THEN
@pytest.mark.unit
async def test_feature():
    # GIVEN: Setup
    # WHEN: Action
    # THEN: Assertion
```

---

## Project Overview

| Metric | Value |
|--------|-------|
| Tests | 5,475+ |
| Coverage | 75% (target: 80%) |
| Pytest markers | 46 |
| Slash commands | 39 |
| Pre-commit hooks | 69 |
| Make targets | 133 |

**Technology Stack**:
- **Framework**: LangGraph >=1.0.4 + LangChain + LiteLLM
- **LLM Providers**: OpenAI, Anthropic, Google (Vertex AI), Azure
- **Auth**: Keycloak SSO + OpenFGA authorization
- **Storage**: PostgreSQL + Redis (langgraph-checkpoint-redis)
- **Observability**: OpenTelemetry + Prometheus + Grafana
- **Deployment**: Kubernetes (Helm + Kustomize)

---

## Key Slash Commands

### Development
- `/test-summary [scope]` - Analyze test results (unit|integration|all)
- `/quick-debug <error>` - AI-assisted error debugging
- `/tdd` - Start TDD workflow

### Sprint Management
- `/start-sprint <type>` - Initialize sprint (technical-debt|feature|bug-fix)
- `/progress-update` - Generate progress report
- `/todo-status` - Enhanced TODO tracking

### Quality
- `/validate` - Run all validations
- `/ci-status` - Check GitHub Actions status
- `/coverage-trend` - Historical coverage tracking

---

## Context Management

**Use `/clear` between unrelated tasks** to reset context window.

**Context files** (in `.claude/context/`):
- `recent-work.md` - Auto-updated via git hook
- `coding-standards.md` - Quick coding reference
- `testing-patterns.md` - 5,475+ test patterns
- `code-patterns.md` - Design patterns library

**Memory files** (in `.claude/memory/` - MANDATORY):
- `python-environment-usage.md` - Virtual environment guide
- `lint-workflow.md` - Linting enforcement
- `pre-commit-hooks-catalog.md` - 69 hooks reference
- `make-targets.md` - 133 targets reference
- `gke-infrastructure-testing.md` - GKE/WIF testing guidance (local vs CI gaps)
- `container-security-patterns.md` - Non-root container UID/GID guide

---

## Git Hooks

**Pre-commit** (< 30s): Ruff format/check, security scan
**Pre-push** (8-12 min): Full test suite, mypy, all hooks

```bash
git commit -m "feat: add feature"  # Fast validation
git push                           # Comprehensive validation
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Format | `uv run ruff format src/` |
| Lint | `uv run ruff check src/` |
| Type check | `uv run mypy src/` |
| Unit tests | `uv run pytest -m unit` |
| All tests | `uv run pytest` |
| Coverage | `uv run pytest --cov=src` |

---

## Project Structure

```
mcp-server-langgraph/
├── src/mcp_server_langgraph/    # Main package
│   ├── core/                     # Agent, config, feature flags
│   ├── auth/                     # Keycloak + OpenFGA
│   ├── llm/                      # LLM factory (multi-provider)
│   ├── mcp/                      # MCP server implementations
│   └── observability/            # OpenTelemetry + metrics
├── tests/                        # 5,475+ tests
├── deployments/                  # K8s, Helm, Kustomize
├── .claude/                      # Claude Code automation
│   ├── commands/                 # 39 slash commands
│   ├── context/                  # Living context files
│   ├── memory/                   # Persistent guidance
│   └── templates/                # 6 professional templates
└── .github/CLAUDE.md             # Comprehensive guide
```

---

## Extended Thinking

Use thinking keywords for complex tasks:

| Keyword | Use Case |
|---------|----------|
| `"think"` | Simple tasks |
| `"think hard"` | New features |
| `"think harder"` | Complex changes |
| `"ultrathink"` | Architectural decisions |

---

## Workflow: Explore → Plan → Code → Commit

1. **EXPLORE**: Read 5-10 related files, review ADRs, check tests
2. **PLAN**: Use TodoWrite to create task breakdown
3. **CODE**: TDD cycle (Red → Green → Refactor)
4. **COMMIT**: Let git hooks validate

---

## Common Issues

**Tests failing?**
```bash
uv run pytest --lf -x  # Run last failed
/test-failure-analysis  # Deep analysis
```

**Type errors?**
```bash
uv run mypy src/
/fix-mypy              # AI-assisted fixing
```

**Linting?**
```bash
uv run ruff check --fix src/
uv run ruff format src/
```

**Container permission errors?**
```bash
# Check container-security-patterns.md for UID reference
# Common fixes: tmpfs uid/gid, file chmod 644, high ports
```

---

## Docker/Container Guidelines

When modifying `docker-compose*.yml` files, ensure:
1. **All containers run as non-root** (except Promtail for Docker socket)
2. **tmpfs mounts include uid/gid** matching container user
3. **Config files are world-readable** (chmod 644)
4. **Services use high ports** (>1024) for non-root binding

See: `.claude/memory/container-security-patterns.md` | ADR-0067

---

## Resources

- **Full Guide**: `.github/CLAUDE.md` (comprehensive, 1,070 lines)
- **Commands**: `.claude/commands/README.md` (39 commands)
- **Templates**: `.claude/templates/README.md` (6 templates)
- **Testing**: `TESTING.md` (test patterns, markers)

---

## Session Start Checklist

1. ✅ Check git status (auto-shown)
2. ✅ TDD mode reminder (auto-shown)
3. 📖 Review recent work: `.claude/context/recent-work.md`
4. 🧪 Verify tests: `/test-summary unit`

---

**Remember**: Tests FIRST, `.venv` ALWAYS, `/clear` OFTEN

🤖 Optimized for Claude Code | Python 3.12 | LangGraph >=1.0.4
