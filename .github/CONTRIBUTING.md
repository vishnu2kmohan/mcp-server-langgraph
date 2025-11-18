# Contributing to MCP Server with LangGraph

Thank you for your interest in contributing! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Code Style](#code-style)
- [Commit Messages](#commit-messages)

## Code of Conduct

By participating in this project, you agree to abide by our Code of Conduct. Please be respectful and constructive in all interactions.

## Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR_USERNAME/mcp-server-langgraph.git
   cd mcp-server-langgraph
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/vishnu2kmohan/mcp-server-langgraph.git
   ```

## Development Setup

### Prerequisites

- Python 3.10+ (3.11+ recommended)
- Docker and Docker Compose
- Git
- kubectl (optional, for Kubernetes development)
- Helm 3+ (optional, for Helm chart development)
- An LLM API key (Google Gemini, Anthropic Claude, or OpenAI)

### Install Dependencies

<Note>
**No manual venv creation needed!** `uv sync` automatically creates `.venv` and installs all dependencies.
</Note>

```bash
# Install uv (fast Python package manager)
# macOS/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"

# Install development dependencies (creates .venv automatically)
make install-dev  # Same as: uv sync

# Start infrastructure
make setup-infra

# Setup OpenFGA
make setup-openfga
```

<Tip>
Use `uv run <command>` to run commands in the virtual environment without activation.
</Tip>

### Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# ANTHROPIC_API_KEY=your-key
# OPENFGA_STORE_ID=from-setup
# OPENFGA_MODEL_ID=from-setup
```

### Database Architecture

The project uses a **multi-database PostgreSQL architecture** with automatic initialization:

**Three Dedicated Databases**:
- `gdpr` / `gdpr_test` - GDPR compliance data (5 tables: user_profiles, user_preferences, consent_records, conversations, audit_logs)
- `openfga` / `openfga_test` - Authorization data (3 tables managed by OpenFGA service)
- `keycloak` / `keycloak_test` - Authentication data (3 tables managed by Keycloak service)

**Environment Detection**: Automatically creates dev or test databases based on `POSTGRES_DB`:
```bash
# Development (default in docker-compose.yml)
POSTGRES_DB=postgres → creates gdpr, openfga, keycloak

# Test (default in docker-compose.test.yml)
POSTGRES_DB=gdpr_test → creates gdpr_test, openfga_test, keycloak_test
```

**Validation**: Verify database setup with runtime validation:
```bash
# After starting infrastructure
docker compose exec agent python -c "
from mcp_server_langgraph.health.database_checks import validate_database_architecture
import asyncio
result = asyncio.run(validate_database_architecture(host='postgres'))
print(f'Valid: {result.is_valid}')
for db_name, db_result in result.databases.items():
    print(f'{db_name}: exists={db_result.exists}, tables_valid={db_result.tables_valid}')
"
```

**See**: [ADR-0060: Database Architecture](../adr/adr-0060-database-architecture-and-naming-convention.md) for complete architecture documentation.

## Making Changes

### Create a Branch

```bash
# Update your fork
git fetch upstream
git checkout main
git merge upstream/main

# Create feature branch
git checkout -b feat/your-feature-name
# or
git checkout -b fix/bug-description
```

### Branch Naming Convention

- `feat/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions/changes
- `ci/` - CI/CD changes
- `chore/` - Maintenance tasks

## Testing

### Run Tests

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run with coverage
make test-coverage

# Run integration tests
make test-integration
```

### Writing Tests

- **Unit tests**: Mock external dependencies, test individual functions
- **Integration tests**: Test component interactions with real services
- **E2E tests**: Test complete workflows

Example:
```python
import pytest
from auth import AuthMiddleware

@pytest.mark.unit
@pytest.mark.auth
def test_create_token():
    """Test JWT token creation"""
    auth = AuthMiddleware(secret_key="test")
    token = auth.create_token("alice")
    assert token is not None
```

### Test Coverage

- Maintain >70% coverage (enforced in CI)
- Aim for >80% coverage
- Critical paths should have >90% coverage

### Validation Workflow

This project uses a **three-tier validation strategy** optimized for developer productivity:

#### Tier-1: Pre-commit Hooks (< 30s)

Runs automatically on `git commit` for **changed files only**.

**What runs**:
- Code formatting (black, isort) - auto-fixes
- Linting (flake8, shellcheck)
- Security scanning (bandit)
- Quick syntax checks

**Duration**: 15-30 seconds
**Purpose**: Catch obvious issues early, auto-fix formatting
**When**: Every commit

```bash
git commit -m "feat: your changes"
# Automatically runs tier-1 validation
```

**Note**: You can commit frequently without performance penalty. Auto-fixers will format your code automatically.

#### Tier-2: Pre-push Hooks (3-5 min)

Runs automatically on `git push` with **dev profile** (faster iteration).

**What runs** (4 phases):
1. **Phase 1**: Lockfile + workflow validation (< 30s)
2. **Phase 2**: MyPy type checking (1-2 min, warning-only)
3. **Phase 3**: Focused test suite (unit, smoke, API tests) with dev profile
   - Property tests: 25 examples (vs 100 in CI)
   - Integration tests: Manual stage (run via `make test-integration`)
4. **Phase 4**: Selected pre-commit hooks on all files

**Duration**: 3-5 minutes (optimized for developer productivity)
**Purpose**: Catch regressions before pushing to remote
**When**: Every push

```bash
git push
# Automatically runs tier-2 validation
# Expected duration: 3-5 minutes
```

**CLI Availability**: External tool hooks (actionlint, mintlify, helm, kubectl) gracefully skip if tools are not installed. You can develop without installing all tools.

**Emergency bypass** (use sparingly):
```bash
git push --no-verify  # Skip hooks (emergency only!)
```

#### Tier-3: CI/Full Validation (12-15 min)

Runs automatically in **CI/CD pipelines** with **ci profile** (comprehensive).

**What runs**:
- Complete test suite with ci profile
  - Property tests: 100 examples (thorough validation)
  - Integration tests: Full Docker stack with 4x parallelization
  - E2E tests: Complete user journey validation
  - Quality tests: Property, contract, performance regression
- All pre-commit hooks on all files
- Full deployment validation
- Security scans (Trivy, CodeQL)

**Duration**: 12-15 minutes
**Purpose**: Comprehensive validation before merge
**When**: Every pull request, push to main/develop

**Manual run** (CI-equivalent local validation):
```bash
make validate-full
# Runs complete CI validation locally
# Duration: 12-15 minutes
```

#### Validation Tier Summary

| Tier | Stage | Duration | Profile | When | What Runs |
|------|-------|----------|---------|------|-----------|
| **Tier-1** | Pre-commit | < 30s | N/A | Every commit | Formatting, linting, quick checks |
| **Tier-2** | Pre-push | 3-5 min | dev (25 examples) | Every push | Focused tests, type checking |
| **Tier-3** | CI/Full | 12-15 min | ci (100 examples) | PR, main/develop | Complete validation |

#### Best Practices

**✅ DO**:
- Commit frequently (tier-1 is fast!)
- Push strategically (tier-2 is focused)
- Let hooks run (they catch issues early)
- Run `make validate-full` before creating PR (CI-equivalent)
- Run `make test-integration` when changing infrastructure code

**❌ DON'T**:
- Use `--no-verify` unless emergency
- Skip tier-2 validation (it's optimized for speed)
- Expect tier-2 to catch everything (tier-3/CI is comprehensive)

**Performance Monitoring**:
```bash
# Measure hook performance
python scripts/measure_hook_performance.py --stage all
```

**See Also**:
- [Git Hooks Guide](../TESTING.md#git-hooks-and-validation) - Complete guide
- [Hook Categorization](../docs-internal/HOOK_CATEGORIZATION.md) - Detailed hook breakdown
- [Remediation Report](../docs-internal/CODEX_FINDINGS_REMEDIATION_REPORT_2025-11-16.md) - Optimization rationale

## Submitting Changes

### Before Submitting

```bash
# 1. Format code
make format

# 2. Run linters
make lint

# 3. Run tests
make test

# 4. Check security
make security-check
```

### Commit Your Changes

```bash
git add .
git commit -m "feat: add new feature description"
```

### Push and Create PR

```bash
# Push to your fork
git push origin feat/your-feature-name

# Create Pull Request on GitHub
# Fill out the PR template completely
```

### Pull Request Process

1. **Fill out the PR template** completely
2. **Link related issues** (e.g., "Closes #123")
3. **Ensure CI passes** - All checks must be green
4. **Request review** from appropriate code owners
5. **Address feedback** promptly
6. **Keep PR updated** with main branch

### PR Checklist

- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] Code formatted (`make format`)
- [ ] Linting passes (`make lint`)
- [ ] Security scan passes
- [ ] Coverage maintained (>70%)
- [ ] PR description is clear
- [ ] Commits follow convention

## Code Style

### Python Style

We follow **PEP 8** with some modifications:

- **Line length**: 127 characters
- **Formatter**: Black
- **Import sorter**: isort
- **Type hints**: Required for public APIs
- **Docstrings**: Google style

### Formatting

```bash
# Auto-format code
make format

# Check formatting
black --check .
isort --check .
```

### Type Hints

```python
from typing import Optional, List, Dict

async def get_secret(
    key: str,
    fallback: Optional[str] = None
) -> Optional[str]:
    """
    Get secret from Infisical.

    Args:
        key: Secret key name
        fallback: Fallback value if not found

    Returns:
        Secret value or fallback
    """
    pass
```

### Docstrings

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description of function.

    Longer description if needed, explaining the purpose
    and behavior in detail.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When validation fails
        RuntimeError: When operation fails
    """
    pass
```

## Commit Messages

We follow **Conventional Commits** specification:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Formatting, missing semicolons, etc.
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `test`: Adding missing tests
- `build`: Changes to build system or dependencies
- `ci`: Changes to CI configuration
- `chore`: Other changes that don't modify src or test files

### Examples

```bash
# Simple commit
feat: add StreamableHTTP transport

# With scope
fix(auth): handle expired tokens gracefully

# With body and footer
feat(mcp): add resource listing support

Implement MCP resources/list method to allow clients
to discover available resources dynamically.

Closes #123
```

### Breaking Changes

```bash
feat!: change authentication API

BREAKING CHANGE: Authentication now requires OpenFGA
setup. Update your configuration to include OPENFGA_STORE_ID.
```

## Code Review Process

### As a Contributor

- **Respond to feedback** within 48 hours
- **Ask questions** if feedback is unclear
- **Be open** to suggestions and improvements
- **Update your PR** promptly

### As a Reviewer

- **Be constructive** and respectful
- **Explain your reasoning** for requested changes
- **Approve when ready** - don't block unnecessarily
- **Use suggestion feature** for minor changes

## Areas to Contribute

### Good First Issues

Look for issues labeled `good first issue`:
- Documentation improvements
- Test coverage increases
- Minor bug fixes
- Code cleanup

### High Priority

- Security improvements
- Performance optimizations
- Test coverage gaps
- Documentation updates

### Feature Requests

Check issues labeled `enhancement` for requested features.

## Getting Help

### Where to Ask Questions

- **GitHub Discussions**: For questions, ideas, and general discussion
- **GitHub Issues**: For bug reports and feature requests (use templates)
- **Documentation**: Check our comprehensive guides first
  - [README.md](../README.md) - Getting started
  - [Testing Guide](../docs-internal/testing/TESTING.md) - Testing guide
  - [Production Checklist](../docs/deployment/production-checklist.mdx) - Deployment
  - [Security Audit](../archive/SECURITY_AUDIT.md) - Security

### Response Time

- **Critical bugs**: 24-48 hours
- **Feature requests**: 1-2 weeks
- **Questions**: 2-5 business days

### Community Support

We welcome community members helping each other! If you know the answer to someone's question, please share your knowledge.

### Additional Resources

For more information:
- **Testing Guide**: [Testing Documentation](../docs-internal/testing/TESTING.md)
- **Production Checklist**: [docs/deployment/production-checklist.mdx](../docs/deployment/production-checklist.mdx)
- **Security Policy**: [SECURITY.md](../SECURITY.md)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to MCP Server with LangGraph!** 🚀
