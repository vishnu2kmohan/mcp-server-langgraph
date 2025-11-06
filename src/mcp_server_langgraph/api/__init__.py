"""API module for HTTP endpoints"""

from .api_keys import router as api_keys_router
from .gdpr import router as gdpr_router
from .health import router as health_router
from .scim import router as scim_router
from .service_principals import router as service_principals_router

__all__ = [
    "api_keys_router",
    "gdpr_router",
    "health_router",
    "scim_router",
    "service_principals_router",
]
