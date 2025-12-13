"""
OpenFGA Playground Auth Proxy

Protects OpenFGA Playground with:
- Keycloak JWT authentication
- OpenFGA authorization (user must have 'admin' on 'authz:playground')

Reference: ADR-0068 - Gateway-Level Authentication (native OAuth2)
"""

from mcp_server_langgraph.authz_proxy.server import app

__all__ = ["app"]
