# Scripts Registry

This registry catalogs all automation scripts in the `scripts/` directory, organized by category for easy discovery and maintenance.

**Last Updated:** $(date +%Y-%m-%d)
**Total Scripts:** 116

## Table of Contents

- [Validators](#validators) - Scripts that validate code quality and compliance
- [Deployment](#deployment) - Cloud deployment automation
- [Testing](#testing) - Test orchestration and execution
- [Infrastructure](#infrastructure) - Infrastructure management and health checks
- [Development Tools](#development-tools) - Developer workflow automation
- [Maintenance](#maintenance) - Repository maintenance and cleanup scripts

---

## Validators

Scripts that validate code quality, test organization, and CI/CD configuration.

### Core Validators

- **`validate_ci_cd.py`** - Validates CI/CD workflow configuration matches local development setup
  - Pre-commit hook: `validate-ci-cd-workflows`
  - Ensures local/CI parity

- **`validate_pre_push_hook.py`** - Validates pre-push hook configuration
  - Ensures comprehensive test coverage before push
  - Checks for required validation patterns

- **`check_test_memory_safety.py`** - Enforces pytest-xdist memory safety patterns
  - Pre-commit hook: `check-test-memory-safety`
  - Validates 3-part pattern: xdist_group + teardown_method + gc.collect()
  - Prevents memory leaks in parallel test execution

### Test Validators

- **`validation/validate_test_isolation.py`** - Validates test isolation patterns
  - Checks for dependency override cleanup
  - Validates xdist compatibility
  - Warns about missing xdist_group markers

- **`validate_test_fixtures.py`** - Validates test fixture patterns
  - FastAPI auth override patterns
  - Ollama model name validation
  - Circuit breaker isolation checks

- **`validate_pytest_markers.py`** - Validates pytest marker consistency
  - Ensures markers are properly applied
  - Checks for marker organization

- **`validate_fixture_organization.py`** - Prevents duplicate autouse fixtures
  - Enforces conftest.py placement rules
  - See: CODEX_FINDINGS_VALIDATION_REPORT.md

### Configuration Validators

- **`validate_github_workflows.py`** - Validates GitHub Actions workflow YAML
  - Syntax checking
  - Job dependency validation

- **`validate_keycloak_config.py`** - Validates Keycloak setup
  - Realm configuration
  - Client setup validation

- **`validate_docker_image_contents.py`** - Validates Docker image builds
  - Required files present
  - Proper layer caching

### Cloud Validators

- **`validate_gke_autopilot_compliance.py`** - Validates GKE Autopilot compatibility
  - Resource limits
  - Security policies

- **`validate_terraform_state.py`** - Validates Terraform state consistency

---

## Deployment

Cloud deployment automation for AWS, Azure, and GCP.

### Production Deployment

- **`deploy-gcp-gke.sh`** - Deploy to Google Kubernetes Engine (GKE)
  - Autopilot mode support
  - Multi-region deployment
  - Health check validation

- **`deploy-aws-eks.sh`** - Deploy to Amazon Elastic Kubernetes Service (EKS)
  - IAM role configuration
  - LoadBalancer setup

- **`deploy-azure-aks.sh`** - Deploy to Azure Kubernetes Service (AKS)
  - Azure AD integration
  - Network policy setup

### Deployment Utilities

- **`init_openfga_test.sh`** - Initialize OpenFGA for testing
  - Store creation
  - Authorization model setup

- **`wait-for-services.sh`** - Wait for services to be healthy
  - Postgres, Redis, OpenFGA, Keycloak readiness checks

- **`validate-infrastructure.sh`** - Validate infrastructure is ready
  - Service health checks
  - Connectivity validation

---

## Testing

Test orchestration and execution scripts.

### Integration Testing

- **`test-integration.sh`** - Integration test orchestration
  - Docker Compose infrastructure startup
  - Test execution
  - Cleanup automation

- **`test-workflows.sh`** - GitHub Actions workflow testing
  - Local workflow execution
  - Act-based testing

- **`test_agentic_loop.sh`** - Agent behavior testing
  - LangGraph agent testing

### Test Infrastructure

- **`smoke-test-compose.sh`** - Docker Compose smoke tests
  - Quick infrastructure validation

- **`migrate_integration_tests.py`** - Migrate integration tests to tests/integration/
  - Automated test reorganization
  - Preserves git history with `git mv`
  - Created: 2025-11-16 (OpenAI Codex Finding #3)

---

## Infrastructure

Infrastructure management, health checks, and service orchestration.

- **`init-infrastructure.sh`** - Initialize infrastructure services
- **`cleanup-infrastructure.sh`** - Cleanup infrastructure resources
- **`health-check-all.sh`** - Check health of all services

---

## Development Tools

Developer workflow automation and productivity tools.

### Worktree Management

- **`start-worktree-session.sh`** - Start git worktree session
  - Feature branch isolation
  - Clean environment setup

- **`cleanup-worktrees.sh`** - Cleanup old worktree sessions
  - Removes stale branches
  - Frees disk space

### Version Management

- **`bump-version.sh`** - Bump semantic version
  - Major, minor, patch bumps
  - Git tag creation

### Code Quality

- **`format-all.sh`** - Format all code
  - Black, isort, autoflake
  - Consistent code style

- **`lint-all.sh`** - Run all linters
  - flake8, mypy, bandit

---

## Maintenance

Repository maintenance, cleanup, and optimization scripts.

- **`cleanup-cache.sh`** - Clear build and test caches
- **`update-dependencies.sh`** - Update Python dependencies
- **`prune-docker.sh`** - Cleanup unused Docker resources

---

## Usage Guidelines

### Running Scripts

Most scripts are executable and can be run directly:

```bash
# Validators (usually run via pre-commit)
python scripts/validate_ci_cd.py
python scripts/check_test_memory_safety.py

# Deployment
./scripts/deploy-gcp-gke.sh --env production

# Testing
./scripts/test-integration.sh --verbose
```

### Adding New Scripts

When adding a new script:

1. **Choose appropriate category** (Validators, Deployment, Testing, etc.)
2. **Add module docstring** documenting purpose, usage, and examples
3. **Make executable** (if shell script): `chmod +x scripts/your-script.sh`
4. **Add shebang** (`#!/bin/bash` or `#!/usr/bin/env python3`)
5. **Update this registry** in the appropriate category
6. **Add meta-tests** if it's a validator script

### Shell Script Best Practices

All shell scripts should follow these conventions:

```bash
#!/usr/bin/env bash
set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Clear documentation
# Proper error handling
# Use functions for complex logic
```

### Python Script Best Practices

All Python scripts should follow these conventions:

```python
#!/usr/bin/env python3
"""
Module docstring explaining purpose.

Usage:
    python scripts/your_script.py [options]
"""

import argparse
import sys

def main():
    """Main function with clear logic."""
    parser = argparse.ArgumentParser(description="...")
    # ... implementation ...
    return 0  # Proper exit code

if __name__ == "__main__":
    sys.exit(main())
```

---

## Deprecation Policy

Deprecated scripts are marked here with ~~strikethrough~~ and moved to `scripts/deprecated/` after 2 sprint cycles.

### Deprecated Scripts

None currently.

---

## References

- **Meta-Tests:** `tests/meta/test_scripts_governance.py` validates script organization
- **Pre-Commit:** `.pre-commit-config.yaml` configures validator script execution
- **CI/CD:** `.github/workflows/` uses these scripts for automation

---

## Maintenance

This registry is validated by `tests/meta/test_scripts_governance.py`. When scripts are added, moved, or removed, update this file accordingly.

**Registry Validation:**
```bash
pytest tests/meta/test_scripts_governance.py -v
```
