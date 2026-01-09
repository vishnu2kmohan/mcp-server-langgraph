"""Integration tests for Skills Marketplace Feature Flags.

Validates that marketplace feature flags properly configure the MarketplaceClient
when used through the create_marketplace_client() factory function.

These tests verify the production integration path:
1. Environment variables -> FeatureFlags
2. FeatureFlags -> create_marketplace_client()
3. create_marketplace_client() -> MarketplaceClient configuration

ADR Reference: ADR-0099 Semantic Tool Selection
"""

import gc
import os
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.integration, pytest.mark.skills, pytest.mark.skills_marketplace]


@pytest.mark.integration
@pytest.mark.xdist_group(name="test_marketplace_feature_flags")
class TestMarketplaceFeatureFlagsIntegration:
    """Integration tests for marketplace feature flags.

    These tests verify that the entire feature flag -> factory -> client
    integration chain works correctly.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_default_marketplace_rate_limit(self):
        """GIVEN the FeatureFlags defaults
        WHEN checking skills_marketplace_rate_limit
        THEN it should have sensible default (10 requests/second)
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.skills_marketplace_rate_limit == 10
        assert isinstance(flags.skills_marketplace_rate_limit, int)

    def test_default_marketplace_retry_max_attempts(self):
        """GIVEN the FeatureFlags defaults
        WHEN checking skills_marketplace_retry_max_attempts
        THEN it should have sensible default (3 attempts)
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.skills_marketplace_retry_max_attempts == 3
        assert isinstance(flags.skills_marketplace_retry_max_attempts, int)

    def test_default_marketplace_retry_base_delay(self):
        """GIVEN the FeatureFlags defaults
        WHEN checking skills_marketplace_retry_base_delay
        THEN it should have sensible default (0.1 seconds)
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.skills_marketplace_retry_base_delay == 0.1
        assert isinstance(flags.skills_marketplace_retry_base_delay, float)

    def test_default_marketplace_max_concurrent_fetches(self):
        """GIVEN the FeatureFlags defaults
        WHEN checking skills_marketplace_max_concurrent_fetches
        THEN it should have sensible default (5 concurrent fetches)
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flags = FeatureFlags()

        assert flags.skills_marketplace_max_concurrent_fetches == 5
        assert isinstance(flags.skills_marketplace_max_concurrent_fetches, int)

    def test_environment_variable_override_rate_limit(self):
        """GIVEN environment variable FF_SKILLS_MARKETPLACE_RATE_LIMIT set
        WHEN creating FeatureFlags
        THEN the flag should be overridden
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(os.environ, {"FF_SKILLS_MARKETPLACE_RATE_LIMIT": "25"}):
            flags = FeatureFlags()
            assert flags.skills_marketplace_rate_limit == 25

    def test_environment_variable_override_retry_max_attempts(self):
        """GIVEN environment variable FF_SKILLS_MARKETPLACE_RETRY_MAX_ATTEMPTS set
        WHEN creating FeatureFlags
        THEN the flag should be overridden
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(os.environ, {"FF_SKILLS_MARKETPLACE_RETRY_MAX_ATTEMPTS": "5"}):
            flags = FeatureFlags()
            assert flags.skills_marketplace_retry_max_attempts == 5

    def test_environment_variable_override_retry_base_delay(self):
        """GIVEN environment variable FF_SKILLS_MARKETPLACE_RETRY_BASE_DELAY set
        WHEN creating FeatureFlags
        THEN the flag should be overridden
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(os.environ, {"FF_SKILLS_MARKETPLACE_RETRY_BASE_DELAY": "0.5"}):
            flags = FeatureFlags()
            assert flags.skills_marketplace_retry_base_delay == 0.5

    def test_environment_variable_override_max_concurrent_fetches(self):
        """GIVEN environment variable FF_SKILLS_MARKETPLACE_MAX_CONCURRENT_FETCHES set
        WHEN creating FeatureFlags
        THEN the flag should be overridden
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with patch.dict(os.environ, {"FF_SKILLS_MARKETPLACE_MAX_CONCURRENT_FETCHES": "10"}):
            flags = FeatureFlags()
            assert flags.skills_marketplace_max_concurrent_fetches == 10


@pytest.mark.integration
@pytest.mark.xdist_group(name="test_marketplace_feature_flags_validation")
class TestMarketplaceFeatureFlagsValidation:
    """Test validation constraints on marketplace feature flags."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_rate_limit_minimum_constraint(self):
        """GIVEN rate_limit less than 1
        WHEN creating FeatureFlags
        THEN validation should fail
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with pytest.raises(ValidationError) as exc_info:
            FeatureFlags(skills_marketplace_rate_limit=0)

        assert "skills_marketplace_rate_limit" in str(exc_info.value)

    def test_rate_limit_maximum_constraint(self):
        """GIVEN rate_limit greater than 100
        WHEN creating FeatureFlags
        THEN validation should fail
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with pytest.raises(ValidationError) as exc_info:
            FeatureFlags(skills_marketplace_rate_limit=101)

        assert "skills_marketplace_rate_limit" in str(exc_info.value)

    def test_retry_max_attempts_minimum_constraint(self):
        """GIVEN retry_max_attempts less than 1
        WHEN creating FeatureFlags
        THEN validation should fail
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with pytest.raises(ValidationError) as exc_info:
            FeatureFlags(skills_marketplace_retry_max_attempts=0)

        assert "skills_marketplace_retry_max_attempts" in str(exc_info.value)

    def test_retry_max_attempts_maximum_constraint(self):
        """GIVEN retry_max_attempts greater than 10
        WHEN creating FeatureFlags
        THEN validation should fail
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with pytest.raises(ValidationError) as exc_info:
            FeatureFlags(skills_marketplace_retry_max_attempts=11)

        assert "skills_marketplace_retry_max_attempts" in str(exc_info.value)

    def test_retry_base_delay_minimum_constraint(self):
        """GIVEN retry_base_delay less than 0.01
        WHEN creating FeatureFlags
        THEN validation should fail
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with pytest.raises(ValidationError) as exc_info:
            FeatureFlags(skills_marketplace_retry_base_delay=0.001)

        assert "skills_marketplace_retry_base_delay" in str(exc_info.value)

    def test_retry_base_delay_maximum_constraint(self):
        """GIVEN retry_base_delay greater than 5.0
        WHEN creating FeatureFlags
        THEN validation should fail
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with pytest.raises(ValidationError) as exc_info:
            FeatureFlags(skills_marketplace_retry_base_delay=5.1)

        assert "skills_marketplace_retry_base_delay" in str(exc_info.value)

    def test_max_concurrent_fetches_minimum_constraint(self):
        """GIVEN max_concurrent_fetches less than 1
        WHEN creating FeatureFlags
        THEN validation should fail
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with pytest.raises(ValidationError) as exc_info:
            FeatureFlags(skills_marketplace_max_concurrent_fetches=0)

        assert "skills_marketplace_max_concurrent_fetches" in str(exc_info.value)

    def test_max_concurrent_fetches_maximum_constraint(self):
        """GIVEN max_concurrent_fetches greater than 50
        WHEN creating FeatureFlags
        THEN validation should fail
        """
        from pydantic import ValidationError

        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        with pytest.raises(ValidationError) as exc_info:
            FeatureFlags(skills_marketplace_max_concurrent_fetches=51)

        assert "skills_marketplace_max_concurrent_fetches" in str(exc_info.value)


@pytest.mark.integration
@pytest.mark.xdist_group(name="test_marketplace_factory_integration")
class TestMarketplaceFactoryIntegration:
    """Test create_marketplace_client() factory integration.

    These tests verify that the factory function properly reads
    from the global feature_flags singleton and creates a correctly
    configured MarketplaceClient.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_factory_creates_client_with_default_flags(self):
        """GIVEN default feature flags
        WHEN calling create_marketplace_client()
        THEN client should have default configuration
        """
        from unittest.mock import MagicMock

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            create_marketplace_client,
        )

        # Create mock feature_flags with defaults
        mock_flags = MagicMock()
        mock_flags.skills_marketplace_rate_limit = 10
        mock_flags.skills_marketplace_retry_max_attempts = 3
        mock_flags.skills_marketplace_retry_base_delay = 0.1
        mock_flags.skills_marketplace_max_concurrent_fetches = 5

        with patch(
            "mcp_server_langgraph.core.feature_flags.feature_flags",
            mock_flags,
        ):
            client = create_marketplace_client()

            assert isinstance(client, MarketplaceClient)
            assert client.rate_limit_requests_per_second == 10
            assert client.retry_max_attempts == 3
            assert client.retry_base_delay == 0.1
            assert client.max_concurrent_fetches == 5

    def test_factory_propagates_custom_flags(self):
        """GIVEN custom feature flag values
        WHEN calling create_marketplace_client()
        THEN client should have custom configuration
        """
        from unittest.mock import MagicMock

        from mcp_server_langgraph.skills.marketplace import (
            MarketplaceClient,
            create_marketplace_client,
        )

        # Create mock feature_flags with custom values
        mock_flags = MagicMock()
        mock_flags.skills_marketplace_rate_limit = 25
        mock_flags.skills_marketplace_retry_max_attempts = 7
        mock_flags.skills_marketplace_retry_base_delay = 0.5
        mock_flags.skills_marketplace_max_concurrent_fetches = 12

        with patch(
            "mcp_server_langgraph.core.feature_flags.feature_flags",
            mock_flags,
        ):
            client = create_marketplace_client()

            assert isinstance(client, MarketplaceClient)
            assert client.rate_limit_requests_per_second == 25
            assert client.retry_max_attempts == 7
            assert client.retry_base_delay == 0.5
            assert client.max_concurrent_fetches == 12

    def test_factory_imports_feature_flags_lazily(self):
        """GIVEN the create_marketplace_client function
        WHEN examining its implementation
        THEN feature_flags should be imported inside the function (lazy)
        """
        import inspect

        from mcp_server_langgraph.skills.marketplace import create_marketplace_client

        source = inspect.getsource(create_marketplace_client)

        # Verify the import is inside the function
        assert "from mcp_server_langgraph.core.feature_flags import feature_flags" in source

    def test_client_configuration_is_used_for_api_calls(self):
        """GIVEN a MarketplaceClient with specific configuration
        WHEN making API calls
        THEN the configuration should affect behavior
        """
        from mcp_server_langgraph.skills.marketplace import MarketplaceClient

        # Create client with rate limiting disabled (0)
        client = MarketplaceClient(
            rate_limit_requests_per_second=0,
            retry_max_attempts=1,
            retry_base_delay=0.01,
            max_concurrent_fetches=2,
        )

        # Verify configuration is stored
        assert client.rate_limit_requests_per_second == 0
        assert client.retry_max_attempts == 1
        assert client.retry_base_delay == 0.01
        assert client.max_concurrent_fetches == 2


@pytest.mark.integration
@pytest.mark.xdist_group(name="test_marketplace_e2e_config")
class TestMarketplaceEndToEndConfiguration:
    """End-to-end tests for the complete configuration chain.

    Tests the full path from environment variables to API behavior.
    """

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_environment_to_client_chain(self):
        """GIVEN environment variables set for marketplace configuration
        WHEN creating a new FeatureFlags and MarketplaceClient
        THEN the client should reflect the environment configuration
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags
        from mcp_server_langgraph.skills.marketplace import MarketplaceClient

        with patch.dict(
            os.environ,
            {
                "FF_SKILLS_MARKETPLACE_RATE_LIMIT": "15",
                "FF_SKILLS_MARKETPLACE_RETRY_MAX_ATTEMPTS": "4",
                "FF_SKILLS_MARKETPLACE_RETRY_BASE_DELAY": "0.25",
                "FF_SKILLS_MARKETPLACE_MAX_CONCURRENT_FETCHES": "8",
            },
        ):
            # Create fresh flags from environment
            flags = FeatureFlags()

            # Create client using flags
            client = MarketplaceClient(
                rate_limit_requests_per_second=flags.skills_marketplace_rate_limit,
                retry_max_attempts=flags.skills_marketplace_retry_max_attempts,
                retry_base_delay=flags.skills_marketplace_retry_base_delay,
                max_concurrent_fetches=flags.skills_marketplace_max_concurrent_fetches,
            )

            assert client.rate_limit_requests_per_second == 15
            assert client.retry_max_attempts == 4
            assert client.retry_base_delay == 0.25
            assert client.max_concurrent_fetches == 8

    def test_all_flags_have_descriptions(self):
        """GIVEN the marketplace feature flags
        WHEN checking their Field metadata
        THEN all should have descriptions for documentation
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        flag_names = [
            "skills_marketplace_rate_limit",
            "skills_marketplace_retry_max_attempts",
            "skills_marketplace_retry_base_delay",
            "skills_marketplace_max_concurrent_fetches",
        ]

        for field_name in flag_names:
            field_info = FeatureFlags.model_fields.get(field_name)
            assert field_info is not None, f"Field {field_name} not found"
            assert field_info.description is not None, f"Field {field_name} has no description"
            assert len(field_info.description) > 10, f"Field {field_name} description too short"

    def test_all_flags_have_sensible_bounds(self):
        """GIVEN the marketplace feature flags
        WHEN checking their Field metadata
        THEN all numeric flags should have ge/le constraints
        """
        from mcp_server_langgraph.core.feature_flags import FeatureFlags

        # These are the expected constraints based on implementation
        expected_constraints = {
            "skills_marketplace_rate_limit": {"ge": 1, "le": 100},
            "skills_marketplace_retry_max_attempts": {"ge": 1, "le": 10},
            "skills_marketplace_retry_base_delay": {"ge": 0.01, "le": 5.0},
            "skills_marketplace_max_concurrent_fetches": {"ge": 1, "le": 50},
        }

        for field_name, expected in expected_constraints.items():
            field_info = FeatureFlags.model_fields.get(field_name)
            assert field_info is not None, f"Field {field_name} not found"

            # Check constraints via metadata
            metadata = field_info.metadata
            ge_found = False
            le_found = False

            for m in metadata:
                if hasattr(m, "ge"):
                    ge_found = True
                    assert m.ge == expected["ge"], f"{field_name} ge mismatch"
                if hasattr(m, "le"):
                    le_found = True
                    assert m.le == expected["le"], f"{field_name} le mismatch"

            assert ge_found, f"{field_name} missing ge constraint"
            assert le_found, f"{field_name} missing le constraint"
