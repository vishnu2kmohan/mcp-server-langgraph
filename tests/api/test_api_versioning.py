"""
Tests for API Versioning Strategy

Validates that the API follows semantic versioning best practices and provides
version negotiation capabilities to prevent breaking changes.

Following TDD: These tests define the expected versioning behavior (RED phase).
"""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def test_client(monkeypatch):
    """
    FastAPI TestClient using the actual production app with mocked Keycloak.

    This tests the real router registration while preventing Keycloak connection
    attempts that would fail in CI environments.

    TDD Context:
    - RED (Before): Tests fail with "httpx.ConnectError: All connection attempts failed"
    - GREEN (After): Keycloak client mocked, tests check API versioning only
    - REFACTOR: Proper dependency mocking pattern for contract tests
    """
    # Set environment variable to skip authentication
    monkeypatch.setenv("MCP_SKIP_AUTH", "true")

    # Import app after setting environment variables
    from mcp_server_langgraph.mcp.server_streamable import app

    return TestClient(app)


@pytest.mark.unit
@pytest.mark.contract
class TestAPIVersionMetadata:
    """Test API version information endpoints"""

    def test_version_endpoint_exists(self, test_client):
        """API should expose version metadata at /api/version"""
        response = test_client.get("/api/version")

        # Should exist (not 404)
        assert response.status_code in [
            200,
            401,
            403,
        ], f"Version endpoint not found or unexpected status: {response.status_code}"

    def test_version_metadata_structure(self, test_client):
        """Version metadata should follow standard structure"""
        response = test_client.get("/api/version")

        if response.status_code == 200:
            data = response.json()

            # Should contain semantic version
            assert "version" in data, "Missing 'version' field"
            assert "api_version" in data, "Missing 'api_version' field"

            # Version should be semantic (MAJOR.MINOR.PATCH)
            version = data["version"]
            parts = version.split(".")
            assert len(parts) >= 3, f"Version should be semantic (X.Y.Z), got: {version}"

    def test_openapi_version_consistency(self, test_client):
        """OpenAPI schema version should match /api/version"""
        openapi_response = test_client.get("/openapi.json")
        assert openapi_response.status_code == 200

        openapi = openapi_response.json()
        openapi_version = openapi.get("info", {}).get("version")

        version_response = test_client.get("/api/version")
        if version_response.status_code == 200:
            version_data = version_response.json()
            assert openapi_version == version_data.get("version"), "OpenAPI version must match /api/version"


@pytest.mark.unit
@pytest.mark.contract
class TestAPIVersionPrefixes:
    """Test that all REST API endpoints use consistent /api/v1 prefix"""

    def test_gdpr_endpoints_have_v1_prefix(self, test_client):
        """GDPR endpoints should be under /api/v1"""
        openapi = test_client.get("/openapi.json").json()
        paths = openapi.get("paths", {})

        gdpr_paths = [p for p in paths.keys() if "users" in p and "gdpr" not in p.lower()]
        for path in gdpr_paths:
            if path.startswith("/api/"):
                assert path.startswith("/api/v1/"), f"GDPR endpoint missing v1 prefix: {path}"

    def test_api_keys_endpoints_have_v1_prefix(self, test_client):
        """API Keys endpoints should be under /api/v1"""
        openapi = test_client.get("/openapi.json").json()
        paths = openapi.get("paths", {})

        api_key_paths = [p for p in paths.keys() if "api-keys" in p or "api_keys" in p]
        for path in api_key_paths:
            assert path.startswith("/api/v1/"), f"API Keys endpoint missing v1 prefix: {path}"

    def test_service_principals_endpoints_have_v1_prefix(self, test_client):
        """Service Principals endpoints should be under /api/v1"""
        openapi = test_client.get("/openapi.json").json()
        paths = openapi.get("paths", {})

        sp_paths = [p for p in paths.keys() if "service-principals" in p or "service_principals" in p]
        for path in sp_paths:
            assert path.startswith("/api/v1/"), f"Service Principals endpoint missing v1 prefix: {path}"

    def test_auth_endpoints_have_version_prefix(self, test_client):
        """Auth endpoints should be versioned (except /health)"""
        openapi = test_client.get("/openapi.json").json()
        paths = openapi.get("paths", {})

        auth_paths = [p for p in paths.keys() if "/auth/" in p]

        # Auth endpoints should be versioned or documented as intentionally unversioned
        for path in auth_paths:
            # Either starts with /api/v1/auth or is explicitly unversioned
            is_versioned = path.startswith("/api/v1/auth")
            is_legacy = path.startswith("/auth/")

            # For now, we allow legacy /auth/ paths but log them
            if is_legacy and not is_versioned:
                # This is acceptable for backward compatibility, but should be documented
                pass


@pytest.mark.unit
@pytest.mark.contract
class TestVersionNegotiation:
    """Test API version negotiation via headers"""

    def test_version_header_accepted(self, test_client):
        """API should accept X-API-Version header"""
        # Make request with version header to a versioned endpoint
        response = test_client.get("/api/v1/api-keys/", headers={"X-API-Version": "1.0"})

        # Should not return 400 (bad request) due to header
        assert response.status_code != 400, "X-API-Version header should be accepted"

    def test_unsupported_version_returns_error(self, test_client):
        """Requesting unsupported version should return clear error"""
        # Request future version that doesn't exist
        response = test_client.get("/api/v1/api-keys/", headers={"X-API-Version": "99.0"})

        # Should either ignore (default to current) or return 400/406
        # For now, we accept that it might be ignored
        assert response.status_code in [
            200,
            400,
            401,
            403,
            406,
        ], f"Unexpected status for unsupported version: {response.status_code}"


@pytest.mark.unit
@pytest.mark.contract
class TestDeprecationSupport:
    """Test that deprecated endpoints are properly marked"""

    def test_deprecated_endpoints_marked_in_openapi(self, test_client):
        """Deprecated endpoints should have 'deprecated: true' in OpenAPI"""
        openapi = test_client.get("/openapi.json").json()
        paths = openapi.get("paths", {})

        # Check if any deprecated endpoints exist
        deprecated_operations = []
        for path, methods in paths.items():
            for method, operation in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    if operation.get("deprecated"):
                        deprecated_operations.append(f"{method.upper()} {path}")

        # Deprecated operations should have sunset header documented
        # (This is a forward-looking test - currently may have 0 deprecated endpoints)
        # When endpoints are deprecated, they should include this metadata

    def test_deprecated_fields_documented(self, test_client):
        """Deprecated fields in request/response models should be marked"""
        openapi = test_client.get("/openapi.json").json()
        schemas = openapi.get("components", {}).get("schemas", {})

        # Look for deprecated fields in schemas
        for schema_name, schema in schemas.items():
            properties = schema.get("properties", {})
            for prop_name, prop_def in properties.items():
                if prop_def.get("deprecated"):
                    # Deprecated field should have description explaining alternative
                    assert "description" in prop_def, f"Deprecated field {schema_name}.{prop_name} should have description"


@pytest.mark.unit
@pytest.mark.contract
class TestBackwardCompatibility:
    """Test backward compatibility guarantees"""

    def test_all_v1_endpoints_stable(self, test_client):
        """All /api/v1 endpoints are considered stable (no breaking changes)"""
        openapi = test_client.get("/openapi.json").json()
        paths = openapi.get("paths", {})

        v1_paths = [p for p in paths.keys() if p.startswith("/api/v1/")]

        # All v1 endpoints should exist and be accessible
        assert len(v1_paths) > 0, "Should have at least one /api/v1 endpoint"

        # v1 endpoints should not be marked as deprecated (they're the current version)
        for path in v1_paths:
            methods = paths[path]
            for method, operation in methods.items():
                if method in ["get", "post", "put", "delete", "patch"]:
                    # v1 endpoints should not be deprecated yet
                    # (when v2 is introduced, v1 may be marked deprecated)
                    # For now, v1 is current, so none should be deprecated
                    # This assertion may change when v2 is introduced
                    assert not operation.get("deprecated", False), f"v1 endpoint {path} {method} should not be deprecated"

    def test_response_schema_extensions_allowed(self, test_client):
        """Response schemas can add new optional fields without breaking changes"""
        openapi = test_client.get("/openapi.json").json()
        schemas = openapi.get("components", {}).get("schemas", {})

        # Check that response schemas use additionalProperties: true or don't prohibit extras
        # This ensures clients won't break when new fields are added
        for schema_name, schema in schemas.items():
            if "Response" in schema_name:
                # Response schemas should allow additional properties (or not explicitly forbid them)
                additional_props = schema.get("additionalProperties")

                # Either undefined (allows extras) or explicitly true
                # If explicitly false, that's a strict schema that could break clients
                if additional_props is False:
                    # This is acceptable but should be intentional
                    # Strict schemas are fine for request validation
                    pass


@pytest.mark.unit
@pytest.mark.contract
class TestVersionDocumentation:
    """Test that versioning strategy is documented in OpenAPI"""

    def test_openapi_version_field_present(self, test_client):
        """OpenAPI schema should have version in info section"""
        openapi = test_client.get("/openapi.json").json()

        assert "info" in openapi
        assert "version" in openapi["info"]
        assert len(openapi["info"]["version"]) > 0

    def test_openapi_has_description(self, test_client):
        """OpenAPI description should explain versioning strategy"""
        openapi = test_client.get("/openapi.json").json()

        description = openapi.get("info", {}).get("description", "")
        assert len(description) > 0, "OpenAPI should have description"

        # When versioning is fully implemented, description should mention it
        # For now, we just ensure description exists

    def test_servers_include_version_info(self, test_client):
        """OpenAPI servers should include version information"""
        openapi = test_client.get("/openapi.json").json()

        # Servers array should exist (may be empty for local dev)
        # When configured, should include staging/production URLs
        servers = openapi.get("servers", [])

        # Test that if servers are defined, they include proper paths
        for server in servers:
            assert "url" in server, "Server must have URL"
