# Configuration Files

Non-standard configuration files that don't follow dotfile conventions.

## Test Configuration

- `pytest.ini` - Pytest configuration (test paths, markers, options)
- `mutmut.py` - Mutation testing configuration (defines files to mutate, test runners)

## Why This Directory?

Most Python tool configurations use dotfiles in the root directory (`.flake8`, `.coveragerc`, `.pre-commit-config.yaml`, etc.) following Python ecosystem conventions. However, some tools like `pytest` and `mutmut` can use either dotfiles or non-dotfiles.

This directory centralizes non-dotfile configs to keep the root directory clean and organized.

## Standard Dotfile Configs (in root)

For reference, the following configs remain in the root as standard dotfiles:
- `.flake8` - Flake8 linter configuration
- `.coveragerc` - Coverage.py configuration
- `.pre-commit-config.yaml` - Pre-commit hooks
- `.editorconfig` - Editor configuration
- `.cursorrules` - Cursor AI IDE rules

---

See also:
- [pyproject.toml](../pyproject.toml) - Main Python project configuration (PEP 621)
- [Makefile](../Makefile) - Build automation and command shortcuts
