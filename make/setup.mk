# ==============================================================================
# Setup & Installation
# ==============================================================================

install:
	uv sync --frozen --no-dev
	@echo "Production dependencies installed from lockfile"
	@echo "  Note: Uses uv.lock for reproducible builds"

install-dev:
	uv sync --frozen --extra dev
	@echo "Development dependencies installed from lockfile"
	@echo "  Note: Uses uv.lock with dev extra for CI parity"

setup-infra:
	$(DOCKER_COMPOSE) up -d
	@echo "Infrastructure started"
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
	@echo "Remember to update .env with OPENFGA_STORE_ID and OPENFGA_MODEL_ID"

setup-keycloak:
	@echo "Setting up Keycloak..."
	@echo "Waiting for Keycloak to start (this may take 60+ seconds)..."
	$(UV_RUN) python scripts/setup/setup_keycloak.py
	@echo ""
	@echo "Remember to update .env with KEYCLOAK_CLIENT_SECRET"

setup-infisical:
	@echo "Setting up Infisical..."
	$(UV_RUN) python scripts/setup/setup_infisical.py
