# MCP Server LangGraph - AI Agent Instructions

**Purpose**: Instructions for AI coding assistants (OpenAI Codex, GitHub Copilot, Cursor, etc.)
**Last Updated**: 2026-01-28

---

## Quick Start

### Python Environment (CRITICAL)

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

## Project Overview

| Metric | Value |
|--------|-------|
| Tests | 20,000+ |
| Coverage | 75% (target: 80%) |
| ADRs | 104 |
| Feature Flags | 355 |
| Pytest Markers | 168 |

### Technology Stack

- **Framework**: LangGraph >=1.0.4 + LangChain + LiteLLM
- **Frontend**: Agent Studio (React 18 + Redux Toolkit + RTK Query + Vite)
- **LLM Providers**: OpenAI, Anthropic, Google (Vertex AI), Azure
- **Auth**: Keycloak SSO + OpenFGA authorization + DPoP token binding
- **Storage**: PostgreSQL + Redis (langgraph-checkpoint-redis)
- **Execution**: Docker/Kubernetes sandbox code execution engine
- **Observability**: OpenTelemetry + Grafana LGTM (Loki/Tempo/Mimir/Alloy)
- **Deployment**: Kubernetes (Helm + Kustomize)

---

## Project Structure

```
mcp-server-langgraph/
├── src/mcp_server_langgraph/    # Main package
│   ├── core/                     # Agent, config, feature flags (355 flags)
│   ├── auth/                     # Keycloak + OpenFGA + DPoP
│   ├── llm/                      # LLM factory (multi-provider)
│   ├── mcp/                      # MCP server implementations
│   ├── studio/                   # Agent Studio frontend (React + Redux)
│   ├── execution/                # Sandboxed code execution engine
│   ├── security/                 # Prompt injection protection
│   └── observability/            # OpenTelemetry + Grafana LGTM
├── tests/                        # 20,000+ tests
├── deployments/                  # K8s, Helm, Kustomize
├── docs/                         # Mintlify documentation
├── docs-internal/                # Internal architecture docs
│   └── archive/reference/AGENTS.md  # Agent architecture documentation
└── adr/                          # Architecture Decision Records (104 ADRs)
```

---

## Development Workflow

### TDD: Test-Driven Development (MANDATORY)

Write tests FIRST, then implementation (Red-Green-Refactor):

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

### Workflow: Explore → Plan → Code → Commit

1. **EXPLORE**: Read 5-10 related files, review ADRs, check tests
2. **PLAN**: Create task breakdown before writing code
3. **CODE**: TDD cycle (Red → Green → Refactor)
4. **COMMIT**: Let git hooks validate

---

## Commands Reference

### Testing

| Task | Command |
|------|---------|
| Unit tests | `uv run pytest -m unit` |
| All tests | `uv run pytest` |
| Coverage | `uv run pytest --cov=src` |
| Last failed | `uv run pytest --lf -x` |

### Code Quality

| Task | Command |
|------|---------|
| Format | `uv run ruff format src/` |
| Lint | `uv run ruff check src/` |
| Auto-fix | `uv run ruff check --fix src/` |
| Type check | `uv run mypy src/` |

### Makefile Targets (161 available)

```bash
make test              # Run all automated tests
make test-unit         # Run unit tests only
make test-integration  # Run integration tests
make lint-fix          # Auto-fix linting + format
make validate-all      # Run all deployment validations
make help              # List all available targets
```

---

## Core Design Patterns

### Pydantic Settings for Configuration

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    """Application settings with environment variable support"""
    service_name: str = "mcp-server-langgraph"
    log_level: str = "INFO"
    redis_url: str = "redis://localhost:6379"

    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()  # Singleton instance
```

### Factory Pattern for Dependencies

```python
class LLMFactory:
    """Factory for creating LLM instances"""

    @staticmethod
    def create(provider: str = "anthropic") -> BaseLLM:
        if provider == "anthropic":
            return AnthropicLLM(api_key=settings.anthropic_api_key)
        elif provider == "openai":
            return OpenAILLM(api_key=settings.openai_api_key)
        raise ValueError(f"Unknown provider: {provider}")
```

### Async Context Managers

```python
class DatabaseConnection:
    async def __aenter__(self):
        self.conn = await connect(settings.database_url)
        return self.conn

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.conn.close()
```

---

## Testing Patterns

### Async Tests with Fixtures

```python
import pytest
from unittest.mock import AsyncMock, patch

class TestSessionStore:
    @pytest.fixture
    def store(self):
        return SessionStore(default_ttl=3600)

    @pytest.mark.asyncio
    @pytest.mark.unit
    async def test_create_session(self, store):
        # GIVEN
        user_id = "user:alice"

        # WHEN
        session_id = await store.create(user_id=user_id)

        # THEN
        assert session_id is not None
        session = await store.get(session_id)
        assert session.user_id == user_id
```

### Mocking External Services

```python
# Mock Redis
@patch("redis.asyncio.Redis.from_url")
async def test_with_redis_mock(mock_redis):
    mock_client = AsyncMock()
    mock_redis.return_value = mock_client
    mock_client.get.return_value = b'{"key": "value"}'
    # ... test code

# Mock HTTP calls
@patch("httpx.AsyncClient.post")
async def test_with_http_mock(mock_post):
    mock_post.return_value = AsyncMock(
        status_code=200,
        json=AsyncMock(return_value={"result": "ok"})
    )
    # ... test code
```

### Key Pytest Markers

```python
@pytest.mark.unit           # Fast, no external deps
@pytest.mark.integration    # Requires infrastructure
@pytest.mark.slow           # Long-running tests
@pytest.mark.asyncio        # Async tests
@pytest.mark.parametrize    # Parameterized tests
```

---

## Code Style Guidelines

### General Principles

- **Match existing patterns**: Follow conventions already in the codebase
- **Minimal changes only**: Don't refactor or "improve" beyond the ask
- **No unnecessary abstractions**: One-time operations don't need helpers
- **Avoid over-engineering**: Simple solutions preferred

### Python Conventions

- **Line length**: 127 characters (configured in `pyproject.toml`)
- **Target version**: Python 3.12
- **Type hints**: Required for all public APIs
- **Docstrings**: Required for all public functions and classes
- **Imports**: Grouped by stdlib, third-party, local (sorted by Ruff)

### Testing Conventions

- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`
- Follow GIVEN-WHEN-THEN structure
- Use fixtures for test setup
- Mock external dependencies

---

## Git Guidelines

### Commit Practices

- **Never commit unprompted**: Wait for explicit request
- **Use conventional commits**: `feat:`, `fix:`, `docs:`, `refactor:`, etc.
- **Never force push to main/master**: Warn first
- **Never amend pushed commits**: Create new commits for fixes

### Git Hooks

**Pre-commit** (< 30s): Ruff format/check, security scan
**Pre-push** (8-12 min): Full test suite, mypy, all hooks

```bash
git commit -m "feat: add feature"  # Fast validation
git push                           # Comprehensive validation
```

---

## Security Guidelines

- **Do not commit secrets**: No `.env`, credentials, API keys in commits
- **Follow OWASP guidelines**: Prevent injection, XSS, CSRF vulnerabilities
- **Validate at boundaries**: User input, external APIs
- **Use parameterized queries**: Never string-concatenate SQL
- **Security scanning**: Bandit runs on pre-commit

---

## Common Issues & Solutions

### Tests failing?

```bash
uv run pytest --lf -x  # Run last failed, stop on first failure
uv run pytest -v --tb=short  # Verbose with short traceback
```

### Type errors?

```bash
uv run mypy src/
# If missing stubs:
uv sync --extra dev  # Installs types-* packages
```

### Linting issues?

```bash
uv run ruff check --fix src/
uv run ruff format src/
```

### Import errors?

```bash
# Verify using correct Python
uv run python -c "import sys; print(sys.executable)"
# Should show: .venv/bin/python
```

### Async test issues?

```python
# Wrong: session-scoped async fixture
@pytest.fixture(scope="session")  # Can cause event loop issues

# Correct: function-scoped (default)
@pytest.fixture
async def my_fixture():
    ...
```

---

## Resources

### AI Assistant Configurations

- `.ai/README.md` - Universal AI assistant instructions (Copilot, Cursor, Gemini)
- `.cursorrules` - Cursor AI rules and patterns
- `.github/copilot-instructions.md` - GitHub Copilot instructions

### For Claude Code Users

For Claude-specific features and detailed guidance:
- `.claude/CLAUDE.md` - Quick start guide
- `.github/CLAUDE.md` - Comprehensive integration guide
- `.claude/commands/` - 44 slash commands
- `.claude/templates/` - 8 professional templates

### Project Documentation

- `docs/` - Mintlify documentation (public)
- `docs-internal/` - Internal architecture docs
- `adr/` - Architecture Decision Records (104 ADRs)
- `TESTING.md` - Test patterns and markers
- `CONTRIBUTING.md` - Contribution guidelines
- `SECURITY.md` - Security policies and reporting

### Frontend Development

- `docs-internal/frontend/STYLE.md` - Design system (CVA, Radix colors, accessibility)
- `src/mcp_server_langgraph/studio/frontend/CONTRIBUTING.md` - Frontend contribution guide

### Agent Architecture

For documentation about the project's internal agent system (LangGraph/Pydantic AI):
- `docs-internal/archive/reference/AGENTS.md` - Agent architecture documentation

---

## File Size Note

This file is designed to be under 32 KiB for OpenAI Codex compatibility.

---

**Python 3.12 | LangGraph >=1.0.4 | uv package manager**
