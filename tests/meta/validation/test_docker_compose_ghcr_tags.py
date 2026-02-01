"""
Meta tests for Docker Compose GHCR tagging consistency.

These tests verify that all custom-built services in docker-compose.test.yml
have proper GHCR (GitHub Container Registry) tags configured.

Reference: Test Infrastructure Improvements Plan
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

# Mark all tests in this module
pytestmark = [pytest.mark.meta, pytest.mark.docker]

# Expected GHCR registry prefix
GHCR_REGISTRY = "ghcr.io/vishnu2kmohan"

# Custom-built services that must have GHCR tags
CUSTOM_BUILD_SERVICES = {
    "alembic-migrate-test": {
        "image_name": "mcp-server-langgraph-alembic",
        "expected_tags": ["latest", "local"],
    },
    "openfga-seed-test": {
        "image_name": "mcp-server-langgraph-openfga-seed",
        "expected_tags": ["latest", "local"],
    },
    "keycloak-test": {
        "image_name": "mcp-server-langgraph-keycloak",
        "expected_tags": ["latest", "local"],
    },
    "mcp-server-test": {
        "image_name": "mcp-server-langgraph",
        "expected_tags": ["test-latest", "test-local"],
    },
    # NOTE: authz-proxy-test removed in Phase 4 decommission
    "agent-studio-sandbox": {
        "image_name": "mcp-server-langgraph-agent-studio-sandbox",
        "expected_tags": ["latest", "local"],
    },
}


@pytest.fixture(scope="module")
def compose_config() -> dict[str, Any]:
    """Load and parse docker-compose.test.yml."""
    project_root = Path(__file__).parents[3]
    compose_path = project_root / "docker-compose.test.yml"

    if not compose_path.exists():
        pytest.skip(f"docker-compose.test.yml not found at {compose_path}")

    with open(compose_path) as f:
        return yaml.safe_load(f)


class TestGHCRTagConsistency:
    """Tests for GHCR tag configuration in docker-compose.test.yml."""

    def test_all_custom_services_have_build_section(self, compose_config: dict[str, Any]) -> None:
        """
        GIVEN docker-compose.test.yml
        WHEN checking custom-built services
        THEN each service should have a build section
        """
        services = compose_config.get("services", {})
        missing_build = []

        for service_name in CUSTOM_BUILD_SERVICES:
            service = services.get(service_name, {})
            if "build" not in service:
                missing_build.append(service_name)

        assert not missing_build, (
            f"Services missing build section: {missing_build}. All custom-built services must have a build configuration."
        )

    def test_all_custom_services_use_ghcr_prefix(self, compose_config: dict[str, Any]) -> None:
        """
        GIVEN docker-compose.test.yml
        WHEN checking custom-built services
        THEN all build.tags should use ghcr.io/vishnu2kmohan/ prefix
        """
        services = compose_config.get("services", {})
        incorrect_prefix = []

        for service_name, expected in CUSTOM_BUILD_SERVICES.items():
            service = services.get(service_name, {})
            build_config = service.get("build", {})

            if isinstance(build_config, str):
                # Simple build context without tags
                incorrect_prefix.append((service_name, "no tags defined"))
                continue

            tags = build_config.get("tags", [])
            for tag in tags:
                if not tag.startswith(GHCR_REGISTRY):
                    incorrect_prefix.append((service_name, tag))

        assert not incorrect_prefix, (
            f"Services with incorrect GHCR prefix: {incorrect_prefix}. All tags must use '{GHCR_REGISTRY}/' prefix."
        )

    def test_all_custom_services_have_required_tags(self, compose_config: dict[str, Any]) -> None:
        """
        GIVEN docker-compose.test.yml
        WHEN checking custom-built services
        THEN each service should have all expected tags (latest, local variants)
        """
        services = compose_config.get("services", {})
        missing_tags: list[tuple[str, list[str]]] = []

        for service_name, expected in CUSTOM_BUILD_SERVICES.items():
            service = services.get(service_name, {})
            build_config = service.get("build", {})

            if isinstance(build_config, str):
                missing_tags.append((service_name, expected["expected_tags"]))
                continue

            tags = build_config.get("tags", [])
            expected_image = f"{GHCR_REGISTRY}/{expected['image_name']}"

            for expected_tag in expected["expected_tags"]:
                full_expected = f"{expected_image}:{expected_tag}"
                if full_expected not in tags:
                    if (service_name, [expected_tag]) not in [(s, t) for s, t in missing_tags]:
                        existing = [t for s, t in missing_tags if s == service_name]
                        if existing:
                            existing[0].append(expected_tag)
                        else:
                            missing_tags.append((service_name, [expected_tag]))

        assert not missing_tags, (
            f"Services missing expected tags: {missing_tags}. "
            "Each custom service should have both :latest and :local tags "
            "(or :test-latest and :test-local for mcp-server-test)."
        )

    def test_image_names_match_expected_pattern(self, compose_config: dict[str, Any]) -> None:
        """
        GIVEN docker-compose.test.yml
        WHEN checking custom-built services
        THEN image names should follow the mcp-server-langgraph-* pattern
        """
        services = compose_config.get("services", {})
        incorrect_names = []

        for service_name, expected in CUSTOM_BUILD_SERVICES.items():
            service = services.get(service_name, {})
            build_config = service.get("build", {})

            if isinstance(build_config, str):
                continue

            tags = build_config.get("tags", [])
            expected_image = expected["image_name"]

            for tag in tags:
                # Extract image name from tag (e.g., ghcr.io/vishnu2kmohan/name:tag)
                if ":" in tag:
                    image_part = tag.rsplit(":", 1)[0]
                else:
                    image_part = tag

                if not image_part.endswith(f"/{expected_image}"):
                    incorrect_names.append((service_name, tag, expected_image))

        assert not incorrect_names, (
            f"Services with incorrect image names: {incorrect_names}. Image names should match expected pattern."
        )


class TestBuildContextIntegrity:
    """Tests for build context and Dockerfile configuration."""

    def test_all_build_contexts_exist(self, compose_config: dict[str, Any]) -> None:
        """
        GIVEN docker-compose.test.yml
        WHEN checking build contexts
        THEN all specified build contexts should exist
        """
        services = compose_config.get("services", {})
        project_root = Path(__file__).parents[3]
        missing_contexts = []

        for service_name in CUSTOM_BUILD_SERVICES:
            service = services.get(service_name, {})
            build_config = service.get("build", {})

            if isinstance(build_config, str):
                context = build_config
            else:
                context = build_config.get("context", ".")

            # Resolve context path relative to project root
            context_path = project_root / context
            if not context_path.exists():
                missing_contexts.append((service_name, context))

        assert not missing_contexts, f"Services with missing build contexts: {missing_contexts}"

    def test_all_dockerfiles_exist(self, compose_config: dict[str, Any]) -> None:
        """
        GIVEN docker-compose.test.yml
        WHEN checking Dockerfiles
        THEN all specified Dockerfiles should exist
        """
        services = compose_config.get("services", {})
        project_root = Path(__file__).parents[3]
        missing_dockerfiles = []

        for service_name in CUSTOM_BUILD_SERVICES:
            service = services.get(service_name, {})
            build_config = service.get("build", {})

            if isinstance(build_config, str):
                continue

            dockerfile = build_config.get("dockerfile")
            if dockerfile:
                context = build_config.get("context", ".")
                dockerfile_path = project_root / context / dockerfile
                if not dockerfile_path.exists():
                    # Also check relative to project root directly
                    dockerfile_path = project_root / dockerfile
                    if not dockerfile_path.exists():
                        missing_dockerfiles.append((service_name, dockerfile))

        assert not missing_dockerfiles, f"Services with missing Dockerfiles: {missing_dockerfiles}"


class TestOIDCWaitInitContainer:
    """Tests for the OIDC wait init container used by OpenFGA."""

    def test_oidc_wait_init_container_exists(self, compose_config: dict[str, Any]) -> None:
        """
        GIVEN docker-compose.test.yml
        WHEN checking for openfga-oidc-wait service
        THEN it should exist as an init container
        """
        services = compose_config.get("services", {})
        assert "openfga-oidc-wait" in services, (
            "openfga-oidc-wait init container not found. "
            "This is required because OpenFGA uses a distroless image without shell."
        )

    def test_oidc_wait_uses_alpine(self, compose_config: dict[str, Any]) -> None:
        """
        GIVEN docker-compose.test.yml
        WHEN checking openfga-oidc-wait service
        THEN it should use Alpine image (has shell and wget)
        """
        services = compose_config.get("services", {})
        oidc_wait = services.get("openfga-oidc-wait", {})

        image = oidc_wait.get("image", "")
        assert "alpine" in image.lower(), "openfga-oidc-wait should use Alpine image for shell access"

    def test_openfga_depends_on_oidc_wait(self, compose_config: dict[str, Any]) -> None:
        """
        GIVEN docker-compose.test.yml
        WHEN checking openfga-test service
        THEN it should depend on openfga-oidc-wait completing successfully
        """
        services = compose_config.get("services", {})
        openfga_service = services.get("openfga-test", {})

        depends_on = openfga_service.get("depends_on", {})
        assert "openfga-oidc-wait" in depends_on, "openfga-test must depend on openfga-oidc-wait init container"

        oidc_wait_condition = depends_on.get("openfga-oidc-wait", {})
        condition = oidc_wait_condition.get("condition", "")
        assert condition == "service_completed_successfully", (
            "openfga-test must wait for openfga-oidc-wait to complete successfully"
        )


class TestInfrastructureMakefileTargets:
    """Tests for infrastructure.mk target configuration."""

    @pytest.fixture(scope="class")
    def infrastructure_mk_content(self) -> str:
        """Load infrastructure.mk content."""
        project_root = Path(__file__).parents[3]
        mk_path = project_root / "make" / "infrastructure.mk"

        if not mk_path.exists():
            pytest.skip(f"infrastructure.mk not found at {mk_path}")

        return mk_path.read_text()

    def test_cleanup_images_target_exists(self, infrastructure_mk_content: str) -> None:
        """
        GIVEN make/infrastructure.mk
        WHEN checking for test-infra-cleanup-images target
        THEN it should exist
        """
        assert "test-infra-cleanup-images:" in infrastructure_mk_content, (
            "Missing test-infra-cleanup-images target in infrastructure.mk. "
            "This target is needed to clean up local Docker images."
        )

    def test_ghcr_registry_defined(self, infrastructure_mk_content: str) -> None:
        """
        GIVEN make/infrastructure.mk
        WHEN checking for GHCR registry definition
        THEN it should define GHCR_REGISTRY variable
        """
        assert "GHCR_REGISTRY" in infrastructure_mk_content, (
            "Missing GHCR_REGISTRY variable in infrastructure.mk. This variable defines the registry prefix for image cleanup."
        )

    def test_test_images_list_defined(self, infrastructure_mk_content: str) -> None:
        """
        GIVEN make/infrastructure.mk
        WHEN checking for test images list
        THEN it should define TEST_IMAGES variable with all custom images
        """
        assert "TEST_IMAGES" in infrastructure_mk_content, (
            "Missing TEST_IMAGES variable in infrastructure.mk. This variable lists all custom-built images for cleanup."
        )
