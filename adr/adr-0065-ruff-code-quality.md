# 65. Ruff for Code Quality

Date: 2025-11-29

## Status

Accepted

## Category

Development & Tooling

## Context

Python code quality historically required multiple tools:

- **black**: Code formatting
- **isort**: Import sorting
- **flake8**: Linting (style, errors)
- **pylint**: Deep static analysis
- **pyupgrade**: Python version upgrades
- **autoflake**: Remove unused imports

This creates:
- Complex configuration across multiple files
- Slow execution (multiple passes over code)
- Conflicting rules between tools
- Version compatibility issues

### Performance Comparison (large codebase, ~50k lines)

| Tool | Time | Rules |
|------|------|-------|
| flake8 | ~15s | ~100 |
| pylint | ~45s | ~200 |
| black + isort | ~8s | formatting |
| **ruff** | **~0.5s** | **800+** |

## Decision

Use **ruff** (by Astral) as the single tool for linting, formatting, and import sorting.

### Key Reasons

1. **Speed**: 10-100x faster than alternatives (written in Rust)
2. **All-in-one**: Replaces black, isort, flake8, pyupgrade, autoflake
3. **800+ Rules**: Covers flake8, pylint, pyupgrade, bandit, and more
4. **Auto-fix**: Most issues can be fixed automatically
5. **pyproject.toml**: Single configuration file
6. **Active Development**: Rapid iteration by Astral team

### Configuration

```toml
# pyproject.toml
[tool.ruff]
target-version = "py311"
line-length = 120
src = ["src", "tests"]

[tool.ruff.lint]
select = [
    "E",      # pycodestyle errors
    "W",      # pycodestyle warnings
    "F",      # pyflakes
    "I",      # isort
    "B",      # flake8-bugbear
    "C4",     # flake8-comprehensions
    "UP",     # pyupgrade
    "ARG",    # flake8-unused-arguments
    "SIM",    # flake8-simplify
    "TCH",    # flake8-type-checking
    "PTH",    # flake8-use-pathlib
    "ERA",    # eradicate (commented code)
    "PL",     # pylint
    "PERF",   # perflint
    "RUF",    # ruff-specific
]
ignore = [
    "PLR0913",  # Too many arguments (acceptable for complex APIs)
    "PLR2004",  # Magic values (too noisy)
]

[tool.ruff.lint.per-file-ignores]
"tests/*" = ["ARG", "PLR2004"]  # Allow unused args and magic values in tests

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
docstring-code-format = true
```

### Usage

```bash
# Check for issues
ruff check src/

# Fix issues automatically
ruff check --fix src/

# Format code
ruff format src/

# Check and format in one command
ruff check --fix src/ && ruff format src/
```

### Pre-commit Integration

```yaml
# .pre-commit-config.yaml
- repo: https://github.com/astral-sh/ruff-pre-commit
  rev: v0.8.0
  hooks:
    - id: ruff
      args: [--fix]
    - id: ruff-format
```

## Consequences

### Positive

- **Speed**: Near-instant linting, even on large codebases
- **Simplicity**: One tool, one config file
- **Consistency**: Same rules across all developers
- **Auto-fix**: Most issues resolved automatically
- **Modern Rules**: Catches Python 3.11+ improvements

### Negative

- **New Tool**: Team must learn ruff-specific configuration
- **Less Mature**: Some edge cases not covered by flake8/pylint
- **Opinionated**: Less flexibility than separate tools

### Migration from Multiple Tools

```bash
# Remove old tools
pip uninstall black isort flake8 pylint autoflake pyupgrade

# Install ruff
uv add ruff --dev

# Convert configurations
# - .flake8 → pyproject.toml [tool.ruff.lint]
# - pyproject.toml [tool.black] → [tool.ruff.format]
# - pyproject.toml [tool.isort] → [tool.ruff.lint.isort]

# Run migration
ruff check --fix --unsafe-fixes src/
ruff format src/
```

## Rule Categories

| Category | Prefix | Description |
|----------|--------|-------------|
| pycodestyle | E, W | PEP 8 style |
| pyflakes | F | Undefined names, unused imports |
| isort | I | Import sorting |
| flake8-bugbear | B | Likely bugs |
| flake8-comprehensions | C4 | Simplify comprehensions |
| pyupgrade | UP | Python version upgrades |
| pylint | PL | Deep analysis |
| ruff-specific | RUF | Ruff-only rules |

## Alternatives Considered

### black + isort + flake8
- **Rejected**: Slow, multiple configurations, version conflicts
- Three separate tools with overlapping concerns

### pylint
- **Rejected**: Very slow, overly strict defaults
- Many false positives require extensive configuration

### pyright/mypy (for linting)
- **Considered**: Type-based linting is powerful
- **Kept alongside ruff**: mypy for type checking, ruff for style/bugs

## References

- Configuration: `pyproject.toml` [tool.ruff]
- Pre-commit: `.pre-commit-config.yaml`
- Related ADRs: [ADR-0064](adr-0064-pre-commit-hooks-strategy.md), [ADR-0062](adr-0062-uv-package-management.md)
- External: [Ruff Documentation](https://docs.astral.sh/ruff/)
