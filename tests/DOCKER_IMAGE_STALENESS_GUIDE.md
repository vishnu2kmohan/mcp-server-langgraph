# Docker Image Staleness Troubleshooting Guide

## Problem: Test Failures in Docker but Passes Locally

### Symptoms

- Tests pass when run locally: `pytest tests/api/test_api_keys_endpoints.py::TestCreateAPIKey`
- Tests fail when run in Docker: `make test-integration`
- Error messages like `401 Unauthorized` or similar behavior differences
- Recent fixes don't appear to be working in CI/CD

### Root Cause

**The Docker test image is stale and doesn't include recent code changes.**

Docker images are cached and only rebuilt when explicitly requested or when the Dockerfile changes. This means:

1. You commit a fix to the codebase
2. Local tests pass (using your updated code)
3. Docker tests fail (using the old cached image)
4. CI/CD fails (also using cached images)

### How to Identify This Issue

#### Method 1: Check Image Build Time

```bash
# Check when the Docker test image was last built
docker image inspect docker-test-runner:latest --format='{{.Created}}'

# Compare with recent git commits
git log --format="%H %ai %s" -10
```

**Red Flag**: If the image was built before your recent commits, it's stale.

#### Method 2: Run Diagnostic Tests

```bash
# Run the diagnostic test suite
pytest tests/regression/test_bearer_scheme_override_diagnostic.py -xvs

# Look for test: test_docker_image_has_fix
# If it fails or warns about stale image, rebuild is needed
```

#### Method 3: Check Docker Image Layers

```bash
# List images
docker images | grep -E "mcp-server-langgraph|test-runner"

# If you see multiple images or old timestamps, rebuild is needed
```

### Solution: Rebuild the Docker Image

#### Option 1: Quick Rebuild (Recommended)

```bash
# Rebuild test runner image with no cache
./scripts/test-integration.sh --build --no-cache

# This will:
# 1. Stop existing containers
# 2. Rebuild the image from scratch
# 3. Run integration tests
# 4. Use the latest code
```

#### Option 2: Manual Docker Compose Rebuild

```bash
# Stop existing containers
docker compose -f docker/docker-compose.test.yml down -v

# Rebuild with no cache
docker compose -f docker/docker-compose.test.yml build --no-cache test-runner

# Run tests
docker compose -f docker/docker-compose.test.yml up --abort-on-container-exit --exit-code-from test-runner
```

#### Option 3: Full Cleanup and Rebuild

```bash
# Clean up ALL related images (use with caution!)
docker rmi $(docker images -q 'docker-test-runner' 'mcp-server-langgraph')

# Rebuild from scratch
./scripts/test-integration.sh --build --no-cache
```

### Verification

After rebuilding, verify the fix is working:

```bash
# Run the specific failing tests
./scripts/test-integration.sh

# Should now see:
# ✓ TestCreateAPIKey::test_create_api_key_success PASSED
# ✓ All 5 tests passing
```

### Prevention

#### 1. Always Rebuild After Significant Changes

```bash
# Before committing changes that affect tests
./scripts/test-integration.sh --build
```

#### 2. Use Make Targets with Rebuild

```bash
# Development workflow
make test-unit           # Fast local tests
make test-integration    # Rebuilds if needed

# If tests fail unexpectedly
./scripts/test-integration.sh --build --no-cache
```

#### 3. CI/CD Configuration

Most CI/CD systems rebuild Docker images on every run, so this is less of an issue in CI/CD.
However, if using Docker layer caching in CI/CD, ensure cache is invalidated when:
- Dockerfile changes
- Dependencies change (pyproject.toml, uv.lock)
- Source code changes significantly

#### 4. Document Image Version

```bash
# Add image build info to diagnostic output
docker image inspect docker-test-runner:latest --format='{{.Created}}'

# Compare with current HEAD
git log -1 --format="%H %ai %s"
```

## Example: The 401 Unauthorized Case

### Timeline of Events

1. **Nov 11, 11:08 AM**: Docker image built
2. **Nov 11, 3:38 PM**: Commit 05a54e1 - Fixed bearer_scheme override (fixes 401 errors)
3. **Nov 11, 10:00 PM**: Commit 23115fe - Additional test coverage
4. **Nov 12, 1:01 AM**: Commit 7b51437 - Current HEAD

### Problem

- Docker image from 11:08 AM **does not include** the fix from 3:38 PM
- Image is 16 hours behind the fix, 14 hours behind current HEAD
- Local tests pass (using code with fix)
- Docker tests fail (using image without fix)

### Solution Applied

```bash
# Rebuild with latest code
./scripts/test-integration.sh --build --no-cache

# Verify fix is present
pytest tests/regression/test_bearer_scheme_override_diagnostic.py -xvs

# All tests now pass
```

## Technical Details

### Why Docker Images Get Stale

Docker uses layer caching for efficiency:

```dockerfile
# These layers are cached
FROM python:3.12-slim AS base
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# This layer contains your source code
COPY src/ src/
COPY tests/ tests/

# If only source code changes, previous layers are cached
# But the source code layer is NOT rebuilt unless forced
```

### When to Rebuild

**Always rebuild when:**
- ✅ Source code changes significantly
- ✅ Test code changes
- ✅ Dependencies change
- ✅ Dockerfile changes
- ✅ Tests mysteriously fail in Docker but pass locally

**No need to rebuild when:**
- ❌ Documentation changes only
- ❌ Environment variables change (set in docker-compose.yml)
- ❌ Configuration files change (if mounted as volumes)

### Cache Invalidation Strategies

```bash
# Strategy 1: Selective rebuild (faster)
docker compose -f docker/docker-compose.test.yml build test-runner

# Strategy 2: Full rebuild (slower but thorough)
docker compose -f docker/docker-compose.test.yml build --no-cache

# Strategy 3: Multi-stage rebuild
docker compose -f docker/docker-compose.test.yml build --build-arg BUILDKIT_INLINE_CACHE=1
```

## Diagnostic Commands Cheat Sheet

```bash
# Check Docker image status
docker images | grep -E "mcp-server-langgraph|test-runner"
docker image inspect docker-test-runner:latest --format='{{.Created}}'

# Check git status
git log --format="%ai %s" -10
git diff HEAD~5..HEAD --stat

# Run diagnostic tests
pytest tests/regression/test_bearer_scheme_override_diagnostic.py -xvs

# Rebuild and test
./scripts/test-integration.sh --build --no-cache

# Check if fix is in Docker
docker run --rm docker-test-runner:latest cat /app/tests/api/test_api_keys_endpoints.py | grep bearer_scheme

# View Docker build history
docker history docker-test-runner:latest --no-trunc
```

## Related Issues

- Issue: "Tests fail with 401 Unauthorized in Docker"
  - Solution: Rebuild Docker image to include bearer_scheme override fix

- Issue: "Tests pass locally but fail in CI/CD"
  - Solution: Check if CI/CD is using cached Docker images

- Issue: "Integration tests are flaky"
  - Solution: Ensure Docker image is always up-to-date

## See Also

- [PYTEST_XDIST_BEST_PRACTICES.md](./PYTEST_XDIST_BEST_PRACTICES.md) - pytest-xdist worker isolation
- [test_bearer_scheme_override_diagnostic.py](./regression/test_bearer_scheme_override_diagnostic.py) - Diagnostic tests
- [docker-compose.test.yml](../docker/docker-compose.test.yml) - Integration test configuration
- [test-integration.sh](../scripts/test-integration.sh) - Integration test script

---

**Last Updated**: 2025-11-12
**Related Commit**: 05a54e1 (bearer_scheme override fix)
**Diagnostic Test**: tests/regression/test_bearer_scheme_override_diagnostic.py
