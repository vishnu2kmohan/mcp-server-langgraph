# ==============================================================================
# Validation
# ==============================================================================

.PHONY: validate-openapi validate-deployments validate-docker-compose validate-lgtm-config \
	validate-dashboards validate-docker-image validate-helm validate-kustomize validate-all \
	validate-docs validate-workflows validate-commit validate-push-changed validate-push-full \
	validate-push validate-full validate-pre-push validate-pre-push-quick validate-pre-push-full \
	validate-pre-push-ci _validate-pre-push-phases-1-2 _validate-pre-push-phase-4 \
	act-dry-run test-workflows test-precommit-validation

validate-openapi:
	@echo "Validating OpenAPI schema..."
	OTEL_SDK_DISABLED=true $(UV_RUN) python scripts/validators/validate_openapi.py 2>&1 | grep -v -E "(WARNING|trace_id|span_id|resource\.|Transient error|exporter\.py|Traceback|File \"|ImportError:|pydantic-ai|fall back)"
	@echo "OpenAPI validation complete"

validate-deployments:
	@echo "Validating all deployment configurations..."
	$(UV_RUN) python scripts/validators/validate_deployments.py
	@echo "Deployment validation complete"

validate-docker-compose:
	@echo "Validating Docker Compose configuration..."
	$(DOCKER_COMPOSE) -f docker-compose.yml config --quiet
	@echo "Docker Compose valid"

validate-lgtm-config:
	@echo "Validating LGTM stack configurations..."
	@echo "  Validating Mimir config..."
	@docker run --rm -v $(PWD)/docker/mimir:/etc/mimir grafana/mimir:3.0.1 \
		-config.file=/etc/mimir/mimir-config.yaml -print.config > /dev/null 2>&1 && \
		echo "  Mimir config valid" || \
		(echo "  Mimir config invalid" && exit 1)
	@echo "  Validating Loki config (YAML syntax)..."
	@$(UV_RUN) python -c "import yaml; yaml.safe_load(open('docker/loki/loki-config.yaml'))" && \
		echo "  Loki config YAML valid" || \
		(echo "  Loki config YAML invalid" && exit 1)
	@echo "LGTM configurations valid"

validate-dashboards:
	@echo "Validating Grafana dashboard JSON files..."
	@$(UV_RUN) python scripts/validators/validate_dashboards.py
	@echo "Dashboard validation complete"

validate-docker-image:
	@echo "Validating Docker test image freshness..."
	@./scripts/validators/validate_docker_image_freshness.sh --check-commits
	@echo "Docker image is up-to-date"

validate-helm:
	@echo "Validating Helm chart..."
	helm lint deployments/helm/mcp-server-langgraph
	helm template test-release deployments/helm/mcp-server-langgraph --dry-run > /dev/null
	@echo "Helm chart valid"

validate-kustomize:
	@echo "Validating Kustomize overlays in parallel..."
	@( \
		echo "  Validating dev overlay..." && kubectl kustomize deployments/overlays/dev > /dev/null 2>&1 && echo "  dev overlay valid" \
	) & pid1=$$!; \
	( \
		echo "  Validating staging overlay..." && kubectl kustomize deployments/overlays/staging > /dev/null 2>&1 && echo "  staging overlay valid" \
	) & pid2=$$!; \
	( \
		echo "  Validating production overlay..." && kubectl kustomize deployments/overlays/production > /dev/null 2>&1 && echo "  production overlay valid" \
	) & pid3=$$!; \
	wait $$pid1 $$pid2 $$pid3
	@echo "All Kustomize overlays valid"

validate-all: validate-deployments validate-docker-compose validate-lgtm-config validate-dashboards validate-docker-image validate-helm validate-kustomize
	@echo "All deployment validations passed"

validate-docs:
	@echo "Checking Claude Code documentation accuracy..."
	@$(UV_RUN) python scripts/validators/check-claude-docs-accuracy.py

validate-workflows:
	@echo "Comprehensive Workflow Validation (CI-Equivalent)"
	@echo ""
	@echo "STEP 1: Check actionlint is available"
	@if ! command -v actionlint >/dev/null 2>&1; then \
		echo "ERROR: actionlint not found."; \
		echo "Install via: brew install actionlint"; \
		exit 1; \
	else \
		echo "actionlint available"; \
	fi
	@echo ""
	@echo "STEP 2: Run actionlint on all workflow files"
	@actionlint -color -shellcheck= .github/workflows/*.{yml,yaml} && echo "actionlint validation passed" || (echo "actionlint validation failed" && exit 1)
	@echo ""
	@echo "STEP 3: Run workflow validation test suite"
	@OTEL_SDK_DISABLED=true $(UV_RUN) pytest \
		tests/meta/ci/test_workflow_syntax.py \
		tests/meta/ci/test_workflow_security.py \
		tests/meta/ci/test_workflow_dependencies.py \
		tests/meta/infrastructure/test_docker_paths.py \
		-v --tb=short && echo "Workflow test suite passed" || (echo "Workflow tests failed" && exit 1)
	@echo ""
	@echo "STEP 4: Validate pytest configuration compatibility"
	@$(UV_RUN) python scripts/validators/validate_pytest_config.py && echo "Pytest config validation passed" || (echo "Pytest config validation failed" && exit 1)
	@echo ""
	@echo "All workflow validations passed (CI-equivalent)"

# ==============================================================================
# Tiered Validation System
# ==============================================================================

validate-commit:
	@echo "TIER 1 VALIDATION - Quick Checks (<30s)"
	@echo ""
	@echo "Running pre-commit hooks (staged files only)..."
	@pre-commit run --show-diff-on-failure
	@echo ""
	@echo "Tier 1 validation complete!"

validate-push-changed:
	@echo "TIER 2 VALIDATION - Critical Checks (Changed Files)"
	@echo ""
	@echo "STEP 1: Tier 1 Validation (pre-commit hooks - changed files)"
	@pre-commit run --show-diff-on-failure
	@echo ""
	@echo "STEP 2: Tier 2 Validation (pre-push hooks - changed files)"
	@pre-commit run --hook-stage pre-push --show-diff-on-failure
	@echo ""
	@echo "Tier 1 + Tier 2 validation complete (changed files)!"

validate-push-full:
	@echo "TIER 2 VALIDATION - Critical Checks (All Files)"
	@echo ""
	@echo "STEP 1: Tier 1 Validation (pre-commit hooks - all files)"
	@pre-commit run --all-files --show-diff-on-failure
	@echo ""
	@echo "STEP 2: Tier 2 Validation (pre-push hooks - all files)"
	@pre-commit run --hook-stage pre-push --all-files --show-diff-on-failure
	@echo ""
	@echo "Tier 1 + Tier 2 validation complete (all files)!"

validate-push: validate-push-changed

validate-full:
	@echo "TIER 3 VALIDATION - Comprehensive (12-15 min)"
	@echo ""
	@echo "STEP 1: Tier 1 Validation (pre-commit hooks)"
	@pre-commit run --all-files
	@echo ""
	@echo "STEP 2: Tier 2 Validation (pre-push hooks)"
	@pre-commit run --hook-stage pre-push --all-files
	@echo ""
	@echo "STEP 3: Tier 3 Validation (manual hooks + comprehensive tests)"
	@SKIP= pre-commit run --hook-stage manual --all-files
	@echo ""
	@echo "Running comprehensive test suite..."
	@$(MAKE) test-ci
	@echo ""
	@echo "All tiers complete! (Tier 1 + Tier 2 + Tier 3)"

# Internal validation phases
_validate-pre-push-phases-1-2:
	@echo "PHASE 1: Fast Checks (Lockfile & Workflow Validation)"
	@echo ""
	@echo "Lockfile Validation..."
	@uv lock --check && echo "Lockfile valid" || (echo "Lockfile validation failed" && exit 1)
	@echo ""
	@echo "Dependency Tree Validation..."
	@uv pip check && echo "Dependencies valid" || (echo "Dependency conflicts detected" && exit 1)
	@echo ""
	@echo "Workflow Validation Tests..."
	@OTEL_SDK_DISABLED=true $(UV_RUN) pytest tests/meta/ci/test_workflow_syntax.py tests/meta/ci/test_workflow_security.py tests/meta/ci/test_workflow_dependencies.py tests/meta/infrastructure/test_docker_paths.py -v --tb=short && echo "Workflow tests passed" || (echo "Workflow validation failed" && exit 1)
	@echo ""
	@echo "PHASE 2: Type Checking (Critical - matches CI)"
	@echo ""
	@echo "MyPy Type Checking (Critical)..."
	@$(UV_RUN) mypy src/mcp_server_langgraph --no-error-summary && echo "MyPy passed" || (echo "MyPy found type errors" && exit 1)
	@echo ""

_validate-pre-push-phase-4:
	@echo "PHASE 4: Pre-commit Hooks (All Files - pre-push stage)"
	@echo ""
	@echo "Pre-commit Hooks (All Files - Pre-Push Stage)..."
	@SKIP=uv-lock-check,uv-pip-check,mypy,run-pre-push-tests pre-commit run --all-files --hook-stage pre-push --show-diff-on-failure && echo "Pre-commit hooks passed" || (echo "Pre-commit hooks failed" && exit 1)
	@echo ""

validate-pre-push-quick:
	@echo "Running pre-push validation (QUICK - no integration tests)"
	@echo ""
	@$(MAKE) _validate-pre-push-phases-1-2
	@echo "PHASE 3: Test Suite Validation"
	@echo ""
	@echo "Running Unit, API, Property, and Smoke Tests (Optimized)..."
	@$(UV_RUN) python scripts/run_pre_push_tests.py && echo "Fast tests passed" || (echo "Fast tests failed" && exit 1)
	@echo ""
	@echo "Skipping integration tests (use validate-pre-push-full for comprehensive validation)"
	@echo ""
	@$(MAKE) _validate-pre-push-phase-4
	@echo "All pre-push validations passed (QUICK)!"

validate-pre-push-full:
	@echo "CI-EQUIVALENT VALIDATION (FULL)"
	@echo ""
	@$(MAKE) _validate-pre-push-phases-1-2
	@echo "PHASE 3: Test Suite Validation"
	@echo ""
	@echo "Running Unit, API, Property, and Smoke Tests (Optimized)..."
	@$(UV_RUN) python scripts/run_pre_push_tests.py && echo "Fast tests passed" || (echo "Fast tests failed" && exit 1)
	@echo ""
	@echo "Running Integration Tests (Docker)..."
	@./scripts/test-integration.sh && echo "Integration tests passed" || (echo "Integration tests failed" && exit 1)
	@echo ""
	@echo "Running E2E Tests (Docker)..."
	@./scripts/test-e2e.sh && echo "E2E tests passed" || (echo "E2E tests failed" && exit 1)
	@echo ""
	@echo "Running Frontend Tests..."
	@./scripts/test-frontend.sh && echo "Frontend tests passed" || (echo "Frontend tests failed" && exit 1)
	@echo ""
	@$(MAKE) _validate-pre-push-phase-4
	@echo "All pre-push validations passed (FULL)!"

validate-pre-push:
	@if [ "$$CI_PARITY" = "1" ]; then \
		echo "CI_PARITY=1 detected - Running FULL CI-equivalent validation"; \
		$(MAKE) validate-pre-push-full; \
	else \
		echo "Running QUICK validation (skip integration tests)"; \
		echo "Tip: Use 'CI_PARITY=1 make validate-pre-push' for full CI validation"; \
		$(MAKE) validate-pre-push-quick; \
	fi

validate-pre-push-ci:
	@echo "CI-EQUIVALENT VALIDATION (All Files)"
	@echo ""
	CI_PARITY=1 $(MAKE) validate-pre-push-full

act-dry-run:
	@echo "Showing what would execute in CI workflows..."
	@act push --list

test-workflows:
	@echo "Testing critical workflows locally with act..."
	@docker ps > /dev/null 2>&1 || (echo "Docker not running. Start Docker first." && exit 1)
	@echo ""
	@echo "1. Testing CI/CD Pipeline (test job on Python 3.12)..."
	@act push -W .github/workflows/ci.yaml -j test --matrix python-version:3.12 --quiet || echo "  May fail without full infrastructure"
	@echo ""
	@echo "Workflow testing complete"

test-workflow-%:
	@echo "Testing workflow: $*.yaml"
	@act push -W .github/workflows/$*.yaml

test-precommit-validation:
	@echo "Validating pre-commit hook configuration (parallel)..."
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto tests/regression/test_precommit_hook_dependencies.py -v --tb=short
	@echo "Pre-commit validation complete"
