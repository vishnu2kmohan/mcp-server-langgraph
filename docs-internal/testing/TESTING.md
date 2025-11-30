# Testing Guide

Comprehensive guide for running tests in the MCP Server LangGraph project. This document ensures local testing matches CI/CD behavior exactly.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Types](#test-types)
- [Running Tests Locally](#running-tests-locally)
- [Matching CI/CD Behavior](#matching-cicd-behavior)
- [Coverage Reports](#coverage-reports)
- [Development Workflow](#development-workflow)
- [Continuous Integration](#continuous-integration)
- [Troubleshooting](#troubleshooting)

## Quick Start

```bash
# Install dependencies
make install-dev

# Run all tests with coverage (matches CI)
make test-unit

# Fast iteration without coverage
make test-unit-fast

# Integration tests (Docker-based, same as CI)
make test-integration
```

## Test Types

### Unit Tests
- **Marker**: `@pytest.mark.unit`
- **Purpose**: Test individual components in isolation
- **Dependencies**: None (uses mocks)
- **Speed**: Fast (<1 second per test)
- **Command**: `make test-unit`

### Integration Tests
- **Marker**: `@pytest.mark.integration`
- **Purpose**: Test component interactions
- **Dependencies**: Docker services (OpenFGA, Keycloak, Redis, PostgreSQL)
- **Speed**: Medium (1-5 seconds per test)
- **Command**: `make test-integration`

### End-to-End Tests
- **Marker**: `@pytest.mark.e2e`
- **Purpose**: Test complete user workflows
- **Dependencies**: Full system running
- **Speed**: Slow (5+ seconds per test)
- **Command**: `pytest -m e2e`

### Property-Based Tests
- **Marker**: `@pytest.mark.property`
- **Purpose**: Test invariants with generated inputs (Hypothesis)
- **Dependencies**: None
- **Speed**: Medium (100+ test cases generated)
- **Command**: `make test-property`

### Contract Tests
- **Marker**: `@pytest.mark.contract`
- **Purpose**: Validate API contracts (OpenAPI, MCP protocol)
- **Dependencies**: Schema files
- **Speed**: Fast
- **Command**: `make test-contract`

### Performance Regression Tests
- **Marker**: `@pytest.mark.regression`
- **Purpose**: Detect performance degradations
- **Dependencies**: Baseline metrics
- **Speed**: Medium
- **Command**: `make test-regression`

## Running Tests Locally

### All Tests with Coverage (Default)

```bash
# Run all tests with coverage report
make test

# This runs: pytest (uses pyproject.toml defaults)
# - Coverage enabled by default
# - Matches CI/CD behavior
# - Output: Terminal coverage report
```

### Unit Tests

```bash
# With coverage (matches CI)
make test-unit

# Without coverage (fast iteration)
make test-unit-fast

# Exactly as CI runs them
make test-ci
```

### Integration Tests

```bash
# Docker-based (matches CI exactly)
make test-integration

# Local services (faster, but differs from CI)
make test-integration-local

# Rebuild containers and test
make test-integration-build

# Keep containers for debugging
make test-integration-debug

# Cleanup test containers
make test-integration-cleanup
```

### Quality Tests

```bash
# Property-based tests
make test-property

# Contract tests
make test-contract

# Performance regression tests
make test-regression

# All quality tests
make test-all-quality
```

### Compliance Tests

```bash
# GDPR, SOC2, HIPAA, SLA tests
make test-compliance

# Individual compliance tests
pytest -m gdpr
pytest -m soc2
pytest -m sla
```

## Matching CI/CD Behavior

### Exact CI Match

To run tests exactly as they run in CI/CD:

```bash
# Unit tests (CI/CD Pipeline workflow)
make test-ci

# Integration tests (same Docker environment as CI)
make test-integration

# Quality tests (weekly schedule)
make test-property
make test-contract
make test-regression
```

### Key Differences to Avoid

| ❌ Avoid | ✅ Use Instead | Reason |
|---------|---------------|--------|
| `pytest` (without markers) | `make test-unit` | Runs all tests including slow ones |
| `make test-integration-local` | `make test-integration` | CI uses Docker, not local services |
| `pytest --no-cov` (in CI testing) | `make test-ci` | CI always runs with coverage |
| Custom pytest flags | Use Makefile targets | Ensures consistency |

### Version Consistency

**Tool Versions** (as of 2025-10-15):

```txt
# Formatters (flexible - use latest)
black >= 24.1.1
isort >= 7.0.0

# Static Analysis (pinned - exact versions)
flake8 == 7.3.0
mypy == 1.18.2

# Test Framework (flexible minimum)
pytest >= 8.2.0
pytest-asyncio == 0.26.0
pytest-cov == 4.1.0
```

**Updating Versions:**

1. Local changes: Update `pyproject.toml` dev dependencies
2. CI changes: Update `requirements-test.txt`
3. Both should stay in sync!

## Coverage Reports

### Default Coverage (Terminal)

```bash
make test-unit
# Output:
#   Name                             Stmts   Miss  Cover   Missing
#   --------------------------------------------------------------
#   src/mcp_server_langgraph/...     1234    123    90%   45-67, 89-92
```

### HTML Coverage Report

```bash
make test-coverage
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### XML Coverage (for Codecov)

```bash
pytest --cov=src/mcp_server_langgraph --cov-report=xml
# Generates: coverage.xml
```

### Coverage Configuration

Location: `pyproject.toml`

```toml
[tool.coverage.run]
source = ["src/mcp_server_langgraph"]
omit = [
    "*/venv/*",
    "*/tests/*",
    "*/examples/*",
    ...
]

[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",
    "if TYPE_CHECKING:",
    ...
]
```

## Development Workflow

### Fast Iteration

During active development, skip coverage for speed:

```bash
# Fast unit tests
make test-unit-fast

# Watch mode (re-runs on file changes)
make test-watch

# Specific test file
pytest tests/test_session.py --no-cov

# Specific test function
pytest tests/test_session.py::TestInMemorySessionStore::test_create_session --no-cov
```

### Pre-Commit Testing

Before committing code:

```bash
# 1. Run fast tests
make test-unit-fast

# 2. Run formatters
make format

# 3. Run linters
make lint

# 4. Full test with coverage
make test-unit

# 5. Integration tests (if changed integration code)
make test-integration
```

### Pre-Push Testing

Before pushing to remote:

```bash
# 1. Exactly match CI
make test-ci

# 2. Integration tests
make test-integration

# 3. Validate deployments
make validate-all
```

## Continuous Integration

### CI/CD Workflows

**1. CI/CD Pipeline** (`.github/workflows/ci.yaml`)
- **Trigger**: Push to `main`, `develop`, PRs
- **Tests**: Unit tests, integration tests
- **Coverage**: Yes (uploaded to Codecov)
- **Command**: `pytest -m unit --cov=src/mcp_server_langgraph --cov-report=xml`

**2. Quality Tests** (`.github/workflows/quality-tests.yaml`)
- **Trigger**: Push to `main`, PRs, weekly schedule
- **Tests**: Property, contract, regression tests
- **Coverage**: No (performance-focused)
- **Commands**:
  - `pytest -m property -v`
  - `pytest -m contract -v`
  - `pytest -m regression -v`

**3. Mutation Testing** (`.github/workflows/quality-tests.yaml`)
- **Trigger**: Weekly schedule only (slow)
- **Tests**: Mutation tests with mutmut
- **Purpose**: Test effectiveness validation

### Local Equivalent Commands

| CI Workflow | Local Command | Purpose |
|-------------|---------------|---------|
| CI/CD Pipeline → Test | `make test-ci` | Unit tests with coverage |
| CI/CD Pipeline → Lint | `make lint && make format` | Code quality checks |
| Quality Tests → Property | `make test-property` | Property-based tests |
| Quality Tests → Contract | `make test-contract` | API contract validation |
| Quality Tests → Regression | `make test-regression` | Performance regression |
| Quality Tests → Mutation | `make test-mutation` | Test effectiveness |

## Troubleshooting

### Tests Pass Locally But Fail in CI

**Common Causes:**

1. **Version mismatch**
   ```bash
   # Check versions
   pip list | grep -E "pytest|black|isort|flake8|mypy"

   # Reinstall exact CI versions
   pip install -r requirements-test.txt --force-reinstall
   ```

2. **Coverage differences**
   ```bash
   # Use exact CI command
   make test-ci
   ```

3. **Environment variables**
   ```bash
   # Check .env file
   # CI uses GitHub Secrets
   ```

4. **Docker services**
   ```bash
   # Use Docker-based integration tests
   make test-integration  # Not make test-integration-local
   ```

### Coverage Report Shows Wrong Files

**Issue**: Coverage includes files from `venv/` or `tests/`

**Solution**: Already fixed in `pyproject.toml` → Coverage scope is `src/mcp_server_langgraph`

```bash
# Verify coverage configuration
grep -A 10 "\[tool.coverage.run\]" pyproject.toml
```

### Tests Are Slow

**Fast Options:**

```bash
# Skip coverage
pytest --no-cov

# Run only fast tests
pytest -m "not slow"

# Parallel execution
pytest -n auto

# Specific marker
pytest -m unit --no-cov
```

### Integration Tests Fail

**Common Issues:**

1. **Services not running**
   ```bash
   make setup-infra
   docker compose ps
   ```

2. **Port conflicts**
   ```bash
   # Check ports: 8080, 5432, 8081, 16686, 9090, 3000, 6379
   lsof -i :8080
   ```

3. **Docker version**
   ```bash
   docker --version  # Should be 20.10+
   docker compose version  # Should be 2.0+
   ```

### Import Errors

**Issue**: `ModuleNotFoundError` for `mcp_server_langgraph`

**Solution**:
```bash
# Install package in editable mode
pip install -e .

# Or use uv
uv pip install -e .
```

### Type Checking Errors

**Issue**: mypy reports errors locally but not in CI (or vice versa)

**Solution**:
```bash
# Use exact CI mypy version
pip install mypy==1.18.2

# Check configuration
mypy src/ --ignore-missing-imports
```

## Best Practices

### ✅ Do

- Use `make test-unit` for regular testing (matches CI)
- Use `make test-unit-fast` for quick iteration
- Run `make test-ci` before pushing
- Use Docker-based integration tests (`make test-integration`)
- Keep `requirements-test.txt` and `pyproject.toml` in sync
- Add markers to new tests (`@pytest.mark.unit`, etc.)

### ❌ Don't

- Run `pytest` without markers (runs everything)
- Use `make test-integration-local` to validate CI behavior
- Modify pytest flags in CI without updating Makefile
- Skip coverage checks before committing
- Run integration tests without Docker in CI validation

## Quick Reference

```bash
# Most Common Commands
make test-unit           # Unit tests with coverage
make test-unit-fast      # Fast unit tests (no coverage)
make test-ci             # Exact CI match
make test-integration    # Integration tests (Docker)
make test-coverage       # Full coverage report (HTML)
make format              # Format code (black + isort)
make lint                # Run linters
make test-all-quality    # All quality tests

# Test Selection
pytest -m unit                    # Only unit tests
pytest -m integration             # Only integration tests
pytest -m "unit and not slow"     # Fast unit tests
pytest -k "test_session"          # Name pattern matching
pytest tests/test_session.py      # Specific file

# Coverage Options
pytest --cov=src/mcp_server_langgraph         # Default coverage
pytest --no-cov                                # Skip coverage
pytest --cov-report=html                       # HTML report
pytest --cov-report=term-missing               # Terminal with missing lines
```

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Hypothesis Documentation](https://hypothesis.readthedocs.io/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Project README](../../README.md)
- [Contributing Guide](../../.github/CONTRIBUTING.md)

---

**Last Updated**: 2025-10-15
**Python Version**: 3.12
**pytest Version**: 8.2.0+
**Coverage Target**: 70%+ (Current: 86%)
