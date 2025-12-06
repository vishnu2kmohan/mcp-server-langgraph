"""
Playground API module.

Provides FastAPI-based HTTP and WebSocket endpoints for the interactive playground.
"""

from .server import app

__all__ = ["app"]
