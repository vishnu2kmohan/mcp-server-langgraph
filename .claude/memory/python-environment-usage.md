# Python Environment Usage Guidelines

**Date**: 2025-10-21
**Repo**: mcp-server-langgraph
**Purpose**: Ensure consistent use of project virtual environment
**Status**: Active Configuration

---

## Executive Summary

This document establishes the mandatory requirement to **always use the project's uv-managed virtual environment** (`.venv`) instead of system Python when executing Python commands in this repository.

**Environment Details**:
- Virtual environment: `/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/.venv`
- Python version: 3.12.12
- Package manager: uv (`/usr/bin/uv`)
- Created with: `uv venv` (uv-managed virtual environment)

**Key Principle**: Never use bare `python`, `python3`, `pytest`, or `pip` commands. Always use the virtual environment.

---

## Table of Contents

1. [Approved Methods](#approved-methods)
2. [What to Avoid](#what-to-avoid)
3. [Quick Reference](#quick-reference)
4. [Common Use Cases](#common-use-cases)
5. [Troubleshooting](#troubleshooting)
6. [Rationale](#rationale)

---

## Approved Methods

### Method 1: Use `uv run` (Preferred)

**Best for**: All Python command execution in uv-managed projects

```bash
# Run Python scripts
uv run python script.py

# Run pytest
uv run pytest tests/

# Run with arguments
uv run pytest -v -m unit

# Run modules
uv run python -m pytest
uv run python -m mypy src/
```

**Advantages**:
- ✅ Automatically uses the correct virtual environment
- ✅ Ensures all dependencies are available
- ✅ Works even if venv is not activated
- ✅ Recommended by uv best practices

---

### Method 2: Explicit Virtual Environment Path

**Best for**: Direct Python execution when you need absolute certainty

```bash
# Use absolute path
/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/.venv/bin/python script.py

# Use relative path (from project root)
.venv/bin/python script.py
.venv/bin/pytest tests/
.venv/bin/pip install package-name

# Run modules
.venv/bin/python -m pytest
.venv/bin/python -m mypy src/
```

**Advantages**:
- ✅ Explicit and unambiguous
- ✅ Works from any directory
- ✅ Clear which environment is being used
- ✅ No risk of accidentally using system Python

---

### Method 3: Activate Virtual Environment First

**Best for**: Running multiple commands sequentially

```bash
# Activate and run multiple commands
source .venv/bin/activate && python -m pytest && mypy src/

# Or with error handling
source .venv/bin/activate && {
    python -m pytest tests/
    mypy src/
    black --check src/
}
```

**Advantages**:
- ✅ Traditional virtualenv approach
- ✅ Works for multiple commands
- ✅ Clearer command syntax once activated

**Warning**: Only use this when running multiple commands. For single commands, prefer `uv run` or explicit paths.

---

## What to Avoid

### ❌ Never Use Bare Commands

```bash
# ❌ WRONG: Uses system Python
python script.py
python3 script.py
python -m pytest

# ❌ WRONG: Uses system pytest/pip
pytest tests/
pip install package-name

# ❌ WRONG: May use system Python
which python  # Might point to /usr/bin/python3
```

**Why This Fails**:
- Uses system Python (not 3.13.7 from venv)
- Missing project dependencies
- Different package versions
- Inconsistent behavior between local and CI

---

### ❌ Never Assume Activation

```bash
# ❌ WRONG: Assumes venv is activated
pytest tests/  # Might use system pytest

# ✅ CORRECT: Explicitly use venv
uv run pytest tests/
```

**Why This Fails**:
- Virtual environment may not be activated
- Shell session may have changed
- CI environments are not pre-activated

---

## Quick Reference

### Testing Commands

```bash
# Run all tests
uv run pytest

# Run unit tests only
uv run pytest -m unit

# Run with coverage
uv run pytest --cov=src/mcp_server_langgraph

# Run specific test file
uv run pytest tests/test_session.py

# Run specific test function
uv run pytest tests/test_session.py::test_create_session
```

### Code Quality Commands

```bash
# Type checking
uv run mypy src/

# Code formatting (check)
uv run black --check src/

# Code formatting (apply)
uv run black src/

# Import sorting
uv run isort src/

# Linting
uv run flake8 src/
```

### Package Management

```bash
# Install dependencies
uv pip install -e .

# Install dev dependencies
uv pip install -e ".[dev]"

# Install specific package
uv pip install package-name

# Show installed packages
uv pip list

# Show package info
uv pip show package-name
```

### Running Scripts

```bash
# Run MCP server
uv run mcp-server-langgraph

# Run HTTP server
uv run mcp-server-langgraph-http

# Run custom script
uv run python scripts/my_script.py
```

---

## Common Use Cases

### Use Case 1: Running Tests in Bash Tool

```bash
# ✅ CORRECT
uv run pytest -v -m unit

# ❌ WRONG
pytest -v -m unit
```

### Use Case 2: Type Checking

```bash
# ✅ CORRECT
uv run mypy src/mcp_server_langgraph

# ❌ WRONG
mypy src/mcp_server_langgraph
```

### Use Case 3: Running Multiple Commands

```bash
# ✅ CORRECT (preferred)
uv run pytest && uv run mypy src/ && uv run black --check src/

# ✅ CORRECT (alternative)
source .venv/bin/activate && pytest && mypy src/ && black --check src/

# ❌ WRONG
pytest && mypy src/ && black --check src/
```

### Use Case 4: Checking Python Version

```bash
# ✅ CORRECT
uv run python --version
# Expected: Python 3.13.7

# ✅ CORRECT (explicit)
.venv/bin/python --version

# ❌ WRONG
python --version  # Might show system version
```

### Use Case 5: Interactive Python REPL

```bash
# ✅ CORRECT
uv run python

# ✅ CORRECT (explicit)
.venv/bin/python

# ❌ WRONG
python  # Uses system Python
```

---

## Troubleshooting

### Issue: "uv: command not found"

**Cause**: `uv` not installed or not in PATH

**Check**:
```bash
which uv
# Expected: /usr/bin/uv
```

**Solution**: If uv is not available, fall back to explicit paths:
```bash
.venv/bin/python -m pytest
```

---

### Issue: "ModuleNotFoundError" when running tests

**Cause**: Using system Python instead of venv

**Diagnosis**:
```bash
# Check which Python is being used
which python
# If shows /usr/bin/python3, you're using system Python

# Check if venv is activated
echo $VIRTUAL_ENV
# Should show: /home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/.venv
# If empty, venv is not activated
```

**Solution**:
```bash
# Use uv run
uv run pytest

# Or explicit path
.venv/bin/pytest
```

---

### Issue: Different package versions than expected

**Cause**: Installing packages with system pip

**Diagnosis**:
```bash
# Check which pip is being used
which pip
# Should be: /home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/.venv/bin/pip
# NOT: /usr/bin/pip
```

**Solution**:
```bash
# Use uv pip
uv pip install package-name

# Or explicit path
.venv/bin/pip install package-name
```

---

### Issue: Tests pass locally but fail in CI

**Cause**: Different Python versions (system vs venv)

**Solution**: Always use `uv run` or explicit venv paths to match CI behavior

```bash
# CI uses venv, so local commands should too
uv run pytest  # Matches CI environment
```

---

## Rationale

### Why This Matters

1. **Consistency**: Ensures same Python version (3.13.7) and dependencies everywhere
2. **Reliability**: Avoids "works on my machine" issues
3. **CI/CD Alignment**: Matches CI environment behavior
4. **Dependency Isolation**: Project dependencies separate from system
5. **Reproducibility**: Same results across different machines and sessions

### Virtual Environment Details

**Location**: `/home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/.venv`

**Configuration** (from `pyvenv.cfg`):
```
home = /usr
include-system-site-packages = false
version = 3.12.12
executable = /usr/bin/python3.12
```

**Key Points**:
- Does NOT include system site packages (`include-system-site-packages = false`)
- Python 3.12.12 (project requires `>=3.10,<3.13` per pyproject.toml - ✅ within range)
- All dependencies installed via uv/pip into `.venv/lib/python3.12/site-packages/`

---

## Verification Commands

### Verify You're Using the Correct Environment

```bash
# Check Python executable
uv run python -c "import sys; print(sys.executable)"
# Expected: /home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/.venv/bin/python

# Check Python version
uv run python --version
# Expected: Python 3.12.12

# Check package location
uv run python -c "import mcp_server_langgraph; print(mcp_server_langgraph.__file__)"
# Expected: /home/vishnu/git/vishnu2kmohan/mcp-server-langgraph/.venv/lib/python3.12/site-packages/...

# Verify pytest is from venv
uv run pytest --version
# Check if pytest path includes .venv
```

---

## Summary Checklist

Before running any Python command, verify:

- [ ] Using `uv run python` or `.venv/bin/python` (NOT bare `python`)
- [ ] Using `uv run pytest` or `.venv/bin/pytest` (NOT bare `pytest`)
- [ ] Using `uv pip` or `.venv/bin/pip` (NOT bare `pip`)
- [ ] For multiple commands, consider activation OR use multiple `uv run` calls
- [ ] Python version is 3.12.12 (verify with `uv run python --version`)

---

## References

### Internal Documentation
- `.venv/pyvenv.cfg` - Virtual environment configuration
- `pyproject.toml` - Python version requirements (>=3.10,<3.13)
- `.github/CLAUDE.md` - Claude Code integration guide

### External Resources
- [uv documentation](https://github.com/astral-sh/uv)
- [Python venv documentation](https://docs.python.org/3/library/venv.html)

---

**Last Updated**: 2025-10-21
**Virtual Environment Python Version**: 3.12.12
**Package Manager**: uv (latest)
**pyproject.toml Python Requirement**: >=3.10,<3.13

_This is active configuration. All Python commands must follow these guidelines._
