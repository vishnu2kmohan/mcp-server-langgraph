# ==============================================================================
# Testing
# ==============================================================================

test:
	@echo "Running all tests with coverage (parallel execution)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto $(COV_OPTIONS) --cov-report=term-missing
	@echo "Tests complete. Coverage report above."
	@echo ""
	@echo "Tip: Use 'make test-fast' or 'make test-dev' for faster iteration"

test-unit:
	@echo "Running pure unit tests (tests/unit/)..."
	@test -d .venv || (echo "No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto tests/unit $(COV_OPTIONS) --cov-report=term-missing
	@echo "Unit tests complete"

test-local:
	@echo "Running all local tests (Unit + CLI + Validation)..."
	@test -d .venv || (echo "No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto tests/unit tests/cli tests/deployment tests/infrastructure tests/ci
	@echo "Local tests complete"

test-meta:
	@echo "Running meta-tests (test infrastructure validation)..."
	@test -d .venv || (echo "No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto -m meta -v
	@echo "Meta-tests complete"

test-ci:
	@echo "Running tests exactly as CI does (parallel execution)..."
	OTEL_SDK_DISABLED=true HYPOTHESIS_PROFILE=ci $(PYTEST) -n auto -m "unit and not llm" $(COV_OPTIONS) --cov-report=xml --cov-report=term-missing
	@echo "CI-equivalent tests complete"
	@echo "  Coverage XML: coverage.xml"

test-integration:
	@echo "Running integration tests in Docker environment (matches CI)..."
	./scripts/test-integration.sh --build
	@echo "Integration tests complete"

test-integration-services:
	@echo "Starting integration test services only..."
	./scripts/test-integration.sh --services

test-integration-debug:
	@echo "Running integration tests (keep containers for debugging)..."
	./scripts/test-integration.sh --keep

test-integration-cleanup:
	@echo "Cleaning up integration test containers..."
	$(DOCKER_COMPOSE) -f docker-compose.test.yml down -v --remove-orphans
	@echo "Cleanup complete"

# Coverage targets
test-coverage:
	@echo "Generating comprehensive coverage report (parallel execution)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto $(COV_OPTIONS) --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo "Coverage reports generated:"
	@echo "  HTML: htmlcov/index.html"
	@echo "  XML: coverage.xml"

test-coverage-fast:
	@echo "Generating fast coverage report (unit tests only, parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m unit $(COV_OPTIONS) --cov-report=html --cov-report=term-missing
	@echo "Fast coverage report generated:"
	@echo "  HTML: htmlcov/index.html"

test-coverage-html:
	@echo "Generating HTML coverage report only..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto $(COV_OPTIONS) --cov-report=html
	@echo "HTML coverage report generated: htmlcov/index.html"

test-coverage-xml:
	@echo "Generating XML coverage report..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto $(COV_OPTIONS) --cov-report=xml
	@echo "XML coverage report generated: coverage.xml"

test-coverage-terminal:
	@echo "Generating terminal coverage report..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto $(COV_OPTIONS) --cov-report=term-missing
	@echo "Terminal coverage displayed above"

# Quality tests
test-property:
	@echo "Running property-based tests (Hypothesis, parallel)..."
	@test -d .venv || (echo "No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto -m property -v
	@echo "Property tests complete"

test-contract:
	@echo "Running contract tests (MCP protocol, OpenAPI, parallel)..."
	@test -d .venv || (echo "No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto -m contract -v
	@echo "Contract tests complete"

test-regression:
	@echo "Running performance regression tests (parallel)..."
	@test -d .venv || (echo "No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto -m regression -v
	@echo "Regression tests complete"

test-mutation:
	@echo "Running mutation tests (this will take a while)..."
	mutmut run
	mutmut results
	mutmut html
	@echo "Mutation testing complete"
	@echo "  View report: open html/index.html"

test-all-quality: test-property test-contract test-regression
	@echo "All quality tests complete"

benchmark:
	@echo "Running performance benchmarks..."
	$(PYTEST) -m benchmark -v -p no:xdist -o "addopts=-v --strict-markers --tb=short --timeout=60" --benchmark-only --benchmark-autosave
	@echo "Benchmark results saved"

# Fast testing targets
test-fast:
	@echo "Running all tests without coverage (parallel, fast iteration)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto --tb=short
	@echo "Fast tests complete"

test-fast-unit:
	@echo "Running unit tests without coverage (parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m unit --tb=short

test-dev:
	@echo "Running tests in development mode (parallel, fast-fail, no coverage)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -x --maxfail=3 --tb=short -m "(unit or api or property or validation) and not llm and not slow"
	@echo "Development tests complete"

test-fast-core:
	@echo "Running core unit tests only (fastest iteration)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m "unit and not slow and not integration" --tb=line -q
	@echo "Core tests complete (typically < 5 seconds)"

test-slow:
	@echo "Running slow tests only (parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m slow -v --tb=short

test-compliance:
	@echo "Running compliance tests (GDPR, HIPAA, SOC2, SLA, parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto -m "gdpr or soc2 or sla" -v --tb=short

test-failed:
	@echo "Re-running failed tests (parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto --lf -v

test-debug:
	@echo "Running tests in debug mode..."
	OTEL_SDK_DISABLED=true $(PYTEST) -v --pdb --pdbcls=IPython.terminal.debugger:Pdb

test-watch:
	@echo "Running tests in watch mode..."
	$(UV_RUN) ptw --no-cov

test-auth:
	@echo "Testing OpenFGA authorization..."
	$(UV_RUN) python examples/openfga_usage.py

test-mcp:
	@echo "Testing MCP server..."
	$(UV_RUN) python examples/client_stdio.py
