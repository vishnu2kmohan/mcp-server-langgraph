.PHONY: help install install-dev setup-infra setup-openfga setup-infisical test test-unit test-integration test-coverage lint format security-check clean

help:
	@echo "LangGraph MCP Agent - Make Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install production dependencies"
	@echo "  make install-dev      Install development + test dependencies"
	@echo "  make setup-infra      Start Docker infrastructure"
	@echo "  make setup-openfga    Initialize OpenFGA"
	@echo "  make setup-infisical  Initialize Infisical"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all automated tests (unit + integration)"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests"
	@echo "  make test-coverage    Run tests with coverage report"
	@echo "  make test-auth        Test OpenFGA authorization (manual)"
	@echo "  make test-mcp         Test MCP server (manual)"
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
	pip install -r requirements-pinned.txt
	@echo "✓ Dependencies installed"

install-dev:
	pip install -r requirements-pinned.txt
	pip install -r requirements-test.txt
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
	python setup_openfga.py
	@echo ""
	@echo "⚠️  Remember to update .env with OPENFGA_STORE_ID and OPENFGA_MODEL_ID"

setup-infisical:
	@echo "Setting up Infisical..."
	python setup_infisical.py

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
	python example_openfga_usage.py

test-mcp:
	@echo "Testing MCP server..."
	python example_client.py

# Code quality
lint:
	@echo "Running flake8..."
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics --exclude=venv,tests
	@echo "Running mypy..."
	-mypy *.py --ignore-missing-imports

format:
	@echo "Formatting with black..."
	black . --exclude venv
	@echo "Sorting imports with isort..."
	isort . --skip venv

security-check:
	@echo "Running bandit security scan..."
	bandit -r . -x ./tests,./venv -ll

# Running servers
run:
	python mcp_server.py

run-streamable:
	python mcp_server_streamable.py

run-http:
	python mcp_server_http.py

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
	rm -rf venv .venv
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
	@echo "  kubectl apply -k kubernetes/kong/"

test-rate-limit:
	@echo "Testing rate limits..."
	@for i in $$(seq 1 100); do \
		curl -s -o /dev/null -w "Request $$i: %{http_code}\n" \
			-H "apikey: test-key" \
			http://localhost:8000/; \
		sleep 0.1; \
	done
