# Refactoring Checklist

## Overview

Use this checklist for large-scale refactoring tasks to ensure safe, systematic code improvements without introducing regressions.

## Pre-Refactoring Preparation

- [ ] **Identify the problem**: Document what needs refactoring and why
- [ ] **Set clear goals**: Define success criteria (performance, maintainability, testability)
- [ ] **Get stakeholder buy-in**: Ensure team agrees on approach and priority
- [ ] **Create backup branch**: `git checkout -b backup/pre-refactor-$(date +%Y%m%d)`
- [ ] **Verify tests pass**: Run full test suite to establish baseline (`make test-all-quality`)
- [ ] **Check test coverage**: Ensure coverage ≥ 64% before starting (`pytest --cov`)
- [ ] **Freeze new features**: No new features during refactoring (reduce merge conflicts)
- [ ] **Document current behavior**: Write down edge cases and expected behaviors

## Phase 1: Write Tests (TDD Approach)

- [ ] **Identify untested code**: Find gaps in test coverage for refactoring target
- [ ] **Write characterization tests**: Tests that describe current behavior (even if imperfect)
- [ ] **Add edge case tests**: Cover boundary conditions and error scenarios
- [ ] **Run tests**: Verify all new tests pass (`pytest tests/ -xvs`)
- [ ] **Commit tests separately**: `git commit -m "test: add characterization tests for X"`
- [ ] **Verify coverage increase**: Ensure target code has ≥ 80% coverage

## Phase 2: Small, Incremental Changes

- [ ] **Break into small steps**: Each refactoring commit should be < 200 lines changed
- [ ] **One change at a time**: Don't mix multiple refactoring patterns in one commit
- [ ] **Maintain greenbar**: All tests must pass after each commit
- [ ] **Use IDE refactoring tools**: Automated refactoring reduces human error (PyCharm, VSCode)
- [ ] **Review each change**: Use `git diff` to review before committing

### Common Refactoring Patterns

#### Extract Method
- [ ] Identify long methods (> 50 lines)
- [ ] Extract logical blocks into separate functions
- [ ] Add type hints to new functions
- [ ] Write tests for extracted methods
- [ ] Verify original tests still pass

#### Rename for Clarity
- [ ] Identify unclear names (abbreviations, generic terms like `data`, `temp`)
- [ ] Choose descriptive names that reveal intent
- [ ] Use IDE rename refactoring (catches all references)
- [ ] Update documentation/comments
- [ ] Search for string references: `grep -r "old_name" docs/`

#### Remove Duplication (DRY)
- [ ] Identify duplicated code blocks
- [ ] Extract to shared function/class
- [ ] Ensure shared code is well-tested
- [ ] Update all call sites
- [ ] Remove old duplicated code

#### Simplify Conditionals
- [ ] Replace complex if/else with guard clauses
- [ ] Extract conditional logic to well-named functions
- [ ] Use early returns to reduce nesting
- [ ] Replace nested conditionals with strategy pattern (if complex)

#### Improve Error Handling
- [ ] Replace generic exceptions with specific custom exceptions
- [ ] Add context to error messages
- [ ] Ensure all exceptions are tested
- [ ] Document exception contracts in docstrings

## Phase 3: Continuous Validation

### After Each Commit
- [ ] Run affected tests: `pytest tests/path/to/tests/ -xvs`
- [ ] Run linters: `make lint`
- [ ] Check type hints: `mypy src/path/to/module.py`
- [ ] Review diff: `git diff HEAD~1`

### After Each Phase
- [ ] Run full test suite: `make test-unit test-integration`
- [ ] Run property tests: `make test-property`
- [ ] Check coverage: `pytest --cov=src --cov-report=html`
- [ ] Run benchmarks (if applicable): `pytest --benchmark-only`
- [ ] Run security scans: `make security-check`

## Phase 4: Code Review & Documentation

- [ ] **Self-review changes**: Read through entire diff before requesting review
- [ ] **Update docstrings**: Ensure all public APIs have comprehensive docstrings
- [ ] **Update type hints**: Add or improve type annotations
- [ ] **Update comments**: Remove outdated comments, add clarifying ones
- [ ] **Update CHANGELOG.md**: Document refactoring changes
- [ ] **Create ADR** (if architectural): Document decision to refactor
- [ ] **Request peer review**: Get at least one reviewer
- [ ] **Address feedback**: Respond to all review comments

## Phase 5: Integration & Deployment

- [ ] **Merge to main**: After approval, merge via PR
- [ ] **Monitor CI/CD**: Ensure all CI checks pass
- [ ] **Deploy to staging**: Verify behavior in staging environment
- [ ] **Run smoke tests**: Ensure critical paths work
- [ ] **Monitor metrics**: Check for performance regressions (Grafana/Prometheus)
- [ ] **Rollback plan**: Know how to revert if issues arise
- [ ] **Deploy to production**: Follow standard deployment process
- [ ] **Monitor production**: Watch for errors, performance issues for 24-48 hours

## Common Pitfalls to Avoid

- ❌ **Big bang refactoring**: Don't refactor everything at once
- ❌ **Changing behavior**: Refactoring should NOT change external behavior
- ❌ **Skipping tests**: Always maintain greenbar
- ❌ **Mixing features**: Don't add features during refactoring
- ❌ **Ignoring feedback**: Peer review catches issues you miss
- ❌ **Over-engineering**: Keep it simple, don't over-abstract
- ❌ **Breaking APIs**: Maintain backward compatibility or document breaking changes
- ❌ **Forgetting documentation**: Update docs alongside code

## Refactoring Metrics

Track these metrics to measure success:

- **Code complexity**: Cyclomatic complexity should decrease
- **Test coverage**: Should increase or stay the same (never decrease)
- **Build time**: Should stay the same or improve
- **Test execution time**: Should stay the same or improve
- **Bug rate**: Should decrease over time
- **Code duplication**: Should decrease (use tools like `pylint --duplicate-code`)

## Validation Commands

```bash
# Check code complexity
flake8 --max-complexity=10 src/

# Check duplication
pylint --duplicate-code src/

# Check test coverage
pytest --cov=src --cov-report=term-missing --cov-fail-under=64

# Check for dead code
vulture src/

# Run all quality checks
make lint test-unit test-integration
```

## Success Criteria

- [ ] All tests passing
- [ ] Test coverage ≥ 64% (preferably ≥ 80%)
- [ ] No new linter warnings
- [ ] Type checking passes (MyPy)
- [ ] Code review approved
- [ ] CI/CD passing
- [ ] Deployed to production successfully
- [ ] No production incidents for 48 hours post-deployment
- [ ] Metrics show improvement (or no regression)

## Resources

- **Refactoring Book** (Martin Fowler): https://refactoring.com/
- **Clean Code** (Robert Martin): https://www.oreilly.com/library/view/clean-code-a/9780136083238/
- **Working Effectively with Legacy Code** (Michael Feathers)
- **Refactoring Catalog**: https://refactoring.guru/refactoring/catalog

---

**Created**: 2025-11-15
**Template for**: Large-scale refactoring projects
