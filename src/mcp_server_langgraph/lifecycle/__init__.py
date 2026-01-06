"""
Lifecycle management for MCP Server LangGraph.

This package provides lifecycle hooks for application startup and shutdown,
including proper cleanup of database connections and service clients.
"""

from mcp_server_langgraph.lifecycle.cleanup import cleanup_all_clients

__all__ = ["cleanup_all_clients"]
