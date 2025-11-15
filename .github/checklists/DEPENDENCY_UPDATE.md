# Dependency Update Checklist

## Overview

Systematic checklist for updating dependencies (major version upgrades, security patches, or routine maintenance).

## Pre-Update Assessment

### Identify Updates
- [ ] Run `uv lock --upgrade` to check for available updates
- [ ] Review Dependabot/Renovate PRs
- [ ] Check for security advisories: `pip-audit` or `safety check`
- [ ] Prioritize security updates (CVE fixes)
- [ ] Group related dependencies (e.g., all LangChain packages)

### Review Change Logs
- [ ] Read CHANGELOG/release notes for each major update
- [ ] Identify breaking changes
- [ ] Check for deprecation warnings
- [ ] Review migration guides (if provided)
- [ ] Estimate effort required (low/medium/high)

### Risk Assessment
- [ ] **Low risk**: Patch versions (1.2.3 → 1.2.4)
- [ ] **Medium risk**: Minor versions (1.2.0 → 1.3.0)
- [ ] **High risk**: Major versions (1.x → 2.x)
- [ ] **Critical**: Security fixes (immediate update required)

## Phase 1: Preparation

- [ ] Create feature branch: `git checkout -b deps/update-{package}-{version}`
- [ ] Backup current lockfile: `cp uv.lock uv.lock.backup`
- [ ] Run full test suite: `make test-all-quality`
- [ ] Record baseline test results
- [ ] Check current coverage: `pytest --cov`
- [ ] Document current behavior (if complex dependency)

## Phase 2: Update Dependencies

### For Patch/Minor Updates (Low-Medium Risk)
```bash
# Update all dependencies
uv lock --upgrade

# Update specific package
uv add package@latest
```

- [ ] Update lockfile: `uv lock --upgrade`
- [ ] Review changes in `uv.lock`: `git diff uv.lock`
- [ ] Check for unexpected transitive dependency updates
- [ ] Commit: `git commit -m "chore: update dependencies"`

### For Major Updates (High Risk)
```bash
# Update one major dependency at a time
uv add "langgraph@^0.7.0"
```

- [ ] Update ONE major dependency at a time
- [ ] Read migration guide thoroughly
- [ ] Make required code changes
- [ ] Run tests after EACH major update
- [ ] Commit after each successful update
- [ ] Don't mix major updates in one commit

## Phase 3: Code Changes (For Breaking Changes)

### Common Migration Tasks
- [ ] Update import statements (if package structure changed)
- [ ] Rename deprecated functions/classes
- [ ] Update function signatures (if parameters changed)
- [ ] Replace removed APIs with new equivalents
- [ ] Update type hints (if types changed)
- [ ] Update configuration (if config schema changed)

### LangChain/LangGraph Specific
- [ ] Update chain definitions
- [ ] Update agent configurations
- [ ] Update callback handlers
- [ ] Update tool definitions
- [ ] Update prompt templates
- [ ] Test with LangSmith tracing

### FastAPI/Pydantic Specific
- [ ] Update Pydantic models (v1 → v2 if applicable)
- [ ] Update FastAPI route definitions
- [ ] Update dependency injection
- [ ] Update request/response models
- [ ] Test OpenAPI schema generation

## Phase 4: Testing

### Unit Tests
- [ ] Run unit tests: `make test-unit`
- [ ] Fix any test failures
- [ ] Check for new deprecation warnings
- [ ] Update mocks if behavior changed
- [ ] Ensure test coverage didn't decrease

### Integration Tests
- [ ] Run integration tests: `make test-integration`
- [ ] Test with real dependencies (not mocks)
- [ ] Verify third-party integrations still work
- [ ] Test database migrations (if ORM updated)

### E2E Tests
- [ ] Run E2E tests: `make test-e2e`
- [ ] Test critical user journeys
- [ ] Verify UI still works (if frontend deps updated)

### Compatibility Tests
- [ ] Test with different Python versions (3.10, 3.11, 3.12)
- [ ] Test on different platforms (Linux, macOS, Windows - if applicable)
- [ ] Test in Docker container
- [ ] Test deployment to staging

## Phase 5: Security & Quality Checks

- [ ] Run security scan: `pip-audit` or `safety check`
- [ ] Run linters: `make lint`
- [ ] Run type checker: `mypy src/` (if enabled)
- [ ] Check for new vulnerabilities: `bandit -r src/`
- [ ] Scan container images: `trivy image <image>`
- [ ] Review dependency licenses (ensure compatibility)

## Phase 6: Performance Validation

- [ ] Run benchmarks: `pytest --benchmark-only`
- [ ] Compare with baseline benchmarks
- [ ] Check for performance regressions (> 10% slower)
- [ ] Monitor memory usage
- [ ] Test with production-like load (if possible)

## Phase 7: Documentation & Review

- [ ] Update `CHANGELOG.md` with dependency changes
- [ ] Update `README.md` if installation instructions changed
- [ ] Update documentation if APIs changed
- [ ] Create ADR if major architectural impact
- [ ] Request peer code review
- [ ] Address review feedback

## Phase 8: Deployment

### Staging Deployment
- [ ] Deploy to staging environment
- [ ] Run smoke tests
- [ ] Monitor for errors (24 hours)
- [ ] Check Grafana/Prometheus metrics
- [ ] Verify no performance regressions

### Production Deployment
- [ ] Merge PR after approval
- [ ] Wait for CI/CD to pass
- [ ] Deploy during low-traffic window
- [ ] Monitor production closely (48 hours)
- [ ] Have rollback plan ready
- [ ] Document any issues encountered

## Rollback Plan

If issues are discovered:

```bash
# Rollback lockfile
git checkout uv.lock.backup
uv sync

# Or revert entire commit
git revert <commit-hash>

# Or rollback deployment
kubectl rollout undo deployment/mcp-server-langgraph
```

- [ ] Document rollback procedure
- [ ] Test rollback process in staging
- [ ] Know how to quickly revert in production

## Specific Dependency Guidelines

### Python Core Packages
- **LangChain**: Test with LangSmith after updates
- **FastAPI**: Check OpenAPI schema compatibility
- **Pydantic**: Watch for v1 → v2 breaking changes
- **Pytest**: Update test fixtures if needed
- **SQLAlchemy**: Test database queries thoroughly

### Infrastructure
- **Docker base images**: Test build and runtime
- **Kubernetes**: Validate manifests with updated APIs
- **Prometheus**: Check metrics compatibility
- **OpenTelemetry**: Verify trace export

## Frequency Guidelines

- **Security patches**: Immediately (within 24 hours)
- **Critical bug fixes**: Within 1 week
- **Minor updates**: Monthly
- **Major updates**: Quarterly (or as needed)
- **Full dependency audit**: Semi-annually

## Common Pitfalls to Avoid

- ❌ **Updating all at once**: Update incrementally
- ❌ **Skipping tests**: Always run full test suite
- ❌ **Ignoring changelogs**: Read release notes
- ❌ **No rollback plan**: Always have rollback ready
- ❌ **Updating in production**: Test in staging first
- ❌ **Ignoring deprecations**: Address warnings proactively
- ❌ **Batch unrelated updates**: Group logically related deps

## Validation Commands

```bash
# Check for updates
uv lock --upgrade --dry-run

# Security audit
pip-audit
safety check

# Run all tests
make test-unit test-integration test-e2e

# Check for breaking changes (example)
diff <(pip list --format=freeze) <(cat uv.lock)

# Validate lockfile
uv lock --check
```

## Success Criteria

- [ ] All tests passing
- [ ] No new security vulnerabilities
- [ ] No performance regressions
- [ ] Code review approved
- [ ] CI/CD passing
- [ ] Staging deployment successful
- [ ] Production deployment successful
- [ ] No incidents for 48 hours post-deployment
- [ ] Documentation updated

---

**Created**: 2025-11-15
**Frequency**: Monthly (minor), Quarterly (major), Immediate (security)
**Owner**: Engineering Team
