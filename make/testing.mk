# ==============================================================================
# Testing
# ==============================================================================

# ------------------------------------------------------------------------------
# Pytest Parallelism Configuration
# ------------------------------------------------------------------------------
# Determines pytest parallelism flags with opt-out support.
# Precedence: PYTEST_SEQUENTIAL > PYTEST_WORKERS > XDIST_AVAILABLE
#
# Environment variables:
#   PYTEST_SEQUENTIAL=1  - Disable parallel execution entirely
#   PYTEST_WORKERS=N     - Use N workers instead of auto (requires xdist)
#
# Examples:
#   make test-unit                        # Uses $(PYTEST_PARALLEL_FLAG) (default)
#   PYTEST_SEQUENTIAL=1 make test-unit    # Runs sequentially
#   PYTEST_WORKERS=4 make test-unit       # Uses -n 4
# ------------------------------------------------------------------------------

# Default: no parallel flag (will be computed lazily)
PYTEST_PARALLEL_FLAG :=

# Only evaluate parallelism for test/coverage targets (avoids overhead on non-test invocations)
ifneq ($(filter test% coverage% print-pytest-parallel-flag,$(MAKECMDGOALS)),)

# Check for explicit sequential mode first
ifeq ($(PYTEST_SEQUENTIAL),1)
  # Explicit sequential mode - no parallel flag, skip all xdist checks
  PYTEST_PARALLEL_FLAG :=
else
  # Check if xdist is available (only when actually running tests)
  XDIST_AVAILABLE := $(shell $(UV_RUN) python -c "import xdist" 2>/dev/null && echo "yes" || echo "no")
  ifeq ($(XDIST_AVAILABLE),yes)
    # xdist available - use parallel by default or custom worker count
    # Use $(value ...) to get raw env value without Make expansion (prevents injection)
    _PYTEST_WORKERS_RAW := $(value PYTEST_WORKERS)
    ifneq ($(strip $(_PYTEST_WORKERS_RAW)),)
      # Validate PYTEST_WORKERS is a positive integer using Python (no shell injection)
      WORKERS_VALID := $(shell PYTEST_WORKERS='$(_PYTEST_WORKERS_RAW)' $(UV_RUN) python -c "import os; w=os.environ.get('PYTEST_WORKERS',''); print('valid' if w.isdigit() and int(w)>0 else 'invalid')")
      ifeq ($(WORKERS_VALID),valid)
        PYTEST_PARALLEL_FLAG := -n $(_PYTEST_WORKERS_RAW)
      else
        $(warning PYTEST_WORKERS='$(_PYTEST_WORKERS_RAW)' is not a positive integer; using -n auto)
        PYTEST_PARALLEL_FLAG := -n auto
      endif
    else
      PYTEST_PARALLEL_FLAG := -n auto
    endif
  else
    # xdist not available - run sequentially with warning
    PYTEST_PARALLEL_FLAG :=
    ifneq ($(strip $(value PYTEST_WORKERS)),)
      $(warning PYTEST_WORKERS=$(value PYTEST_WORKERS) ignored: pytest-xdist not installed)
    endif
    $(warning pytest-xdist not installed; running tests sequentially)
  endif
endif

endif  # test target filter

# Print target for stable cross-platform test parsing
.PHONY: print-pytest-parallel-flag
print-pytest-parallel-flag:
	@echo "$(PYTEST_PARALLEL_FLAG)"

# ------------------------------------------------------------------------------
# Test Targets
# ------------------------------------------------------------------------------

test:
	@echo "Running all tests with coverage (parallel execution)..."
	OTEL_SDK_DISABLED=true $(PYTEST) $(PYTEST_PARALLEL_FLAG) $(COV_OPTIONS) --cov-report=term-missing
	@echo "Tests complete. Coverage report above."
	@echo ""
	@echo "Tip: Use 'make test-fast' or 'make test-dev' for faster iteration"

test-unit:
	@echo "Running pure unit tests (tests/unit/)..."
	@test -d .venv || (echo "No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest $(PYTEST_PARALLEL_FLAG) tests/unit $(COV_OPTIONS) --cov-report=term-missing
	@echo "Unit tests complete"

test-local:
	@echo "Running all local tests (Unit + CLI + Validation)..."
	@test -d .venv || (echo "No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest $(PYTEST_PARALLEL_FLAG) tests/unit tests/cli tests/deployment tests/infrastructure tests/ci
	@echo "Local tests complete"

test-meta:
	@echo "Running meta-tests (test infrastructure validation)..."
	@test -d .venv || (echo "No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest $(PYTEST_PARALLEL_FLAG) -m meta -v
	@echo "Meta-tests complete"

test-ci:
	@echo "Running tests exactly as CI does (parallel execution)..."
	OTEL_SDK_DISABLED=true HYPOTHESIS_PROFILE=ci $(PYTEST) $(PYTEST_PARALLEL_FLAG) -m "unit and not llm" $(COV_OPTIONS) --cov-report=xml --cov-report=term-missing
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
	OTEL_SDK_DISABLED=true $(PYTEST) $(PYTEST_PARALLEL_FLAG) $(COV_OPTIONS) --cov-report=html --cov-report=term-missing --cov-report=xml
	@echo "Coverage reports generated:"
	@echo "  HTML: htmlcov/index.html"
	@echo "  XML: coverage.xml"

test-coverage-fast:
	@echo "Generating fast coverage report (unit tests only, parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) $(PYTEST_PARALLEL_FLAG) -m unit $(COV_OPTIONS) --cov-report=html --cov-report=term-missing
	@echo "Fast coverage report generated:"
	@echo "  HTML: htmlcov/index.html"

test-coverage-html:
	@echo "Generating HTML coverage report only..."
	OTEL_SDK_DISABLED=true $(PYTEST) $(PYTEST_PARALLEL_FLAG) $(COV_OPTIONS) --cov-report=html
	@echo "HTML coverage report generated: htmlcov/index.html"

test-coverage-xml:
	@echo "Generating XML coverage report..."
	OTEL_SDK_DISABLED=true $(PYTEST) $(PYTEST_PARALLEL_FLAG) $(COV_OPTIONS) --cov-report=xml
	@echo "XML coverage report generated: coverage.xml"

test-coverage-terminal:
	@echo "Generating terminal coverage report..."
	OTEL_SDK_DISABLED=true $(PYTEST) $(PYTEST_PARALLEL_FLAG) $(COV_OPTIONS) --cov-report=term-missing
	@echo "Terminal coverage displayed above"

# Quality tests
test-property:
	@echo "Running property-based tests (Hypothesis, parallel)..."
	@test -d .venv || (echo "No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest $(PYTEST_PARALLEL_FLAG) -m property -v
	@echo "Property tests complete"

test-contract:
	@echo "Running contract tests (MCP protocol, OpenAPI, parallel)..."
	@test -d .venv || (echo "No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest $(PYTEST_PARALLEL_FLAG) -m contract -v
	@echo "Contract tests complete"

test-regression:
	@echo "Running performance regression tests (parallel)..."
	@test -d .venv || (echo "No .venv found. Run: make install-dev" && exit 1)
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest $(PYTEST_PARALLEL_FLAG) -m regression -v
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
	OTEL_SDK_DISABLED=true $(PYTEST) $(PYTEST_PARALLEL_FLAG) --tb=short
	@echo "Fast tests complete"

test-fast-unit:
	@echo "Running unit tests without coverage (parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) $(PYTEST_PARALLEL_FLAG) -m unit --tb=short

test-dev:
	@echo "Running tests in development mode (parallel, fast-fail, no coverage)..."
	OTEL_SDK_DISABLED=true $(PYTEST) $(PYTEST_PARALLEL_FLAG) -x --maxfail=3 --tb=short -m "(unit or api or property or validation) and not llm and not slow"
	@echo "Development tests complete"

test-fast-core:
	@echo "Running core unit tests only (fastest iteration)..."
	OTEL_SDK_DISABLED=true $(PYTEST) $(PYTEST_PARALLEL_FLAG) -m "unit and not slow and not integration" --tb=line -q
	@echo "Core tests complete (typically < 5 seconds)"

test-slow:
	@echo "Running slow tests only (parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) $(PYTEST_PARALLEL_FLAG) -m slow -v --tb=short

test-compliance:
	@echo "Running compliance tests (GDPR, HIPAA, SOC2, SLA, parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) $(PYTEST_PARALLEL_FLAG) -m "gdpr or soc2 or sla" -v --tb=short

test-failed:
	@echo "Re-running failed tests (parallel)..."
	OTEL_SDK_DISABLED=true $(PYTEST) $(PYTEST_PARALLEL_FLAG) --lf -v

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

# ------------------------------------------------------------------------------
# Frontend Test Targets (Sharded Runner for OOM Prevention)
# ------------------------------------------------------------------------------

test-frontend: ## Run frontend tests (sharded, parallel, default 150 shards)
	cd src/mcp_server_langgraph/studio/frontend && bash scripts/run-tests-sharded.sh --parallel

test-frontend-fast: ## Run frontend tests (fast mode, 110 shards, parallel)
	cd src/mcp_server_langgraph/studio/frontend && bash scripts/run-tests-sharded.sh --fast --parallel

test-frontend-ci: ## Run frontend tests in CI mode (50 shards, sequential)
	cd src/mcp_server_langgraph/studio/frontend && bash scripts/run-tests-sharded.sh --ci

test-frontend-scripts: ## Run shell tests for sharded runner script
	bash tests/scripts/test_sharded_runner.sh

.PHONY: test-frontend test-frontend-fast test-frontend-ci test-frontend-scripts
