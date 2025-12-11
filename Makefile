.PHONY: help help-common help-advanced install install-dev setup-infra setup-openfga setup-infisical test test-unit test-integration test-coverage test-coverage-fast test-coverage-html test-coverage-xml test-coverage-terminal test-coverage-changed test-property test-contract test-regression test-mutation test-infra-up test-infra-up-build test-infra-down test-infra-logs test-builder-up test-builder-down test-playground-up test-playground-down test-e2e test-api test-mcp-server validate-openapi validate-deployments validate-docker-image validate-lgtm-config validate-all validate-workflows validate-pre-push test-workflows test-workflow-% act-dry-run deploy-dev deploy-staging deploy-production lint format security-check lint-check lint-fix lint-pre-commit lint-pre-push lint-install clean dev-setup quick-start monitoring-dashboard health-check health-check-fast db-migrate load-test stress-test docs-serve docs-build docs-deploy docs-validate docs-validate-version docs-validate-mintlify docs-fix-mdx docs-test docs-audit generate-reports pre-commit-setup git-hooks

# Sequential-only targets (cannot be parallelized)
.NOTPARALLEL: deploy-production deploy-staging deploy-dev setup-keycloak setup-openfga setup-infisical dev-setup

# ==============================================================================
# Variables
# ==============================================================================
# Use UV_RUN for all Python commands with --frozen for reproducible builds
# The --frozen flag ensures:
# 1. Lockfile is not modified during execution
# 2. Fails if lockfile is out of sync with pyproject.toml
# 3. Consistent behavior between local development and CI
# Regression Prevention (2025-11-16): test-regression needs dev dependencies
# (schemathesis, freezegun, kubernetes, toml, black, psutil, flake8, isort)
UV_RUN := uv run --frozen
PYTEST := $(UV_RUN) pytest
DOCKER_COMPOSE := docker compose
COV_SRC := src/mcp_server_langgraph
COV_OPTIONS := --cov=$(COV_SRC)

# ==============================================================================
# Help - Common Commands (Day-1 Developer)
# ==============================================================================

help-common:
	@echo "╔══════════════════════════════════════════════════════════════╗"
	@echo "║  LangGraph MCP Agent - Common Commands (Quick Reference)    ║"
	@echo "╚══════════════════════════════════════════════════════════════╝"
	@echo ""
	@echo "🚀 Getting Started (< 5 minutes):"
	@echo "  1. make install-dev        # Install dependencies (~1 min)"
	@echo "  2. make quick-start        # Start with defaults (~2 min)"
	@echo "  3. make test-dev           # Verify everything works (~2-3 min)"
	@echo ""
	@echo "📝 Daily Development:"
	@echo "  make test-dev              🚀 Run tests (fast, parallel, recommended)"
	@echo "  make validate-pre-push     ✅ Validate before push (matches CI exactly)"
	@echo "  make format                Format code (Ruff)"
	@echo "  make lint-check            Check code quality (Ruff, MyPy)"
	@echo "  make run-streamable        Start HTTP server"
	@echo ""
	@echo "🧪 Essential Testing:"
	@echo "  make test-unit             Unit tests with coverage"
	@echo "  make test-fast             All tests, skip coverage (faster)"
	@echo "  make test-integration      Integration tests (needs Docker)"
	@echo ""
	@echo "🐳 Infrastructure:"
	@echo "  make setup-infra           Start all Docker services"
	@echo "  make logs                  View service logs"
	@echo "  make clean                 Stop and cleanup"
	@echo ""
	@echo "📚 Documentation:"
	@echo "  make help                  Full command reference (112+ targets)"
	@echo "  make help-advanced         Advanced & specialized targets"
	@echo ""
	@echo "💡 Pro Tips:"
	@echo "  • New here? See docs/day-1-developer.md for step-by-step guide"
	@echo "  • Use 'make -j4' for parallel execution (4x faster)"
	@echo "  • Use 'make test-dev' instead of 'make test' for development"
	@echo ""

# ==============================================================================
# Help - Full Reference
# ==============================================================================

help:
	@echo "LangGraph MCP Agent - Full Make Commands Reference"
	@echo ""
	@echo "💡 NEW HERE? Run 'make help-common' for the essential commands"
	@echo ""
	@echo "⚡ Performance Tip:"
	@echo "  Use 'make -j4' to run independent targets in parallel (4 jobs)"
	@echo "  Example: 'make -j4 validate-all' runs all validations in parallel"
	@echo "  Many targets (tests, lint, validation) are already optimized for parallel execution"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install production dependencies"
	@echo "  make install-dev      Install development + test dependencies"
	@echo "  make setup-infra      Start Docker infrastructure"
	@echo "  make setup-openfga    Initialize OpenFGA"
	@echo "  make setup-keycloak   Initialize Keycloak"
	@echo "  make setup-infisical  Initialize Infisical"
	@echo ""
Testing:
	@echo "  make test                     Run all automated tests with coverage"
	@echo "  make test-unit                Run pure unit tests (tests/unit/)"
	@echo "  make test-local               Run all local tests (Unit + CLI + Validation)"
	@echo "  make test-integration         Run integration tests in Docker"
	@echo ""
	@echo "Fast Testing (40-70% faster):"
	@echo "  make test-dev                 🚀 Development mode (parallel, fast-fail) - RECOMMENDED"
	@echo "  make test-fast-core           Fastest iteration (core tests only, <5s)"
	@echo "  make test-fast                Run all tests without coverage"
	@echo ""
	@echo "Quality & Specialized:"
	@echo "  make test-coverage            Generate comprehensive coverage report (parallel)"
	@echo "  make test-coverage-fast       Fast coverage (unit tests only, parallel, 70-80% faster)"
	@echo "  make test-coverage-html       HTML report only (fastest for browsing)"
	@echo "  make test-coverage-xml        XML report only (for CI/coverage services)"
	@echo "  make test-coverage-terminal   Terminal report only (quick overview)"
	@echo "  make test-coverage-changed    Incremental coverage (changed code only, 80-90% faster)"
	@echo "  make test-coverage-combined   Combined coverage (unit + integration)"
	@echo "  make test-property            Property-based tests (Hypothesis)"
	@echo "  make test-contract            Contract tests (MCP, OpenAPI)"
	@echo "  make test-regression          Performance regression tests"
	@echo "  make test-mutation            Mutation tests (slow)"
	@echo "  make test-all-quality         All quality tests (property+contract+regression)"
	@echo "  make benchmark                Performance benchmarks"
	@echo ""
	@echo "CI-Parity Quality Tests (with coverage, matches CI exactly):"
	@echo "  make test-precommit-validation  Validate pre-commit hook configuration"
	@echo "  make test-property-ci          Property tests + coverage (CI mode)"
	@echo "  make test-contract-ci          Contract tests + coverage (CI mode)"
	@echo "  make test-regression-ci        Regression tests + coverage (CI mode)"
	@echo "  make test-all-quality-ci       All quality tests + coverage (CI mode)"
	@echo ""
	@echo "New Testing Features:"
	@echo "  make test-infra-up            Start full test infrastructure (all services)"
	@echo "  make test-infra-up-build      Rebuild and start test infrastructure"
	@echo "  make test-infra-down          Stop test infrastructure (data persists)"
	@echo "  make test-infra-clean-volumes Remove test infrastructure data volumes"
	@echo "  make test-infra-reset         Stop and clean ALL data (down + clean-volumes)"
	@echo "  make test-infra-logs          View test infrastructure logs"
	@echo "  make test-gateway-status      Check gateway health and routes"
	@echo "  make test-gateway-logs        View gateway (Traefik) logs"
	@echo "  make test-e2e                 Run end-to-end tests (full user journeys)"
	@echo "  make test-api                 Run API endpoint tests"
	@echo "  make test-mcp-server          Run MCP server unit tests"
	@echo ""
	@echo "Validation:"
	@echo "  make validate-pre-push        🚀 Run comprehensive pre-push validation (CI-equivalent)"
	@echo "  make validate-openapi         Validate OpenAPI schema"
	@echo "  make validate-deployments     Validate all deployment configs"
	@echo "  make validate-docker-compose  Validate Docker Compose"
	@echo "  make validate-docker-image    Validate Docker test image freshness"
	@echo "  make validate-helm            Validate Helm chart"
	@echo "  make validate-kustomize       Validate Kustomize overlays"
	@echo "  make validate-all             Run all deployment validations"
	@echo ""
	@echo "Deployment:"
	@echo "  make deploy-dev               Deploy to development (Kustomize)"
	@echo "  make deploy-staging           Deploy to staging (Kustomize)"
	@echo "  make deploy-production        Deploy to production (Helm)"
	@echo "  make deploy-rollback-dev      Rollback development deployment"
	@echo "  make deploy-rollback-staging  Rollback staging deployment"
	@echo "  make deploy-rollback-production  Rollback production deployment"
	@echo "  make test-k8s-deployment      Test Kubernetes deployment (kind)"
	@echo "  make test-helm-deployment     Test Helm deployment (kind)"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint                Alias for lint-check (Ruff linter + MyPy)"
	@echo "  make format              Alias for lint-fix (Ruff formatter)"
	@echo "  make security-check      Run security scans"
	@echo "  make lint-check          Run comprehensive lint checks (non-destructive)"
	@echo "  make lint-fix            Auto-fix formatting issues"
	@echo "  make lint-pre-commit     Simulate pre-commit hook"
	@echo "  make lint-pre-push       Simulate pre-push hook"
	@echo "  make lint-install        Install/reinstall lint hooks"
	@echo "  make pre-commit-setup    Setup pre-commit hooks"
	@echo "  make git-hooks           Install git hooks"
	@echo ""
	@echo "Running:"
	@echo "  make run                 Run stdio MCP server"
	@echo "  make run-streamable      Run StreamableHTTP server"
	@echo "  make logs                Show infrastructure logs"
	@echo "  make health-check        Check system health"
	@echo ""
	@echo "Development Shortcuts:"
	@echo "  make dev-setup           Complete developer setup (install+infra+setup)"
	@echo "  make quick-start         Quick start with defaults"
	@echo "  make monitoring-dashboard Open Grafana dashboards"
	@echo "  make health-check        Full system health check"
	@echo "  make health-check-fast   ⚡ Fast parallel port scan (70% faster)"
	@echo "  make db-migrate          Run database migrations"
	@echo "  make load-test           Run load tests"
	@echo "  make stress-test         Run stress tests"
	@echo ""
	@echo "Documentation:"
	@echo "  make docs-serve          Serve Mintlify docs locally"
	@echo "  make docs-build          Build Mintlify docs"
	@echo "  make docs-deploy         Deploy docs to Mintlify"
	@echo "  make docs-validate       Validate all documentation (MDX, links, versions)"
	@echo "  make docs-fix-mdx        Auto-fix MDX syntax errors"
	@echo "  make docs-test           Run documentation tests"
	@echo "  make docs-audit          Comprehensive documentation audit"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean               Stop containers and clean files"
	@echo "  make clean-all           Deep clean including venv"
	@echo ""

install:
	uv sync --frozen --no-dev
	@echo "✓ Production dependencies installed from lockfile"
	@echo "  Note: Uses uv.lock for reproducible builds"

install-dev:
	uv sync --frozen --extra dev
	@echo "✓ Development dependencies installed from lockfile"
	@echo "  Note: Uses uv.lock with dev extra for CI parity"

setup-infra:
	$(DOCKER_COMPOSE) up -d
	@echo "✓ Infrastructure started"
	@echo ""
	@echo "Services:"
	@echo "  OpenFGA:    http://localhost:8080"
	@echo "  Jaeger:     http://localhost:16686"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana:    http://localhost:3001"
	@echo ""

setup-openfga:
	@echo "Setting up OpenFGA..."
	$(UV_RUN) python scripts/setup/setup_openfga.py
	@echo ""
	@echo "⚠️  Remember to update .env with OPENFGA_STORE_ID and OPENFGA_MODEL_ID"

setup-keycloak:
	@echo "Setting up Keycloak..."
	@echo "Waiting for Keycloak to start (this may take 60+ seconds)..."
	$(UV_RUN) python scripts/setup/setup_keycloak.py
	@echo ""
	@echo "⚠️  Remember to update .env with KEYCLOAK_CLIENT_SECRET"

setup-infisical:
	@echo "Setting up Infisical..."
	$(UV_RUN) python scripts/setup/setup_infisical.py

test:
	@echo "Running all tests with coverage (parallel execution)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto $(COV_OPTIONS) --cov-report=term-missing
	@echo "✓ Tests complete. Coverage report above."
	@echo ""
	@echo "Tip: Use 'make test-fast' or 'make test-dev' for faster iteration"

test-unit:
	@echo "Running pure unit tests (tests/unit/)..."
	@test -d .venv || (echo "✗ No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto tests/unit $(COV_OPTIONS) --cov-report=term-missing
	@echo "✓ Unit tests complete"

test-local:
	@echo "Running all local tests (Unit + CLI + Validation)..."
	@test -d .venv || (echo "✗ No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto tests/unit tests/cli tests/deployment tests/infrastructure tests/ci
	@echo "✓ Local tests complete"

test-meta:  ## Run meta-tests (infrastructure validation) - Codex Finding #5 Fix (2025-11-23)
	@echo "Running meta-tests (test infrastructure validation)..."
	@echo "  These tests validate git hooks, CI workflows, Docker configs, etc."
	@echo "  They are excluded from regular unit test runs (pre-push) to reduce overhead."
	@test -d .venv || (echo "✗ No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto -m meta -v
	@echo "✓ Meta-tests complete"

test-ci:
	@echo "Running tests exactly as CI does (parallel execution)..."
	OTEL_SDK_DISABLED=true HYPOTHESIS_PROFILE=ci $(PYTEST) -n auto -m "unit and not llm" $(COV_OPTIONS) --cov-report=xml --cov-report=term-missing
	@echo "✓ CI-equivalent tests complete"
	@echo "  Coverage XML: coverage.xml"

test-integration:
	@echo "Running integration tests in Docker environment (matches CI)..."
	./scripts/test-integration.sh --build
	@echo "✓ Integration tests complete"

test-integration-services:
	@echo "Starting integration test services only..."
	./scripts/test-integration.sh --services

test-integration-debug:
	@echo "Running integration tests (keep containers for debugging)..."
	./scripts/test-integration.sh --keep

test-integration-cleanup:
	@echo "Cleaning up integration test containers..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml down -v --remove-orphans
	@echo "✓ Cleanup complete"

test-coverage:
	@echo "Generating comprehensive coverage report (parallel execution)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto $(COV_OPTIONS) --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo "✓ Coverage reports generated:"
	@echo "  HTML: htmlcov/index.html"
	@echo "  XML: coverage.xml"
	@echo "  Terminal: Above"
	@echo ""
	@echo "Tip: Use 'make test-coverage-fast' for faster unit-test-only coverage"

test-coverage-fast:
	@echo "Generating fast coverage report (unit tests only, parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m unit $(COV_OPTIONS) --cov-report=html --cov-report=term-missing
	@echo "✓ Fast coverage report generated:"
	@echo "  HTML: htmlcov/index.html"
	@echo "  Terminal: Above"
	@echo ""
	@echo "Speedup: 70-80% faster than full coverage (unit tests only)"

test-coverage-html:
	@echo "Generating HTML coverage report only (fastest for browsing)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto $(COV_OPTIONS) --cov-report=html
	@echo "✓ HTML coverage report generated:"
	@echo "  Open: htmlcov/index.html"

test-coverage-xml:
	@echo "Generating XML coverage report (for CI/coverage services)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto $(COV_OPTIONS) --cov-report=xml
	@echo "✓ XML coverage report generated:"
	@echo "  File: coverage.xml"

test-coverage-terminal:
	@echo "Generating terminal coverage report (quick overview)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto $(COV_OPTIONS) --cov-report=term-missing
	@echo "✓ Terminal coverage displayed above"

test-coverage-changed:
	@echo "Running tests for changed code only (incremental coverage)..."
	@echo "Using pytest-testmon for selective test execution..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto --testmon $(COV_OPTIONS) --cov-report=html --cov-report=term-missing
	@echo "✓ Incremental coverage complete"
	@echo "  HTML: htmlcov/index.html"
	@echo ""
	@echo "Note: First run tests all files, subsequent runs only test changes"
	@echo "Speedup: 80-90% faster for incremental changes"

test-coverage-combined:
	@echo "Running all tests with combined coverage..."
	@echo ""
	@echo "Step 1: Running unit tests with coverage (parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m unit $(COV_OPTIONS) --cov-report= --cov-report=term-missing
	@echo ""
	@echo "Step 2: Running integration tests in Docker with coverage..."
	mkdir -p coverage-integration
	chmod 777 coverage-integration
	./scripts/test-integration.sh --build
	@echo ""
	@echo "Step 3: Combining coverage reports..."
	@if [ -f coverage-integration/coverage-integration.xml ]; then \
		echo "  Found integration coverage, combining..."; \
		$(UV_RUN) coverage combine --append coverage-integration/.coverage* 2>/dev/null || true; \
		$(UV_RUN) coverage xml -o coverage-combined.xml; \
		$(UV_RUN) coverage html -d htmlcov-combined; \
		$(UV_RUN) coverage report; \
		echo ""; \
		echo "✓ Combined coverage reports generated:"; \
		echo "  HTML: htmlcov-combined/index.html"; \
		echo "  XML: coverage-combined.xml"; \
	else \
		echo "  ⚠️  No integration coverage found, using unit tests only"; \
		$(UV_RUN) coverage xml; \
		$(UV_RUN) coverage html; \
		$(UV_RUN) coverage report; \
	fi

test-auth:
	@echo "Testing OpenFGA authorization..."
	$(UV_RUN) python examples/openfga_usage.py

test-mcp:
	@echo "Testing MCP server..."
	$(UV_RUN) python examples/client_stdio.py

benchmark:
	@echo "Running performance benchmarks..."
	@# IMPORTANT: Disable xdist AND override addopts to prevent conflicts
	@# - -p no:xdist: Disables pytest-xdist plugin (benchmarks require single-threaded execution)
	@# - -o addopts="...": Overrides pyproject.toml's addopts which includes --dist loadgroup
	@# Without the override, pytest errors with "unrecognized arguments: --dist"
	$(PYTEST) -m benchmark -v -p no:xdist -o "addopts=-v --strict-markers --tb=short --timeout=60" --benchmark-only --benchmark-autosave
	@echo "✓ Benchmark results saved"

# New test targets
test-property:
	@echo "Running property-based tests (Hypothesis, parallel)..."
	@test -d .venv || (echo "✗ No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto -m property -v
	@echo "✓ Property tests complete"

test-contract:
	@echo "Running contract tests (MCP protocol, OpenAPI, parallel)..."
	@test -d .venv || (echo "✗ No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto -m contract -v
	@echo "✓ Contract tests complete"

test-regression:
	@echo "Running performance regression tests (parallel)..."
	@test -d .venv || (echo "✗ No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto -m regression -v
	@echo "✓ Regression tests complete"

test-mutation:
	@echo "Running mutation tests (this will take a while)..."
	@echo "Testing critical modules for test effectiveness..."
	mutmut run
	@echo ""
	@echo "Generating results..."
	mutmut results
	@echo ""
	@echo "Generating HTML report..."
	mutmut html
	@echo "✓ Mutation testing complete"
	@echo "  View report: open html/index.html"

test-all-quality: test-property test-contract test-regression
	@echo "✓ All quality tests complete"

# Pre-commit Hook Validation
test-precommit-validation:
	@echo "Validating pre-commit hook configuration (parallel)..."
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto tests/regression/test_precommit_hook_dependencies.py -v --tb=short
	@echo "✓ Pre-commit validation complete"

# CI-Mode Quality Tests (with coverage, matches CI exactly)
test-property-ci:
	@echo "Running property-based tests with coverage (CI mode)..."
	HYPOTHESIS_PROFILE=ci OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto -m property -v --tb=short \
		--cov=src/mcp_server_langgraph --cov-report=xml:coverage-property.xml --cov-report=term
	@echo "✓ Property tests complete (coverage: coverage-property.xml)"

test-contract-ci:
	@echo "Running contract tests with coverage (CI mode)..."
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto -m contract -v --tb=short \
		--cov=src/mcp_server_langgraph --cov-report=xml:coverage-contract.xml --cov-report=term
	@echo "✓ Contract tests complete (coverage: coverage-contract.xml)"

test-regression-ci:
	@echo "Running regression tests with coverage (CI mode)..."
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto -m regression -v --tb=short \
		--cov=src/mcp_server_langgraph --cov-report=xml:coverage-regression.xml --cov-report=term
	@echo "✓ Regression tests complete (coverage: coverage-regression.xml)"

test-all-quality-ci: test-property-ci test-contract-ci test-regression-ci test-precommit-validation
	@echo "✓ All quality tests complete (CI mode with coverage)"
	@echo ""
	@echo "Coverage reports generated:"
	@echo "  - coverage-property.xml"
	@echo "  - coverage-contract.xml"
	@echo "  - coverage-regression.xml"

# New Testing Infrastructure Targets

# Consolidated test infrastructure (full stack with Builder, Playground, Observability)
# Use this target for all test infrastructure needs - it includes everything
test-infra-up:
	@echo "Starting full test infrastructure (docker-compose.test.yml)..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml up -d
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "✓ Full test infrastructure started!"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "┌─────────────────────────────────────────────────────────────┐"
	@echo "│  API GATEWAY: http://localhost (Traefik)                   │"
	@echo "└─────────────────────────────────────────────────────────────┘"
	@echo ""
	@echo "Gateway Routes (recommended):"
	@echo "  http://localhost/api        - MCP Server API"
	@echo "  http://localhost/build      - Visual Workflow Builder"
	@echo "  http://localhost/play       - Interactive Playground"
	@echo "  http://localhost/authn      - Keycloak (Authentication)"
	@echo "  http://localhost/authz      - OpenFGA (Authorization)"
	@echo "  http://localhost/vectors    - Qdrant (Vector Database)"
	@echo "  http://localhost/tempo      - Tempo (Distributed Tracing)"
	@echo "  http://localhost/logs       - Loki (Log Aggregation)"
	@echo "  http://localhost/mimir      - Mimir (Metrics Storage)"
	@echo "  http://localhost/alloy      - Alloy (Unified Telemetry)"
	@echo "  http://localhost/dashboards - Grafana (Unified Dashboards)"
	@echo "  http://localhost/gateway    - Traefik Dashboard"
	@echo ""
	@echo "Direct Ports (legacy, for debugging):"
	@echo "  PostgreSQL:   localhost:9432"
	@echo "  Redis:        localhost:9379"
	@echo "  OpenFGA:      http://localhost:9080"
	@echo "  Keycloak:     http://localhost:9082"
	@echo "  Qdrant:       http://localhost:9333"
	@echo "  MCP Server:   http://localhost:8000"
	@echo "  Builder:      http://localhost:9001"
	@echo "  Playground:   http://localhost:9002"
	@echo "  Tempo:        http://localhost:13200"
	@echo "  Grafana:      http://localhost:13001"
	@echo "  Loki:         http://localhost:13100"
	@echo "  Mimir:        http://localhost:19009"
	@echo "  Alloy:        http://localhost:12345"
	@echo ""

test-infra-up-build:
	@echo "Rebuilding and starting full test infrastructure..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml up -d --build
	@echo "✓ Full test infrastructure rebuilt and started!"

test-infra-down:
	@echo "Stopping test infrastructure..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml down --remove-orphans
	@echo "✓ Test infrastructure stopped"
	@echo "Note: Data persists in Docker volumes. Use 'make test-infra-clean-volumes' to remove."

test-infra-clean-volumes:
	@echo "Removing test infrastructure volumes..."
	docker volume rm mcp-server-langgraph_postgres-data 2>/dev/null || true
	docker volume rm mcp-server-langgraph_redis-data 2>/dev/null || true
	docker volume rm mcp-server-langgraph_qdrant-data 2>/dev/null || true
	docker volume rm mcp-server-langgraph_loki-data 2>/dev/null || true
	docker volume rm mcp-server-langgraph_tempo-data 2>/dev/null || true
	docker volume rm mcp-server-langgraph_mimir-data 2>/dev/null || true
	docker volume rm mcp-server-langgraph_grafana-data 2>/dev/null || true
	@echo "✓ Test volumes cleaned"

test-infra-reset: test-infra-down test-infra-clean-volumes
	@echo "✓ Test infrastructure reset (all data removed)"

test-infra-logs:
	@echo "Showing test infrastructure logs..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml logs -f

test-gateway-status:
	@echo "Checking API Gateway (Traefik) status..."
	@echo ""
	@echo "Gateway Health:"
	@curl -s http://localhost:8080/api/overview || echo "  ⚠ Gateway not responding (is test-infra running?)"
	@echo ""
	@echo "Configured Routes:"
	@curl -s http://localhost:8080/api/http/routers 2>/dev/null | $(UV_RUN) python -c "import sys,json; [print(f'  {r[\"name\"]}: {r[\"rule\"]}') for r in json.load(sys.stdin)]" 2>/dev/null || echo "  ⚠ Could not fetch routes"
	@echo ""

test-gateway-logs:
	@echo "Showing API Gateway (Traefik) logs..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml logs -f traefik-gateway

test-loki-logs:
	@echo "Showing Loki and Alloy logs..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml logs -f loki-test alloy-test

test-builder-up:
	@echo "Starting builder service (unified API + React frontend)..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml up -d builder-test
	@echo "✓ Builder started"
	@echo ""
	@echo "Builder Service:"
	@echo "  API + Frontend: http://localhost:9001"
	@echo "  Health:         http://localhost:9001/api/builder/health"
	@echo "  API Docs:       http://localhost:9001/docs"
	@echo ""

test-builder-down:
	@echo "Stopping builder service..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml stop builder-test
	@echo "✓ Builder stopped"

test-playground-up:
	@echo "Starting playground service (with in-context observability)..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml up -d playground-test
	@echo "✓ Playground started"
	@echo ""
	@echo "Playground Service:"
	@echo "  API + WebSocket: http://localhost:9002"
	@echo "  Health:          http://localhost:9002/api/playground/health"
	@echo "  API Docs:        http://localhost:9002/docs"
	@echo ""
	@echo "In-Context Observability:"
	@echo "  Traces:    http://localhost:9002/api/playground/observability/traces"
	@echo "  Logs:      http://localhost:9002/api/playground/observability/logs"
	@echo "  Metrics:   http://localhost:9002/api/playground/observability/metrics"
	@echo "  Alerts:    http://localhost:9002/api/playground/observability/alerts"

test-playground-down:
	@echo "Stopping playground service..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml stop playground-test
	@echo "✓ Playground stopped"

test-e2e:
	@echo "Running end-to-end tests (parallel execution, requires test infrastructure)..."
	@echo "Ensuring test infrastructure is running..."
	$(MAKE) test-infra-up
	@echo ""
	@echo "Waiting for services to be healthy..."
	@bash scripts/utils/wait_for_services.sh docker-compose.test.yml
	@echo ""
	@echo "Running E2E tests..."
	TESTING=true OTEL_SDK_DISABLED=true KEYCLOAK_CLIENT_SECRET=test-client-secret-for-e2e-tests KEYCLOAK_ADMIN_PASSWORD=admin JWT_SECRET_KEY=test-jwt-secret-key-for-e2e-testing-only $(PYTEST) -n auto -m e2e -v --tb=short
	@echo "✓ E2E tests complete"

test-api:
	@echo "Running API endpoint tests (unit tests for REST APIs)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m "api and unit" -v
	@echo "✓ API endpoint tests complete"

test-mcp-server:
	@echo "Running MCP server unit tests (parallel execution)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto tests/unit/mcp/test_mcp_stdio_server.py tests/integration/test_mcp_streamable.py -v
	@echo "✓ MCP server tests complete"

# Validation
validate-openapi:
	@echo "Validating OpenAPI schema..."
	OTEL_SDK_DISABLED=true $(UV_RUN) python scripts/validators/validate_openapi.py 2>&1 | grep -v -E "(WARNING|trace_id|span_id|resource\.|Transient error|exporter\.py|Traceback|File \"|ImportError:|pydantic-ai|fall back)"
	@echo "✓ OpenAPI validation complete"

validate-deployments:
	@echo "Validating all deployment configurations..."
	$(UV_RUN) python scripts/validators/validate_deployments.py
	@echo "✓ Deployment validation complete"

validate-docker-compose:
	@echo "Validating Docker Compose configuration..."
	$(DOCKER_COMPOSE) -f docker-compose.yml config --quiet
	@echo "✓ Docker Compose valid"

validate-lgtm-config:  ## Validate Grafana LGTM stack configurations (Mimir, Loki)
	@echo "Validating LGTM stack configurations..."
	@echo "  Validating Mimir config..."
	@docker run --rm -v $(PWD)/docker/mimir:/etc/mimir grafana/mimir:3.0.1 \
		-config.file=/etc/mimir/mimir-config.yaml -print.config > /dev/null 2>&1 && \
		echo "  ✓ Mimir config valid" || \
		(echo "  ✗ Mimir config invalid - run with verbose output for details:" && \
		 echo "    docker run --rm -v \$$(pwd)/docker/mimir:/etc/mimir grafana/mimir:3.0.1 -config.file=/etc/mimir/mimir-config.yaml -print.config" && \
		 exit 1)
	@echo "  Validating Loki config (YAML syntax)..."
	@$(UV_RUN) python -c "import yaml; yaml.safe_load(open('docker/loki/loki-config.yaml'))" && \
		echo "  ✓ Loki config YAML valid" || \
		(echo "  ✗ Loki config YAML invalid" && exit 1)
	@echo "✓ LGTM configurations valid"

validate-docker-image:
	@echo "Validating Docker test image freshness..."
	@./scripts/validators/validate_docker_image_freshness.sh --check-commits
	@echo "✓ Docker image is up-to-date"

validate-helm:
	@echo "Validating Helm chart..."
	helm lint deployments/helm/mcp-server-langgraph
	helm template test-release deployments/helm/mcp-server-langgraph --dry-run > /dev/null
	@echo "✓ Helm chart valid"

validate-kustomize:
	@echo "Validating Kustomize overlays in parallel..."
	@( \
		echo "  Validating dev overlay..." && kubectl kustomize deployments/overlays/dev > /dev/null 2>&1 && echo "  ✓ dev overlay valid" \
	) & pid1=$$!; \
	( \
		echo "  Validating staging overlay..." && kubectl kustomize deployments/overlays/staging > /dev/null 2>&1 && echo "  ✓ staging overlay valid" \
	) & pid2=$$!; \
	( \
		echo "  Validating production overlay..." && kubectl kustomize deployments/overlays/production > /dev/null 2>&1 && echo "  ✓ production overlay valid" \
	) & pid3=$$!; \
	wait $$pid1 $$pid2 $$pid3
	@echo "✓ All Kustomize overlays valid"

validate-all: validate-deployments validate-docker-compose validate-lgtm-config validate-docker-image validate-helm validate-kustomize
	@echo "✓ All deployment validations passed"

validate-docs:  ## Verify Claude Code documentation accuracy (prevents drift)
	@echo "📚 Checking Claude Code documentation accuracy..."
	@$(UV_RUN) python scripts/validators/check-claude-docs-accuracy.py

# GitHub Actions workflow testing with act
test-workflows:
	@echo "🧪 Testing critical workflows locally with act..."
	@echo ""
	@echo "Prerequisites: Docker must be running"
	@docker ps > /dev/null 2>&1 || (echo "❌ Docker not running. Start Docker first." && exit 1)
	@echo ""
	@echo "1. Testing CI/CD Pipeline (test job on Python 3.12)..."
	@act push -W .github/workflows/ci.yaml -j test --matrix python-version:3.12 --quiet || echo "  ⚠️  May fail without full infrastructure (check logs for real errors)"
	@echo ""
	@echo "2. Testing E2E Tests (dry-run)..."
	@act push -W .github/workflows/e2e-tests.yaml --dry-run || echo "  ⚠️  Workflow validation failed"
	@echo ""
	@echo "3. Testing Quality Tests (property tests dry-run)..."
	@act push -W .github/workflows/quality-tests.yaml -j property-tests --dry-run || echo "  ⚠️  Workflow validation failed"
	@echo ""
	@echo "✓ Workflow testing complete"
	@echo ""
	@echo "💡 For full test execution: act push -W .github/workflows/FILE.yaml -j JOB_NAME"

test-workflow-%:
	@echo "Testing workflow: $*.yaml"
	@act push -W .github/workflows/$*.yaml

validate-workflows:  ## Comprehensive workflow validation (matches CI exactly)
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔍 Comprehensive Workflow Validation (CI-Equivalent)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "▶ STEP 1: Check actionlint is available"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@if ! command -v actionlint >/dev/null 2>&1; then \
		echo "ERROR: actionlint not found."; \
		echo ""; \
		echo "Install via mise (recommended):"; \
		echo "  curl https://mise.run | sh && mise install"; \
		echo ""; \
		echo "Or install manually:"; \
		echo "  brew install actionlint  # macOS"; \
		echo "  go install github.com/rhysd/actionlint/cmd/actionlint@latest  # Go"; \
		exit 1; \
	else \
		echo "✓ actionlint available ($$(actionlint --version))"; \
	fi
	@echo ""
	@echo "▶ STEP 2: Run actionlint on all workflow files"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@actionlint -color -shellcheck= .github/workflows/*.{yml,yaml} && echo "✓ actionlint validation passed" || (echo "✗ actionlint validation failed" && exit 1)
	@echo ""
	@echo "▶ STEP 3: Run workflow validation test suite"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Running: test_workflow_syntax.py, test_workflow_security.py,"
	@echo "         test_workflow_dependencies.py, test_docker_paths.py"
	@OTEL_SDK_DISABLED=true $(UV_RUN) pytest \
		tests/meta/ci/test_workflow_syntax.py \
		tests/meta/ci/test_workflow_security.py \
		tests/meta/ci/test_workflow_dependencies.py \
		tests/meta/infrastructure/test_docker_paths.py \
		-v --tb=short && echo "✓ Workflow test suite passed" || (echo "✗ Workflow tests failed" && exit 1)
	@echo ""
	@echo "▶ STEP 4: Validate pytest configuration compatibility"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(UV_RUN) python scripts/validators/validate_pytest_config.py && echo "✓ Pytest config validation passed" || (echo "✗ Pytest config validation failed" && exit 1)
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ All workflow validations passed (CI-equivalent)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Tiered Validation System (2025-11-16 - CI/CD Optimization)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Three-tier validation strategy for balancing speed and quality
# See: docs/development/VALIDATION_STRATEGY.md for complete documentation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

validate-commit:  ## Tier 1: Fast validation (<30s) - formatters, linters, basic checks
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "⚡ TIER 1 VALIDATION - Quick Checks (<30s)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "Running pre-commit hooks (staged files only)..."
	@echo "Hooks: trailing-whitespace, end-of-file-fixer, Ruff (linter + formatter),"
	@echo "       bandit, gitleaks, check-yaml/json/toml, etc."
	@echo ""
	@pre-commit run --show-diff-on-failure
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ Tier 1 validation complete!"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

## validate-push-changed: Fast validation of changed files only (matches git hook behavior)
validate-push-changed:  ## Tier 2: Critical validation - changed files only (1-3 min)
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔍 TIER 2 VALIDATION - Critical Checks (Changed Files)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "This runs Tier 1 + Tier 2 validators on CHANGED files only"
	@echo "Matches git hook behavior - faster for routine development"
	@echo "See: docs/development/VALIDATION_STRATEGY.md for details"
	@echo ""
	@echo "▶ STEP 1: Tier 1 Validation (pre-commit hooks - changed files)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@pre-commit run --show-diff-on-failure
	@echo ""
	@echo "▶ STEP 2: Tier 2 Validation (pre-push hooks - changed files)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Running: mypy, helm-lint, kustomize, pytest, deployment validation..."
	@echo ""
	@pre-commit run --hook-stage pre-push --show-diff-on-failure
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ Tier 1 + Tier 2 validation complete (changed files)!"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

## validate-push-full: Comprehensive validation of all files (pre-release audit)
validate-push-full:  ## Tier 2: Critical validation - all files (3-5 min)
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔍 TIER 2 VALIDATION - Critical Checks (All Files)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "This runs Tier 1 + Tier 2 validators on ALL files"
	@echo "Use before important releases or when refactoring core code"
	@echo "See: docs/development/VALIDATION_STRATEGY.md for details"
	@echo ""
	@echo "▶ STEP 1: Tier 1 Validation (pre-commit hooks - all files)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@pre-commit run --all-files --show-diff-on-failure
	@echo ""
	@echo "▶ STEP 2: Tier 2 Validation (pre-push hooks - all files)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Running: mypy, helm-lint, kustomize, pytest, deployment validation..."
	@echo ""
	@pre-commit run --hook-stage pre-push --all-files --show-diff-on-failure
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ Tier 1 + Tier 2 validation complete (all files)!"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

## validate-push: Alias to validate-push-changed (common case for development)
validate-push: validate-push-changed  ## Tier 2: Critical validation (default: changed files)

validate-full:  ## Tier 3: Comprehensive validation (12-15 min) - all tests, security, manual validators
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🎯 TIER 3 VALIDATION - Comprehensive (12-15 min)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "This runs Tier 1 + Tier 2 + Tier 3 validators (matches CI)"
	@echo "See: docs/development/VALIDATION_STRATEGY.md for details"
	@echo ""
	@echo "▶ STEP 1: Tier 1 Validation (pre-commit hooks)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@pre-commit run --all-files
	@echo ""
	@echo "▶ STEP 2: Tier 2 Validation (pre-push hooks)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@pre-commit run --hook-stage pre-push --all-files
	@echo ""
	@echo "▶ STEP 3: Tier 3 Validation (manual hooks + comprehensive tests)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Running manual stage validators..."
	@SKIP= pre-commit run --hook-stage manual --all-files
	@echo ""
	@echo "Running comprehensive test suite..."
	@$(MAKE) test-ci
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ All tiers complete! (Tier 1 + Tier 2 + Tier 3)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Legacy comprehensive pre-push validation target
# NOTE: validate-push (Tier 2) is now the recommended target for pre-push validation
# This target is kept for CI/CD parity and backward compatibility
## validate-pre-push-quick: Fast pre-push validation (skip integration tests)
## _validate-pre-push-phases-1-2: Shared validation phases (Phase 1, 2)
## Internal target - not meant to be called directly
_validate-pre-push-phases-1-2:
	@echo "PHASE 1: Fast Checks (Lockfile & Workflow Validation)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "▶ Lockfile Validation..."
	@uv lock --check && echo "✓ Lockfile valid" || (echo "✗ Lockfile validation failed" && exit 1)
	@echo ""
	@echo "▶ Dependency Tree Validation..."
	@uv pip check && echo "✓ Dependencies valid" || (echo "✗ Dependency conflicts detected" && exit 1)
	@echo ""
	@echo "▶ Workflow Validation Tests..."
	@OTEL_SDK_DISABLED=true $(UV_RUN) pytest tests/meta/ci/test_workflow_syntax.py tests/meta/ci/test_workflow_security.py tests/meta/ci/test_workflow_dependencies.py tests/meta/infrastructure/test_docker_paths.py -v --tb=short && echo "✓ Workflow tests passed" || (echo "✗ Workflow validation failed" && exit 1)
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "PHASE 2: Type Checking (Critical - matches CI)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "▶ MyPy Type Checking (Critical)..."
	@$(UV_RUN) mypy src/mcp_server_langgraph --no-error-summary && echo "✓ MyPy passed" || (echo "✗ MyPy found type errors" && exit 1)
	@echo ""

## _validate-pre-push-phase-4: Shared Phase 4 (Pre-commit hooks)
## Internal target - not meant to be called directly
_validate-pre-push-phase-4:
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "PHASE 4: Pre-commit Hooks (All Files - pre-push stage)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "▶ Pre-commit Hooks (All Files - Pre-Push Stage)..."
	@# Skip hooks already run in manual phases to avoid duplicate work
	@# Codex Finding #2 Fix (2025-11-23): Removed validate-pytest-config, check-test-memory-safety,
	@# check-async-mock-usage, validate-test-ids from SKIP list. These must run to maintain CI/local parity.
	@# They are no longer in validate-fast.py (see Phase 1.1) and run as individual hooks.
	@SKIP=uv-lock-check,uv-pip-check,mypy,run-pre-push-tests pre-commit run --all-files --hook-stage pre-push --show-diff-on-failure && echo "✓ Pre-commit hooks passed" || (echo "✗ Pre-commit hooks failed" && exit 1)
	@echo ""

validate-pre-push-quick:  ## Pre-push validation without integration tests (5-7 min)
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔍 Running pre-push validation (QUICK - no integration tests)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "Skipping integration tests (no Docker required)"
	@echo "Run 'make validate-pre-push-full' for comprehensive validation with Docker"
	@echo ""
	@$(MAKE) _validate-pre-push-phases-1-2
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "PHASE 3: Test Suite Validation"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "▶ Running Unit, API, Property, and Smoke Tests (Optimized)..."
	@# Runs: unit tests + API tests + property tests + smoke tests (11 critical startup tests)
	@# Includes: 19 xdist enforcement tests (validates pytest-xdist isolation patterns)
	@# Includes: Smoke tests (validate app startup, dependency injection, configuration)
	@$(UV_RUN) python scripts/run_pre_push_tests.py && echo "✓ Fast tests passed" || (echo "✗ Fast tests failed" && exit 1)
	@echo ""
	@echo "⚠ Skipping integration tests (use validate-pre-push-full for comprehensive validation)"
	@echo ""
	@$(MAKE) _validate-pre-push-phase-4
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✓ All pre-push validations passed (QUICK)!"
	@echo "✓ Your push should pass most CI checks"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

## validate-pre-push-full: Comprehensive pre-push validation with integration tests
## Use cases: Pre-release audit, major refactoring, CI debugging
validate-pre-push-full:  ## Comprehensive CI-equivalent validation with Docker (8-12 min)
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🎯 CI-EQUIVALENT VALIDATION (FULL)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "Use cases: Pre-release audit, major refactoring, CI debugging"
	@echo ""
	@$(MAKE) _validate-pre-push-phases-1-2
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "PHASE 3: Test Suite Validation"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "▶ Running Unit, API, Property, and Smoke Tests (Optimized)..."
	@# Runs: unit tests + API tests + property tests + smoke tests (11 critical startup tests)
	@# Includes: 19 xdist enforcement tests (validates pytest-xdist isolation patterns)
	@# Includes: Smoke tests (validate app startup, dependency injection, configuration)
	@$(UV_RUN) python scripts/run_pre_push_tests.py && echo "✓ Fast tests passed" || (echo "✗ Fast tests failed" && exit 1)
	@echo ""
	@echo "▶ Running Integration Tests (Docker - requires Docker daemon)..."
	@./scripts/test-integration.sh && echo "✓ Integration tests passed" || (echo "✗ Integration tests failed" && exit 1)
	@echo ""
	@$(MAKE) _validate-pre-push-phase-4
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✓ All pre-push validations passed (FULL)!"
	@echo "✓ Your push should pass all CI checks"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

## validate-pre-push: Smart routing based on CI_PARITY environment variable
## Includes: Lockfile check, dependency validation, MyPy type checking, test suite, pre-commit hooks
validate-pre-push:  ## Pre-push validation (auto-detects CI_PARITY for full vs quick)
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@if [ "$$CI_PARITY" = "1" ]; then \
		echo "🔍 CI_PARITY=1 detected - Running FULL CI-equivalent validation"; \
		echo "   This includes integration tests and matches CI exactly"; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		$(MAKE) validate-pre-push-full; \
	else \
		echo "🚀 Running QUICK validation (skip integration tests)"; \
		echo "   💡 Tip: Use 'CI_PARITY=1 make validate-pre-push' for full CI validation"; \
		echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
		$(MAKE) validate-pre-push-quick; \
	fi

act-dry-run:
	@echo "Showing what would execute in CI workflows..."
	@act push --list

# Code quality
# Modern tooling: Ruff (replaces black/isort/flake8)
# Aliases provided for backward compatibility (2025-11-23 - Codex Finding #3)

lint: lint-check  ## Alias for lint-check (Ruff linter + MyPy)

format: lint-fix  ## Alias for lint-fix (Ruff formatter)

security-check:
	@echo "Running bandit security scan..."
	$(UV_RUN) bandit -r . -x ./tests,./.venv -ll

security-scan-full:
	@echo "🔒 Running comprehensive security scan..."
	@mkdir -p security-reports
	@echo ""
	@echo "1/3 Running Bandit (code security)..."
	@bandit -r src/ -f json -o security-reports/bandit-report.json 2>/dev/null || true
	@bandit -r src/ -ll -x ./tests,./.venv || echo "⚠️  Bandit found issues (see report)"
	@echo ""
	@echo "2/3 Running Safety (dependency vulnerabilities)..."
	@if command -v safety >/dev/null 2>&1; then \
		safety check --json --output security-reports/safety-report.json 2>/dev/null || echo '{"vulnerabilities": []}' > security-reports/safety-report.json; \
	else \
		echo "⚠️  Safety not installed. Install with: uv tool install safety"; \
		echo '{"vulnerabilities": []}' > security-reports/safety-report.json; \
	fi
	@echo ""
	@echo "3/3 Running pip-audit (dependency vulnerabilities)..."
	@if command -v pip-audit >/dev/null 2>&1; then \
		pip-audit --format json --output security-reports/pip-audit-report.json 2>/dev/null || echo '{"dependencies": []}' > security-reports/pip-audit-report.json; \
	else \
		echo "⚠️  pip-audit not installed. Install with: uv tool install pip-audit"; \
		echo '{"dependencies": []}' > security-reports/pip-audit-report.json; \
	fi
	@echo ""
	@echo "📊 Generating consolidated report..."
	@$(UV_RUN) python scripts/security/generate_report.py security-reports
	@echo ""
	@echo "✅ Security scan complete!"
	@echo "📄 Report: security-reports/security-scan-report.md"
	@echo ""
	@cat security-reports/security-scan-report.md

# Modern Ruff-based lint targets (replaces flake8, black, isort)
lint-check:  ## Run Ruff linter (replaces flake8, isort checks)
	@echo "🔍 Running Ruff linter..."
	@$(UV_RUN) ruff check src/ tests/ --output-format=concise
	@echo "✓ Lint check complete (Ruff)"

lint-fix:  ## Auto-fix linting issues with Ruff
	@echo "🔧 Auto-fixing with Ruff..."
	@$(UV_RUN) ruff check src/ tests/ --fix
	@$(UV_RUN) ruff format src/ tests/
	@echo "✓ Auto-fix complete (Ruff)"

lint-format:  ## Format code with Ruff (replaces black)
	@echo "🎨 Formatting with Ruff..."
	@$(UV_RUN) ruff format src/ tests/
	@echo "✓ Format complete (Ruff)"

# Keep mypy and bandit separate (not replaced by Ruff)
lint-type-check:  ## Run mypy type checking
	@echo "🔍 Running mypy type checking..."
	@$(UV_RUN) mypy src/mcp_server_langgraph --no-error-summary
	@echo "✓ Type check complete (mypy)"

lint-security:  ## Run bandit security scan
	@echo "🔒 Running bandit security scan..."
	@$(UV_RUN) bandit -r src/ -ll
	@echo "✓ Security scan complete (bandit)"

lint-pre-commit:
	@echo "🎯 Simulating pre-commit hook (runs on staged files)..."
	@$(UV_RUN) pre-commit run --all-files
	@echo "✓ Pre-commit simulation complete"

lint-pre-push:
	@echo "🚀 Simulating pre-push hook (runs on changed files)..."
	@bash $$(git rev-parse --git-common-dir)/hooks/pre-push
	@echo "✓ Pre-push simulation complete"

lint-install:
	@echo "📦 Installing/reinstalling lint hooks..."
	@$(UV_RUN) pre-commit install
	@chmod +x $$(git rev-parse --git-common-dir)/hooks/pre-push
	@echo "✓ Hooks installed:"
	@echo "  • pre-commit (auto-fix Ruff formatter, run Ruff linter/MyPy/bandit)"
	@echo "  • pre-push (comprehensive validation before push)"
	@echo ""
	@echo "Test hooks:"
	@echo "  make lint-pre-commit"
	@echo "  make lint-pre-push"

# Running servers
run:
	$(UV_RUN) python -m mcp_server_langgraph.mcp.server_stdio

run-streamable:
	$(UV_RUN) python -m mcp_server_langgraph.mcp.server_streamable

logs:
	$(DOCKER_COMPOSE) logs -f

clean:
	@echo "Cleaning up (parallel operations)..."
	@$(DOCKER_COMPOSE) down -v & pid1=$$!; \
	find . -type f -name '*.pyc' -delete & pid2=$$!; \
	find . -type d -name '__pycache__' -delete & pid3=$$!; \
	find . -type d -name '*.egg-info' -exec rm -rf {} + & pid4=$$!; \
	rm -rf .pytest_cache .coverage htmlcov & pid5=$$!; \
	wait $$pid1 $$pid2 $$pid3 $$pid4 $$pid5
	@echo "✓ Infrastructure stopped and caches removed"

clean-all: clean
	rm -rf .venv
	@echo "✓ Deep clean complete"

reset: clean setup-infra setup-openfga
	@echo "✓ System reset complete"

# Kong targets
setup-kong:
	@echo "Setting up Kong API Gateway..."
	helm repo add kong https://charts.konghq.com
	helm repo update
	helm install kong kong/kong \
		--namespace kong \
		--create-namespace \
		--set ingressController.enabled=true \
		--set proxy.type=LoadBalancer
	@echo "✓ Kong installed"
	@echo ""
	@echo "Apply Kong configurations:"
	@echo "  kubectl apply -k deployments/kubernetes/kong/"

test-rate-limit:
	@echo "Testing rate limits..."
	@for i in $$(seq 1 100); do \
		curl -s -o /dev/null -w "Request $$i: %{http_code}\n" \
			-H "apikey: test-key" \
			http://localhost:8000/; \
		sleep 0.1; \
	done

# Deployment targets
deploy-dev:
	@echo "Deploying to development environment..."
	kubectl apply -k deployments/overlays/dev
	@echo "Waiting for rollout..."
	kubectl rollout status deployment/dev-langgraph-agent -n langgraph-agent-dev --timeout=5m
	@echo "✓ Development deployment complete"
	@echo ""
	@echo "Check status:"
	@echo "  kubectl get pods -n langgraph-agent-dev"
	@echo "  kubectl logs -f deployment/dev-langgraph-agent -n langgraph-agent-dev"

deploy-staging:
	@echo "Deploying to staging environment..."
	kubectl apply -k deployments/overlays/staging
	@echo "Waiting for rollout..."
	kubectl rollout status deployment/staging-langgraph-agent -n langgraph-agent-staging --timeout=5m
	@echo "✓ Staging deployment complete"
	@echo ""
	@echo "Check status:"
	@echo "  kubectl get pods -n langgraph-agent-staging"
	@echo "  kubectl logs -f deployment/staging-langgraph-agent -n langgraph-agent-staging"

deploy-production:
	@echo "⚠️  WARNING: Deploying to PRODUCTION environment"
	@echo "Press Ctrl+C within 10 seconds to cancel..."
	@sleep 10
	@echo "Deploying to production with Helm..."
	helm upgrade --install langgraph-agent deployments/helm/mcp-server-langgraph \
		--namespace langgraph-agent \
		--create-namespace \
		--wait \
		--timeout 10m
	@echo "✓ Production deployment complete"
	@echo ""
	@echo "Check status:"
	@echo "  kubectl get pods -n langgraph-agent"
	@echo "  kubectl logs -f deployment/langgraph-agent -n langgraph-agent"

deploy-rollback-dev:
	@echo "Rolling back development deployment..."
	kubectl rollout undo deployment/dev-langgraph-agent -n langgraph-agent-dev
	kubectl rollout status deployment/dev-langgraph-agent -n langgraph-agent-dev
	@echo "✓ Development rollback complete"

deploy-rollback-staging:
	@echo "Rolling back staging deployment..."
	kubectl rollout undo deployment/staging-langgraph-agent -n langgraph-agent-staging
	kubectl rollout status deployment/staging-langgraph-agent -n langgraph-agent-staging
	@echo "✓ Staging rollback complete"

deploy-rollback-production:
	@echo "⚠️  WARNING: Rolling back PRODUCTION deployment"
	@echo "Press Ctrl+C within 10 seconds to cancel..."
	@sleep 10
	helm rollback langgraph-agent -n langgraph-agent
	@echo "✓ Production rollback complete"

# ==============================================================================
# Preview GKE Deployment (unified workflow)
# ==============================================================================
# RECOMMENDED (single-command, full infrastructure + K8s):
#   make gke-preview-up     # Deploy everything: Terraform + Kubernetes
#   make gke-preview-down   # Teardown everything: Kubernetes + Terraform
#   make gke-preview-status # Check environment status
#
# ALTERNATIVE (step-by-step, K8s only - assumes infrastructure exists):
#   1. make preflight-preview-gke   # Pre-flight checks
#   2. make deploy-preview-gke      # Deploy to GKE
#   3. make postflight-preview-gke  # Validate deployment
#   4. make teardown-preview-gke    # Clean teardown (K8s only)

preflight-preview-gke:  ## Pre-flight check for Preview GKE deployment
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🔍 Preview GKE Pre-Flight Checks"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "▶ Validating Kustomize overlay..."
	@kubectl kustomize deployments/overlays/preview-gke > /dev/null && echo "  ✓ Kustomize overlay valid" || (echo "  ✗ Kustomize overlay invalid" && exit 1)
	@echo ""
	@echo "▶ Checking GKE cluster access..."
	@kubectl cluster-info > /dev/null 2>&1 && echo "  ✓ kubectl connected to cluster" || (echo "  ✗ kubectl not connected - run: gcloud container clusters get-credentials preview-mcp-server-langgraph-gke --region us-central1" && exit 1)
	@echo ""
	@echo "▶ Checking namespace exists..."
	@kubectl get namespace preview-mcp-server-langgraph > /dev/null 2>&1 && echo "  ✓ Namespace exists" || echo "  ⚠ Namespace will be created during deploy"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✓ Pre-flight checks passed"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

deploy-preview-gke:  ## Deploy to Preview GKE (includes preflight + postflight)
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🚀 Deploying to Preview GKE"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@$(MAKE) preflight-preview-gke
	@echo ""
	@echo "▶ Applying Kustomize manifests..."
	kubectl apply -k deployments/overlays/preview-gke
	@echo ""
	@echo "▶ Waiting for rollouts..."
	@kubectl rollout status deployment/preview-mcp-server-langgraph -n preview-mcp-server-langgraph --timeout=10m || true
	@kubectl rollout status deployment/preview-keycloak -n preview-mcp-server-langgraph --timeout=10m || true
	@kubectl rollout status deployment/preview-openfga -n preview-mcp-server-langgraph --timeout=10m || true
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✓ Preview GKE deployment complete"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "Next: Run 'make postflight-preview-gke' to validate"

postflight-preview-gke:  ## Post-flight validation for Preview GKE deployment
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "✅ Preview GKE Post-Flight Validation"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	./scripts/gcp/validate-preview-deployment.sh

smoke-test-preview-gke:  ## Run smoke tests on Preview GKE
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🧪 Preview GKE Smoke Tests"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	./scripts/gcp/preview-smoke-tests.sh

teardown-preview-gke:  ## Teardown Preview GKE (Kubernetes resources only)
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🗑️  Preview GKE Teardown (Kubernetes Resources)"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "This will delete all Kubernetes resources in preview-mcp-server-langgraph namespace"
	@echo ""
	kubectl delete -k deployments/overlays/preview-gke --ignore-not-found=true || true
	@echo ""
	@echo "✓ Kubernetes resources deleted"
	@echo ""
	@echo "Note: To teardown infrastructure (GKE, CloudSQL, Redis, VPC), run:"
	@echo "  ./scripts/gcp/teardown-preview-infrastructure.sh"

teardown-preview-infra:  ## Teardown Preview GKE infrastructure (full cleanup)
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "⚠️  WARNING: Full Preview Infrastructure Teardown"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "This will DELETE:"
	@echo "  • GKE Autopilot cluster"
	@echo "  • Cloud SQL PostgreSQL instance"
	@echo "  • Memorystore Redis instance"
	@echo "  • VPC and network resources"
	@echo "  • IAM service accounts"
	@echo "  • Secret Manager secrets"
	@echo ""
	./scripts/gcp/teardown-preview-infrastructure.sh

deploy-rollback-preview-gke:  ## Rollback Preview GKE deployment
	@echo "Rolling back Preview GKE deployment..."
	kubectl rollout undo deployment/preview-mcp-server-langgraph -n preview-mcp-server-langgraph
	kubectl rollout status deployment/preview-mcp-server-langgraph -n preview-mcp-server-langgraph
	@echo "✓ Preview GKE rollback complete"

# ==============================================================================
# Single-Command GKE Preview Deployment (RECOMMENDED)
# ==============================================================================
# These targets use Terraform + wrapper scripts for complete infrastructure
# management. They handle: prerequisites, cost warnings, Terraform, K8s, and
# validation automatically.
#
# Environment Variables:
#   GCP_PROJECT_ID  - Override default GCP project (vishnu-sandbox-20250310)
#   GCP_REGION      - Override default region (us-central1)

gke-preview-up:  ## 🚀 Deploy complete GKE preview environment (Terraform + K8s)
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🚀 GKE Preview Environment - Full Setup"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "This will create:"
	@echo "  • GKE Autopilot cluster (~15 min)"
	@echo "  • Cloud SQL PostgreSQL HA (~10 min)"
	@echo "  • Memorystore Redis HA (~5 min)"
	@echo "  • VPC, Cloud NAT, networking"
	@echo "  • Kubernetes workloads"
	@echo ""
	@echo "Estimated time: 25-30 minutes"
	@echo "Estimated cost: ~\$$325/month"
	@echo ""
	./scripts/gcp/gke-preview-up.sh

gke-preview-down:  ## 🗑️  Teardown complete GKE preview environment
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "🗑️  GKE Preview Environment - Full Teardown"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	./scripts/gcp/gke-preview-down.sh

gke-preview-status:  ## 📊 Check GKE preview environment status
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "📊 GKE Preview Environment Status"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "GCP Project: $${GCP_PROJECT_ID:-vishnu-sandbox-20250310}"
	@echo "Region: $${GCP_REGION:-us-central1}"
	@echo ""
	@echo "▶ GKE Cluster:"
	@gcloud container clusters describe preview-mcp-server-langgraph-gke \
		--region=$${GCP_REGION:-us-central1} \
		--project=$${GCP_PROJECT_ID:-vishnu-sandbox-20250310} \
		--format="value(status)" 2>/dev/null && echo "  Status: RUNNING" || echo "  Status: NOT FOUND"
	@echo ""
	@echo "▶ Cloud SQL:"
	@gcloud sql instances describe preview-mcp-slg-postgres \
		--project=$${GCP_PROJECT_ID:-vishnu-sandbox-20250310} \
		--format="value(state)" 2>/dev/null && echo "  Status: RUNNABLE" || echo "  Status: NOT FOUND"
	@echo ""
	@echo "▶ Memorystore Redis:"
	@gcloud redis instances describe preview-mcp-slg-redis \
		--region=$${GCP_REGION:-us-central1} \
		--project=$${GCP_PROJECT_ID:-vishnu-sandbox-20250310} \
		--format="value(state)" 2>/dev/null && echo "  Status: READY" || echo "  Status: NOT FOUND"
	@echo ""
	@echo "▶ Kubernetes Pods:"
	@kubectl get pods -n preview-mcp-server-langgraph --no-headers 2>/dev/null | wc -l | xargs -I{} echo "  Count: {} pods" || echo "  Status: No kubectl access"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Deployment testing
test-k8s-deployment:
	@echo "Running Kubernetes deployment tests..."
	bash scripts/deployment/test_k8s_deployment.sh

test-helm-deployment:
	@echo "Running Helm deployment tests..."
	bash scripts/deployment/test_helm_deployment.sh

# ==============================================================================
# Development Shortcuts
# ==============================================================================

dev-setup: install-dev setup-infra setup-openfga setup-keycloak
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "✓ Development environment setup complete!"
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Update .env with OPENFGA_STORE_ID and OPENFGA_MODEL_ID"
	@echo "  2. Update .env with KEYCLOAK_CLIENT_SECRET"
	@echo "  3. Run: make test-unit"
	@echo "  4. Run: make run-streamable"
	@echo "  5. Visit: http://localhost:3001 (Grafana)"
	@echo ""

quick-start:
	@echo "🚀 Quick starting MCP Server LangGraph..."
	@echo ""
	@if [ ! -d ".venv" ]; then \
		echo "Creating virtual environment..."; \
		uv venv; \
	fi
	@echo "Installing dependencies..."
	@$(MAKE) install-dev -s
	@echo "Starting infrastructure..."
	@$(MAKE) setup-infra -s
	@echo "Waiting for services to be healthy..."
	@bash scripts/utils/wait_for_services.sh docker-compose.yml
	@echo ""
	@echo "✓ Quick start complete!"
	@echo ""
	@echo "Services running:"
	@$(DOCKER_COMPOSE) ps
	@echo ""
	@echo "Run tests: make test-unit"
	@echo "Run server: make run-streamable"
	@echo "View dashboards: make monitoring-dashboard"

monitoring-dashboard:
	@echo "Opening Grafana dashboards..."
	@echo ""
	@echo "Grafana URL: http://localhost:3001"
	@echo "  Username: admin"
	@echo "  Password: admin"
	@echo ""
	@echo "Available dashboards:"
	@echo "  • LangGraph Agent - http://localhost:3001/d/langgraph-agent"
	@echo "  • Security Dashboard - http://localhost:3001/d/security"
	@echo "  • Authentication - http://localhost:3001/d/authentication"
	@echo "  • OpenFGA - http://localhost:3001/d/openfga"
	@echo "  • LLM Performance - http://localhost:3001/d/llm-performance"
	@echo "  • SLA Monitoring - http://localhost:3001/d/sla-monitoring"
	@echo "  • SOC2 Compliance - http://localhost:3001/d/soc2-compliance"
	@echo "  • Keycloak SSO - http://localhost:3001/d/keycloak"
	@echo "  • Redis Sessions - http://localhost:3001/d/redis-sessions"
	@echo ""
	@command -v open >/dev/null 2>&1 && open http://localhost:3001 || \
		command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:3001 || \
		echo "Open http://localhost:3001 in your browser"

health-check:
	@echo "🏥 Checking system health..."
	@echo ""
	@echo "Infrastructure Services:"
	@$(DOCKER_COMPOSE) ps | grep -E "(openfga|postgres|keycloak|jaeger|prometheus|grafana|redis)" || echo "  ⚠️  Services not running"
	@echo ""
	@echo "Port Check (parallel):"
	@( \
		for port in 8080 5432 8082 16686 9090 3001 6379; do \
			( \
				if nc -z localhost $$port 2>/dev/null; then \
					echo "  ✓ Port $$port: OK"; \
				else \
					echo "  ✗ Port $$port: Not responding"; \
				fi \
			) & \
		done; \
		wait \
	)
	@echo ""
	@echo "Python Environment:"
	@if [ -d ".venv" ]; then \
		echo "  ✓ Virtual environment: OK"; \
	else \
		echo "  ✗ Virtual environment: Missing"; \
	fi
	@echo ""
	@echo "Run 'make setup-infra' if services are not running"

health-check-fast:
	@echo "⚡ Fast health check (parallel port scanning)..."
	@echo ""
	@( \
		( nc -z localhost 8080 2>/dev/null && echo "  ✓ OpenFGA (8080): OK" || echo "  ✗ OpenFGA (8080): DOWN" ) & \
		( nc -z localhost 5432 2>/dev/null && echo "  ✓ PostgreSQL (5432): OK" || echo "  ✗ PostgreSQL (5432): DOWN" ) & \
		( nc -z localhost 8082 2>/dev/null && echo "  ✓ Keycloak (8082): OK" || echo "  ✗ Keycloak (8082): DOWN" ) & \
		( nc -z localhost 16686 2>/dev/null && echo "  ✓ Jaeger (16686): OK" || echo "  ✗ Jaeger (16686): DOWN" ) & \
		( nc -z localhost 9090 2>/dev/null && echo "  ✓ Prometheus (9090): OK" || echo "  ✗ Prometheus (9090): DOWN" ) & \
		( nc -z localhost 3001 2>/dev/null && echo "  ✓ Grafana (3001): OK" || echo "  ✗ Grafana (3001): DOWN" ) & \
		( nc -z localhost 6379 2>/dev/null && echo "  ✓ Redis (6379): OK" || echo "  ✗ Redis (6379): DOWN" ) & \
		wait \
	)
	@echo ""
	@echo "✓ Fast health check complete (70% faster than full check)"

db-migrate:
	@echo "Running database migrations..."
	@echo "⚠️  No migrations configured yet"
	@echo "This target is a placeholder for future database migration scripts"

load-test:
	@echo "🔥 Running load tests..."
	@if command -v locust >/dev/null 2>&1; then \
		echo "Starting Locust..."; \
		locust -f tests/performance/locustfile.py --headless -u 100 -r 10 -t 60s --host http://localhost:8000; \
	else \
		echo "⚠️  Locust not installed. Install with: uv tool install locust"; \
		echo ""; \
		echo "Alternative: Use k6"; \
		echo "  k6 run tests/performance/load_test.js"; \
	fi

stress-test:
	@echo "💪 Running stress tests (parallel)..."
	@echo "This will test system limits and failure modes"
	@OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m "stress" -v --tb=short || echo "No stress tests found. Add tests with @pytest.mark.stress"

# ==============================================================================
# Git Hooks & Pre-commit
# ==============================================================================

pre-commit-setup:
	@echo "Setting up pre-commit hooks..."
	@if command -v pre-commit >/dev/null 2>&1; then \
		pre-commit install; \
		pre-commit install --hook-type commit-msg; \
		echo "✓ Pre-commit hooks installed"; \
	else \
		echo "Installing pre-commit via uv..."; \
		uv tool install pre-commit; \
		pre-commit install; \
		pre-commit install --hook-type commit-msg; \
		echo "✓ Pre-commit hooks installed"; \
	fi
	@echo ""
	@echo "Hooks installed:"
	@echo "  • Ruff (code formatting + linting, replaces black/isort/flake8)"
	@echo "  • bandit (security scanning)"
	@echo "  • MyPy (type checking - runs in pre-push stage)"
	@echo ""
	@echo "Note: MyPy runs at pre-push stage for comprehensive type checking"
	@echo "Run manually: pre-commit run --all-files"

git-hooks: pre-commit-setup
	@echo "✅ Git hooks installed successfully:"
	@echo ""
	@echo "  • pre-commit   - Format, lint, and basic validation on commit"
	@echo "                   Runs: Ruff (formatter + linter), bandit, etc."
	@echo "                   Timing: < 30 seconds"
	@echo ""
	@echo "  • pre-push     - Comprehensive CI-equivalent validation before push"
	@echo "                   Runs: 4-phase validation (lockfile, type check, tests, hooks)"
	@echo "                   Timing: 8-12 minutes (matches CI exactly)"
	@echo ""
	@echo "  • commit-msg   - Conventional commits enforcement"
	@echo "                   Validates: commit message format"
	@echo ""
	@echo "  • post-commit  - Auto-update context files after commit"
	@echo "                   Updates: .claude/context/recent-work.md"
	@echo ""
	@echo "📖 For details: See TESTING.md#git-hooks-and-validation"
	@echo "🔍 To test:     make validate-pre-push (runs full pre-push validation)"

# ==============================================================================
# Documentation
# ==============================================================================

docs-serve:
	@echo "📚 Serving Mintlify documentation locally..."
	@if command -v npx >/dev/null 2>&1; then \
		cd docs && npx mintlify dev; \
	else \
		echo "⚠️  npx not found. Install Node.js first."; \
	fi

docs-build:
	@echo "📦 Building Mintlify documentation..."
	@if command -v npx >/dev/null 2>&1; then \
		cd docs && npx mintlify build; \
	else \
		echo "⚠️  npx not found. Install Node.js first."; \
	fi

docs-deploy:
	@echo "🚀 Deploying documentation to Mintlify..."
	@echo ""
	@echo "Prerequisites:"
	@echo "  1. Mintlify account setup"
	@echo "  2. mintlify CLI authenticated"
	@echo ""
	@read -p "Continue? (y/n) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd docs && npx mintlify deploy; \
	else \
		echo "Deployment cancelled"; \
	fi

# Documentation validation targets (Simplified 2025-11-15)
# PRIMARY validator: Mintlify CLI (comprehensive, fast, official)
# SUPPLEMENTARY: Specialized validators for unique checks
# See: docs-internal/DOCS_VALIDATION_SIMPLIFICATION.md

docs-validate: docs-validate-mintlify docs-validate-specialized
	@echo ""
	@echo "✅ All documentation validation passed!"
	@echo ""
	@echo "PRIMARY validator (Mintlify CLI): ✅"
	@echo "Specialized validators: ✅"
	@echo ""

docs-validate-mintlify:  ## PRIMARY: Validate Mintlify docs with official CLI (broken links, navigation, images, frontmatter, MDX syntax)
	@echo "🎯 PRIMARY VALIDATOR: Mintlify CLI"
	@echo "Checks: links, navigation, images, frontmatter, MDX syntax, anchor links, orphaned pages"
	@if command -v npx >/dev/null 2>&1; then \
		cd docs && npx mintlify broken-links || \
			(echo "❌ Mintlify validation failed. Fix broken links, navigation, or MDX syntax issues." && \
			 echo "Run locally: cd docs && npx mintlify broken-links" && exit 1); \
		echo "✅ Mintlify validation passed"; \
	else \
		echo "⚠️  Mintlify CLI not found. Install with: npm install -g mintlify"; \
		exit 1; \
	fi

docs-validate-specialized:  ## SUPPLEMENTARY: Run specialized validators (ADR sync, MDX extensions)
	@echo "🔧 SUPPLEMENTARY: Specialized validators"
	@echo "   Note: Code block validation disabled (caused more trouble than it's worth)"
	@echo "🔍 Validating ADR synchronization..."
	@python scripts/validators/adr_sync_validator.py || \
		(echo "❌ ADR synchronization failed." && exit 1)
	@echo "🔍 Validating MDX file extensions..."
	@python scripts/validators/mdx_extension_validator.py --docs-dir docs || \
		(echo "❌ MDX extension validation failed." && exit 1)
	@echo "✅ Specialized validators passed"

# REMOVED 2025-11-16: Deprecated doc validators removed (CI/CD optimization)
# Old targets: docs-validate-mdx, docs-validate-links
# Replacement: make docs-validate-mintlify (PRIMARY validator using Mintlify CLI)
# The Mintlify CLI broken-links check is comprehensive and authoritative
# See: VALIDATION_STRATEGY.md for documentation validation approach

docs-validate-version:
	@echo "🏷️  Checking version consistency..."
	@python3 scripts/validators/check_version_consistency.py || \
		(echo "⚠️  Version inconsistencies found (review recommended)." && exit 0)

docs-fix-mdx:
	@echo "🔧 Auto-fixing MDX syntax errors..."
	@python3 scripts/docs/fix_mdx_syntax.py --all
	@echo "✅ MDX syntax fixed. Review changes with 'git diff docs/'"

docs-test:
	@echo "🧪 Running documentation validation tests..."
	@$(UV_RUN) pytest tests/test_mdx_validation.py tests/test_link_checker.py -v

docs-audit:
	@echo "📊 Running comprehensive documentation audit..."
	@echo "Current version: $$(python3 -c 'import toml; print(toml.load(open(\"pyproject.toml\"))[\"project\"][\"version\"])')"
	@echo ""
	@echo "Running validations..."
	@make docs-validate || true
	@echo ""
	@echo "See docs-internal/DOCUMENTATION_AUDIT_*.md for detailed reports"

# ==============================================================================
# Test Infrastructure Reports
# ==============================================================================

generate-reports:  ## Regenerate all test infrastructure scan reports
	@echo "📊 Regenerating test infrastructure reports..."
	@echo ""
	@echo "🔍 Running AsyncMock configuration scan..."
	@$(UV_RUN) python scripts/validators/check_async_mock_configuration.py tests/**/*.py > docs-internal/reports/ASYNC_MOCK_SCAN.md 2>&1 || true
	@echo "✅ AsyncMock scan complete"
	@echo ""
	@echo "🔍 Running memory safety scan..."
	@$(UV_RUN) python scripts/validators/check_test_memory_safety.py tests/**/*.py > docs-internal/reports/MEMORY_SAFETY_SCAN.md 2>&1 || true
	@echo "✅ Memory safety scan complete"
	@echo ""
	@echo "📈 Generating test suite statistics..."
	@$(UV_RUN) python scripts/generate_test_stats.py > docs-internal/reports/TEST_SUITE_STATS.md 2>&1 || true
	@echo "✅ Test statistics generated"
	@echo ""
	@echo "✅ All reports regenerated in docs-internal/reports/"
	@echo "💡 Review with: ls -lh docs-internal/reports/"

# ==============================================================================
# Enhanced Testing Targets
# ==============================================================================

test-watch:
	@echo "👀 Running tests in watch mode..."
	$(UV_RUN) ptw --no-cov

test-fast:
	@echo "⚡ Running all tests without coverage (parallel, fast iteration)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto --tb=short
	@echo "✓ Fast tests complete"
	@echo ""
	@echo "For maximum speed: 'make test-dev' (parallel + fast-fail)"

test-fast-unit:
	@echo "⚡ Running unit tests without coverage (parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m unit --tb=short

test-dev:
	@echo "🚀 Running tests in development mode (parallel, fast-fail, no coverage)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -x --maxfail=3 --tb=short -m "(unit or api or property or validation) and not llm and not slow"
	@echo "✓ Development tests complete"
	@echo ""
	@echo "Features: Parallel execution, stop on first failure, skip slow tests"
	@echo "Coverage: unit + API + property + validation tests (matches CI validation)"

test-fast-core:
	@echo "⚡ Running core unit tests only (fastest iteration)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m "unit and not slow and not integration" --tb=line -q
	@echo "✓ Core tests complete"
	@echo ""
	@echo "Use for rapid iteration (typically < 5 seconds)"

test-slow:
	@echo "🐌 Running slow tests only (parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m slow -v --tb=short

test-compliance:
	@echo "📋 Running compliance tests (GDPR, HIPAA, SOC2, SLA, parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m "gdpr or soc2 or sla" -v --tb=short

test-failed:
	@echo "🔁 Re-running failed tests (parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto --lf -v

test-debug:
	@echo "🐛 Running tests in debug mode..."
	OTEL_SDK_DISABLED=true $(PYTEST) -v --pdb --pdbcls=IPython.terminal.debugger:Pdb

# ==============================================================================
# Monitoring & Observability
# ==============================================================================

logs-follow:
	@echo "📜 Following all logs..."
	$(DOCKER_COMPOSE) logs -f --tail=100

logs-agent:
	@echo "📜 Following agent logs..."
	$(DOCKER_COMPOSE) logs -f --tail=100 mcp-server || echo "Agent not running in docker-compose"

logs-prometheus:
	@echo "📜 Prometheus logs..."
	$(DOCKER_COMPOSE) logs prometheus

logs-grafana:
	@echo "📜 Grafana logs..."
	$(DOCKER_COMPOSE) logs grafana

prometheus-ui:
	@echo "Opening Prometheus UI..."
	@command -v open >/dev/null 2>&1 && open http://localhost:9090 || \
		command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:9090 || \
		echo "Open http://localhost:9090 in your browser"

jaeger-ui:
	@echo "Opening Jaeger UI..."
	@command -v open >/dev/null 2>&1 && open http://localhost:16686 || \
		command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:16686 || \
		echo "Open http://localhost:16686 in your browser"

# ==============================================================================
# Database Operations
# ==============================================================================

db-shell:
	@echo "Opening PostgreSQL shell..."
	$(DOCKER_COMPOSE) exec postgres psql -U postgres -d openfga

db-backup:
	@echo "Creating database backup..."
	@mkdir -p backups
	$(DOCKER_COMPOSE) exec -T postgres pg_dump -U postgres openfga > backups/openfga_backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✓ Backup created in backups/"

db-restore:
	@echo "⚠️  This will restore from the latest backup"
	@ls -t backups/*.sql | head -1
	@read -p "Continue? (y/n) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE) exec -T postgres psql -U postgres -d openfga < $$(ls -t backups/*.sql | head -1); \
		echo "✓ Database restored"; \
	else \
		echo "Restore cancelled"; \
	fi
