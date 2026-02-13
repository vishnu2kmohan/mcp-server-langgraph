---
name: release-prep
description: Validate release readiness with automated checks and artifact generation. Use when preparing a new version release.
argument-hint: "<version>"
allowed-tools:
  - Bash(uv:*)
  - Bash(npm:*)
  - Bash(git:*)
  - Bash(gh:*)
  - Read
  - Glob
  - Grep
disable-model-invocation: true
---
# Release Preparation Checklist

**Usage**: `/release-prep <version>`

**Example**: `/release-prep 2.8.0`

**Purpose**: Automated release readiness validation

---

## Release Preparation Workflow

### Step 1: Validate Version Number

Parse and validate version from $ARGUMENTS:

```bash
VERSION=$ARGUMENTS

# Validate semantic versioning format
if [[ ! $VERSION =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Invalid version format. Use X.Y.Z (e.g., 2.8.0)"
    exit 1
fi

echo "Preparing release v$VERSION"
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

For the release notes format template, see [references/version-bump-procedures.md](references/version-bump-procedures.md).

### Step 4: Version Bump and Build Artifacts

For detailed version bump procedures (files to update, build/test commands), see [references/release-checklist.md](references/release-checklist.md).

### Step 5: Pre-Release Validation

**Final Checks**:
- [ ] All tests passing (100%)
- [ ] Code coverage maintained (>=69%)
- [ ] Linting clean
- [ ] Security scan clean
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
- [ ] Breaking changes documented (if any)
- [ ] Version bumped in all configs
- [ ] Docker image builds successfully
- [ ] Helm chart validates
- [ ] Release notes prepared

### Step 6: Create Release Branch and Generate Commands

For release branch creation, release commands, and post-release procedures, see [references/version-bump-procedures.md](references/version-bump-procedures.md).

---

## Related Commands

- `/validate` - Run all validations
- `/test-summary` - Comprehensive test report
- `/progress-update` - Final sprint status

---

**Last Updated**: 2025-10-20
