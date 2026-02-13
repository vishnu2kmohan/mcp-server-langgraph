# Version Bump Procedures Reference

Release branch creation, release commands, and release notes format.

---

## Create Release Branch

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

---

## Generate Release Commands

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

## Release Notes Format Template

```markdown
# Release v$VERSION

**Release Date**: YYYY-MM-DD
**Type**: Major | Minor | Patch

## Highlights

- [Key feature 1]
- [Key feature 2]
- [Key improvement]

## New Features

- [List from CHANGELOG]

## Bug Fixes

- [List from CHANGELOG]

## Documentation

- [Updates]

## Breaking Changes

- [If any]

## Deployment Notes

- [Any special deployment steps]

## Links

- Full Changelog: [link]
- Documentation: [link]
```

---

**Last Updated**: 2025-10-20
