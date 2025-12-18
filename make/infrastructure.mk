# ==============================================================================
# Test Infrastructure
# ==============================================================================

test-infra-up:
	@echo "Starting full test infrastructure (docker-compose.test.yml)..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml up -d
	@echo ""
	@echo "Full test infrastructure started!"
	@echo ""
	@echo "Gateway Routes (recommended):"
	@echo "  http://localhost/api        - MCP Server API"
	@echo "  http://localhost/build      - Visual Workflow Builder"
	@echo "  http://localhost/play       - Interactive Playground"
	@echo "  http://localhost/authn      - Keycloak (Authentication)"
	@echo "  http://localhost/authz      - OpenFGA (Authorization)"
	@echo "  http://localhost/dashboards - Grafana (Unified Dashboards)"
	@echo ""
	@echo "Direct Ports (legacy, for debugging):"
	@echo "  PostgreSQL:   localhost:9432"
	@echo "  Redis:        localhost:9379"
	@echo "  OpenFGA:      http://localhost:9080"
	@echo "  Keycloak:     http://localhost:9082"
	@echo "  MCP Server:   http://localhost:8000"
	@echo ""

test-infra-up-build:
	@echo "Rebuilding and starting full test infrastructure..."
	@npm install --package-lock-only --prefix src/mcp_server_langgraph/studio/frontend
	$(DOCKER_COMPOSE) -f docker-compose.test.yml up --build -d
	@echo "Full test infrastructure rebuilt and started!"

test-infra-down:
	@echo "Stopping test infrastructure..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml down --remove-orphans
	@echo "Test infrastructure stopped"
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
	@echo "Test volumes cleaned"

test-infra-reset: test-infra-down test-infra-clean-volumes
	@echo "Test infrastructure reset (all data removed)"

test-infra-logs:
	@echo "Showing test infrastructure logs..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml logs -f

test-gateway-status:
	@echo "Checking API Gateway (Traefik) status..."
	@curl -s http://localhost:8080/api/overview || echo "  Gateway not responding (is test-infra running?)"
	@echo ""

test-gateway-logs:
	@echo "Showing API Gateway (Traefik) logs..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml logs -f traefik-gateway

test-loki-logs:
	@echo "Showing Loki and Alloy logs..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml logs -f loki-test alloy-test

test-studio-up:
	@echo "Starting unified Studio frontend..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml up -d mcp-server-test
	@echo "Studio started"
	@echo ""
	@echo "Unified Studio:"
	@echo "  Frontend:  http://localhost/studio (via Traefik gateway)"
	@echo "  API:       http://localhost:8000"
	@echo "  Health:    http://localhost:8000/health/live"
	@echo "  API Docs:  http://localhost:8000/docs"
	@echo ""

test-studio-down:
	@echo "Stopping unified Studio frontend..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml stop mcp-server-test
	@echo "Studio stopped"

# DEPRECATED aliases
test-builder-up: test-studio-up
	@echo "DEPRECATED: test-builder-up is deprecated. Use 'make test-studio-up' instead."

test-builder-down: test-studio-down
	@echo "DEPRECATED: test-builder-down is deprecated. Use 'make test-studio-down' instead."

test-playground-up: test-studio-up
	@echo "DEPRECATED: test-playground-up is deprecated. Use 'make test-studio-up' instead."

test-playground-down: test-studio-down
	@echo "DEPRECATED: test-playground-down is deprecated. Use 'make test-studio-down' instead."

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
	@echo "E2E tests complete"

test-e2e-ci:
	@echo "Running E2E tests with CI parity..."
	@./scripts/test-e2e.sh && echo "E2E tests passed" || (echo "E2E tests failed" && exit 1)

test-frontend-ci:
	@echo "Running frontend tests with CI parity..."
	@./scripts/test-frontend.sh && echo "Frontend tests passed" || (echo "Frontend tests failed" && exit 1)

test-api:
	@echo "Running API endpoint tests..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m "api and unit" -v
	@echo "API endpoint tests complete"

test-mcp-server:
	@echo "Running MCP server unit tests (parallel execution)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto tests/unit/mcp/test_mcp_stdio_server.py tests/integration/test_mcp_streamable.py -v
	@echo "MCP server tests complete"
