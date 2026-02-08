---
description: CRITICAL Python virtual environment rules - always use uv or .venv
paths:
  - "**/*.py"
  - "pyproject.toml"
  - "uv.lock"
globs:
  - "**/*.py"
---

# Python Environment Rules

**CRITICAL**: Always use `.venv`. Never use bare `python`, `pytest`, or `pip`.

## Commands

| Task | Command |
|------|---------|
| Run tests | `uv run --frozen pytest` |
| Run script | `uv run --frozen python script.py` |
| Type check | `uv run --frozen mypy src/` |
| Format | `uv run --frozen ruff format src/` |
| Lint | `uv run --frozen ruff check src/` |
| Install deps | `uv sync` |

## Common Mistakes

| Wrong | Correct |
|-------|---------|
| `python script.py` | `uv run --frozen python script.py` |
| `pytest tests/` | `uv run --frozen pytest tests/` |
| `pip install pkg` | `uv pip install pkg` |

## Fallback (if uv unavailable)

```bash
.venv/bin/python script.py
.venv/bin/pytest tests/
```

## Environment

- Python: 3.12
- Package manager: uv
- Virtual env: `.venv` (project root)

**Rule**: When in doubt, prefix with `uv run --frozen`.

---

## Shift-Left Patterns (Pre-Commit Prevention)

### subprocess.run() Requires Timeout (CRITICAL)

```python
# CORRECT - ALWAYS include timeout parameter
result = subprocess.run(cmd, capture_output=True, timeout=60)

# WRONG - Hangs indefinitely if process stalls
result = subprocess.run(cmd, capture_output=True)
```

### Never Use SQLAlchemy create_all()

```python
# CORRECT - Use Alembic migrations
alembic upgrade head

# WRONG - Bypasses migration history
Base.metadata.create_all(engine)  # Never in src/, only in tests
```
