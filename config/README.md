# Config Directory

Non-standard configuration files that don't fit in `pyproject.toml`.

## Files

- `mutmut.py` - Mutation testing configuration (mutmut requires Python file)

## Configuration Consolidation

As of v2.0.0, most tool configurations have been consolidated into `pyproject.toml` following modern Python best practices:

**Moved to pyproject.toml**:
- ✅ `pytest` - Test configuration, markers (was `config/pytest.ini`)
- ✅ `coverage` - Coverage settings (was `.coveragerc`)
- ✅ `flake8` - Linting rules (was `.flake8`)
- ✅ `black` - Code formatting
- ✅ `isort` - Import sorting
- ✅ `mypy` - Type checking

**Remains in config/**:
- `mutmut.py` - Mutation testing (requires `.py` file, not supported in pyproject.toml)

**Standard dotfiles kept in root**:
- `.pre-commit-config.yaml` - Pre-commit hooks (standard location)
- `.editorconfig` - Editor settings (cross-editor standard)
- `.gitignore` - Git exclusions (standard location)

## Benefits

1. **Single Source of Truth**: All Python tooling in `pyproject.toml`
2. **Easier Maintenance**: No need to sync multiple config files
3. **Modern Python**: Follows PEP 518, PEP 621 standards
4. **Cleaner Root**: Fewer dotfiles cluttering repository

## Usage

Tools automatically find configuration in `pyproject.toml`:

```bash
# All tools read from pyproject.toml now
pytest -m unit -v
black .
isort .
flake8
mypy .
coverage run -m pytest

# Mutmut still uses config/mutmut.py
mutmut run
```

---

**See also**:
- `pyproject.toml` - Modern Python project configuration
- `docs/development/ide-setup.md` - IDE-specific configurations
