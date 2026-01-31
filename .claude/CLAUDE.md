# MCP Server LangGraph - Claude Code Quick Start

**Purpose**: Essential context auto-loaded at session start
**Full Guide**: `.github/CLAUDE.md` (1,070 lines)

---

## CRITICAL: Python Environment

**ALWAYS use `.venv`**: `uv run --frozen <command>` or `.venv/bin/python`
**Full guide**: `.claude/memory/python-environment-usage.md`

---

## TDD Mode Active

**Write tests FIRST, then implementation (Red-Green-Refactor)**

```python
@pytest.mark.unit
async def test_feature():
    # GIVEN → WHEN → THEN
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Unit tests | `uv run --frozen pytest -m unit` |
| All tests | `uv run --frozen pytest` |
| Format | `uv run --frozen ruff format src/` |
| Lint | `uv run --frozen ruff check src/` |
| Type check | `uv run --frozen mypy src/` |
| Coverage | `uv run --frozen pytest --cov=src` |

---

## Git Hooks

| Stage | Trigger | Duration | Purpose |
|-------|---------|----------|---------|
| Pre-commit | `git commit` | < 30s | Ruff format/check, security scan |
| Pre-push | `git push` | 8-12 min | Full test suite, mypy, all hooks |

---

## Project Structure

```
src/mcp_server_langgraph/
├── core/       # Agent, config, feature flags (355 flags)
├── auth/       # Keycloak + OpenFGA + DPoP
├── llm/        # LLM factory (multi-provider)
├── mcp/        # MCP server implementations
├── studio/     # Agent Studio frontend (React + Redux)
├── execution/  # Sandboxed code execution engine
├── security/   # Prompt injection protection
└── observability/  # OpenTelemetry + Grafana LGTM
```

---

## Extended Thinking

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

## Context Files

**Essential** (in `.claude/context/`):
- `recent-work.md` - Auto-updated via git hook
- `testing-patterns.md` - Test patterns reference
- `pytest-markers.md` - 168 markers catalog

**Memory** (in `.claude/memory/`):
- `python-environment-usage.md` - Virtual environment guide
- `validation-strategy.md` - Lint + hooks reference
- `efficient-tool-usage.md` - Script-based bulk operations

---

## Slash Commands

See `.claude/commands/README.md` for all 46 commands.

**Most Used**:
- `/test-summary [scope]` - Analyze test results
- `/quick-debug <error>` - AI-assisted debugging
- `/tdd` - Start TDD workflow
- `/validate` - Run all validations

---

## Common Issues

Use `/quick-debug <error>` for AI-assisted debugging.

**Quick fixes**:
```bash
uv run --frozen pytest --lf -x       # Run last failed
uv run --frozen ruff check --fix src/  # Auto-fix linting
uv run --frozen mypy src/            # Type check
```

---

## Resources

| Resource | Path |
|----------|------|
| Full Guide | `.github/CLAUDE.md` |
| Commands | `.claude/commands/README.md` |
| Templates | `.claude/templates/README.md` |
| Testing | `docs-internal/testing/TESTING.md` |
| AI Agents | `AGENTS.md` |

---

**Remember**: Tests FIRST, `.venv` ALWAYS, `/clear` OFTEN

Python 3.12 | LangGraph >=1.0.4 | Claude Opus 4.5
