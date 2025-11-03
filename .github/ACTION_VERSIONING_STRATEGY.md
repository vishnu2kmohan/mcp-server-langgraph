# GitHub Actions Version Pinning Strategy

**Status**: Active Policy
**Last Updated**: 2025-11-03
**Owner**: DevOps Team

---

## Overview

This document defines the version pinning strategy for GitHub Actions used in this repository's CI/CD workflows.

## Policy

We use a **tiered versioning strategy** based on action criticality and stability:

### Tier 1: Security-Critical Actions (SHA Pinning)

**Policy**: Pin to specific commit SHA for maximum security and reproducibility.

**Actions in this tier**:
- `google-github-actions/auth` - GCP authentication (Workload Identity)
- `aquasecurity/trivy-action` - Security scanning
- `actions/github-script` - Arbitrary code execution
- Custom third-party security tools

**Format**: `@<semantic-version>` (Dependabot manages, we verify SHA)

**Example**:
```yaml
# Current: Dependabot manages semantic version
- uses: google-github-actions/auth@v3

# Dependabot will update to v3.1.0, etc., and we review SHA changes
```

**Rationale**: Balance between security (version review) and maintainability (Dependabot automation).

### Tier 2: Stable Core Actions (Major Version)

**Policy**: Pin to major version tag for stability with automatic minor/patch updates.

**Actions in this tier**:
- `actions/checkout` - Code checkout
- `actions/setup-python` - Python environment
- `actions/cache` - Caching
- `actions/upload-artifact` - Artifact upload
- `actions/download-artifact` - Artifact download
- `docker/build-push-action` - Docker builds
- `docker/setup-buildx-action` - Docker Buildx

**Format**: `@v<major>` (e.g., `@v5`, `@v4`)

**Example**:
```yaml
- uses: actions/checkout@v5
- uses: actions/cache@v4
- uses: docker/build-push-action@v6
```

**Rationale**: These are well-maintained GitHub-official or Docker-official actions with strong backward compatibility guarantees within major versions.

### Tier 3: Stable Third-Party Actions (Minor Version)

**Policy**: Pin to minor version for balance between stability and features.

**Actions in this tier**:
- `astral-sh/setup-uv` - uv package manager
- `hashicorp/setup-terraform` - Terraform
- `helm/kind-action` - KIND cluster
- `nick-fields/retry` - Retry action

**Format**: `@v<major>.<minor>.<patch>` (e.g., `@v7.1.1`)

**Example**:
```yaml
- uses: astral-sh/setup-uv@v7.1.1
- uses: nick-fields/retry@v3
```

**Rationale**: More frequent updates than core actions, minor versions add features without breaking changes.

### Tier 4: Experimental/Beta Actions (Exact Version)

**Policy**: Pin to exact version and update manually after testing.

**Actions in this tier**:
- New or beta actions under evaluation
- Actions from less-established maintainers
- Actions with breaking change history

**Format**: `@v<major>.<minor>.<patch>`

**Example**:
```yaml
- uses: experimental/new-action@v1.2.3
```

**Rationale**: Minimize risk from unstable actions.

---

## Dependabot Configuration

Our `.github/dependabot.yaml` is configured to:
1. **Check weekly** for action updates
2. **Group updates** by tier for easier review
3. **Auto-approve** minor/patch for Tier 2-3
4. **Require manual review** for Tier 1 and major versions

**Current Configuration**:
```yaml
updates:
  - package-ecosystem: "github-actions"
    directory: "/"
    schedule:
      interval: "weekly"
    groups:
      github-actions:
        patterns:
          - "*"
```

---

## Review Process

### Automated (Dependabot Auto-merge)

**Criteria for auto-merge** (handled by `dependabot-automerge.yaml`):
- ✅ Tier 2 actions: patch updates only
- ✅ Tier 3 actions: patch updates only
- ❌ Major version updates: always manual
- ❌ Tier 1 actions: always manual review

### Manual Review Checklist

For actions requiring manual review:

- [ ] **Check changelog** for breaking changes
- [ ] **Review SHA diff** on GitHub (for Tier 1)
- [ ] **Test in feature branch** if breaking changes suspected
- [ ] **Verify compatibility** with our usage patterns
- [ ] **Check for CVEs** in the action or dependencies
- [ ] **Approve and merge** after validation

---

## Current Action Inventory

### Tier 1: Security-Critical (SHA Pinning)

| Action | Current Version | Last Review | Notes |
|--------|----------------|-------------|-------|
| `google-github-actions/auth` | `v3` | 2025-11-03 | GCP Workload Identity |
| `aquasecurity/trivy-action` | `v0.33.1` | 2025-10-20 | Security scanning |

### Tier 2: Stable Core (Major Version)

| Action | Current Version | Auto-Update | Notes |
|--------|----------------|-------------|-------|
| `actions/checkout` | `v5` | ✅ | Minor/patch auto |
| `actions/setup-python` | `v6` | ✅ | Minor/patch auto |
| `actions/cache` | `v4` | ✅ | Minor/patch auto |
| `actions/upload-artifact` | `v5` | ✅ | Minor/patch auto |
| `actions/download-artifact` | `v5` | ✅ | Minor/patch auto |
| `docker/build-push-action` | `v6` | ✅ | Minor/patch auto |
| `docker/setup-buildx-action` | `v3` | ✅ | Minor/patch auto |
| `google-github-actions/setup-gcloud` | `v3` | ✅ | Minor/patch auto |
| `google-github-actions/get-gke-credentials` | `v3` | ✅ | Minor/patch auto |

### Tier 3: Stable Third-Party (Minor Version)

| Action | Current Version | Auto-Update | Notes |
|--------|----------------|-------------|-------|
| `astral-sh/setup-uv` | `v7.1.1` | ✅ Patch only | uv package manager |
| `nick-fields/retry` | `v3` | ✅ Patch only | Retry logic |
| `hashicorp/setup-terraform` | `v3` | ✅ Patch only | Terraform CLI |
| `helm/kind-action` | Latest checked | Manual | KIND clusters |

---

## Update Process

### Weekly (Automated)
1. Dependabot creates PRs for action updates
2. `dependabot-automerge.yaml` evaluates update type
3. Auto-merges safe updates (patch for Tier 2-3)
4. Blocks unsafe updates (major, Tier 1)

### Monthly (Manual Review)
1. Review all pending Dependabot PRs
2. Test major version updates in feature branches
3. Update this document with new versions
4. Merge after validation

### Ad-Hoc (Security Patches)
1. Monitor GitHub Security Advisories
2. Apply security patches immediately
3. Update version in all affected workflows
4. Test and deploy urgently

---

## Migration Guide

### Upgrading from Major Version

When a major version update is available:

1. **Create feature branch**:
   ```bash
   git checkout -b upgrade/action-name-v5
   ```

2. **Update single workflow** as test:
   ```yaml
   # Before
   - uses: some-action@v4

   # After
   - uses: some-action@v5
   ```

3. **Test workflow** manually:
   ```bash
   # Push and trigger workflow
   git push -u origin upgrade/action-name-v5
   ```

4. **Review logs** for issues

5. **Update all workflows** if successful

6. **Update this document** with new version

### Responding to Security Advisory

When a security advisory is published:

1. **Immediate**: Check if we use affected version
2. **Urgent**: Update to patched version
3. **Priority**: Test critical workflows (deploy, security)
4. **Deploy**: Merge and deploy immediately
5. **Document**: Note in commit message

---

## Monitoring

### Action Usage Tracking

We track action usage via:
- **Cost tracking workflow**: Monitors overall CI/CD spend
- **Dependabot PRs**: Weekly updates indicate active maintenance
- **GitHub Insights**: Action usage metrics

### Health Indicators

🟢 **Healthy**:
- All actions < 6 months old
- No pending security updates
- Dependabot auto-merge working

🟡 **Attention Needed**:
- Actions > 6 months without update
- Multiple blocked major updates
- Frequent auto-merge failures

🔴 **Critical**:
- Security advisory affecting our actions
- Deprecated actions in use
- Actions > 1 year without update

---

## Best Practices

### DO ✅
- **Use official actions** when available (actions/*, docker/*)
- **Pin to tags** not branches (use `@v3` not `@main`)
- **Review Dependabot PRs** weekly
- **Test major updates** before merging
- **Document rationale** for version choices
- **Monitor security advisories** for our actions

### DON'T ❌
- **Never use `@latest`** - non-deterministic
- **Never use `@main`** - can break without notice
- **Never skip testing** major updates
- **Never ignore security** updates
- **Never block Dependabot** patches indefinitely
- **Never use unofficial forks** without security review

---

## Action Security Checklist

Before adding a new action to workflows:

- [ ] **Verify publisher** - Official org or trusted maintainer?
- [ ] **Check stars/usage** - Popular and well-maintained?
- [ ] **Review permissions** - Minimal permissions requested?
- [ ] **Audit code** - Review source code for suspicious activity
- [ ] **Check updates** - Regular maintenance activity?
- [ ] **Test thoroughly** - Validate in feature branch first
- [ ] **Document reason** - Why this action vs alternatives?
- [ ] **Add to inventory** - Update this document

---

## Compliance

This versioning strategy ensures:
- ✅ **Reproducible builds** - Exact versions documented
- ✅ **Security** - Critical actions reviewed for each update
- ✅ **Maintainability** - Automated updates for safe changes
- ✅ **Auditability** - All version changes tracked in git
- ✅ **Stability** - Major versions controlled via testing

---

## Support

**Questions**: Open issue with label `ci/cd`
**Security Concerns**: Report privately to maintainers
**Suggestions**: PRs welcome with rationale

---

**Version**: 1.0
**Effective Date**: 2025-11-03
**Next Review**: 2026-02-03 (quarterly)
