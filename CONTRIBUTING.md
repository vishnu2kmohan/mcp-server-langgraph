# Contributing to MCP Server LangGraph

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Table of Contents

- [Development Setup](#development-setup)
- [Testing GitHub Actions Workflows](#testing-github-actions-workflows)
- [Code Contribution Process](#code-contribution-process)
- [Testing Requirements](#testing-requirements)
- [Code Style](#code-style)
- [Commit Guidelines](#commit-guidelines)

---

## Development Setup

### Quick Start

```bash
# Clone repository
git clone https://github.com/vishnu2kmohan/mcp-server-langgraph.git
cd mcp-server-langgraph

# Install dependencies
uv sync --extra dev --extra builder

# Setup infrastructure
make dev-setup

# Run tests
make test
```

### Prerequisites

- **Python**: 3.10, 3.11, or 3.12 (3.13+ not supported)
- **uv**: Package manager (install: `curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Docker**: For test infrastructure and workflow testing
- **act**: For local GitHub Actions testing (install: `brew install act`)

---

## Testing GitHub Actions Workflows

### ⚠️ REQUIRED: Test Workflows with act Before Committing

All changes to `.github/workflows/*.yaml` files **MUST** be tested locally with `act` before pushing.

**Why?** Recent CI failures were caused by issues that `act` would have caught:
- Missing dependencies (ModuleNotFoundError)
- Missing system tools (jq: command not found)
- Incorrect Python usage (bare `python` instead of `uv run python`)

### Quick Testing

```bash
# Validate syntax only (fast - 2 seconds)
make validate-workflows

# Test with act (2-5 minutes)
act push -W .github/workflows/YOUR_WORKFLOW.yaml -j JOB_NAME
```

### Complete Testing Checklist

See [.github/WORKFLOW_TESTING_CHECKLIST.md](.github/WORKFLOW_TESTING_CHECKLIST.md) for detailed checklist.

**Summary**:
1. ✅ Validate YAML syntax: `make validate-workflows`
2. ✅ Test with act: `act push -W .github/workflows/FILE.yaml -j JOB`
3. ✅ Fix any issues found
4. ✅ Run pre-commit hooks
5. ✅ Commit and push
6. ✅ Monitor CI: `gh run watch`

**Documentation**: [docs/development/testing-workflows-locally.md](docs/development/testing-workflows-locally.md)

---

## Code Contribution Process

### 1. Fork and Create Branch

```bash
# Fork repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/mcp-server-langgraph.git
cd mcp-server-langgraph

# Create feature branch
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Follow code style guidelines (Black, isort)
- Add tests for new features (TDD required)
- Update documentation as needed

### 3. Run Tests Locally

```bash
# Run all tests
make test

# Run specific test types
make test-unit              # Fast unit tests
make test-integration       # Integration tests
make test-e2e               # End-to-end tests (requires infrastructure)
make test-property          # Property-based tests
make test-contract          # Contract tests

# Run linting
make lint-check

# Run security checks
make security-check
```

### 4. Test Workflow Changes (If Applicable)

If you modified `.github/workflows/*.yaml`:

```bash
# Required: Test with act
act push -W .github/workflows/YOUR_FILE.yaml -j JOB_NAME

# See: .github/WORKFLOW_TESTING_CHECKLIST.md
```

### 5. Run Pre-commit Hooks

```bash
# Install hooks (first time)
make lint-install

# Run hooks
pre-commit run --all-files
```

### 6. Commit and Push

```bash
git add .
git commit -m "feat: your feature description"
git push origin feature/your-feature-name
```

### 7. Create Pull Request

- Open PR on GitHub
- Fill out PR template
- Link related issues
- Wait for CI checks to pass
- Address review comments

---

## Testing Requirements

### Test-Driven Development (TDD)

This project follows TDD principles (see global CLAUDE.md for details):

1. **Write tests FIRST** before implementation
2. **Verify tests FAIL** initially (RED phase)
3. **Implement minimally** to make tests pass (GREEN phase)
4. **Refactor** while keeping tests green

### Test Coverage

- **Minimum**: 80% code coverage
- **Target**: 90%+ coverage
- **Critical paths**: 100% coverage (security, payments, data handling)

### Test Types Required

| Feature Type | Required Tests |
|--------------|----------------|
| **New Feature** | Unit + Integration + Property-based |
| **Bug Fix** | Regression test + Unit test |
| **Refactoring** | Existing tests must pass |
| **API Changes** | Contract tests + Integration tests |

---

## Code Style

### Python Style Guide

**Formatters** (enforced by pre-commit):
- **Black**: Line length 127
- **isort**: Profile black
- **flake8**: Max line 127, extends ignore E203,W503

**Type Checking** (gradually enforced):
- **mypy**: Gradual strict mode (see pyproject.toml)
- All new code must have type hints

### Running Formatters

```bash
# Check formatting
make lint-check

# Auto-fix formatting
make lint-fix
```

### Configuration

All style configuration is in `pyproject.toml`:
```toml
[tool.black]
line-length = 127

[tool.isort]
profile = "black"
line_length = 127

[tool.mypy]
python_version = "3.11"
disallow_untyped_defs = true
```

---

## Commit Guidelines

### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding/updating tests
- `chore`: Maintenance tasks
- `ci`: CI/CD changes

**Examples**:

```
feat(auth): add JWT token rotation

Implements automatic token refresh when token expires within 5 minutes.
Includes comprehensive tests and metrics.

Closes #123
```

```
fix(ci): add missing optional dependencies to workflows

- Add --extra dev --extra builder to uv sync commands
- Fixes ModuleNotFoundError in E2E and unit tests
- Tested locally with act before committing

Fixes: #456
```

### Signing Commits

```bash
# Configure GPG signing
git config --global commit.gpgsign true
git config --global user.signingkey YOUR_KEY_ID

# Or use -S flag
git commit -S -m "feat: add feature"
```

---

## CI/CD Guidelines

### Workflow Modification Guidelines

**MUST**:
- ✅ Use `uv` for all Python operations (not `pip`)
- ✅ Use `uv run python` for scripts (not bare `python`)
- ✅ Use `uv sync --extra dev --extra builder` for tests
- ✅ Test with `act` before committing
- ✅ Add timeouts to all jobs
- ✅ Use path filters to skip unnecessary runs

**MUST NOT**:
- ❌ Use `pip install` directly
- ❌ Use bare `python` or `python3` for project scripts
- ❌ Skip act testing for workflow changes
- ❌ Push workflow changes without local validation

### Testing Workflows Before Commit

**Minimum**:
```bash
make validate-workflows  # Syntax check
```

**Recommended**:
```bash
act push -W .github/workflows/YOUR_FILE.yaml -j JOB_NAME
```

**Best Practice**:
```bash
# Follow complete checklist
cat .github/WORKFLOW_TESTING_CHECKLIST.md
```

---

## Pull Request Process

### Before Submitting PR

- [ ] All tests pass locally
- [ ] Pre-commit hooks pass
- [ ] Workflows tested with act (if modified)
- [ ] Documentation updated
- [ ] CHANGELOG.md updated (for features/fixes)
- [ ] No debug code or console.log statements

### PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update
- [ ] CI/CD improvement

## Testing
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Tested locally
- [ ] Workflows tested with act (if applicable)

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests pass locally
- [ ] No new warnings

## Related Issues
Closes #<issue_number>
```

---

## Questions or Issues?

- **Documentation**: See [docs/](docs/)
- **Development Setup**: [docs/advanced/development-setup.mdx](docs/advanced/development-setup.mdx)
- **Workflow Testing**: [docs/development/testing-workflows-locally.md](docs/development/testing-workflows-locally.md)
- **CI/CD Troubleshooting**: [docs/ci-cd-troubleshooting.md](docs/ci-cd-troubleshooting.md)
- **GitHub Discussions**: Open a discussion
- **Issues**: Open an issue with the bug/feature template

---

## Code of Conduct

Be respectful, constructive, and collaborative. We're all here to build great software together.

---

**Last Updated**: 2025-11-02
**Maintained By**: MCP Server LangGraph Team
