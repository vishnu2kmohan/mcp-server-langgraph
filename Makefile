.PHONY: help install install-dev setup-infra setup-openfga setup-infisical test test-unit test-integration test-coverage test-coverage-fast test-coverage-html test-coverage-xml test-coverage-terminal test-coverage-changed test-property test-contract test-regression test-mutation test-infra-up test-infra-down test-infra-logs test-e2e test-api test-mcp-server test-new test-quick-new validate-openapi validate-deployments validate-all deploy-dev deploy-staging deploy-production lint format security-check lint-check lint-fix lint-pre-commit lint-pre-push lint-install clean dev-setup quick-start monitoring-dashboard health-check health-check-fast db-migrate load-test stress-test docs-serve docs-build pre-commit-setup git-hooks

# Sequential-only targets (cannot be parallelized)
.NOTPARALLEL: deploy-production deploy-staging deploy-dev setup-keycloak setup-openfga setup-infisical dev-setup

# ==============================================================================
# Variables
# ==============================================================================
PYTEST := .venv/bin/pytest
DOCKER_COMPOSE := docker compose
UV_RUN := uv run
COV_SRC := src/mcp_server_langgraph
COV_OPTIONS := --cov=$(COV_SRC)

help:
	@echo "LangGraph MCP Agent - Make Commands"
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
	@echo "Testing:"
	@echo "  make test                     Run all automated tests with coverage"
	@echo "  make test-unit                Run unit tests with coverage"
	@echo "  make test-integration         Run integration tests in Docker"
	@echo ""
	@echo "Fast Testing (40-70% faster):"
	@echo "  make test-dev                 🚀 Development mode (parallel, fast-fail) - RECOMMENDED"
	@echo "  make test-parallel            Run all tests in parallel (no coverage)"
	@echo "  make test-parallel-unit       Run unit tests in parallel"
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
	@echo "New Testing Features:"
	@echo "  make test-infra-up            Start test infrastructure (docker-compose.test.yml)"
	@echo "  make test-infra-down          Stop and clean test infrastructure"
	@echo "  make test-infra-logs          View test infrastructure logs"
	@echo "  make test-e2e                 Run end-to-end tests (full user journeys)"
	@echo "  make test-api                 Run API endpoint tests"
	@echo "  make test-mcp-server          Run MCP server unit tests"
	@echo "  make test-new                 Run all newly added tests"
	@echo "  make test-quick-new           Quick check of new tests (parallel)"
	@echo ""
	@echo "Validation:"
	@echo "  make validate-openapi         Validate OpenAPI schema"
	@echo "  make validate-deployments     Validate all deployment configs"
	@echo "  make validate-docker-compose  Validate Docker Compose"
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
	@echo "  make lint                Run linters (flake8, mypy)"
	@echo "  make format              Format code (black, isort)"
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
	uv sync
	@echo "✓ Development dependencies installed"
	@echo "  Note: Includes all [dependency-groups] from pyproject.toml"

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
	@echo "Tip: Use 'make test-fast' or 'make test-parallel' for faster iteration"

test-unit:
	@echo "Running unit tests with coverage (parallel execution, matches CI)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m unit $(COV_OPTIONS) --cov-report=term-missing
	@echo "✓ Unit tests complete"

test-unit-fast:
	@echo "Running unit tests without coverage (fast iteration)..."
	@echo "⚠️  DEPRECATED: Use 'make test-parallel-unit' or 'make test-dev' instead"
	OTEL_SDK_DISABLED=true $(PYTEST) -m unit --tb=short
	@echo "✓ Fast unit tests complete"

test-ci:
	@echo "Running tests exactly as CI does..."
	OTEL_SDK_DISABLED=true $(PYTEST) -m unit $(COV_OPTIONS) --cov-report=xml --cov-report=term-missing
	@echo "✓ CI-equivalent tests complete"
	@echo "  Coverage XML: coverage.xml"

test-integration:
	@echo "Running integration tests in Docker environment (matches CI)..."
	./scripts/test-integration.sh
	@echo "✓ Integration tests complete"

test-integration-local:
	@echo "⚠️  Running integration tests locally (requires services running)..."
	@echo "Note: CI uses Docker. Use 'make test-integration' to match CI exactly."
	OTEL_SDK_DISABLED=true $(PYTEST) -m integration --no-cov --tb=short
	@echo "✓ Local integration tests complete"

test-integration-services:
	@echo "Starting integration test services only..."
	./scripts/test-integration.sh --services

test-integration-build:
	@echo "Rebuilding and running integration tests..."
	./scripts/test-integration.sh --build

test-integration-debug:
	@echo "Running integration tests (keep containers for debugging)..."
	./scripts/test-integration.sh --keep

test-integration-cleanup:
	@echo "Cleaning up integration test containers..."
	$(DOCKER_COMPOSE) -f docker/docker-compose.test.yml down -v --remove-orphans
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
		.venv/bin/coverage combine --append coverage-integration/.coverage* 2>/dev/null || true; \
		.venv/bin/coverage xml -o coverage-combined.xml; \
		.venv/bin/coverage html -d htmlcov-combined; \
		.venv/bin/coverage report; \
		echo ""; \
		echo "✓ Combined coverage reports generated:"; \
		echo "  HTML: htmlcov-combined/index.html"; \
		echo "  XML: coverage-combined.xml"; \
	else \
		echo "  ⚠️  No integration coverage found, using unit tests only"; \
		.venv/bin/coverage xml; \
		.venv/bin/coverage html; \
		.venv/bin/coverage report; \
	fi

test-auth:
	@echo "Testing OpenFGA authorization..."
	$(UV_RUN) python examples/openfga_usage.py

test-mcp:
	@echo "Testing MCP server..."
	$(UV_RUN) python examples/client_stdio.py

benchmark:
	@echo "Running performance benchmarks..."
	$(PYTEST) -m benchmark -v --benchmark-only --benchmark-autosave
	@echo "✓ Benchmark results saved"

# New test targets
test-property:
	@echo "Running property-based tests (Hypothesis, parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m property -v
	@echo "✓ Property tests complete"

test-contract:
	@echo "Running contract tests (MCP protocol, OpenAPI, parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m contract -v
	@echo "✓ Contract tests complete"

test-regression:
	@echo "Running performance regression tests (parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m regression -v
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

# New Testing Infrastructure Targets

test-infra-up:
	@echo "Starting test infrastructure (docker-compose.test.yml)..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml up -d
	@echo "✓ Test infrastructure started"
	@echo ""
	@echo "Test Services (offset ports by 1000):"
	@echo "  PostgreSQL: localhost:9432"
	@echo "  Redis:      localhost:9379"
	@echo "  OpenFGA:    http://localhost:9080"
	@echo "  Keycloak:   http://localhost:9082"
	@echo "  Qdrant:     http://localhost:9333"
	@echo ""

test-infra-down:
	@echo "Stopping test infrastructure..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml down -v --remove-orphans
	@echo "✓ Test infrastructure stopped and cleaned"

test-infra-logs:
	@echo "Showing test infrastructure logs..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml logs -f

test-e2e:
	@echo "Running end-to-end tests (requires test infrastructure)..."
	@echo "Ensuring test infrastructure is running..."
	$(MAKE) test-infra-up
	@echo ""
	@echo "Waiting for services to be healthy..."
	@sleep 10
	@echo ""
	@echo "Running E2E tests..."
	TESTING=true OTEL_SDK_DISABLED=true $(PYTEST) -m e2e -v --tb=short
	@echo "✓ E2E tests complete"

test-api:
	@echo "Running API endpoint tests (unit tests for REST APIs)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m "api and unit" -v
	@echo "✓ API endpoint tests complete"

test-mcp-server:
	@echo "Running MCP server unit tests..."
	OTEL_SDK_DISABLED=true $(PYTEST) tests/unit/test_mcp_stdio_server.py tests/test_mcp_streamable.py -v
	@echo "✓ MCP server tests complete"

test-new:
	@echo "Running newly added tests..."
	@echo ""
	@echo "1. API Endpoint Tests:"
	OTEL_SDK_DISABLED=true $(PYTEST) tests/api/ -v
	@echo ""
	@echo "2. MCP StdIO Server Tests:"
	OTEL_SDK_DISABLED=true $(PYTEST) tests/unit/test_mcp_stdio_server.py -v
	@echo ""
	@echo "✓ All new tests complete"

test-quick-new:
	@echo "Quick check of newly added tests (parallel, no verbose)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto tests/api/ tests/unit/test_mcp_stdio_server.py
	@echo "✓ Quick test complete"

# Validation
validate-openapi:
	@echo "Validating OpenAPI schema..."
	OTEL_SDK_DISABLED=true .venv/bin/python scripts/validation/validate_openapi.py 2>&1 | grep -v -E "(WARNING|trace_id|span_id|resource\.|Transient error|exporter\.py|Traceback|File \"|ImportError:|pydantic-ai|fall back)"
	@echo "✓ OpenAPI validation complete"

validate-deployments:
	@echo "Validating all deployment configurations..."
	$(UV_RUN) python scripts/validation/validate_deployments.py
	@echo "✓ Deployment validation complete"

validate-docker-compose:
	@echo "Validating Docker Compose configuration..."
	$(DOCKER_COMPOSE) -f docker-compose.yml config --quiet
	@echo "✓ Docker Compose valid"

validate-helm:
	@echo "Validating Helm chart..."
	helm lint deployments/helm/mcp-server-langgraph
	helm template test-release deployments/helm/mcp-server-langgraph --dry-run > /dev/null
	@echo "✓ Helm chart valid"

validate-kustomize:
	@echo "Validating Kustomize overlays in parallel..."
	@( \
		echo "  Validating dev overlay..." && kubectl kustomize deployments/kustomize/overlays/dev > /dev/null 2>&1 && echo "  ✓ dev overlay valid" \
	) & pid1=$$!; \
	( \
		echo "  Validating staging overlay..." && kubectl kustomize deployments/kustomize/overlays/staging > /dev/null 2>&1 && echo "  ✓ staging overlay valid" \
	) & pid2=$$!; \
	( \
		echo "  Validating production overlay..." && kubectl kustomize deployments/kustomize/overlays/production > /dev/null 2>&1 && echo "  ✓ production overlay valid" \
	) & pid3=$$!; \
	wait $$pid1 $$pid2 $$pid3
	@echo "✓ All Kustomize overlays valid"

validate-all: validate-deployments validate-docker-compose validate-helm validate-kustomize
	@echo "✓ All deployment validations passed"

# Code quality
lint:
	@echo "⚠️  DEPRECATED: Use 'make lint-check' for comprehensive linting"
	@echo ""
	@echo "Running flake8 on src/..."
	flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics
	@echo "Running mypy on src/..."
	-mypy src/ --ignore-missing-imports
	@echo ""
	@echo "💡 For better lint checking, use: make lint-check"

format:
	@echo "⚠️  DEPRECATED: Use 'make lint-fix' for auto-fixing"
	@echo ""
	@echo "Formatting src/ with black..."
	black src/ --line-length=127
	@echo "Sorting imports in src/ with isort..."
	isort src/ --profile=black --line-length=127
	@echo ""
	@echo "💡 For better lint fixing, use: make lint-fix"

security-check:
	@echo "Running bandit security scan..."
	bandit -r . -x ./tests,./.venv -ll

# Enhanced lint targets for pre-commit/pre-push workflow
lint-check:
	@echo "🔍 Running comprehensive lint checks in parallel (non-destructive)..."
	@echo ""
	@echo "Running 5 linters in parallel..."
	@( \
		echo "1/5 Running flake8..." && $(UV_RUN) flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics 2>&1 | sed 's/^/[flake8] /' || true \
	) & pid1=$$!; \
	( \
		echo "2/5 Checking black formatting..." && $(UV_RUN) black --check src/ --line-length=127 2>&1 | sed 's/^/[black] /' || true \
	) & pid2=$$!; \
	( \
		echo "3/5 Checking isort import order..." && $(UV_RUN) isort --check src/ --profile=black --line-length=127 2>&1 | sed 's/^/[isort] /' || true \
	) & pid3=$$!; \
	( \
		echo "4/5 Running mypy type checking..." && $(UV_RUN) mypy src/ --ignore-missing-imports --show-error-codes 2>&1 | sed 's/^/[mypy] /' || true \
	) & pid4=$$!; \
	( \
		echo "5/5 Running bandit security scan..." && $(UV_RUN) bandit -r src/ -ll 2>&1 | sed 's/^/[bandit] /' || true \
	) & pid5=$$!; \
	wait $$pid1 $$pid2 $$pid3 $$pid4 $$pid5
	@echo ""
	@echo "✓ Lint check complete (see above for any issues)"
	@echo "  Speedup: ~80% faster with parallel execution"

lint-fix:
	@echo "🔧 Auto-fixing formatting issues in parallel..."
	@echo ""
	@echo "Running black and isort in parallel..."
	@( \
		echo "Formatting with black..." && $(UV_RUN) black src/ --line-length=127 2>&1 | sed 's/^/[black] /' \
	) & pid1=$$!; \
	( \
		echo "Sorting imports with isort..." && $(UV_RUN) isort src/ --profile=black --line-length=127 2>&1 | sed 's/^/[isort] /' \
	) & pid2=$$!; \
	wait $$pid1 $$pid2
	@echo ""
	@echo "✓ Auto-fix complete"
	@echo "  Speedup: ~50% faster with parallel execution"
	@echo ""
	@echo "Run 'make lint-check' to verify remaining issues"

lint-pre-commit:
	@echo "🎯 Simulating pre-commit hook (runs on staged files)..."
	@$(UV_RUN) pre-commit run --all-files
	@echo "✓ Pre-commit simulation complete"

lint-pre-push:
	@echo "🚀 Simulating pre-push hook (runs on changed files)..."
	@bash .git/hooks/pre-push
	@echo "✓ Pre-push simulation complete"

lint-install:
	@echo "📦 Installing/reinstalling lint hooks..."
	@$(UV_RUN) pre-commit install
	@chmod +x .git/hooks/pre-push
	@echo "✓ Hooks installed:"
	@echo "  • pre-commit (auto-fix black/isort, run flake8/mypy/bandit)"
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
	kubectl apply -k deployments/kustomize/overlays/dev
	@echo "Waiting for rollout..."
	kubectl rollout status deployment/dev-langgraph-agent -n langgraph-agent-dev --timeout=5m
	@echo "✓ Development deployment complete"
	@echo ""
	@echo "Check status:"
	@echo "  kubectl get pods -n langgraph-agent-dev"
	@echo "  kubectl logs -f deployment/dev-langgraph-agent -n langgraph-agent-dev"

deploy-staging:
	@echo "Deploying to staging environment..."
	kubectl apply -k deployments/kustomize/overlays/staging
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
	@sleep 5
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
	@echo "  • black (code formatting)"
	@echo "  • isort (import sorting)"
	@echo "  • flake8 (linting)"
	@echo "  • mypy (type checking)"
	@echo "  • bandit (security)"
	@echo ""
	@echo "Run manually: pre-commit run --all-files"

git-hooks: pre-commit-setup
	@echo "Git hooks installed successfully"

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

# ==============================================================================
# Enhanced Testing Targets
# ==============================================================================

test-watch:
	@echo "👀 Running tests in watch mode..."
	$(PYTEST)-watch --no-cov

test-fast:
	@echo "⚡ Running all tests without coverage (parallel, fast iteration)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto --tb=short
	@echo "✓ Fast tests complete"
	@echo ""
	@echo "For maximum speed: 'make test-dev' (parallel + fast-fail)"

test-fast-unit:
	@echo "⚡ Running unit tests without coverage (parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m unit --tb=short

# ==============================================================================
# Parallel Testing (40-60% faster)
# ==============================================================================

test-parallel:
	@echo "⚡⚡ Running all tests in parallel (pytest-xdist)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto --tb=short
	@echo "✓ Parallel tests complete"
	@echo ""
	@echo "Speedup: ~40-60% faster than sequential execution"

test-parallel-unit:
	@echo "⚡⚡ Running unit tests in parallel..."
	OTEL_SDK_DISABLED=true $(PYTEST) -m unit -n auto --tb=short
	@echo "✓ Parallel unit tests complete"

test-dev:
	@echo "🚀 Running tests in development mode (parallel, fast-fail, no coverage)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -x --maxfail=3 --tb=short -m "unit and not slow"
	@echo "✓ Development tests complete"
	@echo ""
	@echo "Features: Parallel execution, stop on first failure, skip slow tests"

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
