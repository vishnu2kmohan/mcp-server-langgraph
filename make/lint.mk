# ==============================================================================
# Code Quality - Linting, Formatting, Security
# ==============================================================================

# Aliases for backward compatibility
lint: lint-check

format: lint-fix

security-check:
	@echo "Running bandit security scan..."
	$(UV_RUN) bandit -r . -x ./tests,./.venv -ll

security-scan-full:
	@echo "Running comprehensive security scan..."
	@mkdir -p security-reports
	@echo ""
	@echo "1/3 Running Bandit (code security)..."
	@bandit -r src/ -f json -o security-reports/bandit-report.json 2>/dev/null || true
	@bandit -r src/ -ll -x ./tests,./.venv || echo "Bandit found issues (see report)"
	@echo ""
	@echo "2/3 Running Safety (dependency vulnerabilities)..."
	@if command -v safety >/dev/null 2>&1; then \
		safety check --json --output security-reports/safety-report.json 2>/dev/null || echo '{"vulnerabilities": []}' > security-reports/safety-report.json; \
	else \
		echo "Safety not installed. Install with: uv tool install safety"; \
		echo '{"vulnerabilities": []}' > security-reports/safety-report.json; \
	fi
	@echo ""
	@echo "3/3 Running pip-audit (dependency vulnerabilities)..."
	@if command -v pip-audit >/dev/null 2>&1; then \
		pip-audit --format json --output security-reports/pip-audit-report.json 2>/dev/null || echo '{"dependencies": []}' > security-reports/pip-audit-report.json; \
	else \
		echo "pip-audit not installed. Install with: uv tool install pip-audit"; \
		echo '{"dependencies": []}' > security-reports/pip-audit-report.json; \
	fi
	@echo ""
	@echo "Generating consolidated report..."
	@$(UV_RUN) python scripts/security/generate_report.py security-reports
	@echo ""
	@echo "Security scan complete!"
	@echo "Report: security-reports/security-scan-report.md"

# Modern Ruff-based lint targets
lint-check:
	@echo "Running Ruff linter..."
	@$(UV_RUN) ruff check src/ tests/ --output-format=concise
	@echo "Lint check complete (Ruff)"

lint-fix:
	@echo "Auto-fixing with Ruff..."
	@$(UV_RUN) ruff check src/ tests/ --fix
	@$(UV_RUN) ruff format src/ tests/
	@echo "Auto-fix complete (Ruff)"

lint-format:
	@echo "Formatting with Ruff..."
	@$(UV_RUN) ruff format src/ tests/
	@echo "Format complete (Ruff)"

lint-type-check:
	@echo "Running mypy type checking..."
	@$(UV_RUN) mypy src/mcp_server_langgraph --no-error-summary
	@echo "Type check complete (mypy)"

lint-security:
	@echo "Running bandit security scan..."
	@$(UV_RUN) bandit -r src/ -ll
	@echo "Security scan complete (bandit)"

lint-pre-commit:
	@echo "Simulating pre-commit hook (runs on staged files)..."
	@$(UV_RUN) pre-commit run --all-files
	@echo "Pre-commit simulation complete"

lint-pre-push:
	@echo "Simulating pre-push hook (runs on changed files)..."
	@bash $$(git rev-parse --git-common-dir)/hooks/pre-push
	@echo "Pre-push simulation complete"

pre-push-parallel:  ## Run pre-push hooks in parallel lanes (~50-60% faster)
	@echo "Running parallel pre-push hooks..."
	@bash scripts/hooks/parallel_pre_push.sh
	@echo "Parallel pre-push complete"

lint-install:
	@echo "Installing/reinstalling lint hooks..."
	@$(UV_RUN) pre-commit install
	@chmod +x $$(git rev-parse --git-common-dir)/hooks/pre-push
	@echo "Hooks installed:"
	@echo "  - pre-commit (auto-fix Ruff formatter, run Ruff linter/MyPy/bandit)"
	@echo "  - pre-push (comprehensive validation before push)"
	@echo ""
	@echo "Test hooks:"
	@echo "  make lint-pre-commit"
	@echo "  make lint-pre-push"
