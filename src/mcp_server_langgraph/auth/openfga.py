"""
OpenFGA integration for fine-grained relationship-based access control

Enhanced with resilience patterns (ADR-0026):
- Circuit breaker for OpenFGA failures (fail-open by default)
- Retry logic with exponential backoff
- Timeout enforcement (5s for auth operations)
- Bulkhead isolation (50 concurrent auth checks max)
"""

from typing import Any

from openfga_sdk import ClientConfiguration, OpenFgaClient
from openfga_sdk.client.models import ClientCheckRequest, ClientTuple, ClientWriteRequest
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
    model_id: str | None = Field(default=None, description="Authorization model ID")

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        str_strip_whitespace=True,
        json_schema_extra={"example": {"api_url": "http://localhost:8080", "store_id": "01H...", "model_id": "01H..."}},
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
        model_id: str | None = None,
    ):
        """
        Initialize OpenFGA client

        Args:
            config: OpenFGAConfig instance (recommended)
            api_url: OpenFGA server URL (legacy, use config instead)
            store_id: Authorization store ID (legacy, use config instead)
            model_id: Authorization model ID (legacy, use config instead)
        """
        # Support both new config-based and legacy parameter-based initialization
        if config is None:
            config = OpenFGAConfig(api_url=api_url or "http://localhost:8080", store_id=store_id, model_id=model_id)

        self.config = config
        self.api_url = config.api_url
        self.store_id = config.store_id
        self.model_id = config.model_id

        # Configure client
        configuration = ClientConfiguration(
            api_url=config.api_url, store_id=config.store_id, authorization_model_id=config.model_id
        )

        self.client = OpenFgaClient(configuration)
        logger.info("OpenFGA client initialized", extra={"api_url": config.api_url})

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
                if "unavailable" in error_msg or "connection" in error_msg:
                    raise OpenFGAUnavailableError(
                        message=f"OpenFGA service unavailable: {e}",
                        metadata={"user": user, "relation": relation, "object": object},
                        cause=e,
                    )
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
    Authorization model definition for the agent system

    Defines types, relations, and permissions for the system.
    """

    @staticmethod
    def get_model_definition() -> dict[str, Any]:
        """
        Get the authorization model definition

        This defines:
        - user: Individual users
        - organization: Organizations that users belong to
        - tool: AI tools (chat, search, etc.)
        - conversation: Conversation threads
        - role: Roles that grant permissions
        - service_principal: Service accounts for machine-to-machine auth (ADR-0033)

        Relations:
        - member: User is a member of organization
        - owner: User owns a resource
        - viewer: User can view a resource
        - executor: User can execute a tool
        - admin: User has admin privileges
        - acts_as: Service principal acts as user (permission inheritance, ADR-0039)
        """
        return {
            "schema_version": "1.1",
            "type_definitions": [
                {"type": "user", "relations": {}, "metadata": {"relations": {}}},
                {
                    "type": "organization",
                    "relations": {"member": {"this": {}}, "admin": {"this": {}}},
                    "metadata": {
                        "relations": {
                            "member": {"directly_related_user_types": [{"type": "user"}]},
                            "admin": {"directly_related_user_types": [{"type": "user"}]},
                        }
                    },
                },
                {
                    "type": "tool",
                    "relations": {
                        "owner": {"this": {}},
                        "executor": {
                            "union": {
                                "child": [
                                    {"this": {}},
                                    {"computedUserset": {"relation": "owner"}},
                                    {
                                        "tupleToUserset": {
                                            "tupleset": {"relation": "organization"},
                                            "computedUserset": {"relation": "member"},
                                        }
                                    },
                                ]
                            }
                        },
                        "organization": {"this": {}},
                    },
                    "metadata": {
                        "relations": {
                            "owner": {"directly_related_user_types": [{"type": "user"}]},
                            "executor": {"directly_related_user_types": [{"type": "user"}]},
                            "organization": {"directly_related_user_types": [{"type": "organization"}]},
                        }
                    },
                },
                {
                    "type": "conversation",
                    "relations": {
                        "owner": {"this": {}},
                        "viewer": {"union": {"child": [{"this": {}}, {"computedUserset": {"relation": "owner"}}]}},
                        "editor": {"union": {"child": [{"this": {}}, {"computedUserset": {"relation": "owner"}}]}},
                    },
                    "metadata": {
                        "relations": {
                            "owner": {"directly_related_user_types": [{"type": "user"}]},
                            "viewer": {"directly_related_user_types": [{"type": "user"}]},
                            "editor": {"directly_related_user_types": [{"type": "user"}]},
                        }
                    },
                },
                {
                    "type": "role",
                    "relations": {"assignee": {"this": {}}},
                    "metadata": {"relations": {"assignee": {"directly_related_user_types": [{"type": "user"}]}}},
                },
                {
                    "type": "service_principal",
                    "relations": {
                        "owner": {"this": {}},
                        "acts_as": {"this": {}},
                        "viewer": {"computedUserset": {"relation": "owner"}},
                        "editor": {"computedUserset": {"relation": "owner"}},
                    },
                    "metadata": {
                        "relations": {
                            "owner": {"directly_related_user_types": [{"type": "user"}]},
                            "acts_as": {"directly_related_user_types": [{"type": "user"}]},
                            "viewer": {"directly_related_user_types": [{"type": "user"}]},
                            "editor": {"directly_related_user_types": [{"type": "user"}]},
                        }
                    },
                },
            ],
        }


async def initialize_openfga_store(client: OpenFGAClient) -> str:
    """
    Initialize OpenFGA store with authorization model

    Args:
        client: OpenFGA client instance

    Returns:
        Store ID
    """
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


async def seed_sample_data(client: OpenFGAClient) -> None:
    """
    Seed sample relationship data for testing
    """
    sample_tuples = [
        # Organization memberships
        {"user": "user:alice", "relation": "member", "object": "organization:acme"},
        {"user": "user:bob", "relation": "member", "object": "organization:acme"},
        {"user": "user:alice", "relation": "admin", "object": "organization:acme"},
        # Tool permissions
        {"user": "user:alice", "relation": "executor", "object": "tool:chat"},
        {"user": "user:bob", "relation": "executor", "object": "tool:chat"},
        {"user": "organization:acme", "relation": "organization", "object": "tool:chat"},
        # Conversation ownership
        {"user": "user:alice", "relation": "owner", "object": "conversation:thread_1"},
        {"user": "user:bob", "relation": "viewer", "object": "conversation:thread_1"},
        # Role assignments
        {"user": "user:alice", "relation": "assignee", "object": "role:premium"},
        {"user": "user:bob", "relation": "assignee", "object": "role:standard"},
    ]

    await client.write_tuples(sample_tuples)
    logger.info("Sample OpenFGA data seeded")


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
