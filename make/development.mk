# ==============================================================================
# Development Shortcuts
# ==============================================================================

# ==============================================================================
# Dev-Lite Stack (Minimal Resources)
# ==============================================================================

dev-lite-up:
	@echo "Starting lightweight development stack..."
	@echo ""
	@echo "This uses ~512MB RAM (vs ~4GB full stack)"
	@echo "Excluded: Keycloak, OpenFGA, Qdrant, LGTM Stack"
	@echo ""
	$(DOCKER_COMPOSE) -f docker/docker-compose.dev-lite.yml up -d
	@echo ""
	@echo "Dev-lite services started!"
	@echo ""
	@echo "Services:"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Redis:      localhost:6379"
	@echo ""
	@echo "Environment:"
	@echo "  Copy .env.dev-lite to .env or source it:"
	@echo "  cp .env.dev-lite .env"
	@echo ""
	@echo "Run tests: make test-unit"
	@echo "Run server: make run-streamable"

dev-lite-down:
	@echo "Stopping lightweight development stack..."
	$(DOCKER_COMPOSE) -f docker/docker-compose.dev-lite.yml down
	@echo "Dev-lite services stopped"

dev-lite-logs:
	@echo "Showing dev-lite logs..."
	$(DOCKER_COMPOSE) -f docker/docker-compose.dev-lite.yml logs -f

dev-lite-status:
	@echo "Dev-lite status:"
	@$(DOCKER_COMPOSE) -f docker/docker-compose.dev-lite.yml ps

# ==============================================================================
# Full Development Setup
# ==============================================================================

dev-setup: install-dev setup-infra setup-openfga setup-keycloak
	@echo ""
	@echo "Development environment setup complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  1. Update .env with OPENFGA_STORE_ID and OPENFGA_MODEL_ID"
	@echo "  2. Update .env with KEYCLOAK_CLIENT_SECRET"
	@echo "  3. Run: make test-unit"
	@echo "  4. Run: make run-streamable"
	@echo "  5. Visit: http://localhost:3001 (Grafana)"
	@echo ""

quick-start:
	@echo "Quick starting MCP Server LangGraph..."
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
	@echo "Quick start complete!"
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
	@echo "  - LangGraph Agent"
	@echo "  - Security Dashboard"
	@echo "  - Authentication"
	@echo "  - OpenFGA"
	@echo "  - LLM Performance"
	@echo "  - SLA Monitoring"
	@echo "  - SOC2 Compliance"
	@echo "  - Keycloak SSO"
	@echo "  - Redis Sessions"
	@echo ""
	@command -v open >/dev/null 2>&1 && open http://localhost:3001 || \
		command -v xdg-open >/dev/null 2>&1 && xdg-open http://localhost:3001 || \
		echo "Open http://localhost:3001 in your browser"

health-check:
	@echo "Checking system health..."
	@echo ""
	@echo "Infrastructure Services:"
	@$(DOCKER_COMPOSE) ps | grep -E "(openfga|postgres|keycloak|jaeger|prometheus|grafana|redis)" || echo "  Services not running"
	@echo ""
	@echo "Port Check (parallel):"
	@( \
		for port in 8080 5432 8082 16686 9090 3001 6379; do \
			( \
				if nc -z localhost $$port 2>/dev/null; then \
					echo "  Port $$port: OK"; \
				else \
					echo "  Port $$port: Not responding"; \
				fi \
			) & \
		done; \
		wait \
	)
	@echo ""
	@echo "Python Environment:"
	@if [ -d ".venv" ]; then \
		echo "  Virtual environment: OK"; \
	else \
		echo "  Virtual environment: Missing"; \
	fi
	@echo ""
	@echo "Run 'make setup-infra' if services are not running"

health-check-fast:
	@echo "Fast health check (parallel port scanning)..."
	@echo ""
	@( \
		( nc -z localhost 8080 2>/dev/null && echo "  OpenFGA (8080): OK" || echo "  OpenFGA (8080): DOWN" ) & \
		( nc -z localhost 5432 2>/dev/null && echo "  PostgreSQL (5432): OK" || echo "  PostgreSQL (5432): DOWN" ) & \
		( nc -z localhost 8082 2>/dev/null && echo "  Keycloak (8082): OK" || echo "  Keycloak (8082): DOWN" ) & \
		( nc -z localhost 16686 2>/dev/null && echo "  Jaeger (16686): OK" || echo "  Jaeger (16686): DOWN" ) & \
		( nc -z localhost 9090 2>/dev/null && echo "  Prometheus (9090): OK" || echo "  Prometheus (9090): DOWN" ) & \
		( nc -z localhost 3001 2>/dev/null && echo "  Grafana (3001): OK" || echo "  Grafana (3001): DOWN" ) & \
		( nc -z localhost 6379 2>/dev/null && echo "  Redis (6379): OK" || echo "  Redis (6379): DOWN" ) & \
		wait \
	)
	@echo ""
	@echo "Fast health check complete"

db-migrate:
	@echo "Running database migrations..."
	@echo "No migrations configured yet"
	@echo "This target is a placeholder for future migration scripts"

load-test:
	@echo "Running load tests..."
	@if command -v locust >/dev/null 2>&1; then \
		echo "Starting Locust..."; \
		locust -f tests/performance/locustfile.py --headless -u 100 -r 10 -t 60s --host http://localhost:8000; \
	else \
		echo "Locust not installed. Install with: uv tool install locust"; \
		echo ""; \
		echo "Alternative: Use k6"; \
		echo "  k6 run tests/performance/load_test.js"; \
	fi

stress-test:
	@echo "Running stress tests (parallel)..."
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
		echo "Pre-commit hooks installed"; \
	else \
		echo "Installing pre-commit via uv..."; \
		uv tool install pre-commit; \
		pre-commit install; \
		pre-commit install --hook-type commit-msg; \
		echo "Pre-commit hooks installed"; \
	fi
	@echo ""
	@echo "Hooks installed:"
	@echo "  - Ruff (code formatting + linting)"
	@echo "  - bandit (security scanning)"
	@echo "  - MyPy (type checking - runs in pre-push stage)"
	@echo ""
	@echo "Note: MyPy runs at pre-push stage for comprehensive type checking"
	@echo "Run manually: pre-commit run --all-files"

git-hooks: pre-commit-setup
	@echo "Git hooks installed successfully:"
	@echo ""
	@echo "  - pre-commit   - Format, lint, and basic validation on commit"
	@echo "  - pre-push     - Comprehensive CI-equivalent validation before push"
	@echo "  - commit-msg   - Conventional commits enforcement"
	@echo "  - post-commit  - Auto-update context files after commit"
	@echo ""
	@echo "For details: See TESTING.md#git-hooks-and-validation"
	@echo "To test: make validate-pre-push"

# ==============================================================================
# Running Servers
# ==============================================================================

run:
	$(UV_RUN) python -m mcp_server_langgraph.mcp.server_stdio

run-streamable:
	$(UV_RUN) python -m mcp_server_langgraph.mcp.server_streamable

logs:
	$(DOCKER_COMPOSE) logs -f

logs-follow:
	@echo "Following all logs..."
	$(DOCKER_COMPOSE) logs -f --tail=100

logs-agent:
	@echo "Following agent logs..."
	$(DOCKER_COMPOSE) logs -f --tail=100 mcp-server || echo "Agent not running in docker-compose"

logs-prometheus:
	@echo "Prometheus logs..."
	$(DOCKER_COMPOSE) logs prometheus

logs-grafana:
	@echo "Grafana logs..."
	$(DOCKER_COMPOSE) logs grafana

# ==============================================================================
# Daemon Management
# ==============================================================================

kill-daemons:  ## Stop background daemons (dmypy, etc.)
	@echo "Stopping background daemons..."
	@uv run --frozen dmypy kill 2>/dev/null || true
	@rm -rf ~/.cache/pre-commit-lane-* 2>/dev/null || true
	@echo "Daemons stopped and lane caches cleaned"

# ==============================================================================
# Cleanup
# ==============================================================================

clean:
	@echo "Cleaning up (parallel operations)..."
	@$(DOCKER_COMPOSE) down -v & pid1=$$!; \
	find . -type f -name '*.pyc' -delete & pid2=$$!; \
	find . -type d -name '__pycache__' -delete & pid3=$$!; \
	find . -type d -name '*.egg-info' -exec rm -rf {} + & pid4=$$!; \
	rm -rf .pytest_cache .coverage htmlcov & pid5=$$!; \
	wait $$pid1 $$pid2 $$pid3 $$pid4 $$pid5
	@echo "Infrastructure stopped and caches removed"

clean-all: clean
	rm -rf .venv
	@echo "Deep clean complete"

reset: clean setup-infra setup-openfga
	@echo "System reset complete"

# ==============================================================================
# Monitoring & Observability
# ==============================================================================

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
	@echo "Backup created in backups/"

db-restore:
	@echo "This will restore from the latest backup"
	@ls -t backups/*.sql | head -1
	@read -p "Continue? (y/n) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		$(DOCKER_COMPOSE) exec -T postgres psql -U postgres -d openfga < $$(ls -t backups/*.sql | head -1); \
		echo "Database restored"; \
	else \
		echo "Restore cancelled"; \
	fi
