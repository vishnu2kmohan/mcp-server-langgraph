"""
Test Plugins Package.

Provides modular pytest fixtures organized by domain.
Register plugins in conftest.py via pytest_plugins list.

Available plugins:
- auth_plugin: Authentication fixtures (users, JWT tokens)
- settings_plugin: Application settings fixtures
- agent_plugin: LangGraph agent fixtures
- mcp_plugin: MCP (Model Context Protocol) fixtures
- resilience_plugin: Circuit breaker and resilience fixtures
- infrastructure_plugin: E2E infrastructure fixtures
- mock_fixtures_plugin: General mock fixtures
- container_plugin: DI container fixtures

Usage in conftest.py:
    pytest_plugins = [
        "tests.plugins.auth_plugin",
        "tests.plugins.settings_plugin",
        "tests.plugins.agent_plugin",
        "tests.plugins.mcp_plugin",
        "tests.plugins.resilience_plugin",
        "tests.plugins.infrastructure_plugin",
        "tests.plugins.mock_fixtures_plugin",
        "tests.plugins.container_plugin",
    ]
"""

__all__ = [
    "auth_plugin",
    "settings_plugin",
    "agent_plugin",
    "mcp_plugin",
    "resilience_plugin",
    "infrastructure_plugin",
    "mock_fixtures_plugin",
    "container_plugin",
]
