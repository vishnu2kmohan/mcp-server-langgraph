# Python Environment Usage

**CRITICAL**: Always use `.venv`. Never use bare `python`, `pytest`, or `pip`.

---

## Approved Methods (in order of preference)

### 1. uv run (Preferred)
```bash
uv run --frozen pytest tests/
uv run --frozen python script.py
uv run --frozen mypy src/
```

### 2. Explicit venv path
```bash
.venv/bin/python script.py
.venv/bin/pytest tests/
```

### 3. Activate first (multiple commands only)
```bash
source .venv/bin/activate && pytest && mypy src/
```

---

## Quick Reference

| Task | Command |
|------|---------|
| Run tests | `uv run --frozen pytest` |
| Run script | `uv run --frozen python script.py` |
| Type check | `uv run --frozen mypy src/` |
| Format | `uv run --frozen ruff format src/` |
| Install deps | `uv sync` |
| Install dev deps | `uv sync --extra dev` |
| Check version | `uv run --frozen python --version` |

---

## Common Mistakes

| Wrong | Correct |
|-------|---------|
| `python script.py` | `uv run --frozen python script.py` |
| `pytest tests/` | `uv run --frozen pytest tests/` |
| `pip install pkg` | `uv pip install pkg` |
| `which python` | `.venv/bin/python --version` |

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| `ModuleNotFoundError` | Using system Python → use `uv run --frozen` |
| `uv: command not found` | Fall back to `.venv/bin/python` |
| Missing type stubs | `uv sync --extra dev` |
| Tests pass locally, fail CI | Different Python → use `uv run --frozen` |

---

## Environment Details

| Setting | Value |
|---------|-------|
| Virtual env | `.venv` (project root) |
| Python version | 3.12 |
| Package manager | uv |
| Requirement | `>=3.11, <3.14` |

---

## Multi-Python Testing

```bash
# Pre-push runs multi-version tests automatically
git push

# Manual execution
./scripts/test_python_versions.sh
./scripts/test_python_versions.sh --quick
```

---

**Rule**: If unsure, prefix with `uv run --frozen`.
