"""
MCP Server Presets

Pre-configured setups for different use cases:
- QuickStart: Minimal in-memory setup (< 2 minutes)
- Development: Docker Compose stack (15 minutes)
- Production: Full enterprise features (1-2 hours)
"""

from .quickstart import QuickStart


__all__ = ["QuickStart"]
