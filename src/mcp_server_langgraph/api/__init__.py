"""API module for HTTP endpoints"""

from .gdpr import router as gdpr_router

__all__ = ["gdpr_router"]
