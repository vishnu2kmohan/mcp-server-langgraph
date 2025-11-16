# Review Pull Request

Comprehensive PR review checklist to ensure code quality, testing, and best practices.

## Usage

```bash
/review-pr
```

## Pre-Review Setup

### 1. Fetch PR Code

```bash
# Using gh CLI
gh pr checkout <PR_NUMBER>

# Or manual checkout
git fetch origin pull/<PR_NUMBER>/head:pr-<PR_NUMBER>
git checkout pr-<PR_NUMBER>
```

### 2. Understand Changes

```bash
# View files changed
git diff main...HEAD --stat

# View detailed diff
git diff main...HEAD

# View commits in PR
git log main..HEAD --oneline
```

## Review Checklist

### Code Quality

#### Readability
- [ ] Code is self-explanatory (minimal comments needed)
- [ ] Variable/function names are descriptive
- [ ] Functions are small and focused (< 50 lines ideally)
- [ ] No deeply nested conditionals (< 4 levels)
- [ ] Consistent with existing code style

#### Design
- [ ] Follows SOLID principles
- [ ] No code duplication (DRY)
- [ ] Proper separation of concerns
- [ ] Uses appropriate design patterns
- [ ] Follows existing architectural patterns (check ADRs)

#### Type Safety
- [ ] All functions have type hints
- [ ] Type hints are accurate and helpful
- [ ] No unnecessary `Any` types
- [ ] Proper handling of Optional types
- [ ] MyPy passes (or errors documented)

### Testing

#### Test Coverage
- [ ] New code has tests (TDD followed)
- [ ] Tests cover happy path
- [ ] Tests cover edge cases
- [ ] Tests cover error scenarios
- [ ] Coverage ≥ 80% for new code

#### Test Quality
- [ ] Tests are independent (no shared state)
- [ ] Tests are deterministic (not flaky)
- [ ] Test names are descriptive (test_X_when_Y_then_Z format)
- [ ] Proper use of fixtures
- [ ] No test code duplication

#### Test Execution
```bash
# Run all tests
make test-all-quality

# Run with coverage
pytest --cov=src --cov-report=term-missing tests/

# Check for flaky tests
pytest tests/ --count=5
```

### Security

- [ ] No hardcoded credentials or secrets
- [ ] Input validation implemented
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (proper output encoding)
- [ ] Command injection prevention
- [ ] Path traversal prevention
- [ ] Authentication checks on protected endpoints
- [ ] Authorization checks (OpenFGA)
- [ ] Rate limiting considered (if public endpoint)
- [ ] Secrets in environment variables or Infisical

```bash
# Run security scans
make security-check
bandit -r src/
```

### Performance

- [ ] No obvious performance issues
- [ ] Database queries optimized (indexes, no N+1)
- [ ] Caching used where appropriate
- [ ] Async/await used for I/O operations
- [ ] No unnecessary loops or recursion
- [ ] Reasonable memory usage

```bash
# Run benchmarks
pytest --benchmark-only

# Check slow tests
pytest -m unit --durations=20
```

### Error Handling

- [ ] Errors are caught and handled appropriately
- [ ] Error messages are informative
- [ ] Custom exceptions used (not generic Exception)
- [ ] Errors are logged with context
- [ ] No swallowed exceptions (empty except blocks)
- [ ] Proper cleanup in finally blocks

### Documentation

- [ ] Docstrings for all public functions/classes
- [ ] Docstrings follow Google/NumPy style
- [ ] Complex logic has explanatory comments
- [ ] CHANGELOG.md updated
- [ ] README.md updated (if user-facing change)
- [ ] ADR created (if architectural decision)
- [ ] API documentation updated (OpenAPI)

### Configuration & Deployment

- [ ] Environment variables documented in .env.example
- [ ] Configuration changes in core/config.py
- [ ] Database migrations included (if schema changes)
- [ ] Kubernetes manifests updated (if needed)
- [ ] Feature flags used (if gradual rollout)
- [ ] Backward compatibility maintained

### Git & Commits

- [ ] Commits are logical and atomic
- [ ] Commit messages are clear and descriptive
- [ ] Follows conventional commits format
- [ ] No merge commits (rebased on main)
- [ ] No unnecessary files in PR (no .env, IDE files)

### CI/CD

- [ ] All CI checks passing
- [ ] No new linter warnings
- [ ] No new type errors (if MyPy enabled)
- [ ] Tests passing in CI
- [ ] Code coverage threshold met (≥ 64%)
- [ ] Security scans passing

```bash
# Simulate CI locally
make test-all-quality
make lint-check
make security-check
```

## Review Process

### 1. Automated Checks

```bash
# Run pre-commit hooks
pre-commit run --all-files

# Run tests
make test-all-quality

# Check coverage
pytest --cov=src --cov-report=html tests/
open htmlcov/index.html

# Run linters
make lint-check

# Run security scans
make security-check
```

### 2. Manual Code Review

- [ ] Read through all changed files
- [ ] Understand the purpose of each change
- [ ] Look for potential bugs
- [ ] Check for code smells
- [ ] Verify edge cases are handled

### 3. Test the Changes

```bash
# Run the application locally
make run

# Test the feature manually
# (API requests, UI interactions, etc.)

# Test error scenarios
# (invalid inputs, missing dependencies, etc.)
```

### 4. Provide Feedback

**Constructive Feedback Format**:

```markdown
## Major Issues (Must Fix)
- [ ] Issue 1: Description and suggested fix
- [ ] Issue 2: Description and suggested fix

## Minor Issues (Nice to Have)
- Suggestion 1: Enhancement idea
- Suggestion 2: Style improvement

## Questions
- Question 1 about approach X
- Question 2 about design decision Y

## Positive Feedback
- Good: Well-structured code in module X
- Good: Comprehensive tests for edge cases
```

### 5. Approval Criteria

**Approve if**:
- ✅ All automated checks passing
- ✅ Code quality meets standards
- ✅ Tests are comprehensive
- ✅ No security issues
- ✅ Documentation is complete
- ✅ No major concerns

**Request changes if**:
- ❌ Failing tests
- ❌ Security vulnerabilities
- ❌ Missing tests for new code
- ❌ Breaking changes without migration path
- ❌ Major design issues

## Common Issues to Watch For

### Code Smells
- Long functions (> 50 lines)
- Too many parameters (> 5)
- Deep nesting (> 4 levels)
- God classes (too many responsibilities)
- Magic numbers (use named constants)
- Premature optimization

### Testing Smells
- Tests without assertions
- Tests testing implementation (not behavior)
- Flaky tests (timing-dependent)
- Tests with external dependencies (not mocked)
- Overly complex test setup

### Security Smells
- String concatenation for SQL queries
- User input directly in shell commands
- Sensitive data in logs
- Missing input validation
- No authentication on endpoints

## Review Commands

```bash
# View PR files
gh pr view <PR_NUMBER> --web

# View PR diff
gh pr diff <PR_NUMBER>

# View PR checks
gh pr checks <PR_NUMBER>

# Comment on PR
gh pr comment <PR_NUMBER> --body "Comment text"

# Approve PR
gh pr review <PR_NUMBER> --approve

# Request changes
gh pr review <PR_NUMBER> --request-changes --body "Feedback"

# View PR discussion
gh pr view <PR_NUMBER>
```

## Post-Review

### If Approved
- [ ] PR merged to main
- [ ] Delete feature branch
- [ ] Monitor deployment
- [ ] Close related issues

### If Changes Requested
- [ ] Author addresses feedback
- [ ] Re-review after updates
- [ ] Continue conversation if needed

---

**Remember**: Code review is about collaboration, not criticism. Be constructive, specific, and kind in feedback.
