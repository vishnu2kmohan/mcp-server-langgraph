"""
Advanced Role Mapping Engine

Provides flexible, configurable mapping of Keycloak roles/groups to OpenFGA tuples.
Supports:
- Simple role mappings
- Group pattern matching (regex)
- Conditional mappings based on attributes
- Role hierarchies
- Custom transformation rules
"""

import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

from mcp_server_langgraph.auth.keycloak import KeycloakUser
from mcp_server_langgraph.observability.telemetry import logger


# ============================================================================
# Pydantic Models for Type-Safe Role Mapping Configuration
# ============================================================================


class OpenFGATuple(BaseModel):
    """
    Type-safe OpenFGA tuple structure

    Represents a relationship tuple in OpenFGA.
    """

    user: str = Field(..., description="User ID (e.g., 'user:alice')")
    relation: str = Field(..., description="Relation type (e.g., 'member', 'admin')")
    object: str = Field(..., description="Object identifier (e.g., 'workspace:engineering')")

    model_config = ConfigDict(
        frozen=False,
        validate_assignment=True,
        str_strip_whitespace=True,
        json_schema_extra={"example": {"user": "user:alice", "relation": "member", "object": "workspace:engineering"}},
    )

    def to_dict(self) -> dict[str, str]:
        """Convert to dictionary for backward compatibility"""
        return self.model_dump()

    @classmethod
    def from_dict(cls, data: dict[str, str]) -> "OpenFGATuple":
        """Create OpenFGATuple from dictionary"""
        return cls(**data)


class SimpleRoleMappingConfig(BaseModel):
    """
    Configuration for simple role mapping
    """

    keycloak_role: str = Field(..., description="Keycloak role name")
    realm: bool = Field(True, description="Whether this is a realm role (vs client role)")
    openfga_relation: str = Field(..., description="OpenFGA relation to assign")
    openfga_object: str = Field(..., description="OpenFGA object to relate to")

    model_config = ConfigDict(frozen=False, validate_assignment=True, str_strip_whitespace=True)


class GroupMappingConfig(BaseModel):
    """
    Configuration for group pattern mapping
    """

    pattern: str = Field(..., description="Regex pattern to match groups")
    openfga_relation: str = Field(..., description="OpenFGA relation to assign")
    openfga_object_template: str = Field(..., description="Template for object name (e.g., 'workspace:{group_name}')")

    model_config = ConfigDict(frozen=False, validate_assignment=True, str_strip_whitespace=True)


class ConditionConfig(BaseModel):
    """
    Configuration for conditional mapping condition
    """

    attribute: str = Field(..., description="User attribute to check")
    operator: str = Field("==", description="Comparison operator (==, !=, in, >=, <=)")
    value: Any = Field(..., description="Value to compare against")

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, v: str) -> str:
        """Validate operator is supported"""
        supported = {"==", "!=", "in", ">=", "<="}
        if v not in supported:
            raise ValueError(f"Operator must be one of {supported}, got: {v}")
        return v

    model_config = ConfigDict(frozen=False, validate_assignment=True, str_strip_whitespace=True)


class ConditionalMappingConfig(BaseModel):
    """
    Configuration for conditional mapping
    """

    condition: ConditionConfig = Field(..., description="Condition to evaluate")
    openfga_tuples: list[dict[str, str]] = Field(..., description="Tuples to create if condition is met")

    model_config = ConfigDict(frozen=False, validate_assignment=True)


class MappingRule:
    """Base class for mapping rules"""

    def __init__(self, config: dict[str, Any]) -> None:
        self.config = config

    def applies_to(self, user: KeycloakUser) -> bool:
        """Check if this rule applies to the user"""
        raise NotImplementedError

    def generate_tuples(self, user: KeycloakUser) -> list[dict[str, str]]:
        """Generate OpenFGA tuples for this rule"""
        raise NotImplementedError


class SimpleRoleMapping(MappingRule):
    """Simple 1:1 role to tuple mapping"""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        # Validate and store config as Pydantic model
        self.mapping_config = SimpleRoleMappingConfig(**config)
        self.keycloak_role = self.mapping_config.keycloak_role
        self.is_realm_role = self.mapping_config.realm
        self.openfga_relation = self.mapping_config.openfga_relation
        self.openfga_object = self.mapping_config.openfga_object

    def applies_to(self, user: KeycloakUser) -> bool:
        """Check if user has the role"""
        if self.is_realm_role:
            return self.keycloak_role in user.realm_roles
        # Check client roles
        return any(self.keycloak_role in client_roles for client_roles in user.client_roles.values())

    def generate_tuples(self, user: KeycloakUser) -> list[dict[str, str]]:
        """Generate tuple if role matches"""
        if not self.applies_to(user):
            return []

        # Create Pydantic tuple, then convert to dict for backward compatibility
        tuple_obj = OpenFGATuple(user=user.user_id, relation=self.openfga_relation, object=self.openfga_object)
        return [tuple_obj.to_dict()]


class GroupMapping(MappingRule):
    """Pattern-based group mapping with regex"""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        # Validate and store config as Pydantic model
        self.mapping_config = GroupMappingConfig(**config)
        self.pattern = re.compile(self.mapping_config.pattern)
        self.openfga_relation = self.mapping_config.openfga_relation
        self.openfga_object_template = self.mapping_config.openfga_object_template

    def applies_to(self, user: KeycloakUser) -> bool:
        """Check if user has any matching groups"""
        return any(self.pattern.match(group) for group in user.groups)

    def generate_tuples(self, user: KeycloakUser) -> list[dict[str, str]]:
        """Generate tuples for all matching groups"""
        tuples = []

        for group in user.groups:
            match = self.pattern.match(group)
            if match:
                # Extract group name from pattern
                group_name = match.groups()[-1] if match.groups() else group.strip("/").split("/")[-1]

                # Apply template
                openfga_object = self.openfga_object_template.format(group_name=group_name)

                # Create Pydantic tuple, then convert to dict
                tuple_obj = OpenFGATuple(user=user.user_id, relation=self.openfga_relation, object=openfga_object)
                tuples.append(tuple_obj.to_dict())

        return tuples


class ConditionalMapping(MappingRule):
    """Conditional mapping based on user attributes"""

    def __init__(self, config: dict[str, Any]) -> None:
        super().__init__(config)
        # Validate and store config as Pydantic model
        self.mapping_config = ConditionalMappingConfig(**config)
        self.condition = self.mapping_config.condition
        self.attribute = self.condition.attribute
        self.operator = self.condition.operator
        self.value = self.condition.value
        self.openfga_tuples = self.mapping_config.openfga_tuples

    def applies_to(self, user: KeycloakUser) -> bool:
        """Check if condition is met"""
        attr_value = user.attributes.get(self.attribute)

        if attr_value is None:
            return False

        # Handle list attributes
        if isinstance(attr_value, list):
            attr_value = attr_value[0] if attr_value else None

        if attr_value is None:
            return False

        # Apply operator (already validated by Pydantic)
        if self.operator == "==":
            return attr_value == self.value  # type: ignore[no-any-return]
        if self.operator == "!=":
            return attr_value != self.value  # type: ignore[no-any-return]
        if self.operator == "in":
            return attr_value in self.value
        if self.operator == ">=":
            return float(attr_value) >= float(self.value)
        if self.operator == "<=":
            return float(attr_value) <= float(self.value)
        logger.warning(f"Unknown operator: {self.operator}")
        return False

    def generate_tuples(self, user: KeycloakUser) -> list[dict[str, str]]:
        """Generate tuples if condition is met"""
        if not self.applies_to(user):
            return []

        tuples = []
        for tuple_config in self.openfga_tuples:
            # Create Pydantic tuple, then convert to dict
            tuple_obj = OpenFGATuple(user=user.user_id, relation=tuple_config["relation"], object=tuple_config["object"])
            tuples.append(tuple_obj.to_dict())

        return tuples


class RoleMapper:
    """
    Advanced role mapping engine

    Loads configuration from YAML and applies mapping rules to generate
    OpenFGA tuples from Keycloak user data.
    """

    def __init__(self, config_path: str | None = None, config_dict: dict[str, Any] | None = None) -> None:
        """
        Initialize role mapper

        Args:
            config_path: Path to YAML configuration file
            config_dict: Configuration dictionary (alternative to file)
        """
        self.rules: list[MappingRule] = []
        self.hierarchies: dict[str, list[str]] = {}

        # Load configuration
        if config_path:
            self.load_from_file(config_path)
        elif config_dict:
            self.load_from_dict(config_dict)
        else:
            # Use default hardcoded mapping for backward compatibility
            self._load_default_config()

        logger.info(f"RoleMapper initialized with {len(self.rules)} rules")

    def load_from_file(self, config_path: str) -> None:
        """Load configuration from YAML file"""
        path = Path(config_path)

        if not path.exists():
            logger.warning(f"Role mapping config not found: {config_path}, using defaults")
            self._load_default_config()
            return

        try:
            with open(path) as f:
                config = yaml.safe_load(f)

            self.load_from_dict(config)
            logger.info(f"Loaded role mapping config from {config_path}")

        except Exception as e:
            logger.error(f"Failed to load role mapping config: {e}", exc_info=True)
            self._load_default_config()

    def load_from_dict(self, config: dict[str, Any]) -> None:
        """Load configuration from dictionary"""
        self.rules = []

        # Load simple mappings
        for mapping in config.get("simple_mappings", []):
            self.rules.append(SimpleRoleMapping(mapping))

        # Load group mappings
        for mapping in config.get("group_mappings", []):
            self.rules.append(GroupMapping(mapping))

        # Load conditional mappings
        for mapping in config.get("conditional_mappings", []):
            self.rules.append(ConditionalMapping(mapping))

        # Load role hierarchies
        self.hierarchies = config.get("hierarchies", {})

        logger.info(f"Loaded {len(self.rules)} mapping rules")

    def _load_default_config(self) -> None:
        """Load default hardcoded mapping for backward compatibility"""
        default_config = {
            "simple_mappings": [
                {"keycloak_role": "admin", "realm": True, "openfga_relation": "admin", "openfga_object": "system:global"},
                {"keycloak_role": "premium", "realm": True, "openfga_relation": "assignee", "openfga_object": "role:premium"},
                {"keycloak_role": "user", "realm": True, "openfga_relation": "assignee", "openfga_object": "role:user"},
            ],
            "group_mappings": [
                {
                    "pattern": "^/(?:.+/)?([^/]+)$",
                    "openfga_relation": "member",
                    "openfga_object_template": "organization:{group_name}",
                }
            ],
        }

        self.load_from_dict(default_config)
        logger.info("Using default role mapping configuration")

    async def map_user_to_tuples(self, user: KeycloakUser) -> list[dict[str, str]]:
        """
        Map Keycloak user to OpenFGA tuples

        Args:
            user: Keycloak user to map

        Returns:
            List of OpenFGA tuples
        """
        tuples = []
        seen_tuples: set[tuple[str, ...]] = set()  # Deduplicate

        # Apply all mapping rules
        for rule in self.rules:
            try:
                rule_tuples = rule.generate_tuples(user)
                for t in rule_tuples:
                    # Deduplicate using tuple representation
                    tuple_key = (t["user"], t["relation"], t["object"])
                    if tuple_key not in seen_tuples:
                        tuples.append(t)
                        seen_tuples.add(tuple_key)
            except Exception as e:
                logger.error(f"Error applying mapping rule: {e}", exc_info=True)

        # Apply role hierarchies
        tuples = self._apply_hierarchies(user, tuples)

        logger.info(
            f"Mapped user to {len(tuples)} OpenFGA tuples", extra={"username": user.username, "tuple_count": len(tuples)}
        )

        return tuples

    def _apply_hierarchies(self, user: KeycloakUser, tuples: list[dict[str, str]]) -> list[dict[str, str]]:
        """Apply role hierarchies to expand tuples"""
        if not self.hierarchies:
            return tuples

        expanded_tuples = tuples.copy()
        seen_tuples = {(t["user"], t["relation"], t["object"]) for t in tuples}

        # Find all roles user has
        user_roles = set()
        for tuple_data in tuples:
            if tuple_data["relation"] == "assignee" and tuple_data["object"].startswith("role:"):
                role_name = tuple_data["object"].split(":")[-1]
                user_roles.add(role_name)

        # Expand with inherited roles
        for role in user_roles:
            if role in self.hierarchies:
                inherited_roles = self.hierarchies[role]
                for inherited_role in inherited_roles:
                    tuple_key = (user.user_id, "assignee", f"role:{inherited_role}")
                    if tuple_key not in seen_tuples:
                        expanded_tuples.append(
                            {"user": user.user_id, "relation": "assignee", "object": f"role:{inherited_role}"}
                        )
                        seen_tuples.add(tuple_key)

        if len(expanded_tuples) > len(tuples):
            logger.info(f"Role hierarchies expanded {len(tuples)} to {len(expanded_tuples)} tuples")

        return expanded_tuples

    def add_rule(self, rule: MappingRule) -> None:
        """Dynamically add a mapping rule"""
        self.rules.append(rule)
        logger.info(f"Added new mapping rule: {type(rule).__name__}")

    def validate_config(self) -> list[str]:
        """
        Validate configuration

        Returns:
            List of validation errors (empty if valid)
        """
        errors = []

        # Check that all rules are valid
        for i, rule in enumerate(self.rules):
            try:
                # Try to access required attributes
                if isinstance(rule, SimpleRoleMapping):
                    _ = rule.keycloak_role
                    _ = rule.openfga_relation
                    _ = rule.openfga_object
                elif isinstance(rule, GroupMapping):
                    _ = rule.pattern
                    _ = rule.openfga_relation
                    _ = rule.openfga_object_template
                elif isinstance(rule, ConditionalMapping):
                    _ = rule.attribute
                    _ = rule.openfga_tuples
            except Exception as e:
                errors.append(f"Rule {i}: {e}")

        # Validate hierarchies
        for role, inherited in self.hierarchies.items():
            if not isinstance(inherited, list):
                errors.append(f"Hierarchy for '{role}': must be a list")  # type: ignore[unreachable]

            # Check for circular dependencies
            if role in inherited:
                errors.append(f"Hierarchy for '{role}': circular dependency")

        return errors
