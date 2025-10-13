.PHONY: help install install-dev setup-infra setup-openfga setup-infisical test test-unit test-integration test-coverage test-property test-contract test-regression test-mutation validate-openapi validate-deployments validate-all deploy-dev deploy-staging deploy-production lint format security-check clean

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
	@echo "  make test                Run all automated tests (unit + integration)"
	@echo "  make test-unit           Run unit tests only"
	@echo "  make test-integration    Run integration tests"
	@echo "  make test-coverage       Run tests with coverage report"
	@echo "  make test-property       Run property-based tests (Hypothesis)"
	@echo "  make test-contract       Run contract tests (MCP, OpenAPI)"
	@echo "  make test-regression     Run performance regression tests"
	@echo "  make test-mutation       Run mutation tests (slow)"
	@echo "  make test-all-quality    Run all quality tests (property+contract+regression)"
	@echo "  make benchmark           Run performance benchmarks"
	@echo "  make test-auth           Test OpenFGA authorization (manual)"
	@echo "  make test-mcp            Test MCP server (manual)"
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
	@echo "  make lint             Run linters (flake8, mypy)"
	@echo "  make format           Format code (black, isort)"
	@echo "  make security-check   Run security scans"
	@echo ""
	@echo "Running:"
	@echo "  make run              Run stdio MCP server"
	@echo "  make run-streamable   Run StreamableHTTP server"
	@echo "  make logs             Show infrastructure logs"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Stop containers and clean files"
	@echo "  make clean-all        Deep clean including venv"
	@echo ""

install:
	uv pip install -r requirements-pinned.txt
	@echo "✓ Dependencies installed"

install-dev:
	uv sync
	@echo "✓ Development dependencies installed"

setup-infra:
	docker-compose up -d
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
	pytest -v

test-unit:
	pytest -m unit -v

test-integration:
	pytest -m integration -v --tb=short

test-coverage:
	pytest --cov=. --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo "✓ Coverage report generated in htmlcov/index.html"

test-auth:
	@echo "Testing OpenFGA authorization..."
	python examples/openfga_usage.py

test-mcp:
	@echo "Testing MCP server..."
	python examples/client_stdio.py

benchmark:
	@echo "Running performance benchmarks..."
	pytest -m benchmark -v --benchmark-only --benchmark-autosave
	@echo "✓ Benchmark results saved"

# New test targets
test-property:
	@echo "Running property-based tests (Hypothesis)..."
	pytest -m property -v
	@echo "✓ Property tests complete"

test-contract:
	@echo "Running contract tests (MCP protocol, OpenAPI)..."
	pytest -m contract -v
	@echo "✓ Contract tests complete"

test-regression:
	@echo "Running performance regression tests..."
	pytest -m regression -v
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
	python scripts/validation/validate_openapi.py
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
	helm lint deployments/helm/langgraph-agent
	helm template test-release deployments/helm/langgraph-agent --dry-run > /dev/null
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

# Running servers
run:
	python -m mcp_server_langgraph.mcp.server_stdio

run-streamable:
	python -m mcp_server_langgraph.mcp.server_streamable

logs:
	docker-compose logs -f

clean:
	docker-compose down -v
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
	helm upgrade --install langgraph-agent deployments/helm/langgraph-agent \
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
