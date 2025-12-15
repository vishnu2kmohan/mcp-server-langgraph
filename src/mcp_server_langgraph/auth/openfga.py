"""
OpenFGA integration for fine-grained relationship-based access control

Enhanced with resilience patterns (ADR-0026):
- Circuit breaker for OpenFGA failures (fail-open by default)
- Retry logic with exponential backoff
- Timeout enforcement (5s for auth operations)
- Bulkhead isolation (50 concurrent auth checks max)

Authentication (ADR-0068):
- Preshared key authentication for API access
- All API requests require: Authorization: Bearer <preshared-key>

Configuration:
- Authorization model loaded from config/openfga/model.json
- Model is configuration, not code (separation of concerns)
"""

import json
import os
from pathlib import Path
from typing import Any

import httpx
from openfga_sdk import ClientConfiguration, OpenFgaClient
from openfga_sdk.client.models import ClientCheckRequest, ClientTuple, ClientWriteRequest
from openfga_sdk.credentials import CredentialConfiguration, Credentials
from pydantic import BaseModel, ConfigDict, Field

from mcp_server_langgraph.core.exceptions import OpenFGAError, OpenFGATimeoutError, OpenFGAUnavailableError
from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer
from mcp_server_langgraph.resilience import circuit_breaker, retry_with_backoff, with_bulkhead, with_timeout


class OpenFGAConfig(BaseModel):
    """
    Type-safe OpenFGA configuration

    Configuration for OpenFGA authorization service.
    """

    api_url: str = Field(default="http://localhost:8080", description="OpenFGA server API URL")
    store_id: str | None = Field(default=None, description="Authorization store ID")
    store_name: str | None = Field(
        default=None,
        description="Store name for dynamic lookup. If store_id is not set, "
        "the client will look up the store by name on initialization.",
    )
    model_id: str | None = Field(default=None, description="Authorization model ID")
    preshared_key: str | None = Field(
        default=None,
        description="Preshared key for API authentication (ADR-0068). "
        "If set, all API requests will include Authorization: Bearer <key>",
    )

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "api_url": "http://localhost:8080",
                "store_id": "01H...",
                "model_id": "01H...",
                "preshared_key": "test-openfga-preshared-key",
            }
        },
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for backward compatibility"""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "OpenFGAConfig":
        """Create OpenFGAConfig from dictionary"""
        return cls(**data)


class OpenFGAClient:
    """
    OpenFGA client for relationship-based authorization

    Implements Zanzibar-style authorization with fine-grained permissions
    based on relationships between users, resources, and roles.
    """

    def __init__(
        self,
        config: OpenFGAConfig | None = None,
        api_url: str | None = None,
        store_id: str | None = None,
        store_name: str | None = None,
        model_id: str | None = None,
        preshared_key: str | None = None,
    ):
        """
        Initialize OpenFGA client (lazy async initialization pattern)

        NOTE: This __init__ is sync-safe and doesn't create async resources.
        The actual OpenFgaClient is created lazily on first async method call.

        This prevents "RuntimeError: no running event loop" when instantiating
        from synchronous code or module imports.

        Args:
            config: OpenFGAConfig instance (recommended)
            api_url: OpenFGA server URL (legacy, use config instead)
            store_id: Authorization store ID (legacy, use config instead)
            store_name: Store name for dynamic lookup (legacy, use config instead)
            model_id: Authorization model ID (legacy, use config instead)
            preshared_key: Preshared key for API auth (legacy, use config instead)
        """
        # Support both new config-based and legacy parameter-based initialization
        if config is None:
            # Check environment variables if not provided
            env_preshared_key = preshared_key or os.getenv("OPENFGA_PRESHARED_KEY")
            env_store_name = store_name or os.getenv("OPENFGA_STORE_NAME")
            config = OpenFGAConfig(
                api_url=api_url or "http://localhost:8080",
                store_id=store_id,
                store_name=env_store_name,
                model_id=model_id,
                preshared_key=env_preshared_key,
            )

        self.config = config
        self.api_url = config.api_url
        self.store_id = config.store_id
        self.store_name = config.store_name
        self.model_id = config.model_id
        self.preshared_key = config.preshared_key

        # Lazy initialization: Store configuration, don't create OpenFgaClient yet
        # This prevents creating aiohttp resources which require an event loop
        self._client: OpenFgaClient | None = None
        self._initialized = False

        logger.info(
            "OpenFGA client wrapper created (lazy init)",
            extra={
                "api_url": config.api_url,
                "store_name": config.store_name,
                "auth_enabled": config.preshared_key is not None,
            },
        )

    async def _ensure_initialized(self) -> None:
        """
        Ensure OpenFgaClient is initialized (lazy async initialization)

        This method creates the actual OpenFgaClient on first async call.
        Called by all async methods before performing operations.

        If preshared_key is configured, credentials are added for API authentication (ADR-0068).
        If store_id is not set but store_name is, looks up the store by name.
        """
        if not self._initialized:
            # Look up store by name if store_id is not set but store_name is
            store_id = self.config.store_id
            if not store_id and self.config.store_name:
                store_id = await self._lookup_store_by_name(self.config.store_name)
                if store_id:
                    self.store_id = store_id
                    self.config.store_id = store_id
                    logger.info(
                        "Resolved store by name",
                        extra={"store_name": self.config.store_name, "store_id": store_id},
                    )
                else:
                    logger.warning(
                        "Could not find store by name",
                        extra={"store_name": self.config.store_name},
                    )

            # Build credentials if preshared key is configured
            credentials = None
            if self.config.preshared_key:
                credentials = Credentials(
                    method="api_token",
                    configuration=CredentialConfiguration(api_token=self.config.preshared_key),
                )

            configuration = ClientConfiguration(
                api_url=self.config.api_url,
                store_id=store_id,
                authorization_model_id=self.config.model_id,
                credentials=credentials,
            )
            self._client = OpenFgaClient(configuration)
            self._initialized = True
            logger.info(
                "OpenFGA SDK client initialized",
                extra={
                    "api_url": self.config.api_url,
                    "store_id": store_id,
                    "auth_enabled": credentials is not None,
                },
            )

    async def _lookup_store_by_name(self, store_name: str) -> str | None:
        """
        Look up an OpenFGA store by name.

        This enables dynamic store discovery when OPENFGA_STORE_NAME is set
        but OPENFGA_STORE_ID is not. The store is typically created by the
        openfga-seed container during test infrastructure startup.

        Args:
            store_name: Name of the store to look up

        Returns:
            Store ID if found, None otherwise
        """
        try:
            headers = {"Content-Type": "application/json"}
            if self.config.preshared_key:
                headers["Authorization"] = f"Bearer {self.config.preshared_key}"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.config.api_url}/stores",
                    headers=headers,
                )

                if response.status_code == 200:
                    stores = response.json().get("stores", [])
                    for store in stores:
                        if store.get("name") == store_name:
                            store_id: str = store["id"]
                            return store_id

                logger.debug(
                    "Store not found by name",
                    extra={"store_name": store_name, "status": response.status_code},
                )
                return None

        except Exception as e:
            logger.warning(f"Error looking up store by name: {e}")
            return None

    async def close(self) -> None:
        """
        Close the OpenFGA client and release resources.

        This properly closes the underlying aiohttp ClientSession to prevent
        "Unclosed client session" warnings during garbage collection.
        """
        if self._client is not None:
            try:
                # OpenFgaClient has a close method that closes the aiohttp session
                await self._client.close()
                logger.debug("OpenFGA SDK client closed")
            except Exception as e:
                logger.warning(f"Error closing OpenFGA client: {e}")
            finally:
                self._client = None
                self._initialized = False

    async def __aenter__(self) -> "OpenFGAClient":
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: type | None, exc_val: Exception | None, exc_tb: object | None) -> None:
        """Async context manager exit - ensures proper cleanup."""
        await self.close()

    @property
    def client(self) -> OpenFgaClient:
        """
        Get OpenFgaClient instance

        NOTE: This property should only be accessed from async methods
        after calling _ensure_initialized().
        """
        if self._client is None:
            msg = (
                "OpenFgaClient not initialized. "
                "Call await _ensure_initialized() before accessing client. "
                "This is a bug - all async methods should call _ensure_initialized()."
            )
            raise RuntimeError(msg)
        return self._client

    def _circuit_breaker_fallback(
        self, user: str, relation: str, object: str, context: dict[str, Any] | None = None, critical: bool = True
    ) -> bool:
        """
        Circuit breaker fallback for check_permission.

        Security policy:
        - critical=True (default): Fail-closed (deny access) when circuit opens
        - critical=False: Fail-open (allow access) when circuit opens

        Args:
            user: User identifier
            relation: Relation to check
            object: Object identifier
            context: Additional contextual data
            critical: If True, fail-closed; if False, fail-open

        Returns:
            False for critical resources (fail-closed), True for non-critical (fail-open)
        """
        if critical:
            logger.warning(
                "OpenFGA circuit breaker open: DENYING access to critical resource",
                extra={"user": user, "relation": relation, "object": object, "critical": critical},
            )
            return False  # Fail-closed for critical resources
        else:
            logger.warning(
                "OpenFGA circuit breaker open: ALLOWING access to non-critical resource",
                extra={"user": user, "relation": relation, "object": object, "critical": critical},
            )
            return True  # Fail-open for non-critical resources

    @circuit_breaker(
        name="openfga",
        fail_max=10,
        timeout=30,
        fallback=lambda self, *args, **kwargs: self._circuit_breaker_fallback(*args, **kwargs),
    )
    @retry_with_backoff()  # Uses global config (prod: 3 attempts, test: 1 attempt for fast tests)
    @with_timeout(operation_type="auth")
    @with_bulkhead(resource_type="openfga")
    async def check_permission(
        self, user: str, relation: str, object: str, context: dict[str, Any] | None = None, critical: bool = True
    ) -> bool:
        """
        Check if user has permission via relationship (with resilience protection).

        Protected by:
        - Circuit breaker: Fail-closed (deny) by default when OpenFGA is down (10 failures → open, 30s timeout)
        - Retry logic: Configurable via global resilience config (default: 3 attempts with exponential backoff)
        - Timeout: 5s timeout for auth operations
        - Bulkhead: Limit to 50 concurrent auth checks

        Args:
            user: User identifier (e.g., "user:123")
            relation: Relation to check (e.g., "can_read", "can_execute")
            object: Object identifier (e.g., "tool:chat", "resource:conversation_123")
            context: Additional contextual data for dynamic checks
            critical: If True (default), fail-closed when circuit opens; if False, fail-open

        Returns:
            True if user has permission, False otherwise
            When circuit breaker is open:
            - False if critical=True (fail-closed, secure by default)
            - True if critical=False (fail-open, prefer availability)

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open (uses fallback for return value)
            OpenFGATimeoutError: If check exceeds 5s timeout
            OpenFGAError: For other OpenFGA errors
        """
        await self._ensure_initialized()  # Lazy initialization
        with tracer.start_as_current_span("openfga.check") as span:
            span.set_attribute("user", user)
            span.set_attribute("relation", relation)
            span.set_attribute("object", object)

            try:
                request = ClientCheckRequest(user=user, relation=relation, object=object, contextual_tuples=[])

                response = await self.client.check(request)
                allowed = response.allowed

                span.set_attribute("allowed", allowed)

                logger.info(
                    "Permission check", extra={"user": user, "relation": relation, "object": object, "allowed": allowed}
                )

                # Track metrics
                if allowed:
                    metrics.successful_calls.add(1, {"operation": "check_permission"})
                else:
                    metrics.authz_failures.add(1, {"relation": relation})

                return allowed  # type: ignore[no-any-return]

            except Exception as e:
                error_msg = str(e).lower()

                if "timeout" in error_msg or "timed out" in error_msg:
                    raise OpenFGATimeoutError(
                        message=f"OpenFGA check timed out: {e}",
                        metadata={"user": user, "relation": relation, "object": object},
                        cause=e,
                    )
                elif "unavailable" in error_msg or "connection" in error_msg:
                    raise OpenFGAUnavailableError(
                        message=f"OpenFGA service unavailable: {e}",
                        metadata={"user": user, "relation": relation, "object": object},
                        cause=e,
                    )
                else:
                    logger.error(
                        f"OpenFGA check failed: {e}",
                        extra={"user": user, "relation": relation, "object": object},
                        exc_info=True,
                    )
                    span.record_exception(e)
                    metrics.failed_calls.add(1, {"operation": "check_permission"})

                    raise OpenFGAError(
                        message=f"OpenFGA error: {e}",
                        metadata={"user": user, "relation": relation, "object": object},
                        cause=e,
                    )

    @circuit_breaker(name="openfga")
    @retry_with_backoff()  # Uses global config (prod: 3 attempts, test: 1 attempt for fast tests)
    @with_timeout(operation_type="auth")
    async def write_tuples(self, tuples: list[dict[str, str]]) -> None:
        """
        Write relationship tuples to OpenFGA (with resilience protection).

        Protected by:
        - Circuit breaker: Fail fast if OpenFGA is down
        - Retry logic: Configurable via global resilience config (default: 3 attempts, writes are idempotent)
        - Timeout: 5s timeout for auth operations

        Args:
            tuples: List of relationship tuples
                   Each tuple: {"user": "user:123", "relation": "member", "object": "org:acme"}

        Raises:
            CircuitBreakerOpenError: If circuit breaker is open
            OpenFGAError: For OpenFGA errors
        """
        await self._ensure_initialized()  # Lazy initialization
        with tracer.start_as_current_span("openfga.write_tuples"):
            try:
                client_tuples = [ClientTuple(user=t["user"], relation=t["relation"], object=t["object"]) for t in tuples]

                request = ClientWriteRequest(writes=client_tuples)
                await self.client.write(request)

                logger.info("Tuples written to OpenFGA", extra={"count": len(tuples)})

                metrics.successful_calls.add(1, {"operation": "write_tuples"})

            except Exception as e:
                logger.error(f"Failed to write tuples: {e}", exc_info=True)
                metrics.failed_calls.add(1, {"operation": "write_tuples"})

                raise OpenFGAError(
                    message=f"Failed to write tuples: {e}",
                    metadata={"tuple_count": len(tuples)},
                    cause=e,
                )

    async def delete_tuples(self, tuples: list[dict[str, str]]) -> None:
        """
        Delete relationship tuples from OpenFGA

        Args:
            tuples: List of relationship tuples to delete
        """
        await self._ensure_initialized()  # Lazy initialization
        with tracer.start_as_current_span("openfga.delete_tuples"):
            try:
                client_tuples = [ClientTuple(user=t["user"], relation=t["relation"], object=t["object"]) for t in tuples]

                request = ClientWriteRequest(deletes=client_tuples)
                await self.client.write(request)

                logger.info("Tuples deleted from OpenFGA", extra={"count": len(tuples)})

            except Exception as e:
                logger.error(f"Failed to delete tuples: {e}", exc_info=True)
                raise

    async def delete_tuples_for_object(self, object_id: str) -> None:
        """
        Delete all tuples related to an object (helper for cleanup operations).

        This implements proper cleanup for resource deletion, ensuring no orphaned
        authorization tuples remain in OpenFGA (important for GDPR compliance).

        Args:
            object_id: Object identifier (e.g., "service_principal:batch-job")

        Implementation:
        1. Extracts object type from object_id
        2. Gets model definition to find all available relations
        3. Expands each relation to find all users with permissions
        4. Deletes tuples in batches (100 per batch) with retry logic
        """
        await self._ensure_initialized()  # Lazy initialization
        logger.info(f"Deleting tuples for object: {object_id}")

        # Extract object type from object_id (e.g., "service_principal:batch-job" -> "service_principal")
        object_type = object_id.split(":")[0] if ":" in object_id else object_id

        # Get authorization model to determine available relations for this type
        model_def = OpenFGAAuthorizationModel.get_model_definition()
        type_defs = model_def.get("type_definitions", [])

        # Find the type definition for this object type
        type_def = next((t for t in type_defs if t.get("type") == object_type), None)

        if not type_def:
            logger.warning(f"Type '{object_type}' not found in authorization model, skipping cleanup")
            return

        # Get all relations for this type
        relations = type_def.get("relations", {})
        if not relations:
            logger.info(f"No relations defined for type '{object_type}', nothing to clean up")
            return

        # Collect all tuples to delete across all relations
        tuples_to_delete: list[dict[str, str]] = []

        for relation_name in relations:
            try:
                # Expand relation to find all users with this permission
                expansion = await self.expand_relation(relation=relation_name, object=object_id)

                # Extract users from expansion tree
                users = _extract_users_from_expansion(expansion)

                # Build tuples for deletion
                for user in users:
                    tuples_to_delete.append({"user": user, "relation": relation_name, "object": object_id})

                logger.debug(
                    f"Found {len(users)} users with '{relation_name}' relation to {object_id}",
                    extra={"object_id": object_id, "relation": relation_name, "user_count": len(users)},
                )

            except Exception as e:
                # Log but continue with other relations
                logger.warning(
                    f"Error expanding relation '{relation_name}' for {object_id}: {e}",
                    extra={"object_id": object_id, "relation": relation_name, "error": str(e)},
                )

        # Delete tuples in batches (100 per batch as per user requirement)
        if not tuples_to_delete:
            logger.info(f"No tuples found for {object_id}, nothing to delete")
            return

        batch_size = 100
        total_batches = (len(tuples_to_delete) + batch_size - 1) // batch_size

        logger.info(
            f"Deleting {len(tuples_to_delete)} tuples for {object_id} in {total_batches} batch(es)",
            extra={"object_id": object_id, "tuple_count": len(tuples_to_delete), "batch_count": total_batches},
        )

        for i in range(0, len(tuples_to_delete), batch_size):
            batch = tuples_to_delete[i : i + batch_size]
            batch_num = i // batch_size + 1

            try:
                await self.delete_tuples(batch)
                logger.info(
                    f"Deleted batch {batch_num}/{total_batches} ({len(batch)} tuples)",
                    extra={"object_id": object_id, "batch": batch_num, "tuples_in_batch": len(batch)},
                )
            except Exception as e:
                logger.error(
                    f"Failed to delete batch {batch_num}/{total_batches} for {object_id}: {e}",
                    extra={"object_id": object_id, "batch": batch_num, "error": str(e)},
                )
                # Note: Continue with next batch even if one fails
                # This ensures partial cleanup is better than no cleanup

    async def list_objects(self, user: str, relation: str, object_type: str) -> list[str]:
        """
        List all objects of a type that user has relation to

        Args:
            user: User identifier
            relation: Relation to check
            object_type: Type of objects to list (e.g., "tool", "conversation")

        Returns:
            List of object identifiers
        """
        await self._ensure_initialized()  # Lazy initialization
        with tracer.start_as_current_span("openfga.list_objects"):
            try:
                response = await self.client.list_objects(user=user, relation=relation, type=object_type)

                objects = response.objects or []

                logger.info(
                    "Objects listed",
                    extra={"user": user, "relation": relation, "object_type": object_type, "count": len(objects)},
                )

                return objects

            except Exception as e:
                logger.error(f"Failed to list objects: {e}", exc_info=True)
                raise

    async def expand_relation(self, relation: str, object: str) -> dict[str, Any]:
        """
        Expand a relation to see all users with access

        Args:
            relation: Relation to expand
            object: Object identifier

        Returns:
            Tree structure showing all users with access
        """
        await self._ensure_initialized()  # Lazy initialization
        with tracer.start_as_current_span("openfga.expand"):
            try:
                response = await self.client.expand(relation=relation, object=object)

                return response.tree.model_dump() if response.tree else {}

            except Exception as e:
                logger.error(f"Failed to expand relation: {e}", exc_info=True)
                raise


def _extract_users_from_expansion(expansion: dict[str, Any]) -> list[str]:
    """
    Extract all user IDs from an OpenFGA expansion tree.

    Recursively traverses the expansion tree to find all leaf nodes containing users.

    Args:
        expansion: Expansion tree from OpenFGA expand() call

    Returns:
        List of user IDs (e.g., ["user:alice", "user:bob"])

    Example expansion structures:
        Simple leaf: {"leaf": {"users": {"users": ["user:alice"]}}}
        Union: {"union": {"nodes": [{"leaf": ...}, {"leaf": ...}]}}
        Empty: {}
    """
    if not expansion:
        return []

    users: list[str] = []

    # Handle leaf nodes (direct user lists)
    if "leaf" in expansion:
        leaf = expansion["leaf"]
        if isinstance(leaf, dict) and "users" in leaf:
            user_data = leaf["users"]
            if isinstance(user_data, dict) and "users" in user_data:
                user_list = user_data["users"]
                if isinstance(user_list, list):
                    users.extend(user_list)

    # Handle union nodes (multiple children)
    if "union" in expansion:
        union = expansion["union"]
        if isinstance(union, dict) and "nodes" in union:
            nodes = union["nodes"]
            if isinstance(nodes, list):
                for node in nodes:
                    users.extend(_extract_users_from_expansion(node))

    # Handle intersection nodes (all children must be true)
    if "intersection" in expansion:
        intersection = expansion["intersection"]
        if isinstance(intersection, dict) and "nodes" in intersection:
            nodes = intersection["nodes"]
            if isinstance(nodes, list):
                for node in nodes:
                    users.extend(_extract_users_from_expansion(node))

    # Handle difference nodes (exclusion)
    if "difference" in expansion:
        difference = expansion["difference"]
        if isinstance(difference, dict):
            # Base users
            if "base" in difference:
                users.extend(_extract_users_from_expansion(difference["base"]))
            # Subtract users are excluded, so we don't add them

    return list(set(users))  # Deduplicate


class OpenFGAAuthorizationModel:
    """
    Authorization model loader for the agent system.

    Loads model definition from configuration file (config/openfga/model.json).
    This separates configuration from code, following best practices.

    Types defined in the model:
    - user: Individual users
    - organization: Organizations that users belong to
    - tool: AI tools (chat, search, etc.)
    - conversation: Conversation threads
    - role: Roles that grant permissions
    - service_principal: Service accounts for machine-to-machine auth (ADR-0033)
    - vector_store: Qdrant vector database collections (ADR-0068)
    - authz: OpenFGA Playground access control (ADR-0068)
    """

    # Default model file path (relative to project root)
    DEFAULT_MODEL_PATH = "config/openfga/model.json"

    # Cache for loaded model
    _cached_model: dict[str, Any] | None = None

    @classmethod
    def get_model_definition(cls, model_path: str | Path | None = None) -> dict[str, Any]:
        """
        Load the authorization model from configuration file.

        Model is cached after first load to avoid repeated file I/O.

        Args:
            model_path: Path to model JSON file. If None, uses DEFAULT_MODEL_PATH.
                       Can be overridden via OPENFGA_MODEL_PATH environment variable.

        Returns:
            Authorization model definition as dict.

        Raises:
            FileNotFoundError: If model file does not exist.
            json.JSONDecodeError: If model file is not valid JSON.
        """
        # Return cached model if available
        if cls._cached_model is not None:
            return cls._cached_model

        # Determine model path
        if model_path is None:
            model_path = os.getenv("OPENFGA_MODEL_PATH", cls.DEFAULT_MODEL_PATH)

        model_path = Path(model_path)

        # Try multiple locations for the model file
        search_paths = [
            model_path,  # Absolute or relative as provided
            Path(__file__).parent.parent.parent.parent / model_path,  # From project root
            Path.cwd() / model_path,  # From current working directory
        ]

        for path in search_paths:
            if path.exists():
                logger.info(f"Loading OpenFGA model from: {path}")
                with open(path) as f:
                    cls._cached_model = json.load(f)
                return cls._cached_model

        # If no file found, log available search paths and raise error
        logger.error(
            f"OpenFGA model file not found. Searched: {[str(p) for p in search_paths]}",
            extra={"search_paths": [str(p) for p in search_paths]},
        )
        raise FileNotFoundError(
            f"OpenFGA model file not found at {model_path}. Searched paths: {[str(p) for p in search_paths]}"
        )

    @classmethod
    def clear_cache(cls) -> None:
        """Clear the cached model (useful for testing)."""
        cls._cached_model = None

    @classmethod
    def get_type_names(cls) -> list[str]:
        """Get list of type names defined in the model."""
        model = cls.get_model_definition()
        return [t.get("type", "") for t in model.get("type_definitions", [])]

    @classmethod
    def get_relations_for_type(cls, type_name: str) -> list[str]:
        """Get list of relations defined for a specific type."""
        model = cls.get_model_definition()
        for type_def in model.get("type_definitions", []):
            if type_def.get("type") == type_name:
                return list(type_def.get("relations", {}).keys())
        return []


async def initialize_openfga_store(client: OpenFGAClient) -> str:
    """
    Initialize OpenFGA store with authorization model

    Args:
        client: OpenFGA client instance

    Returns:
        Store ID
    """
    await client._ensure_initialized()  # Lazy initialization
    with tracer.start_as_current_span("openfga.initialize_store"):
        try:
            # Create store
            store = await client.client.create_store(body={"name": "langgraph-agent-store"})
            store_id = store.id

            logger.info("OpenFGA store created", extra={"store_id": store_id})

            # Update client configuration
            client.store_id = store_id
            client.client.store_id = store_id

            # Write authorization model
            model_def = OpenFGAAuthorizationModel.get_model_definition()
            model_response = await client.client.write_authorization_model(body=model_def)
            model_id = model_response.authorization_model_id

            logger.info("OpenFGA authorization model created", extra={"model_id": model_id})

            # Update client with model ID
            client.model_id = model_id
            client.client.authorization_model_id = model_id

            return store_id  # type: ignore[no-any-return]

        except Exception as e:
            logger.error(f"Failed to initialize OpenFGA store: {e}", exc_info=True)
            raise


def load_sample_tuples(tuples_path: str | Path | None = None) -> list[dict[str, str]]:
    """
    Load sample relationship tuples from config file.

    This function loads tuples from config/openfga/sample-tuples.json,
    which is the single source of truth for test user permissions.

    Args:
        tuples_path: Path to tuples config file. If None, uses default path
                    or OPENFGA_TUPLES_PATH environment variable.

    Returns:
        List of tuple dicts with user, relation, object keys.

    Raises:
        FileNotFoundError: If tuples config file does not exist.
        json.JSONDecodeError: If tuples config file is not valid JSON.
    """
    # Determine tuples path
    if tuples_path is None:
        tuples_path = os.getenv("OPENFGA_TUPLES_PATH", "config/openfga/sample-tuples.json")

    tuples_path = Path(tuples_path)

    # Try multiple locations for the tuples file
    search_paths = [
        tuples_path,  # Absolute or relative as provided
        Path(__file__).parent.parent.parent.parent / tuples_path,  # From project root
        Path.cwd() / tuples_path,  # From current working directory
    ]

    for path in search_paths:
        if path.exists():
            logger.info(f"Loading OpenFGA sample tuples from: {path}")
            with open(path) as f:
                config = json.load(f)

            raw_tuples = config.get("tuples", [])

            # Filter out _comment keys and keep only user/relation/object
            tuples = []
            for t in raw_tuples:
                tuples.append(
                    {
                        "user": t["user"],
                        "relation": t["relation"],
                        "object": t["object"],
                    }
                )

            return tuples

    # If no file found, log available search paths and raise error
    logger.error(
        f"OpenFGA sample tuples file not found. Searched: {[str(p) for p in search_paths]}",
        extra={"search_paths": [str(p) for p in search_paths]},
    )
    raise FileNotFoundError(
        f"OpenFGA sample tuples file not found at {tuples_path}. Searched paths: {[str(p) for p in search_paths]}"
    )


async def seed_sample_data(client: OpenFGAClient, tuples_path: str | Path | None = None) -> None:
    """
    Seed sample relationship data for testing from config file.

    This function loads tuples from config/openfga/sample-tuples.json
    (single source of truth) and writes them to OpenFGA.

    Args:
        client: OpenFGA client instance.
        tuples_path: Optional path to tuples config file.

    Raises:
        FileNotFoundError: If tuples config file does not exist.
    """
    sample_tuples = load_sample_tuples(tuples_path)

    await client.write_tuples(sample_tuples)
    logger.info("Sample OpenFGA data seeded", extra={"tuple_count": len(sample_tuples)})


async def check_permission(
    user_id: str,
    relation: str,
    object: str,
    openfga_client: OpenFGAClient,
) -> bool:
    """
    Check if user has permission with support for service principal inheritance.

    This function implements permission checking with acts_as relationship support (ADR-0039).
    Service principals (user_id starting with "service:") can inherit permissions from
    associated users via the acts_as relationship.

    Args:
        user_id: User or service principal ID (e.g., "user:alice" or "service:batch-job")
        relation: Relation to check (e.g., "viewer", "editor", "executor")
        object: Object to check permission on (e.g., "conversation:thread1")
        openfga_client: OpenFGA client instance

    Returns:
        True if user/service has permission (directly or inherited), False otherwise

    Example:
        >>> # Direct permission check
        >>> allowed = await check_permission("user:alice", "viewer", "conversation:1", openfga)
        >>> # Service principal with inherited permission
        >>> allowed = await check_permission("service:batch-job", "viewer", "conversation:1", openfga)
    """
    # 1. Direct permission check
    has_direct_permission = await openfga_client.check_permission(
        user=user_id,
        relation=relation,
        object=object,
    )

    if has_direct_permission:
        return True

    # 2. If service principal, check inherited permissions via acts_as
    if user_id.startswith("service:"):
        # List all users this service principal acts as
        try:
            # Query for acts_as relationships
            associated_users = await openfga_client.list_objects(
                user=user_id,
                relation="acts_as",
                object_type="user",
            )

            # Check if any associated user has the permission
            for associated_user in associated_users:
                user_has_permission = await openfga_client.check_permission(
                    user=associated_user,
                    relation=relation,
                    object=object,
                )

                if user_has_permission:
                    # Log inherited access for audit trail
                    logger.info(
                        f"{user_id} accessed {object} via inherited permission from {associated_user}",
                        extra={
                            "service_principal": user_id,
                            "associated_user": associated_user,
                            "resource": object,
                            "relation": relation,
                            "permission_type": "inherited",
                        },
                    )
                    return True

        except Exception as e:
            logger.warning(
                f"Error checking acts_as relationships for {user_id}: {e}",
                exc_info=True,
            )
            # Continue with denial if acts_as check fails

    return False
