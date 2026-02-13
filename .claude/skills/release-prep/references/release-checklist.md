# Release Checklist Reference

Detailed checklists for version bumping, building artifacts, and release validation.

---

## Version Bump Checklist

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

---

## Build and Test Release Artifacts

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

---

## Release Checklist Template

```markdown
# Release v$VERSION Checklist

## Pre-Release
- [ ] All tests passing
- [ ] Code coverage >= target
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

## Release Types

### Patch Release (X.Y.Z -> X.Y.Z+1)
- Bug fixes only
- No new features
- Backward compatible
- Can deploy immediately

### Minor Release (X.Y.Z -> X.Y+1.0)
- New features
- Backward compatible
- Deprecations allowed
- Staged deployment recommended

### Major Release (X.Y.Z -> X+1.0.0)
- Breaking changes
- Architecture changes
- Migration required
- Careful deployment planning

---

**Last Updated**: 2025-10-20
