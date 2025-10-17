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

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
make install-dev

# Start infrastructure
make setup-infra

# Setup OpenFGA
make setup-openfga
```

### Environment Configuration

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# ANTHROPIC_API_KEY=your-key
# OPENFGA_STORE_ID=from-setup
# OPENFGA_MODEL_ID=from-setup
```

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
  - [TESTING.md](../TESTING.md) - Testing guide
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
- **Testing Guide**: [TESTING.md](../TESTING.md)
- **Production Checklist**: [docs/deployment/production-checklist.mdx](../docs/deployment/production-checklist.mdx)
- **Security Policy**: [SECURITY.md](../SECURITY.md)

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to MCP Server with LangGraph!** 🚀
