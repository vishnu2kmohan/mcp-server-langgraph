"""Authentication and authorization modules."""

from mcp_server_langgraph.auth.connection_scope import (
    ConnectionScope,
    can_use_connection,
    filter_accessible_connections,
)
from mcp_server_langgraph.auth.encrypted_session_store import EncryptedSessionStore
from mcp_server_langgraph.auth.middleware import AuthMiddleware
from mcp_server_langgraph.auth.openfga import OpenFGAClient, initialize_openfga_store, seed_sample_data
from mcp_server_langgraph.auth.session_encryptor import (
    DecryptionError,
    EncryptionError,
    SessionEncryptor,
    derive_key,
)

__all__ = [
    "AuthMiddleware",
    "ConnectionScope",
    "DecryptionError",
    "EncryptedSessionStore",
    "EncryptionError",
    "OpenFGAClient",
    "SessionEncryptor",
    "can_use_connection",
    "derive_key",
    "filter_accessible_connections",
    "initialize_openfga_store",
    "seed_sample_data",
]
