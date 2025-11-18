"""
Web Playground for MCP Server with LangGraph

Interactive testing environment with:
- Real-time chat interface
- WebSocket streaming
- Trace visualization
- Tool invocation display
- Conversation export
- Session management

Example:
    # Start playground server
    uvicorn mcp_server_langgraph.playground.api.server:app --port 8002

    # Open frontend
    open http://localhost:3001
"""

from .api.server import app


__all__ = ["app"]
