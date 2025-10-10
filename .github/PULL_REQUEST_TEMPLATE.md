## Description

<!-- Provide a clear and concise description of the changes -->

## Type of Change

<!-- Mark the relevant option with an 'x' -->

- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update
- [ ] Performance improvement
- [ ] Code refactoring
- [ ] CI/CD changes
- [ ] Dependencies update

## Related Issues

<!-- Link to related issues, e.g., "Closes #123" or "Fixes #456" -->

Closes #

## Changes Made

<!-- List the main changes made in this PR -->

-
-
-

## Testing

<!-- Describe the tests you've added or run -->

- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Manual testing performed
- [ ] All existing tests pass

### Test Coverage

```bash
# Paste test coverage results here
pytest --cov=. --cov-report=term-missing
```

## Checklist

<!-- Mark completed items with an 'x' -->

### Code Quality

- [ ] Code follows the project's style guidelines
- [ ] Self-review of code completed
- [ ] Code is well-commented, particularly in hard-to-understand areas
- [ ] No new warnings or errors introduced
- [ ] Linting passes (`make lint`)
- [ ] Formatting is correct (`make format`)

### Testing

- [ ] Unit tests cover new/changed code
- [ ] Integration tests updated if needed
- [ ] Tests pass locally (`make test`)
- [ ] Test coverage is maintained or improved (>70%)

### Documentation

- [ ] README updated if needed
- [ ] Docstrings added/updated for new functions/classes
- [ ] `CHANGELOG.md` updated (if applicable)
- [ ] API documentation updated (if applicable)

### Security

- [ ] No secrets or sensitive data committed
- [ ] Security scan passes (`make security-check`)
- [ ] Dependencies are up to date and secure
- [ ] Input validation added where necessary

### Deployment

- [ ] Changes are backward compatible
- [ ] Database migrations included (if needed)
- [ ] Configuration changes documented
- [ ] Kubernetes manifests updated (if needed)

## Screenshots/Logs

<!-- If applicable, add screenshots or logs to help explain your changes -->

## Performance Impact

<!-- Describe any performance implications -->

- [ ] No performance impact
- [ ] Performance improved
- [ ] Performance may be affected (explain below)

## Deployment Notes

<!-- Any special deployment considerations? -->

## Rollback Plan

<!-- How can these changes be rolled back if needed? -->

## Additional Context

<!-- Add any other context about the PR here -->

---

**Reviewer Guidelines:**

- Verify all checklist items are completed
- Check test coverage remains above 70%
- Ensure CI/CD pipeline passes
- Review security implications
- Validate documentation updates
