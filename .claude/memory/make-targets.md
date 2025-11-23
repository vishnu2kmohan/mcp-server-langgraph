# Makefile Targets Guide

**Last Updated**: 2025-11-23
**Purpose**: Complete reference for all Make targets
**Total Targets**: 122 targets organized by category
**File**: `Makefile` (primary development interface)

---

## Quick Reference

### Most Common Commands

```bash
# Development Setup
make install-dev          # Install all dependencies
make setup-infra         # Start Docker infrastructure
make dev-setup           # Complete setup (install + infra)

# Testing
make test               # Run all automated tests
make test-unit          # Fast unit tests only
make test-coverage      # Tests with coverage report

# Validation
make validate-all       # All validations (deployments + OpenAPI)
make lint              # Run linters (ruff, mypy)
make format            # Auto-format code

# Running
make run               # Run MCP server (stdio)
make health-check      # Check system health
```

---

## Three-Tier Validation System

### Tier 1: validate-commit (< 30s)

**Purpose**: Fast validation for commit phase
**Usage**: `make validate-commit`

**Includes**:
- `ruff` - Linting and import sorting
- `ruff-format` - Code formatting
- `bandit` - Security scanning
- YAML/JSON/TOML validation

**Speed**: < 30 seconds
**Scope**: Changed files only (via pre-commit)

---

### Tier 2: validate-push (3-5 min)

**Purpose**: Comprehensive validation before push
**Usage**: `make validate-push`

**Includes**:
- All Tier 1 validations
- `mypy` - Type checking (blocking)
- Unit tests (`pytest -m unit`)
- Smoke tests (`pytest -m smoke`)
- Integration tests (`pytest -m integration`)
- Property tests (`pytest -m property`)

**Speed**: 3-5 minutes
**Scope**: All files

---

### Tier 3: validate-full (12-15 min)

**Purpose**: Full CI-equivalent validation
**Usage**: `make validate-full`

**Includes**:
- All Tier 2 validations
- Deployment validation (Helm, Kustomize)
- E2E tests
- Contract tests
- Regression tests
- Documentation validation

**Speed**: 12-15 minutes
**Scope**: Complete project

**When to use**: Before creating PR, after major changes

---

## Installation & Setup (8 targets)

### `make install`
**Purpose**: Install production dependencies only
**Duration**: 2-3 minutes
**Uses**: `uv sync --no-dev`

### `make install-dev`
**Purpose**: Install all dependencies (production + development)
**Duration**: 3-5 minutes
**Uses**: `uv sync`
**Includes**: pytest, mypy, ruff, hypothesis, mutmut, etc.

### `make setup-infra`
**Purpose**: Start all Docker infrastructure services
**Duration**: 30-60 seconds
**Services**: PostgreSQL, Redis, OpenFGA, Keycloak, Prometheus, Grafana
**Command**: `docker-compose up -d`

### `make setup-openfga`
**Purpose**: Initialize OpenFGA authorization model
**Duration**: 5-10 seconds
**Requires**: `setup-infra` first
**Command**: Uploads authorization model via OpenFGA API

### `make setup-keycloak`
**Purpose**: Initialize Keycloak SSO configuration
**Duration**: 10-15 seconds
**Requires**: `setup-infra` first
**Command**: Creates realm, clients, users

### `make setup-infisical`
**Purpose**: Initialize Infisical secrets management
**Duration**: 5 seconds
**Requires**: Infisical service running
**Command**: Creates project and secrets

### `make dev-setup`
**Purpose**: Complete development environment setup
**Duration**: 4-6 minutes
**Runs**: `install-dev` + `setup-infra` + `setup-openfga` + `setup-keycloak`
**One-command setup**: Perfect for new developers

### `make quick-start`
**Purpose**: Minimal quick start with defaults
**Duration**: 2-3 minutes
**Runs**: `install` + basic configuration

---

## Testing (40+ targets)

### Core Test Commands

#### `make test`
**Purpose**: Run all automated tests (unit + integration)
**Duration**: 2-3 minutes
**Command**: `pytest -m "unit or integration"`
**Excludes**: E2E, mutation, regression (too slow for regular use)

#### `make test-unit`
**Purpose**: Fast unit tests only
**Duration**: 30-60 seconds
**Command**: `pytest -m unit`
**Best for**: TDD workflow, rapid iteration

#### `make test-local`
**Purpose**: Local development test suite
**Duration**: 1-2 minutes
**Command**: Similar to `test` but optimized for dev workflow

#### `make test-ci`
**Purpose**: Full CI test suite
**Duration**: 5-8 minutes
**Command**: All tests that run in CI
**When**: Before pushing, validating changes

---

### Integration Testing

#### `make test-integration`
**Purpose**: Integration tests with real services
**Duration**: 1-2 minutes
**Requires**: `test-infra-up` (Docker services running)
**Command**: `pytest -m integration`

#### `make test-integration-services`
**Purpose**: Start required services for integration tests
**Alias for**: `test-infra-up`

#### `make test-integration-build`
**Purpose**: Rebuild Docker images for integration tests
**Duration**: 2-3 minutes
**When**: After Dockerfile changes

#### `make test-integration-debug`
**Purpose**: Run integration tests with debug logging
**Command**: `pytest -m integration -vv --log-cli-level=DEBUG`

#### `make test-integration-cleanup`
**Purpose**: Clean up integration test resources
**Command**: Stops services, removes volumes

---

### Test Infrastructure

#### `make test-infra-up`
**Purpose**: Start Docker services for testing
**Duration**: 20-30 seconds
**Services**: PostgreSQL, Redis, OpenFGA (test instances)
**Command**: `docker-compose -f docker-compose.test.yml up -d`

#### `make test-infra-down`
**Purpose**: Stop test infrastructure
**Command**: `docker-compose -f docker-compose.test.yml down`

#### `make test-infra-logs`
**Purpose**: Show logs from test infrastructure
**Command**: `docker-compose -f docker-compose.test.yml logs -f`

---

### Coverage Testing

#### `make test-coverage`
**Purpose**: Run tests with coverage report
**Duration**: 2-3 minutes
**Command**: `pytest --cov=src --cov-report=html --cov-report=term`
**Output**: Terminal + `htmlcov/index.html`

#### `make test-coverage-fast`
**Purpose**: Coverage for unit tests only (fast)
**Duration**: 45 seconds
**Command**: `pytest -m unit --cov=src --cov-report=term-missing`

#### `make test-coverage-html`
**Purpose**: Generate HTML coverage report
**Output**: `htmlcov/index.html`
**Opens in browser**: Yes (if available)

#### `make test-coverage-xml`
**Purpose**: Generate XML coverage report (for CI)
**Output**: `coverage.xml`
**Use case**: SonarQube, Codecov integration

#### `make test-coverage-terminal`
**Purpose**: Show coverage in terminal only
**Duration**: 2 minutes
**Command**: `pytest --cov=src --cov-report=term-missing`

#### `make test-coverage-changed`
**Purpose**: Coverage for changed files only
**Duration**: 30-60 seconds
**Command**: Uses `git diff` to identify changed files

#### `make test-coverage-combined`
**Purpose**: Combined coverage from multiple test runs
**Duration**: 3-4 minutes
**Runs**: Unit, integration, property tests with coverage merge

---

### Quality Testing

#### `make test-property`
**Purpose**: Property-based tests (Hypothesis)
**Duration**: 1-2 minutes
**Command**: `pytest -m property`
**Examples**: 25-50 (dev), 100 (CI)

#### `make test-contract`
**Purpose**: Contract/protocol compliance tests
**Duration**: 30 seconds
**Command**: `pytest -m contract`
**Validates**: MCP protocol, OpenAPI schema

#### `make test-regression`
**Purpose**: Performance regression tests
**Duration**: 2-3 minutes
**Command**: `pytest -m regression`
**Checks**: Latency, memory, throughput

#### `make test-mutation`
**Purpose**: Mutation testing (test effectiveness)
**Duration**: 20-40 minutes (VERY slow)
**Command**: `mutmut run`
**Use case**: Periodic quality checks (not regular workflow)

#### `make test-all-quality`
**Purpose**: All quality tests
**Duration**: 4-6 minutes
**Runs**: `test-property` + `test-contract` + `test-regression`

---

### Specialized Testing

#### `make test-auth`
**Purpose**: Authentication/authorization tests only
**Duration**: 30 seconds
**Command**: `pytest -m auth`

#### `make test-mcp`
**Purpose**: MCP protocol tests only
**Duration**: 20 seconds
**Command**: `pytest -m mcp`

#### `make test-e2e`
**Purpose**: End-to-end workflow tests
**Duration**: 3-5 minutes
**Requires**: Full infrastructure running
**Command**: `pytest -m e2e`

#### `make test-api`
**Purpose**: API endpoint tests
**Duration**: 1 minute
**Command**: `pytest -m api`

#### `make benchmark`
**Purpose**: Performance benchmarks
**Duration**: 2-3 minutes
**Command**: `pytest --benchmark-only`
**Output**: Benchmark results with statistics

---

### Test Utilities

#### `make test-new`
**Purpose**: Run only newly added tests
**Duration**: Varies
**Command**: Uses pytest-testmon to detect new tests

#### `make test-quick-new`
**Purpose**: Quick run of new/changed tests only
**Duration**: < 1 minute
**Command**: `pytest --testmon --lf`

---

## Validation (20+ targets)

### Deployment Validation

#### `make validate-openapi`
**Purpose**: Validate OpenAPI schema
**Duration**: 2-3 seconds
**Command**: `openapi-spec-validator openapi.yaml`
**Checks**: Syntax, structure, examples

#### `make validate-deployments`
**Purpose**: Validate all deployment configurations
**Duration**: 10-15 seconds
**Runs**: Helm + Kustomize + Docker Compose validation

#### `make validate-docker-compose`
**Purpose**: Validate Docker Compose files
**Duration**: 2 seconds
**Command**: `docker-compose config --quiet`

#### `make validate-docker-image`
**Purpose**: Validate Dockerfile and build
**Duration**: 30-60 seconds (if build needed)
**Command**: `docker build --check`

#### `make validate-helm`
**Purpose**: Validate Helm charts
**Duration**: 3-5 seconds
**Command**: `helm lint deployments/helm/mcp-server-langgraph`
**Checks**: Chart structure, values, templates

#### `make validate-kustomize`
**Purpose**: Validate Kustomize overlays
**Duration**: 5 seconds
**Command**: `kustomize build` for each overlay
**Checks**: dev, staging, production overlays

#### `make validate-all`
**Purpose**: Run all validations
**Duration**: 20-30 seconds
**Runs**: All validation targets

---

### Code Quality Validation

#### `make lint`
**Purpose**: Run all linters
**Duration**: 10-15 seconds
**Runs**: `ruff check` + `mypy`

#### `make format`
**Purpose**: Auto-format code
**Duration**: 5-10 seconds
**Runs**: `ruff format`
**Auto-fixes**: Import sorting, code style

#### `make security-check`
**Purpose**: Security vulnerability scanning
**Duration**: 10 seconds
**Runs**: `bandit -r src/`

#### `make pre-commit-setup`
**Purpose**: Install pre-commit hooks
**Duration**: 30 seconds
**Command**: `pre-commit install --install-hooks`

---

## Running & Monitoring (15+ targets)

### Running Services

#### `make run`
**Purpose**: Run MCP server (stdio mode)
**Duration**: Runs until stopped
**Command**: `uv run python -m mcp_server_langgraph`
**Mode**: Standard I/O transport

#### `make run-streamable`
**Purpose**: Run StreamableHTTP server
**Duration**: Runs until stopped
**Command**: Starts FastAPI server on port 8000
**Mode**: HTTP transport for web clients

---

### Health & Monitoring

#### `make health-check`
**Purpose**: Check system health
**Duration**: 2-3 seconds
**Checks**: Database, Redis, OpenFGA, Keycloak connectivity
**Output**: Health status for each service

#### `make monitoring-dashboard`
**Purpose**: Open Grafana dashboards
**Duration**: Instant
**Command**: Opens http://localhost:3000 in browser
**Requires**: `setup-infra` running

#### `make logs`
**Purpose**: Show infrastructure logs
**Command**: `docker-compose logs --tail=100`

#### `make logs-follow`
**Purpose**: Follow all logs in real-time
**Command**: `docker-compose logs -f`

---

## Deployment (15+ targets)

### Development Deployment

#### `make deploy-dev`
**Purpose**: Deploy to development environment
**Duration**: 30-60 seconds
**Command**: `kustomize build deployments/kustomize/overlays/dev | kubectl apply -f -`
**Target**: Local Kubernetes (kind, minikube, k3s)

#### `make deploy-rollback-dev`
**Purpose**: Rollback development deployment
**Command**: `kubectl rollout undo deployment/mcp-server-langgraph -n dev`

---

### Staging Deployment

#### `make deploy-staging`
**Purpose**: Deploy to staging environment
**Duration**: 1-2 minutes
**Command**: `kustomize build deployments/kustomize/overlays/staging | kubectl apply -f -`
**Target**: Staging Kubernetes cluster

#### `make deploy-rollback-staging`
**Purpose**: Rollback staging deployment
**Command**: `kubectl rollout undo deployment/mcp-server-langgraph -n staging`

---

### Production Deployment

#### `make deploy-production`
**Purpose**: Deploy to production (Helm)
**Duration**: 2-3 minutes
**Command**: `helm upgrade --install mcp-server-langgraph deployments/helm/mcp-server-langgraph`
**Target**: Production Kubernetes cluster
**Warning**: Requires production credentials

#### `make deploy-rollback-production`
**Purpose**: Rollback production deployment
**Command**: `helm rollback mcp-server-langgraph`

---

## Documentation (5+ targets)

#### `make docs-serve`
**Purpose**: Serve Mintlify docs locally
**Duration**: Instant
**Command**: `mintlify dev`
**URL**: http://localhost:3000
**Hot reload**: Yes

#### `make docs-build`
**Purpose**: Build Mintlify docs
**Duration**: 10-15 seconds
**Command**: `mintlify build`
**Output**: `docs/.output/`

#### `make docs-deploy`
**Purpose**: Deploy docs to Mintlify
**Duration**: 30 seconds
**Command**: `mintlify deploy`
**Requires**: Mintlify API key

---

## Utilities (10+ targets)

### Database Operations

#### `make db-migrate`
**Purpose**: Run database migrations
**Duration**: 5-10 seconds
**Command**: `alembic upgrade head`

#### `make db-rollback`
**Purpose**: Rollback last migration
**Command**: `alembic downgrade -1`

#### `make db-reset`
**Purpose**: Reset database (drop + recreate)
**Command**: Drops all tables, re-runs migrations
**Warning**: Destructive operation

---

### Cleanup

#### `make clean`
**Purpose**: Clean build artifacts
**Duration**: 2 seconds
**Removes**: `__pycache__`, `.pytest_cache`, `.mypy_cache`, `*.pyc`

#### `make clean-docker`
**Purpose**: Clean Docker resources
**Duration**: 10-15 seconds
**Removes**: Stopped containers, unused images, volumes

#### `make clean-all`
**Purpose**: Deep clean (all artifacts)
**Duration**: 15-20 seconds
**Removes**: Build artifacts + Docker + coverage reports

---

## Parallel Execution

### Running Multiple Targets

```bash
# Run 4 targets in parallel
make -j4 target1 target2 target3 target4

# Example: Parallel validation
make -j4 validate-openapi validate-helm validate-kustomize validate-docker-compose

# Example: Parallel tests
make -j2 test-unit test-property
```

**Benefits**:
- Faster CI/CD pipelines
- Better resource utilization
- Reduced wait time

**Caution**: Some targets have dependencies and shouldn't run in parallel

---

## Environment Variables

### Customizing Behavior

```bash
# Use specific Python version
PYTHON=python3.11 make test

# Skip slow tests
SKIP_SLOW=1 make test

# Verbose output
VERBOSE=1 make test-integration

# Custom pytest args
PYTEST_ARGS="-k test_auth" make test-unit
```

---

## Common Workflows

### New Developer Onboarding

```bash
# Complete setup (one command)
make dev-setup

# Verify everything works
make test-unit
make health-check
```

**Duration**: 5-7 minutes
**Result**: Fully functional development environment

---

### Daily Development

```bash
# Start day
make test-unit              # Verify clean slate

# During development
make test-unit              # After each change (fast feedback)
make test-coverage-fast     # Check coverage periodically

# Before commit
make lint                   # Check code quality
make format                 # Auto-fix issues

# Before push
make validate-push          # Full validation (3-5 min)
```

---

### Pre-PR Validation

```bash
# Run full validation
make validate-full          # 12-15 minutes

# Or step by step
make lint
make test-coverage
make test-all-quality
make validate-all
```

---

### Debugging

```bash
# Start infrastructure with logs
make test-infra-up
make logs-follow            # Watch logs in separate terminal

# Run tests with debug output
make test-integration-debug

# Check service health
make health-check

# Cleanup and restart
make test-infra-down
make test-infra-up
```

---

## Troubleshooting

### Issue: Make target not found

**Symptoms**:
```
make: *** No rule to make target 'foo'.  Stop.
```

**Fix**:
```bash
# List all targets
make help

# Or grep Makefile
grep "^[a-zA-Z0-9_-]*:" Makefile
```

---

### Issue: Docker services not starting

**Symptoms**:
```
ERROR: for postgres  Cannot start service postgres: ...
```

**Fix**:
```bash
# Check Docker is running
docker ps

# Clean up and retry
make clean-docker
make setup-infra

# Check logs
make logs
```

---

### Issue: Tests failing after `make dev-setup`

**Symptoms**: Integration tests fail with connection errors

**Fix**:
```bash
# Wait for services to be ready
sleep 10

# Verify health
make health-check

# Re-run tests
make test-integration
```

---

## Best Practices

### 1. Use Appropriate Tier

- **During development**: `make test-unit` (fast)
- **Before commit**: `make validate-commit` or `make lint`
- **Before push**: `make validate-push` (comprehensive)
- **Before PR**: `make validate-full` (CI-equivalent)

### 2. Parallel Execution

```bash
# Good: Independent targets
make -j4 lint test-unit test-property validate-openapi

# Bad: Dependent targets
make -j2 setup-infra test-integration  # test-integration needs infra!
```

### 3. Clean State

```bash
# Start fresh when debugging
make clean
make test-infra-down
make test-infra-up
make test-integration
```

### 4. Use Help

```bash
# View all targets with descriptions
make help

# View targets for specific category
make help | grep -i test
make help | grep -i deploy
```

---

## Related Documentation

- Makefile Source: `Makefile`
- Pre-commit Hooks: `.claude/memory/pre-commit-hooks-catalog.md`
- Testing Guide: `TESTING.md`
- pytest Markers: `.claude/context/pytest-markers.md`
- CI/CD Workflow: `.github/workflows/ci.yaml`

---

**Last Audit**: 2025-11-23 (122 targets documented)
**Tier System**: Three-tier validation (< 30s / 3-5min / 12-15min)
**Status**: Production-ready, comprehensive development tooling
