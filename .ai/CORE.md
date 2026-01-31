# AI Coding Assistant Core Instructions

**Purpose**: Single source of truth for all AI coding assistants
**Tools**: OpenAI Codex, GitHub Copilot, Cursor, Gemini Code Assist, Claude Code

---

## Python Environment (CRITICAL)

**ALWAYS use `.venv`**: `uv run --frozen <command>` or `.venv/bin/python`

```bash
# Preferred
uv run --frozen pytest tests/
uv run --frozen python script.py

# Alternative
.venv/bin/python script.py

# NEVER use bare python/pytest/pip
```

**Full guide**: `.claude/memory/python-environment-usage.md`

---

## Project Overview

| Metric | Value |
|--------|-------|
| Tests | 20,000+ |
| Coverage | 75% (target: 80%) |
| ADRs | 104 |
| Feature Flags | 355 |
| Python | 3.12 |
| Package Manager | uv |

**Stack**: LangGraph >=1.0.4 + FastAPI + PostgreSQL + Redis + Keycloak + OpenFGA

---

## Essential Commands

| Task | Command |
|------|---------|
| Unit tests | `uv run --frozen pytest -m unit` |
| All tests | `uv run --frozen pytest` |
| Last failed | `uv run --frozen pytest --lf -x` |
| Format | `uv run --frozen ruff format src/` |
| Lint | `uv run --frozen ruff check src/` |
| Auto-fix | `uv run --frozen ruff check --fix src/` |
| Type check | `uv run --frozen mypy src/` |
| Coverage | `uv run --frozen pytest --cov=src` |

---

## TDD Workflow (MANDATORY)

1. **RED**: Write failing test first
2. **GREEN**: Write minimal code to pass
3. **REFACTOR**: Improve while tests pass

```python
@pytest.mark.unit
async def test_feature():
    # GIVEN: Setup
    # WHEN: Action
    # THEN: Assertion
```

---

## Code Style

| Setting | Value |
|---------|-------|
| Line length | 127 chars |
| Formatter | Ruff |
| Type hints | Required for public APIs |
| Docstrings | Google-style |
| Imports | Sorted by Ruff |

---

## Project Structure

```
src/mcp_server_langgraph/
├── core/           # Agent, config, feature flags
├── auth/           # Keycloak + OpenFGA + DPoP
├── llm/            # LLM factory (multi-provider)
├── mcp/            # MCP server implementations
├── studio/         # Agent Studio (React + Redux)
├── execution/      # Sandboxed code execution
├── security/       # Prompt injection protection
└── observability/  # OpenTelemetry + Grafana LGTM
```

---

## Git Workflow

| Stage | Duration | Purpose |
|-------|----------|---------|
| Pre-commit | < 30s | Ruff format/check, security |
| Pre-push | 8-12 min | Full test suite, mypy |

**Commit format**: `type(scope): message`
- Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

---

## Security Guidelines

- Never hardcode secrets
- Validate at boundaries (user input, external APIs)
- Use parameterized queries
- Check authorization before operations
- Bandit runs on pre-commit

---

## Testing Patterns

### Async Tests
```python
@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result is not None
```

### Mocking
```python
@patch("module.dependency", new_callable=AsyncMock)
async def test_with_mock(mock_dep):
    mock_dep.return_value = "value"
```

### Markers
- `@pytest.mark.unit` - Fast, no external deps
- `@pytest.mark.integration` - Requires infrastructure
- `@pytest.mark.asyncio` - Async tests

---

## Common Issues

| Issue | Fix |
|-------|-----|
| Tests failing | `uv run --frozen pytest --lf -x` |
| Type errors | `uv run --frozen mypy src/` |
| Lint errors | `uv run --frozen ruff check --fix src/` |
| Import errors | Use `uv run --frozen python -c "import ..."` |

---

## Resources

| Resource | Path |
|----------|------|
| Testing | `docs-internal/testing/TESTING.md` |
| Contributing | `CONTRIBUTING.md` |
| Security | `SECURITY.md` |
| Architecture | `adr/` (104 ADRs) |
| Claude Code | `.claude/CLAUDE.md` |
| Full Claude Guide | `.github/CLAUDE.md` |

---

**Remember**: Tests FIRST, `.venv` ALWAYS

Python 3.12 | LangGraph >=1.0.4 | uv package manager
