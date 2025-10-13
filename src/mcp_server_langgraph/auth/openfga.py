"""
OpenFGA integration for fine-grained relationship-based access control
"""

from typing import Any, Dict, List, Optional

from openfga_sdk import ClientConfiguration, OpenFgaClient
from openfga_sdk.client.models import ClientCheckRequest, ClientTuple, ClientWriteRequest
from pydantic import BaseModel, ConfigDict, Field

from mcp_server_langgraph.observability.telemetry import logger, metrics, tracer


class OpenFGAConfig(BaseModel):
    """
    Type-safe OpenFGA configuration

    Configuration for OpenFGA authorization service.
    """

    api_url: str = Field(
        default="http://localhost:8080",
        description="OpenFGA server API URL"
    )
    store_id: Optional[str] = Field(
        default=None,
        description="Authorization store ID"
    )
    model_id: Optional[str] = Field(
        default=None,
        description="Authorization model ID"
    )

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "example": {
                "api_url": "http://localhost:8080",
                "store_id": "01H...",
                "model_id": "01H..."
            }
        }
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for backward compatibility"""
        return self.model_dump(exclude_none=True)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OpenFGAConfig":
        """Create OpenFGAConfig from dictionary"""
        return cls(**data)


class OpenFGAClient:
    """
    OpenFGA client for relationship-based authorization

    Implements Zanzibar-style authorization with fine-grained permissions
    based on relationships between users, resources, and roles.
    """

    def __init__(self, config: Optional[OpenFGAConfig] = None, api_url: Optional[str] = None, store_id: Optional[str] = None, model_id: Optional[str] = None):
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
            config = OpenFGAConfig(
                api_url=api_url or "http://localhost:8080",
                store_id=store_id,
                model_id=model_id
            )

        self.config = config
        self.api_url = config.api_url
        self.store_id = config.store_id
        self.model_id = config.model_id

        # Configure client
        configuration = ClientConfiguration(
            api_url=config.api_url,
            store_id=config.store_id,
            authorization_model_id=config.model_id
        )

        self.client = OpenFgaClient(configuration)
        logger.info("OpenFGA client initialized", extra={"api_url": config.api_url})

    async def check_permission(self, user: str, relation: str, object: str, context: Optional[Dict[str, Any]] = None) -> bool:
        """
        Check if user has permission via relationship

        Args:
            user: User identifier (e.g., "user:123")
            relation: Relation to check (e.g., "can_read", "can_execute")
            object: Object identifier (e.g., "tool:chat", "resource:conversation_123")
            context: Additional contextual data for dynamic checks

        Returns:
            True if user has permission, False otherwise
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

                return allowed

            except Exception as e:
                logger.error(
                    f"OpenFGA check failed: {e}", extra={"user": user, "relation": relation, "object": object}, exc_info=True
                )
                span.record_exception(e)
                metrics.failed_calls.add(1, {"operation": "check_permission"})
                raise

    async def write_tuples(self, tuples: List[Dict[str, str]]) -> None:
        """
        Write relationship tuples to OpenFGA

        Args:
            tuples: List of relationship tuples
                   Each tuple: {"user": "user:123", "relation": "member", "object": "org:acme"}
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
                raise

    async def delete_tuples(self, tuples: List[Dict[str, str]]) -> None:
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

    async def list_objects(self, user: str, relation: str, object_type: str) -> List[str]:
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

    async def expand_relation(self, relation: str, object: str) -> Dict[str, Any]:
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


class OpenFGAAuthorizationModel:
    """
    Authorization model definition for the agent system

    Defines types, relations, and permissions for the system.
    """

    @staticmethod
    def get_model_definition() -> Dict[str, Any]:
        """
        Get the authorization model definition

        This defines:
        - user: Individual users
        - organization: Organizations that users belong to
        - tool: AI tools (chat, search, etc.)
        - conversation: Conversation threads
        - role: Roles that grant permissions

        Relations:
        - member: User is a member of organization
        - owner: User owns a resource
        - viewer: User can view a resource
        - executor: User can execute a tool
        - admin: User has admin privileges
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

            return store_id

        except Exception as e:
            logger.error(f"Failed to initialize OpenFGA store: {e}", exc_info=True)
            raise


async def seed_sample_data(client: OpenFGAClient):
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
