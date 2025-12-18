# ==============================================================================
# Documentation
# ==============================================================================

docs-serve:
	@echo "Serving Mintlify documentation locally..."
	@if command -v npx >/dev/null 2>&1; then \
		cd docs && npx mintlify dev; \
	else \
		echo "npx not found. Install Node.js first."; \
	fi

docs-build:
	@echo "Building Mintlify documentation..."
	@if command -v npx >/dev/null 2>&1; then \
		cd docs && npx mintlify build; \
	else \
		echo "npx not found. Install Node.js first."; \
	fi

docs-deploy:
	@echo "Deploying documentation to Mintlify..."
	@echo ""
	@echo "Prerequisites:"
	@echo "  1. Mintlify account setup"
	@echo "  2. mintlify CLI authenticated"
	@echo ""
	@read -p "Continue? (y/n) " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		cd docs && npx mintlify deploy; \
	else \
		echo "Deployment cancelled"; \
	fi

docs-validate: docs-validate-mintlify docs-validate-specialized
	@echo ""
	@echo "All documentation validation passed!"
	@echo ""

docs-validate-mintlify:
	@echo "PRIMARY VALIDATOR: Mintlify CLI"
	@echo "Checks: links, navigation, images, frontmatter, MDX syntax"
	@if command -v npx >/dev/null 2>&1; then \
		cd docs && npx mintlify broken-links || \
			(echo "Mintlify validation failed." && exit 1); \
		echo "Mintlify validation passed"; \
	else \
		echo "Mintlify CLI not found. Install with: npm install -g mintlify"; \
		exit 1; \
	fi

docs-validate-specialized:
	@echo "SUPPLEMENTARY: Specialized validators"
	@echo "Validating ADR synchronization..."
	@python scripts/validators/adr_sync_validator.py || \
		(echo "ADR synchronization failed." && exit 1)
	@echo "Validating MDX file extensions..."
	@python scripts/validators/mdx_extension_validator.py --docs-dir docs || \
		(echo "MDX extension validation failed." && exit 1)
	@echo "Specialized validators passed"

docs-validate-version:
	@echo "Checking version consistency..."
	@python3 scripts/validators/check_version_consistency.py || \
		(echo "Version inconsistencies found (review recommended)." && exit 0)

docs-fix-mdx:
	@echo "Auto-fixing MDX syntax errors..."
	@python3 scripts/docs/fix_mdx_syntax.py --all
	@echo "MDX syntax fixed. Review changes with 'git diff docs/'"

docs-test:
	@echo "Running documentation validation tests..."
	@$(UV_RUN) pytest tests/test_mdx_validation.py tests/test_link_checker.py -v

docs-audit:
	@echo "Running comprehensive documentation audit..."
	@echo "Current version: $$(python3 -c 'import toml; print(toml.load(open(\"pyproject.toml\"))[\"project\"][\"version\"])')"
	@echo ""
	@echo "Running validations..."
	@make docs-validate || true
	@echo ""
	@echo "See docs-internal/DOCUMENTATION_AUDIT_*.md for detailed reports"

# ==============================================================================
# Test Infrastructure Reports
# ==============================================================================

generate-reports:
	@echo "Regenerating test infrastructure reports..."
	@echo ""
	@echo "Running AsyncMock configuration scan..."
	@$(UV_RUN) python scripts/validators/check_async_mock_configuration.py tests/**/*.py > docs-internal/reports/ASYNC_MOCK_SCAN.md 2>&1 || true
	@echo "AsyncMock scan complete"
	@echo ""
	@echo "Running memory safety scan..."
	@$(UV_RUN) python scripts/validators/check_test_memory_safety.py tests/**/*.py > docs-internal/reports/MEMORY_SAFETY_SCAN.md 2>&1 || true
	@echo "Memory safety scan complete"
	@echo ""
	@echo "Generating test suite statistics..."
	@$(UV_RUN) python scripts/generate_test_stats.py > docs-internal/reports/TEST_SUITE_STATS.md 2>&1 || true
	@echo "Test statistics generated"
	@echo ""
	@echo "All reports regenerated in docs-internal/reports/"
