# Act - Local GitHub Actions Testing Guide

This guide explains how to use [act](https://github.com/nektos/act) to test GitHub Actions workflows locally before pushing to GitHub.

## What is Act?

Act allows you to run your GitHub Actions workflows locally using Docker. This enables:
- **Fast feedback**: Test workflows without pushing commits
- **Cost savings**: Avoid consuming GitHub Actions minutes during development
- **Debugging**: Inspect workflow execution with verbose logging
- **Offline development**: Work on workflows without internet connectivity

## Prerequisites

### 1. Install Act

```bash
# macOS (using Homebrew)
brew install act

# Linux (using curl)
curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash

# Or download from: https://github.com/nektos/act/releases
```

Verify installation:
```bash
act --version
# Should show: act version 0.2.82 or higher
```

### 2. Install Docker

Act requires Docker to run workflow containers:
```bash
# Verify Docker is installed and running
docker --version
docker ps
```

### 3. Install GitHub CLI (gh)

Act is configured to use the GitHub CLI for authentication (more secure than storing tokens):
```bash
# macOS
brew install gh

# Linux
curl -sS https://webi.sh/gh | sh

# Or see: https://cli.github.com/manual/installation
```

Authenticate with GitHub:
```bash
# Login to GitHub
gh auth login

# Verify authentication
gh auth status
```

Act will use your `gh` authentication automatically via:
```bash
act -s GITHUB_TOKEN="$(gh auth token)" [command]
```

**Why gh CLI?**
- ✅ No need to store tokens in files
- ✅ Automatic token refresh
- ✅ Same credentials as your terminal
- ✅ More secure (no plaintext tokens in `.secrets`)

## Configuration Files

This repository includes pre-configured Act files:

### `.actrc`
Main configuration file with optimized settings:
- Uses medium-sized Ubuntu image (`catthehacker/ubuntu:act-latest` ~5.5GB)
- Enables Docker-in-Docker for building images
- Configures artifact storage in `/tmp/act-artifacts`
- Enables container reuse for faster runs
- Verbose output for debugging

### `.secrets`
Template for **optional** secrets (GITHUB_TOKEN is injected via gh CLI):
- `SLACK_WEBHOOK` (optional, for notifications)
- `SLACK_SECURITY_WEBHOOK` (optional, for security alerts)
- `PYPI_TOKEN` (optional, for release testing)
- `MCP_REGISTRY_TOKEN` (optional, for MCP registry updates)

**Note**: `GITHUB_TOKEN` is NOT stored in `.secrets`. It's injected from `gh` CLI.

### `.github/act-event.json`
Event payload that simulates a push to the main branch.

## Quick Start

### Optional: Create a Shell Alias

To avoid typing `act -s GITHUB_TOKEN="$(gh auth token)"` every time, create an alias:

```bash
# Add to your ~/.bashrc or ~/.zshrc
alias act-gh='act -s GITHUB_TOKEN="$(gh auth token)"'

# Or as a function for better compatibility
act-gh() {
  act -s GITHUB_TOKEN="$(gh auth token)" "$@"
}

# Then use it like:
act-gh push --list
act-gh push --workflows .github/workflows/ci.yaml
```

**For the rest of this guide, we'll use the full command for clarity.**

### List Available Workflows

See all workflows triggered by a `push` event:
```bash
act -s GITHUB_TOKEN="$(gh auth token)" push --list
```

This shows 40+ jobs across 12 workflows, organized by execution stage (0-4).

### Test Specific Workflows

**All commands use the pattern**: `act -s GITHUB_TOKEN="$(gh auth token)" [options]`

#### 1. Build Hygiene (Fastest, No Dependencies)
```bash
act -s GITHUB_TOKEN="$(gh auth token)" push --workflows .github/workflows/build-hygiene.yaml
```
**What it does**: Checks for accidentally committed build artifacts
**Runtime**: ~30 seconds
**Docker images needed**: None (uses git commands only)

#### 2. CI Pipeline - Unit Tests
```bash
act -s GITHUB_TOKEN="$(gh auth token)" push --workflows .github/workflows/ci.yaml --job test
```
**What it does**: Runs pytest unit tests on Python 3.10, 3.11, 3.12
**Runtime**: ~5-10 minutes (matrix of 3 Python versions)
**Dependencies**: Python, uv, pytest

Test a specific Python version:
```bash
act -s GITHUB_TOKEN="$(gh auth token)" push --workflows .github/workflows/ci.yaml --job test --matrix python-version:3.12
```

#### 3. Quality Tests
```bash
act -s GITHUB_TOKEN="$(gh auth token)" push --workflows .github/workflows/quality-tests.yaml
```
**What it does**: Runs property-based, contract, regression, and benchmark tests
**Runtime**: ~10-15 minutes
**Dependencies**: hypothesis, schemathesis, pytest-benchmark

#### 4. Coverage Tracking
```bash
act -s GITHUB_TOKEN="$(gh auth token)" push --workflows .github/workflows/coverage-trend.yaml
```
**What it does**: Tracks test coverage trends over time
**Runtime**: ~3-5 minutes
**Dependencies**: pytest-cov, pandas

## Workflows That Work Well with Act

| Workflow | Command | Runtime | Notes |
|----------|---------|---------|-------|
| **build-hygiene** | `act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/build-hygiene.yaml` | 30s | ✅ No external dependencies |
| **ci (test only)** | `act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml --job test --matrix python-version:3.12` | 5min | ✅ Fast unit tests |
| **ci (pre-commit)** | `act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml --job pre-commit` | 2min | ✅ Code quality checks |
| **quality-tests** | `act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/quality-tests.yaml` | 15min | ✅ Advanced testing |
| **coverage-trend** | `act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/coverage-trend.yaml` | 5min | ✅ Coverage analysis |
| **track-skipped-tests** | `act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/track-skipped-tests.yaml` | 3min | ✅ Test monitoring |
| **link-checker** | `act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/link-checker.yaml` | 5min | ✅ Documentation validation |
| **optional-deps-test** | `act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/optional-deps-test.yaml` | 10min | ✅ Dependency testing |

## Workflows with Limitations

### Docker Builds (Slow but Functional)
```bash
# Full Docker build workflow (SLOW - ~30+ minutes)
act -s GITHUB_TOKEN="$(gh auth token)" push --workflows .github/workflows/ci.yaml --job docker-build
```
**Why slow**: Builds 3 Docker images (base, full, test) with multi-stage builds
**Workaround**: Use `--matrix variant:base` to test one variant only

### E2E Tests (Requires Manual Setup)
```bash
# Start infrastructure first
docker-compose -f docker-compose.test.yml up -d

# Then run E2E tests
act -s GITHUB_TOKEN="$(gh auth token)" push --workflows .github/workflows/e2e-tests.yaml
```
**Why manual setup**: E2E tests need PostgreSQL, Redis, OpenFGA, Keycloak, Qdrant
**Services**: Uses docker-compose.test.yml for dependencies

### GCP Workflows (Cannot Run Locally)
These workflows require GCP credentials and Workload Identity:
- `deploy-staging-gke.yaml`
- `deploy-production-gke.yaml`
- `gcp-compliance-scan.yaml`
- `gcp-drift-detection.yaml`

**Skip with**:
```bash
# Test only non-GCP workflows
act -s GITHUB_TOKEN="$(gh auth token)" push --workflows .github/workflows/ci.yaml
```

### Release Workflow (Limited Testing)
```bash
# Test release workflow (will skip actual publishing)
act -s GITHUB_TOKEN="$(gh auth token)" push --workflows .github/workflows/release.yaml
```
**Limitations**:
- Requires tag push event (not simulated by default)
- Skips PyPI publishing (unless `PYPI_TOKEN` is set)
- Skips MCP registry updates (unless `MCP_REGISTRY_TOKEN` is set)
- Docker registry pushes won't work without registry credentials

## Common Use Cases

### 1. Quick Validation Before Commit
```bash
# Run build hygiene and pre-commit checks (fast)
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/build-hygiene.yaml && \
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml --job pre-commit
```

### 2. Full Test Suite (Slow but Thorough)
```bash
# Run all testable workflows (20-30 minutes)
act -s GITHUB_TOKEN="$(gh auth token)" push \
  -W .github/workflows/build-hygiene.yaml \
  -W .github/workflows/ci.yaml \
  -W .github/workflows/quality-tests.yaml \
  -W .github/workflows/coverage-trend.yaml \
  -W .github/workflows/optional-deps-test.yaml
```

### 3. Debug Failing Workflow
```bash
# Run with extra verbose output
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml --job test -v
```

### 4. Test with Specific Matrix Values
```bash
# Test only Python 3.12
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml --job test --matrix python-version:3.12

# Test specific Docker variant
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml --job docker-build --matrix variant:base
```

## Advanced Usage

### Custom Event Payloads

Simulate different events (pull_request, release, etc.):
```bash
# Create custom event file
cat > custom-event.json <<EOF
{
  "pull_request": {
    "number": 42,
    "head": {
      "ref": "feature-branch"
    }
  }
}
EOF

# Use custom event
act pull_request --eventpath custom-event.json
```

### Dry Run (Show What Would Run)
```bash
# See execution plan without running
act -s GITHUB_TOKEN="$(gh auth token)" push --list
act -s GITHUB_TOKEN="$(gh auth token)" push --dryrun
```

### Interactive Debugging
```bash
# Run workflow and drop into shell on failure
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml --job test --interactive
```

### Reuse Containers for Speed
```bash
# Keep containers running between invocations
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml --reuse
```
Note: This is already enabled in `.actrc`

## Troubleshooting

### Issue: "Error: Invalid JWT" or "Bad credentials"
**Cause**: Missing or invalid GitHub token from `gh` CLI
**Fix**:
```bash
# Check if gh is authenticated
gh auth status

# If not authenticated, login
gh auth login

# Verify token is accessible
gh auth token
```

### Issue: Docker permission denied
**Cause**: Current user not in docker group
**Fix**:
```bash
sudo usermod -aG docker $USER
# Log out and back in for changes to take effect
```

### Issue: "Error: failed to start container"
**Cause**: Docker image not found or Docker daemon not running
**Fix**:
```bash
# Check Docker is running
systemctl status docker

# Pull required image
docker pull catthehacker/ubuntu:act-latest
```

### Issue: Workflow runs but steps fail
**Cause**: Missing dependencies or environment differences
**Fix**: Check workflow logs with `-v` flag for detailed output

### Issue: "Unknown Property" or "Unknown Variable Access"
**Cause**: Act's YAML schema validator is strict
**Fix**: This has been resolved in this repository by:
- Using `env` context instead of `secrets` in step-level `if` conditions
- Mapping secrets to environment variables at job level

## Performance Tips

### 1. Use Smaller Images for Simple Workflows
Edit `.actrc` to use micro image for basic workflows:
```bash
-P ubuntu-latest=node:16-buster-slim  # Only 500MB vs 5.5GB
```

### 2. Skip Slow Workflows
```bash
# Test only fast workflows
act -s GITHUB_TOKEN="$(gh auth token)" push \
  -W .github/workflows/build-hygiene.yaml \
  -W .github/workflows/ci.yaml --job pre-commit
```

### 3. Use Matrix Filtering
```bash
# Test one Python version instead of all three
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml --job test --matrix python-version:3.12
```

### 4. Enable Container Reuse
Already enabled in `.actrc` via `--reuse` flag

### 5. Use Local Caching
Act automatically caches actions and dependencies in `/tmp/act-artifacts`

## Integration with Make Commands

This project includes Makefile targets that Act can use:

```bash
# These make commands work inside Act containers too:
make test-unit           # Fast unit tests
make test-all-quality    # All quality tests
make validate-all        # All validations
```

## Limitations and Known Issues

### Act Limitations
1. **No GitHub Environments**: Environment protection rules not supported
2. **No OIDC**: Workload Identity Federation doesn't work
3. **Limited GitHub API**: Some GitHub Actions APIs unavailable
4. **Sequential Matrix**: Matrix builds run sequentially (not parallel)
5. **No Caching**: `actions/cache` doesn't persist between runs

### Workflow-Specific Limitations
1. **GCP Deployments**: Require real GCP credentials (skip these)
2. **Release Publishing**: PyPI/registry pushes won't work without credentials
3. **E2E Tests**: Need manual Docker Compose setup first
4. **Security Scans**: Some scanners may not work in containers

## Best Practices

### 1. Test Incrementally
Start with simple workflows, then add more complex ones:
```bash
# Step 1: Quick validation
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/build-hygiene.yaml

# Step 2: Unit tests
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml --job test --matrix python-version:3.12

# Step 3: Full CI (if step 2 passes)
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml
```

### 2. Use Specific Jobs
Don't run entire workflows if you only need specific jobs:
```bash
# Good: Test only what changed
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml --job test

# Avoid: Running everything (includes slow Docker builds)
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml
```

### 3. Use Shell Alias for Convenience
Add the `act-gh` alias to your shell profile to avoid repetitive typing:
```bash
# Add to ~/.bashrc or ~/.zshrc
act-gh() {
  act -s GITHUB_TOKEN="$(gh auth token)" "$@"
}
```

### 4. Clean Up Containers Periodically
```bash
# Remove old act containers
docker ps -a | grep act | awk '{print $1}' | xargs docker rm

# Clean up images
docker image prune -f
```

### 5. Use Git Hooks for Automated Testing
Add to `.git/hooks/pre-push`:
```bash
#!/bin/bash
echo "Running Act tests before push..."
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/build-hygiene.yaml
if [ $? -ne 0 ]; then
  echo "Act tests failed. Push aborted."
  exit 1
fi
```

## Additional Resources

- **Act Documentation**: https://nektosact.com/
- **Act GitHub**: https://github.com/nektos/act
- **GitHub Actions Docs**: https://docs.github.com/en/actions
- **Docker Images**: https://github.com/catthehacker/docker_images
- **Schema Validation**: https://nektosact.com/usage/schema.html

## Frequently Asked Questions

### Q: How do I test only changed files?
**A**: Act doesn't have built-in change detection. Use git:
```bash
# Test if specific files changed
if git diff --name-only HEAD~1 | grep -q "tests/"; then
  act push -W .github/workflows/ci.yaml --job test
fi
```

### Q: Can I run act in CI/CD?
**A**: Yes, but it's resource-intensive. Better to use act locally and GitHub Actions for CI.

### Q: How do I debug failing steps?
**A**: Use verbose mode and check container logs:
```bash
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml --job test -v
docker logs <container-id>
```

### Q: Why are matrix builds so slow?
**A**: Act runs matrix combinations sequentially. Test specific combinations:
```bash
act -s GITHUB_TOKEN="$(gh auth token)" push --job test --matrix python-version:3.12
```

### Q: Can I use act with VS Code?
**A**: Yes, use the [GitHub Actions extension](https://marketplace.visualstudio.com/items?itemName=github.vscode-github-actions)

## Summary

Act is a powerful tool for testing GitHub Actions locally. This repository is configured with:
- ✅ Optimized `.actrc` for fast local testing
- ✅ GitHub CLI (`gh`) integration for secure token management
- ✅ `.secrets` template for optional workflow credentials
- ✅ Schema validation fixes for act compatibility
- ✅ Comprehensive documentation (this file)

**Recommended Workflow**:
1. Write/modify workflow file
2. Test locally with `act -s GITHUB_TOKEN="$(gh auth token)" push --list`
3. Run specific jobs: `act -s GITHUB_TOKEN="$(gh auth token)" push -W <workflow> --job <job>`
4. Push to GitHub when tests pass

**Quick Commands**:
```bash
# List workflows
act -s GITHUB_TOKEN="$(gh auth token)" push --list

# Fast validation
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/build-hygiene.yaml

# Unit tests (single Python version)
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml --job test --matrix python-version:3.12

# Full test suite (slow)
act -s GITHUB_TOKEN="$(gh auth token)" push -W .github/workflows/ci.yaml -W .github/workflows/quality-tests.yaml
```

---

**Last Updated**: 2025-11-02
**Act Version**: 0.2.82
**Project**: mcp-server-langgraph
