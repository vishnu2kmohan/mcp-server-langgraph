# ==============================================================================
# MCP Server LangGraph - Makefile
# ==============================================================================
# This Makefile has been modularized for maintainability.
# All targets are organized into focused files in the make/ directory.
#
# Quick Reference:
#   make help-common     Essential commands for daily development
#   make help            Full command reference
#   make help-advanced   Advanced and specialized targets
#
# Module Structure:
#   make/variables.mk     - Variables and configuration
#   make/help.mk          - Help targets
#   make/setup.mk         - Installation and setup
#   make/testing.mk       - Test targets
#   make/infrastructure.mk - Docker test infrastructure
#   make/validation.mk    - Validation and CI targets
#   make/lint.mk          - Linting, formatting, security
#   make/deploy.mk        - Deployment targets
#   make/docs.mk          - Documentation targets
#   make/development.mk   - Development shortcuts
# ==============================================================================

.PHONY: help help-common help-advanced

# Sequential-only targets (cannot be parallelized)
.NOTPARALLEL: deploy-production deploy-staging deploy-dev setup-keycloak setup-openfga setup-infisical dev-setup

# Default target
.DEFAULT_GOAL := help-common

# ==============================================================================
# Include modular makefiles
# ==============================================================================

include make/variables.mk
include make/help.mk
include make/setup.mk
include make/testing.mk
include make/infrastructure.mk
include make/validation.mk
include make/lint.mk
include make/deploy.mk
include make/docs.mk
include make/development.mk

# ==============================================================================
# CI-Mode Quality Tests (with coverage, matches CI exactly)
# These are additional targets that bridge multiple modules
# ==============================================================================

test-property-ci:
	@echo "Running property-based tests with coverage (CI mode)..."
	HYPOTHESIS_PROFILE=ci OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto -m property -v --tb=short \
		--cov=src/mcp_server_langgraph --cov-report=xml:coverage-property.xml --cov-report=term
	@echo "Property tests complete (coverage: coverage-property.xml)"

test-contract-ci:
	@echo "Running contract tests with coverage (CI mode)..."
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto -m contract -v --tb=short \
		--cov=src/mcp_server_langgraph --cov-report=xml:coverage-contract.xml --cov-report=term
	@echo "Contract tests complete (coverage: coverage-contract.xml)"

test-regression-ci:
	@echo "Running regression tests with coverage (CI mode)..."
	OTEL_SDK_DISABLED=true $(UV_RUN) pytest -n auto -m regression -v --tb=short \
		--cov=src/mcp_server_langgraph --cov-report=xml:coverage-regression.xml --cov-report=term
	@echo "Regression tests complete (coverage: coverage-regression.xml)"

test-all-quality-ci: test-property-ci test-contract-ci test-regression-ci test-precommit-validation
	@echo "All quality tests complete (CI mode with coverage)"
	@echo ""
	@echo "Coverage reports generated:"
	@echo "  - coverage-property.xml"
	@echo "  - coverage-contract.xml"
	@echo "  - coverage-regression.xml"

test-coverage-changed:
	@echo "Running tests for changed code only (incremental coverage)..."
	OTEL_SDK_DISABLED=true $(PYTEST) -n auto --testmon $(COV_OPTIONS) --cov-report=html --cov-report=term-missing
	@echo "Incremental coverage complete"
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
		$(UV_RUN) coverage combine --append coverage-integration/.coverage* 2>/dev/null || true; \
		$(UV_RUN) coverage xml -o coverage-combined.xml; \
		$(UV_RUN) coverage html -d htmlcov-combined; \
		$(UV_RUN) coverage report; \
		echo ""; \
		echo "Combined coverage reports generated:"; \
		echo "  HTML: htmlcov-combined/index.html"; \
		echo "  XML: coverage-combined.xml"; \
	else \
		echo "  No integration coverage found, using unit tests only"; \
		$(UV_RUN) coverage xml; \
		$(UV_RUN) coverage html; \
		$(UV_RUN) coverage report; \
	fi
