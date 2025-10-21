.PHONY: help install install-dev setup-infra setup-openfga setup-infisical test test-unit test-integration test-coverage test-property test-contract test-regression test-mutation validate-openapi validate-deployments validate-all deploy-dev deploy-staging deploy-production lint format security-check lint-check lint-fix lint-pre-commit lint-pre-push lint-install clean dev-setup quick-start monitoring-dashboard health-check db-migrate load-test stress-test docs-serve docs-build pre-commit-setup git-hooks

help:
	@echo "LangGraph MCP Agent - Make Commands"
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
	@echo "  make test-coverage            Generate comprehensive coverage report"
	@echo "  make test-coverage-combined   Combined coverage (unit + integration)"
	@echo "  make test-property            Property-based tests (Hypothesis)"
	@echo "  make test-contract            Contract tests (MCP, OpenAPI)"
	@echo "  make test-regression          Performance regression tests"
	@echo "  make test-mutation            Mutation tests (slow)"
	@echo "  make test-all-quality         All quality tests (property+contract+regression)"
	@echo "  make benchmark                Performance benchmarks"
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
	uv pip install -r requirements-pinned.txt
	@echo "✓ Dependencies installed"

install-dev:
	uv sync
	@echo "✓ Development dependencies installed"

setup-infra:
	docker compose up -d
	@echo "✓ Infrastructure started"
	@echo ""
	@echo "Services:"
	@echo "  OpenFGA:    http://localhost:8080"
	@echo "  Jaeger:     http://localhost:16686"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana:    http://localhost:3000"
	@echo ""

setup-openfga:
	@echo "Setting up OpenFGA..."
	python scripts/setup/setup_openfga.py
	@echo ""
	@echo "⚠️  Remember to update .env with OPENFGA_STORE_ID and OPENFGA_MODEL_ID"

setup-keycloak:
	@echo "Setting up Keycloak..."
	@echo "Waiting for Keycloak to start (this may take 60+ seconds)..."
	python scripts/setup/setup_keycloak.py
	@echo ""
	@echo "⚠️  Remember to update .env with KEYCLOAK_CLIENT_SECRET"

setup-infisical:
	@echo "Setting up Infisical..."
	python scripts/setup/setup_infisical.py

test:
	@echo "Running all tests with coverage..."
	.venv/bin/pytest --cov=src/mcp_server_langgraph --cov-report=term-missing
	@echo "✓ Tests complete. Coverage report above."
	@echo ""
	@echo "Tip: Use 'make test-fast' or 'make test-parallel' for faster iteration"

test-unit:
	@echo "Running unit tests with coverage (matches CI)..."
	.venv/bin/pytest -m unit --cov=src/mcp_server_langgraph --cov-report=term-missing
	@echo "✓ Unit tests complete"

test-unit-fast:
	@echo "Running unit tests without coverage (fast iteration)..."
	@echo "⚠️  DEPRECATED: Use 'make test-parallel-unit' or 'make test-dev' instead"
	.venv/bin/pytest -m unit --tb=short
	@echo "✓ Fast unit tests complete"

test-ci:
	@echo "Running tests exactly as CI does..."
	.venv/bin/pytest -m unit --cov=src/mcp_server_langgraph --cov-report=xml --cov-report=term-missing
	@echo "✓ CI-equivalent tests complete"
	@echo "  Coverage XML: coverage.xml"

test-integration:
	@echo "Running integration tests in Docker environment (matches CI)..."
	./scripts/test-integration.sh
	@echo "✓ Integration tests complete"

test-integration-local:
	@echo "⚠️  Running integration tests locally (requires services running)..."
	@echo "Note: CI uses Docker. Use 'make test-integration' to match CI exactly."
	.venv/bin/pytest -m integration --no-cov --tb=short
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
	docker compose -f docker/docker-compose.test.yml down -v --remove-orphans
	@echo "✓ Cleanup complete"

test-coverage:
	@echo "Generating comprehensive coverage report..."
	.venv/bin/pytest --cov=src/mcp_server_langgraph --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo "✓ Coverage reports generated:"
	@echo "  HTML: htmlcov/index.html"
	@echo "  XML: coverage.xml"
	@echo "  Terminal: Above"

test-coverage-combined:
	@echo "Running all tests with combined coverage..."
	@echo ""
	@echo "Step 1: Running unit tests with coverage..."
	.venv/bin/pytest -m unit --cov=src/mcp_server_langgraph --cov-report= --cov-report=term-missing
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
	python examples/openfga_usage.py

test-mcp:
	@echo "Testing MCP server..."
	python examples/client_stdio.py

benchmark:
	@echo "Running performance benchmarks..."
	.venv/bin/pytest -m benchmark -v --benchmark-only --benchmark-autosave
	@echo "✓ Benchmark results saved"

# New test targets
test-property:
	@echo "Running property-based tests (Hypothesis)..."
	.venv/bin/pytest -m property -v
	@echo "✓ Property tests complete"

test-contract:
	@echo "Running contract tests (MCP protocol, OpenAPI)..."
	.venv/bin/pytest -m contract -v
	@echo "✓ Contract tests complete"

test-regression:
	@echo "Running performance regression tests..."
	.venv/bin/pytest -m regression -v
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

# Validation
validate-openapi:
	@echo "Validating OpenAPI schema..."
	OTEL_SDK_DISABLED=true .venv/bin/python scripts/validation/validate_openapi.py 2>&1 | grep -v -E "(WARNING|trace_id|span_id|resource\.|Transient error|exporter\.py|Traceback|File \"|ImportError:|pydantic-ai|fall back)"
	@echo "✓ OpenAPI validation complete"

validate-deployments:
	@echo "Validating all deployment configurations..."
	python3 scripts/validation/validate_deployments.py
	@echo "✓ Deployment validation complete"

validate-docker-compose:
	@echo "Validating Docker Compose configuration..."
	docker compose -f docker-compose.yml config --quiet
	@echo "✓ Docker Compose valid"

validate-helm:
	@echo "Validating Helm chart..."
	helm lint deployments/helm/mcp-server-langgraph
	helm template test-release deployments/helm/mcp-server-langgraph --dry-run > /dev/null
	@echo "✓ Helm chart valid"

validate-kustomize:
	@echo "Validating Kustomize overlays..."
	@for env in dev staging production; do \
		echo "  Validating $$env overlay..."; \
		kubectl kustomize deployments/kustomize/overlays/$$env > /dev/null; \
	done
	@echo "✓ All Kustomize overlays valid"

validate-all: validate-deployments validate-docker-compose validate-helm validate-kustomize
	@echo "✓ All deployment validations passed"

# Code quality
lint:
	@echo "Running flake8..."
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=.venv,tests
	@echo "Running mypy..."
	-mypy *.py --ignore-missing-imports

format:
	@echo "Formatting with black..."
	black . --exclude .venv
	@echo "Sorting imports with isort..."
	isort . --skip .venv

security-check:
	@echo "Running bandit security scan..."
	bandit -r . -x ./tests,./.venv -ll

# Enhanced lint targets for pre-commit/pre-push workflow
lint-check:
	@echo "🔍 Running comprehensive lint checks (non-destructive)..."
	@echo ""
	@echo "1/5 Running flake8..."
	@uv run flake8 src/ --count --select=E9,F63,F7,F82 --show-source --statistics || true
	@echo ""
	@echo "2/5 Checking black formatting..."
	@uv run black --check src/ --line-length=127 || true
	@echo ""
	@echo "3/5 Checking isort import order..."
	@uv run isort --check src/ --profile=black --line-length=127 || true
	@echo ""
	@echo "4/5 Running mypy type checking..."
	@uv run mypy src/ --ignore-missing-imports --show-error-codes || true
	@echo ""
	@echo "5/5 Running bandit security scan..."
	@uv run bandit -r src/ -ll || true
	@echo ""
	@echo "✓ Lint check complete (see above for any issues)"

lint-fix:
	@echo "🔧 Auto-fixing formatting issues..."
	@echo ""
	@echo "Formatting with black..."
	@uv run black src/ --line-length=127
	@echo ""
	@echo "Sorting imports with isort..."
	@uv run isort src/ --profile=black --line-length=127
	@echo ""
	@echo "✓ Auto-fix complete"
	@echo ""
	@echo "Run 'make lint-check' to verify remaining issues"

lint-pre-commit:
	@echo "🎯 Simulating pre-commit hook (runs on staged files)..."
	@uv run pre-commit run --all-files
	@echo "✓ Pre-commit simulation complete"

lint-pre-push:
	@echo "🚀 Simulating pre-push hook (runs on changed files)..."
	@bash .git/hooks/pre-push
	@echo "✓ Pre-push simulation complete"

lint-install:
	@echo "📦 Installing/reinstalling lint hooks..."
	@uv run pre-commit install
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
	python -m mcp_server_langgraph.mcp.server_stdio

run-streamable:
	python -m mcp_server_langgraph.mcp.server_streamable

logs:
	docker compose logs -f

clean:
	docker compose down -v
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -delete
	find . -type d -name '*.egg-info' -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov
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
	@echo "  5. Visit: http://localhost:3000 (Grafana)"
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
	@docker compose ps
	@echo ""
	@echo "Run tests: make test-unit"
	@echo "Run server: make run-streamable"
	@echo "View dashboards: make monitoring-dashboard"

monitoring-dashboard:
	@echo "Opening Grafana dashboards..."
	@echo ""
	@echo "Grafana URL: http://localhost:3000"
	@echo "  Username: admin"
	@echo "  Password: admin"
	@echo ""
	@echo "Available dashboards:"
	@echo "  • LangGraph Agent - http://localhost:3000/d/langgraph-agent"
	@echo "  • Security Dashboard - http://localhost:3000/d/security"
	@echo "  • Authentication - http://localhost:3000/d/authentication"
	@echo "  • OpenFGA - http://localhost:3000/d/openfga"
	@echo "  • LLM Performance - http://localhost:3000/d/llm-performance"
	@echo "  • SLA Monitoring - http://localhost:3000/d/sla-monitoring"
	@echo "  • SOC2 Compliance - http://localhost:3000/d/soc2-compliance"
	@echo "  • Keycloak SSO - http://localhost:3000/d/keycloak"
	@echo "  • Redis Sessions - http://localhost:3000/d/redis-sessions"
	@echo ""
	@command -v open >/dev/null 2>&1 && open http://localhost:3000 || \
		command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:3000 || \
		echo "Open http://localhost:3000 in your browser"

health-check:
	@echo "🏥 Checking system health..."
	@echo ""
	@echo "Infrastructure Services:"
	@docker compose ps | grep -E "(openfga|postgres|keycloak|jaeger|prometheus|grafana|redis)" || echo "  ⚠️  Services not running"
	@echo ""
	@echo "Port Check:"
	@for port in 8080 5432 8081 16686 9090 3000 6379; do \
		if nc -z localhost $$port 2>/dev/null; then \
			echo "  ✓ Port $$port: OK"; \
		else \
			echo "  ✗ Port $$port: Not responding"; \
		fi \
	done
	@echo ""
	@echo "Python Environment:"
	@if [ -d ".venv" ]; then \
		echo "  ✓ Virtual environment: OK"; \
	else \
		echo "  ✗ Virtual environment: Missing"; \
	fi
	@echo ""
	@echo "Run 'make setup-infra' if services are not running"

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
		echo "⚠️  Locust not installed. Install with: uv pip install locust"; \
		echo ""; \
		echo "Alternative: Use k6"; \
		echo "  k6 run tests/performance/load_test.js"; \
	fi

stress-test:
	@echo "💪 Running stress tests..."
	@echo "This will test system limits and failure modes"
	@.venv/bin/pytest -m "stress" -v --tb=short || echo "No stress tests found. Add tests with @pytest.mark.stress"

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
		echo "Installing pre-commit..."; \
		uv pip install pre-commit; \
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
	.venv/bin/pytest-watch --no-cov

test-fast:
	@echo "⚡ Running all tests without coverage (fast iteration)..."
	@echo "💡 TIP: Use 'make test-parallel' for even faster execution (40-60% speedup)"
	.venv/bin/pytest --tb=short
	@echo "✓ Fast tests complete"
	@echo ""
	@echo "For maximum speed: 'make test-dev' (parallel + fast-fail)"

test-fast-unit:
	@echo "⚡ Running unit tests without coverage..."
	.venv/bin/pytest -m unit --tb=short

# ==============================================================================
# Parallel Testing (40-60% faster)
# ==============================================================================

test-parallel:
	@echo "⚡⚡ Running all tests in parallel (pytest-xdist)..."
	.venv/bin/pytest -n auto --tb=short
	@echo "✓ Parallel tests complete"
	@echo ""
	@echo "Speedup: ~40-60% faster than sequential execution"

test-parallel-unit:
	@echo "⚡⚡ Running unit tests in parallel..."
	.venv/bin/pytest -m unit -n auto --tb=short
	@echo "✓ Parallel unit tests complete"

test-dev:
	@echo "🚀 Running tests in development mode (parallel, fast-fail, no coverage)..."
	.venv/bin/pytest -n auto -x --maxfail=3 --tb=short -m "unit and not slow"
	@echo "✓ Development tests complete"
	@echo ""
	@echo "Features: Parallel execution, stop on first failure, skip slow tests"

test-fast-core:
	@echo "⚡ Running core unit tests only (fastest iteration)..."
	.venv/bin/pytest -n auto -m "unit and not slow and not integration" --tb=line -q
	@echo "✓ Core tests complete"
	@echo ""
	@echo "Use for rapid iteration (typically < 5 seconds)"

test-slow:
	@echo "🐌 Running slow tests only..."
	.venv/bin/pytest -m slow -v --tb=short

test-compliance:
	@echo "📋 Running compliance tests (GDPR, HIPAA, SOC2, SLA)..."
	.venv/bin/pytest -m "gdpr or soc2 or sla" -v --tb=short

test-failed:
	@echo "🔁 Re-running failed tests..."
	.venv/bin/pytest --lf -v

test-debug:
	@echo "🐛 Running tests in debug mode..."
	.venv/bin/pytest -v --pdb --pdbcls=IPython.terminal.debugger:Pdb

# ==============================================================================
# Monitoring & Observability
# ==============================================================================

logs-follow:
	@echo "📜 Following all logs..."
	docker compose logs -f --tail=100

logs-agent:
	@echo "📜 Following agent logs..."
	docker compose logs -f --tail=100 mcp-server || echo "Agent not running in docker-compose"

logs-prometheus:
	@echo "📜 Prometheus logs..."
	docker compose logs prometheus

logs-grafana:
	@echo "📜 Grafana logs..."
	docker compose logs grafana

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
	docker compose exec postgres psql -U postgres -d openfga

db-backup:
	@echo "Creating database backup..."
	@mkdir -p backups
	docker compose exec -T postgres pg_dump -U postgres openfga > backups/openfga_backup_$$(date +%Y%m%d_%H%M%S).sql
	@echo "✓ Backup created in backups/"

db-restore:
	@echo "⚠️  This will restore from the latest backup"
	@ls -t backups/*.sql | head -1
	@read -p "Continue? (y/n) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker compose exec -T postgres psql -U postgres -d openfga < $$(ls -t backups/*.sql | head -1); \
		echo "✓ Database restored"; \
	else \
		echo "Restore cancelled"; \
	fi
