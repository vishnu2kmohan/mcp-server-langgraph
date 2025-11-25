# Documentation Versioning Strategy

## Overview

This document describes the versioning strategy for maintaining documentation in sync with code releases.

**Last Updated**: 2025-10-18
**Status**: Active

---

## Documentation Locations

### 1. **Primary Sources** (Authoritative)

| Type | Location | Format | Purpose |
|------|----------|--------|---------|
| ADRs | `adr/*.md` | Markdown | Architecture decision records (source of truth) |
| Internal Docs | `docs-internal/*.md` | Markdown | Internal team documentation |
| Templates | `template/*.md` | Markdown | Cookiecutter template documentation |
| Root Docs | `*.md` (root) | Markdown | README, CHANGELOG, CONTRIBUTING, etc. |

### 2. **Published Documentation** (Generated/Derived)

| Type | Location | Format | Purpose |
|------|----------|--------|---------|
| Mintlify Docs | `docs/**/*.mdx` | MDX | Public-facing documentation |
| ADR Copies | `docs/architecture/*.mdx` | MDX | Published ADRs (auto-synced from `adr/`) |
| Release Notes | `docs/releases/*.mdx` | MDX | Version-specific release documentation |

---

## Version Synchronization

### Source of Truth Principle

**Rule**: Each document has ONE authoritative source. All other copies are generated or derived.

| Document | Source | Generated Copies | Sync Method |
|----------|--------|------------------|-------------|
| ADRs | `adr/*.md` | `docs/architecture/*.mdx` | `scripts/sync-adrs.py` |
| CHANGELOG | `CHANGELOG.md` | `docs/releases/*.mdx` | Manual (per release) |
| README | `README.md` | None | Single source |
| API Docs | Code docstrings | `docs/api-reference/*.mdx` | Manual |

---

## Versioning Strategy

### 1. **ADR Versioning**

**ADRs are immutable once accepted** - they represent point-in-time decisions.

**Workflow**:
```bash
# 1. Create/update ADR in source
vim adr/0027-new-decision.md

# 2. Sync to Mintlify
python scripts/sync-adrs.py

# 3. Verify sync
python scripts/sync-adrs.py --check

# 4. Commit both files
git add adr/0027-new-decision.md docs/architecture/adr-0027-new-decision.mdx
git commit -m "docs: add ADR-0027 for [topic]"
```

**Auto-Sync Validation**:
- CI/CD runs `scripts/sync-adrs.py --check` on every PR
- Fails if `adr/*.md` and `docs/architecture/*.mdx` are out of sync
- See: `.github/workflows/link-checker.yml`

**Modifying ADRs**:
- Minor corrections: Update source ADR, re-sync
- Major changes: Create new ADR, mark old as "Superseded"
- Status progression: Proposed → Accepted → Superseded → Deprecated

### 2. **Release Documentation Versioning**

**Each version gets dedicated release documentation**.

**Directory Structure**:
```
docs/releases/
├── overview.mdx           # Version comparison matrix
├── v2-7-0.mdx             # Latest release (detailed)
├── v2-6-0.mdx             # Previous release
├── v2-5-0.mdx
└── ...
```

**Release Documentation Workflow**:

```bash
# 1. Create release notes from CHANGELOG
cat CHANGELOG.md | grep -A100 "## \[2.8.0\]" > release-draft.md

# 2. Create Mintlify release page
cat > docs/releases/v2-8-0.mdx <<EOF
---
title: 'v2.8.0'
description: 'Brief description of major features'
---

<Note type="success">
  **Status**: Released (2025-10-20)
  **Breaking Changes**: [Yes/No]
</Note>

## Overview
...
EOF

# 3. Update overview
vim docs/releases/overview.mdx
# - Update "Latest Release" version
# - Add new version card
# - Update version comparison matrix

# 4. Update navigation
vim docs/docs.json
# Add to "Version History" group

# 5. Commit
git add docs/releases/v2-8-0.mdx docs/releases/overview.mdx docs/docs.json
git commit -m "docs: add v2.8.0 release documentation"
```

### 3. **Documentation Snapshots**

**For major releases, consider documentation snapshots**.

**Approach**:
- Tag documentation state with release: `git tag -a docs-v2.8.0 -m "Documentation snapshot for v2.8.0"`
- Host versioned docs: `https://docs.example.com/v2.8/` (if using Mintlify Pro)
- GitHub releases: Attach documentation PDF/archive

### 4. **CHANGELOG Versioning**

**CHANGELOG.md follows Keep a Changelog format**.

**Structure**:
```markdown
# Changelog

## [Unreleased]
### Added
### Changed
### Fixed

## [2.8.0] - 2025-10-20
### Added
...

## [2.7.0] - 2025-10-17
...
```

**Workflow**:
1. Add entries to `[Unreleased]` during development
2. On release, move `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD`
3. Create new empty `[Unreleased]` section
4. Update comparison links at bottom
5. Create corresponding `docs/releases/vX-Y-Z.mdx`

---

## Automation

### 1. **ADR Sync Script**

**Script**: `scripts/sync-adrs.py`

**Features**:
- ✅ Sync all ADRs: `python scripts/sync-adrs.py`
- ✅ Sync specific ADR: `python scripts/sync-adrs.py --adr 0027`
- ✅ Check sync status: `python scripts/sync-adrs.py --check`
- ✅ Dry run: `python scripts/sync-adrs.py --dry-run`

**CI/CD Integration**:
```yaml
# .github/workflows/link-checker.yml
- name: Check ADR Sync
  run: python scripts/sync-adrs.py --check
```

### 2. **Link Checking**

**Script**: `scripts/check-links.py`

**Features**:
- ✅ Check internal links
- ✅ Categorize by priority (high: GitHub, ADR, docs; low: other)
- ✅ Exclude archives and reports
- ✅ CI/CD integration

**Workflow**:
```yaml
# .github/workflows/link-checker.yml
on:
  pull_request:
    paths:
      - '**.md'
      - '**.mdx'
  schedule:
    - cron: '0 9 * * 1'  # Weekly
```

### 3. **Markdown Validation**

**Tool**: markdownlint-cli2

**Config**: `.markdownlint.json`

**Runs on**: Every PR with markdown changes

---

## Migration Guide Template

When creating major version releases with breaking changes, include a migration guide:

**Template**: `docs/guides/migration-vX-Y.mdx`

```markdown
---
title: "Migration Guide vX.Y-1 → vX.Y"
description: "Guide for upgrading from vX.Y-1 to vX.Y"
icon: "arrow-up"
---

<Warning>
**Breaking Changes**: [List major breaking changes]
</Warning>

## Summary of Changes

### What Changed?

**Before (vX.Y-1)**:
```[language]
[old code example]
```

**After (vX.Y)**:
```[language]
[new code example]
```

### Why This Change?

[Explanation of rationale]

---

## Migration Steps

<Steps>
  <Step title="Step 1">
    [Detailed instructions]
  </Step>
  ...
</Steps>

---

## Troubleshooting

[Common issues and solutions]
```

---

## Documentation Review Checklist

### Before Every Release

- [ ] **CHANGELOG updated** with all changes since last release
- [ ] **Release documentation created** in `docs/releases/vX-Y-Z.mdx`
- [ ] **Overview updated** with latest version info
- [ ] **Navigation updated** in `docs/docs.json`
- [ ] **ADRs synced** via `scripts/sync-adrs.py`
- [ ] **Links validated** via `scripts/check-links.py`
- [ ] **Migration guide created** (if breaking changes)
- [ ] **API docs updated** (if API changes)
- [ ] **README badges updated** (version, coverage, etc.)
- [ ] **Examples updated** (if API changes)

### Monthly Documentation Audit

- [ ] Run `scripts/check-links.py` for broken links
- [ ] Run `scripts/sync-adrs.py --check` for ADR sync
- [ ] Review and archive old reports (>90 days)
- [ ] Update version comparison matrix
- [ ] Review and update getting-started guides
- [ ] Verify deployment documentation accuracy
- [ ] Check for stale TODOs and outdated references

---

## Documentation Categories

### 1. **Versioned Documentation**

Changes with each release:
- Release notes (`docs/releases/*.mdx`)
- API reference (`docs/api-reference/*.mdx`)
- Migration guides (`docs/guides/migration-*.mdx`)
- CHANGELOG.md

### 2. **Living Documentation**

Updates independently of releases:
- Architecture decisions (`adr/*.md`)
- Internal guides (`docs-internal/*.md`)
- Deployment guides (`docs/deployment/*.mdx`)
- Development setup (`docs/advanced/*.mdx`)

### 3. **Immutable Documentation**

Never changes after creation:
- Accepted ADRs (except for clarifications)
- Historical release notes
- Archived reports

---

## Best Practices

### 1. **Semantic Versioning Alignment**

Documentation versions align with package versions:

| Version Type | Documentation Changes |
|--------------|----------------------|
| **Patch** (X.Y.Z) | Bug fixes, minor doc updates, typo corrections |
| **Minor** (X.Y.0) | New features, new guides, expanded documentation |
| **Major** (X.0.0) | Breaking changes, migration guides, restructuring |

### 2. **Single Source of Truth**

- Never duplicate content across files
- Use includes or links to reference content
- Maintain clear source → derived relationships
- Automate synchronization where possible

### 3. **Backward Compatibility**

- Keep old release documentation accessible
- Maintain redirects for moved documentation
- Archive outdated docs, don't delete
- Provide migration paths in documentation

### 4. **Link Hygiene**

- Use relative links within documentation
- Avoid deep links that break on refactoring
- Prefer stable references (ADR numbers, version tags)
- Validate links in CI/CD

### 5. **Documentation Testing**

Treat documentation as code:
- Version control all documentation
- Review documentation changes in PRs
- Automated link checking
- Automated sync validation
- Markdown linting

---

## Tools & Scripts

| Tool | Purpose | Usage |
|------|---------|-------|
| `scripts/sync-adrs.py` | Sync ADRs to Mintlify | `python scripts/sync-adrs.py` |
| `scripts/check-links.py` | Validate internal links | `python scripts/check-links.py` |
| `markdownlint-cli2` | Markdown syntax validation | Automatic in CI/CD |
| `lychee` | External link checking | Automatic in CI/CD |

---

## Future Improvements

### Short-term (Next Quarter)

- [ ] **Automated release note generation** from CHANGELOG
- [ ] **Documentation diffing** between versions
- [ ] **API documentation generation** from code
- [ ] **Inline version warnings** ("This feature is available in v2.7+")

### Long-term (Next Year)

- [ ] **Versioned documentation hosting** (multiple version sites)
- [ ] **Documentation analytics** (track usage, identify gaps)
- [ ] **Interactive examples** (embedded code playgrounds)
- [ ] **Video documentation** (setup guides, features demos)
- [ ] **Automated screenshot updates** (visual documentation)

---

## FAQ

### Q: When should I create a new ADR?

**A**: Create an ADR when:
- Making significant architectural decisions
- Choosing between alternative approaches
- Decisions with long-term consequences
- Decisions that others need to understand

### Q: How do I handle documentation for experimental features?

**A**: Use feature flags and clearly mark as experimental:
```mdx
<Warning>
**Experimental Feature**: This feature is experimental and may change in future releases.
Enable with: `ENABLE_EXPERIMENTAL_FEATURE=true`
</Warning>
```

### Q: Should I version internal documentation?

**A**: Generally no. Internal docs (`docs-internal/`) are living documents that update independently. However:
- Tag snapshots for major milestones
- Archive outdated internal docs to `docs-internal/archive/`
- Keep deployment runbooks version-specific if needed

### Q: How do I deprecate documentation?

**A**:
1. Add deprecation notice at top of page
2. Provide link to replacement documentation
3. Keep deprecated docs accessible (don't delete)
4. After 2 major versions, move to `archive/`

Example:
```mdx
<Warning>
**Deprecated**: This guide is for v2.5 and earlier. For v2.7+, see [New Guide](/path/to/replacement-guide).
</Warning>
```

---

## Support

For questions about documentation versioning:
1. Review this guide
2. Check recent documentation commits
3. Review [ADR-0018: Semantic Versioning Strategy](../adr/adr-0018-semantic-versioning-strategy.md)
4. Open a discussion on GitHub

---

**Last Updated**: 2025-10-18
**Version**: 1.0.0
**Status**: Active
