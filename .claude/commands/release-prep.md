---
description: Automated release readiness validation
argument-hint: <version>
---
# Release Preparation Checklist

**Usage**: `/release-prep <version>`

**Example**: `/release-prep 2.8.0`

**Purpose**: Automated release readiness validation

---

## 🚀 Release Preparation Workflow

### Step 1: Validate Version Number

Parse and validate version from $ARGUMENTS:

```bash
VERSION=$ARGUMENTS

# Validate semantic versioning format
if [[ ! $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "❌ Invalid version format. Use X.Y.Z (e.g., 2.8.0)"
    exit 1
fi

echo "✅ Preparing release v$VERSION"
```

### Step 2: Pre-Release Checklist

Run comprehensive validation:

**Code Quality**:
```bash
# 1. All tests passing
make test-unit
make test-integration
make test-all-quality

# 2. Linting clean
make lint-check

# 3. Security scan
make security-check

# 4. Type checking
mypy src/ --strict
```

**Status**: Pass/Fail for each

**Documentation**:
```bash
# 1. CHANGELOG.md updated
grep -q "## \[$VERSION\]" CHANGELOG.md

# 2. Version in pyproject.toml
grep -q "version = \"$VERSION\"" pyproject.toml

# 3. Breaking changes documented
[ -f BREAKING_CHANGES.md ] && grep -q "## $VERSION" BREAKING_CHANGES.md
```

**Deployment Configs**:
```bash
# 1. Validate all deployment configs
make validate-all

# 2. Check Docker image builds
docker build -t test:$VERSION .

# 3. Verify Helm chart version
grep -q "version: $VERSION" deployments/helm/langgraph-agent/Chart.yaml
```

### Step 3: Generate Release Notes

Create release notes from CHANGELOG.md and git commits:

```bash
# Extract changelog section for this version
sed -n "/## \[$VERSION\]/,/## \[/p" CHANGELOG.md > ${TMPDIR:-/tmp}/release_notes.md

# Add git commit summary since last tag
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "HEAD~10")
git log $LAST_TAG..HEAD --oneline --no-merges >> ${TMPDIR:-/tmp}/release_notes_commits.txt
```

**Format**:
```markdown
# Release v$VERSION

**Release Date**: YYYY-MM-DD
**Type**: Major | Minor | Patch

## 🎯 Highlights

- [Key feature 1]
- [Key feature 2]
- [Key improvement]

## ✨ New Features

- [List from CHANGELOG]

## 🐛 Bug Fixes

- [List from CHANGELOG]

## 📚 Documentation

- [Updates]

## ⚠️ Breaking Changes

- [If any]

## 📦 Deployment Notes

- [Any special deployment steps]

## 🔗 Links

- Full Changelog: [link]
- Documentation: [link]
```

### Step 4: Version Bump Checklist

Files to update with new version:

> **Note**: The sed commands below use `perl -pi -e` for cross-platform compatibility.
> Use `-i ''` on macOS or `-i` on Linux if using sed directly.

```bash
# 1. pyproject.toml (cross-platform)
perl -pi -e "s/version = \".*\"/version = \"$VERSION\"/" pyproject.toml

# 2. docker-compose.yml
perl -pi -e "s/image: .*:latest/image: langgraph-agent:$VERSION/" docker-compose.yml

# 3. Kubernetes manifests (Python for cross-platform)
uv run --frozen python3 -c "
from pathlib import Path
import re
for f in Path('deployments/kubernetes').rglob('*.yaml'):
    content = f.read_text()
    f.write_text(re.sub(r'image: .*:.*', f'image: langgraph-agent:$VERSION', content))
"

# 4. Helm chart
perl -pi -e "s/appVersion: \".*\"/appVersion: \"$VERSION\"/" deployments/helm/langgraph-agent/Chart.yaml

# 5. Kustomize
find deployments/kustomize -name "kustomization.yaml" -exec perl -pi -e "s/newTag: .*/newTag: $VERSION/" {} \;
```

### Step 5: Build and Test Release Artifacts

```bash
# 1. Build Docker image
docker build -t langgraph-agent:$VERSION .

# 2. Test Docker image
docker run --rm langgraph-agent:$VERSION --version

# 3. Build Python package
uv run --frozen python -m build

# 4. Validate package
twine check dist/*
```

### Step 6: Pre-Release Validation

**Final Checks**:
- [ ] All tests passing (100%)
- [ ] Code coverage maintained (≥69%)
- [ ] Linting clean
- [ ] Security scan clean
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Breaking changes documented (if any)
- [ ] Version bumped in all configs
- [ ] Docker image builds successfully
- [ ] Helm chart validates
- [ ] Release notes prepared

### Step 7: Create Release Branch

```bash
# Create release branch
git checkout -b release/v$VERSION

# Commit version bumps
git add .
git commit -m "chore(release): prepare v$VERSION release

- Update version in all deployment configs
- Update CHANGELOG.md
- Generate release notes

Release type: [Major|Minor|Patch]
"

# Push release branch
git push origin release/v$VERSION
```

### Step 8: Generate Release Commands

Provide commands for actual release:

```bash
echo "
=== Release Commands for v$VERSION ===

1. Create Git Tag:
   git tag -a v$VERSION -m 'Release v$VERSION'
   git push origin v$VERSION

2. Create GitHub Release:
   gh release create v$VERSION \\
     --title 'Release v$VERSION' \\
     --notes-file ${TMPDIR:-/tmp}/release_notes.md

3. Build and Push Docker Image:
   docker build -t your-registry/langgraph-agent:$VERSION .
   docker push your-registry/langgraph-agent:$VERSION

4. Deploy Helm Chart:
   helm package deployments/helm/langgraph-agent
   helm push langgraph-agent-$VERSION.tgz your-registry

5. Merge Release Branch:
   git checkout main
   git merge release/v$VERSION
   git push origin main
"
```

---

## 📋 Release Checklist Template

```markdown
# Release v$VERSION Checklist

## Pre-Release
- [ ] All tests passing
- [ ] Code coverage ≥ target
- [ ] Security scan clean
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Version bumped

## Build
- [ ] Docker image builds
- [ ] Python package builds
- [ ] Helm chart validates

## Deploy
- [ ] Tagged in git
- [ ] GitHub release created
- [ ] Docker image pushed
- [ ] Deployed to staging
- [ ] Validated in staging

## Post-Release
- [ ] Deployed to production
- [ ] Monitoring verified
- [ ] Documentation deployed
- [ ] Announcement sent
```

---

## 💡 Release Types

### Patch Release (X.Y.Z → X.Y.Z+1)
- Bug fixes only
- No new features
- Backward compatible
- Can deploy immediately

### Minor Release (X.Y.Z → X.Y+1.0)
- New features
- Backward compatible
- Deprecations allowed
- Staged deployment recommended

### Major Release (X.Y.Z → X+1.0.0)
- Breaking changes
- Architecture changes
- Migration required
- Careful deployment planning

---

## 🔗 Related Commands

- `/validate` - Run all validations
- `/test-summary` - Comprehensive test report
- `/progress-update` - Final sprint status

---

**Last Updated**: 2025-10-20
