"""
Modular test fixtures for improved maintainability.

This package contains extracted non-autouse fixtures from tests/conftest.py
organized by domain:
- docker_fixtures: Docker infrastructure and service management
- time_fixtures: Time manipulation and freezing

These fixtures are automatically loaded via pytest_plugins in tests/conftest.py.

Note: Autouse fixtures (observability, singleton reset) must remain in
tests/conftest.py per fixture organization enforcement rules.
See: tests/meta/test_fixture_organization.py for validation

See: Testing Strategy Remediation Plan - Phase 3
"""
