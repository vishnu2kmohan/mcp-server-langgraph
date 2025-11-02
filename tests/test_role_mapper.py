"""
Comprehensive tests for Role Mapping Engine

Tests cover:
- Simple role mappings
- Group pattern matching
- Conditional mappings
- Role hierarchies
- YAML configuration loading
- Validation
"""

import tempfile
from pathlib import Path

import pytest

from mcp_server_langgraph.auth.keycloak import KeycloakUser
from mcp_server_langgraph.auth.role_mapper import ConditionalMapping, GroupMapping, RoleMapper, SimpleRoleMapping

# ============================================================================
# SimpleRoleMapping Tests
# ============================================================================


@pytest.mark.unit
class TestSimpleRoleMapping:
    """Tests for SimpleRoleMapping"""

    def test_realm_role_mapping(self):
        """Test mapping realm role to OpenFGA tuple"""
        config = {
            "keycloak_role": "admin",
            "realm": True,
            "openfga_relation": "admin",
            "openfga_object": "system:global",
        }
        mapping = SimpleRoleMapping(config)

        user = KeycloakUser(
            id="123",
            username="alice",
            realm_roles=["admin", "user"],
            client_roles={},
            groups=[],
        )

        assert mapping.applies_to(user) is True

        tuples = mapping.generate_tuples(user)
        assert len(tuples) == 1
        assert tuples[0]["user"] == "user:alice"
        assert tuples[0]["relation"] == "admin"
        assert tuples[0]["object"] == "system:global"

    def test_realm_role_not_matching(self):
        """Test realm role that doesn't match"""
        config = {
            "keycloak_role": "premium",
            "realm": True,
            "openfga_relation": "assignee",
            "openfga_object": "role:premium",
        }
        mapping = SimpleRoleMapping(config)

        user = KeycloakUser(id="123", username="bob", realm_roles=["user"], client_roles={}, groups=[])

        assert mapping.applies_to(user) is False
        tuples = mapping.generate_tuples(user)
        assert len(tuples) == 0

    def test_client_role_mapping(self):
        """Test mapping client role to OpenFGA tuple"""
        config = {
            "keycloak_role": "executor",
            "realm": False,
            "openfga_relation": "executor",
            "openfga_object": "tool:all",
        }
        mapping = SimpleRoleMapping(config)

        user = KeycloakUser(
            id="123",
            username="charlie",
            realm_roles=[],
            client_roles={"my-app": ["executor", "viewer"]},
            groups=[],
        )

        assert mapping.applies_to(user) is True

        tuples = mapping.generate_tuples(user)
        assert len(tuples) == 1
        assert tuples[0]["relation"] == "executor"
        assert tuples[0]["object"] == "tool:all"


# ============================================================================
# GroupMapping Tests
# ============================================================================


@pytest.mark.unit
class TestGroupMapping:
    """Tests for GroupMapping"""

    def test_top_level_group_mapping(self):
        """Test mapping top-level group to organization"""
        config = {
            "pattern": "^/([^/]+)$",
            "openfga_relation": "member",
            "openfga_object_template": "organization:{group_name}",
        }
        mapping = GroupMapping(config)

        user = KeycloakUser(
            id="123",
            username="dave",
            realm_roles=[],
            client_roles={},
            groups=["/acme", "/globex"],
        )

        assert mapping.applies_to(user) is True

        tuples = mapping.generate_tuples(user)
        assert len(tuples) == 2

        org_names = {t["object"] for t in tuples}
        assert org_names == {"organization:acme", "organization:globex"}

    def test_nested_group_mapping(self):
        """Test mapping nested groups to teams"""
        config = {
            "pattern": "^/([^/]+)/([^/]+)$",
            "openfga_relation": "member",
            "openfga_object_template": "team:{group_name}",
        }
        mapping = GroupMapping(config)

        user = KeycloakUser(
            id="123",
            username="eve",
            realm_roles=[],
            client_roles={},
            groups=["/acme/engineering", "/acme/sales"],
        )

        tuples = mapping.generate_tuples(user)
        assert len(tuples) == 2

        team_names = {t["object"] for t in tuples}
        assert team_names == {"team:engineering", "team:sales"}

    def test_group_pattern_no_match(self):
        """Test group pattern that doesn't match"""
        config = {
            "pattern": "^/departments/([^/]+)$",
            "openfga_relation": "member",
            "openfga_object_template": "department:{group_name}",
        }
        mapping = GroupMapping(config)

        user = KeycloakUser(
            id="123",
            username="frank",
            realm_roles=[],
            client_roles={},
            groups=["/acme", "/acme/engineering"],  # Doesn't match pattern
        )

        assert mapping.applies_to(user) is False
        tuples = mapping.generate_tuples(user)
        assert len(tuples) == 0


# ============================================================================
# ConditionalMapping Tests
# ============================================================================


@pytest.mark.unit
class TestConditionalMapping:
    """Tests for ConditionalMapping"""

    def test_equality_condition(self):
        """Test conditional mapping with equality operator"""
        config = {
            "condition": {"attribute": "department", "operator": "==", "value": "finance"},
            "openfga_tuples": [
                {"relation": "viewer", "object": "resource:financial-reports"},
                {"relation": "viewer", "object": "resource:audit-logs"},
            ],
        }
        mapping = ConditionalMapping(config)

        user = KeycloakUser(
            id="123",
            username="grace",
            realm_roles=[],
            client_roles={},
            groups=[],
            attributes={"department": ["finance"]},
        )

        assert mapping.applies_to(user) is True

        tuples = mapping.generate_tuples(user)
        assert len(tuples) == 2

        objects = {t["object"] for t in tuples}
        assert objects == {"resource:financial-reports", "resource:audit-logs"}

    def test_inequality_condition(self):
        """Test conditional mapping with != operator"""
        config = {
            "condition": {"attribute": "region", "operator": "!=", "value": "US"},
            "openfga_tuples": [{"relation": "viewer", "object": "resource:international-data"}],
        }
        mapping = ConditionalMapping(config)

        user = KeycloakUser(
            id="123",
            username="henry",
            realm_roles=[],
            client_roles={},
            groups=[],
            attributes={"region": ["EMEA"]},
        )

        assert mapping.applies_to(user) is True
        tuples = mapping.generate_tuples(user)
        assert len(tuples) == 1

    def test_in_condition(self):
        """Test conditional mapping with 'in' operator"""
        config = {
            "condition": {
                "attribute": "job_title",
                "operator": "in",
                "value": ["Manager", "Director", "VP"],
            },
            "openfga_tuples": [{"relation": "admin", "object": "resource:team-reports"}],
        }
        mapping = ConditionalMapping(config)

        user = KeycloakUser(
            id="123",
            username="iris",
            realm_roles=[],
            client_roles={},
            groups=[],
            attributes={"job_title": ["Director"]},
        )

        assert mapping.applies_to(user) is True

    def test_greater_equal_condition(self):
        """Test conditional mapping with >= operator"""
        config = {
            "condition": {"attribute": "security_clearance", "operator": ">=", "value": 3},
            "openfga_tuples": [{"relation": "viewer", "object": "resource:classified"}],
        }
        mapping = ConditionalMapping(config)

        user = KeycloakUser(
            id="123",
            username="jack",
            realm_roles=[],
            client_roles={},
            groups=[],
            attributes={"security_clearance": ["5"]},
        )

        assert mapping.applies_to(user) is True

    def test_condition_not_met(self):
        """Test condition not met"""
        config = {
            "condition": {"attribute": "department", "operator": "==", "value": "hr"},
            "openfga_tuples": [{"relation": "viewer", "object": "resource:hr-data"}],
        }
        mapping = ConditionalMapping(config)

        user = KeycloakUser(
            id="123",
            username="kate",
            realm_roles=[],
            client_roles={},
            groups=[],
            attributes={"department": ["engineering"]},
        )

        assert mapping.applies_to(user) is False
        tuples = mapping.generate_tuples(user)
        assert len(tuples) == 0

    def test_missing_attribute(self):
        """Test conditional mapping with missing attribute"""
        config = {
            "condition": {"attribute": "missing_attr", "operator": "==", "value": "test"},
            "openfga_tuples": [{"relation": "viewer", "object": "resource:test"}],
        }
        mapping = ConditionalMapping(config)

        user = KeycloakUser(id="123", username="liam", realm_roles=[], client_roles={}, groups=[], attributes={})

        assert mapping.applies_to(user) is False


# ============================================================================
# RoleMapper Tests
# ============================================================================


@pytest.mark.unit
class TestRoleMapper:
    """Tests for RoleMapper"""

    @pytest.mark.asyncio
    async def test_default_config(self):
        """Test RoleMapper with default configuration"""
        mapper = RoleMapper()

        user = KeycloakUser(
            id="123",
            username="mike",
            realm_roles=["admin", "user"],
            client_roles={},
            groups=["/acme"],
        )

        tuples = await mapper.map_user_to_tuples(user)

        # Should have admin and organization mappings from defaults
        assert len(tuples) >= 2

        objects = {t["object"] for t in tuples}
        assert "system:global" in objects  # admin role
        assert "organization:acme" in objects  # group mapping

    @pytest.mark.asyncio
    async def test_yaml_config_loading(self):
        """Test loading configuration from YAML file"""
        # Create temporary YAML config
        config_yaml = """
version: "1.0"

simple_mappings:
  - keycloak_role: tester
    realm: true
    openfga_relation: tester
    openfga_object: tool:testing

group_mappings:
  - pattern: "^/qa/([^/]+)$"
    openfga_relation: member
    openfga_object_template: "qa-team:{group_name}"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_yaml)
            config_file = f.name

        try:
            mapper = RoleMapper(config_path=config_file)

            user = KeycloakUser(
                id="123",
                username="nina",
                realm_roles=["tester"],
                client_roles={},
                groups=["/qa/automation"],
            )

            tuples = await mapper.map_user_to_tuples(user)

            objects = {t["object"] for t in tuples}
            assert "tool:testing" in objects
            assert "qa-team:automation" in objects

        finally:
            Path(config_file).unlink()

    @pytest.mark.asyncio
    async def test_dict_config(self):
        """Test loading configuration from dictionary"""
        config_dict = {
            "simple_mappings": [
                {
                    "keycloak_role": "developer",
                    "realm": True,
                    "openfga_relation": "developer",
                    "openfga_object": "tool:all",
                }
            ],
            "conditional_mappings": [
                {
                    "condition": {"attribute": "team", "operator": "==", "value": "backend"},
                    "openfga_tuples": [{"relation": "viewer", "object": "service:api"}],
                }
            ],
        }

        mapper = RoleMapper(config_dict=config_dict)

        user = KeycloakUser(
            id="123",
            username="oscar",
            realm_roles=["developer"],
            client_roles={},
            groups=[],
            attributes={"team": ["backend"]},
        )

        tuples = await mapper.map_user_to_tuples(user)

        objects = {t["object"] for t in tuples}
        assert "tool:all" in objects
        assert "service:api" in objects

    @pytest.mark.asyncio
    async def test_role_hierarchies(self):
        """Test role hierarchy expansion"""
        config_dict = {
            "simple_mappings": [
                {
                    "keycloak_role": "admin",
                    "realm": True,
                    "openfga_relation": "assignee",
                    "openfga_object": "role:admin",
                },
                {
                    "keycloak_role": "premium",
                    "realm": True,
                    "openfga_relation": "assignee",
                    "openfga_object": "role:premium",
                },
                {
                    "keycloak_role": "user",
                    "realm": True,
                    "openfga_relation": "assignee",
                    "openfga_object": "role:user",
                },
            ],
            "hierarchies": {
                "admin": ["premium", "user"],
                "premium": ["user"],
            },
        }

        mapper = RoleMapper(config_dict=config_dict)

        # User with admin role should inherit premium and user
        user = KeycloakUser(id="123", username="paul", realm_roles=["admin"], client_roles={}, groups=[])

        tuples = await mapper.map_user_to_tuples(user)

        roles = {t["object"] for t in tuples if t["relation"] == "assignee"}
        assert "role:admin" in roles
        assert "role:premium" in roles  # Inherited
        assert "role:user" in roles  # Inherited

    @pytest.mark.asyncio
    async def test_deduplication(self):
        """Test that duplicate tuples are deduplicated"""
        config_dict = {
            "simple_mappings": [
                {
                    "keycloak_role": "user",
                    "realm": True,
                    "openfga_relation": "assignee",
                    "openfga_object": "role:user",
                },
                # Duplicate mapping
                {
                    "keycloak_role": "user",
                    "realm": True,
                    "openfga_relation": "assignee",
                    "openfga_object": "role:user",
                },
            ]
        }

        mapper = RoleMapper(config_dict=config_dict)

        user = KeycloakUser(id="123", username="quinn", realm_roles=["user"], client_roles={}, groups=[])

        tuples = await mapper.map_user_to_tuples(user)

        # Should only have one tuple despite duplicate mapping
        assert len(tuples) == 1

    @pytest.mark.asyncio
    async def test_multiple_rule_types(self):
        """Test combining multiple rule types"""
        config_dict = {
            "simple_mappings": [
                {
                    "keycloak_role": "developer",
                    "realm": True,
                    "openfga_relation": "developer",
                    "openfga_object": "tool:all",
                }
            ],
            "group_mappings": [
                {
                    "pattern": "^/([^/]+)$",
                    "openfga_relation": "member",
                    "openfga_object_template": "organization:{group_name}",
                }
            ],
            "conditional_mappings": [
                {
                    "condition": {"attribute": "location", "operator": "==", "value": "remote"},
                    "openfga_tuples": [{"relation": "user", "object": "tool:vpn"}],
                }
            ],
        }

        mapper = RoleMapper(config_dict=config_dict)

        user = KeycloakUser(
            id="123",
            username="rachel",
            realm_roles=["developer"],
            client_roles={},
            groups=["/startup"],
            attributes={"location": ["remote"]},
        )

        tuples = await mapper.map_user_to_tuples(user)

        # Should have tuples from all three rule types
        assert len(tuples) == 3

        objects = {t["object"] for t in tuples}
        assert "tool:all" in objects  # Simple mapping
        assert "organization:startup" in objects  # Group mapping
        assert "tool:vpn" in objects  # Conditional mapping

    def test_add_rule_dynamically(self):
        """Test adding rules dynamically"""
        mapper = RoleMapper(config_dict={"simple_mappings": []})

        assert len(mapper.rules) == 0

        # Add rule
        new_rule = SimpleRoleMapping(
            {
                "keycloak_role": "guest",
                "realm": True,
                "openfga_relation": "guest",
                "openfga_object": "system:limited",
            }
        )

        mapper.add_rule(new_rule)
        assert len(mapper.rules) == 1

    def test_validate_config_valid(self):
        """Test validation of valid configuration"""
        config_dict = {
            "simple_mappings": [
                {
                    "keycloak_role": "admin",
                    "realm": True,
                    "openfga_relation": "admin",
                    "openfga_object": "system:global",
                }
            ],
            "hierarchies": {"admin": ["user"], "premium": ["user"]},
        }

        mapper = RoleMapper(config_dict=config_dict)
        errors = mapper.validate_config()

        assert len(errors) == 0

    def test_validate_config_circular_hierarchy(self):
        """Test validation detects circular hierarchy"""
        config_dict = {
            "simple_mappings": [],
            "hierarchies": {"admin": ["admin"]},  # Circular - admin inherits from itself
        }

        mapper = RoleMapper(config_dict=config_dict)
        errors = mapper.validate_config()

        assert len(errors) > 0
        assert "circular dependency" in errors[0].lower()

    def test_validate_config_invalid_hierarchy_type(self):
        """Test validation detects invalid hierarchy type"""
        config_dict = {
            "simple_mappings": [],
            "hierarchies": {"admin": "user"},  # Should be a list, not string
        }

        mapper = RoleMapper(config_dict=config_dict)
        errors = mapper.validate_config()

        assert len(errors) > 0
        assert "must be a list" in errors[0].lower()


# ============================================================================
# Integration Tests
# ============================================================================


@pytest.mark.unit
class TestRoleMapperIntegration:
    """Integration tests for role mapper"""

    @pytest.mark.asyncio
    async def test_realistic_enterprise_scenario(self):
        """Test realistic enterprise role mapping scenario"""
        config_dict = {
            "simple_mappings": [
                {
                    "keycloak_role": "employee",
                    "realm": True,
                    "openfga_relation": "employee",
                    "openfga_object": "company:acme",
                },
                {
                    "keycloak_role": "developer",
                    "realm": True,
                    "openfga_relation": "developer",
                    "openfga_object": "tool:all",
                },
            ],
            "group_mappings": [
                {
                    "pattern": "^/([^/]+)$",
                    "openfga_relation": "member",
                    "openfga_object_template": "organization:{group_name}",
                },
                {
                    "pattern": "^/([^/]+)/([^/]+)$",
                    "openfga_relation": "member",
                    "openfga_object_template": "team:{group_name}",
                },
            ],
            "conditional_mappings": [
                {
                    "condition": {
                        "attribute": "job_title",
                        "operator": "in",
                        "value": ["Manager", "Director"],
                    },
                    "openfga_tuples": [
                        {"relation": "admin", "object": "resource:team-reports"},
                        {"relation": "viewer", "object": "resource:hr-data"},
                    ],
                },
                {
                    "condition": {"attribute": "security_clearance", "operator": ">=", "value": 3},
                    "openfga_tuples": [{"relation": "viewer", "object": "resource:classified"}],
                },
            ],
            "hierarchies": {"developer": ["employee"]},
        }

        mapper = RoleMapper(config_dict=config_dict)

        # Enterprise user: Director in engineering
        user = KeycloakUser(
            id="123",
            username="sarah",
            realm_roles=["developer", "employee"],  # Has both roles explicitly
            client_roles={},
            groups=["/acme", "/acme/engineering"],
            attributes={
                "job_title": ["Director"],
                "security_clearance": ["4"],
                "department": ["engineering"],
            },
        )

        tuples = await mapper.map_user_to_tuples(user)

        # Verify all expected permissions
        objects = {t["object"] for t in tuples}

        # From simple mappings
        assert "tool:all" in objects  # developer role
        assert "company:acme" in objects  # employee role

        # From group mappings
        assert "organization:acme" in objects
        assert "team:engineering" in objects

        # From conditional mappings
        assert "resource:team-reports" in objects  # Manager/Director
        assert "resource:hr-data" in objects  # Manager/Director
        assert "resource:classified" in objects  # Security clearance >= 3

        # Should have at least 7 tuples
        assert len(tuples) >= 7
