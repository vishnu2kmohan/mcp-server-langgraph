"""Tests for SQL-related feature flags.

TDD: Written FIRST to define expected behavior of SQL feature flags
added in Phase 5 of the SQLGlot migration.
"""

import gc

import pytest

from mcp_server_langgraph.core.feature_flags import FeatureFlags

pytestmark = [pytest.mark.unit]


class TestSQLFeatureFlags:
    """Tests for SQL execution engine feature flags."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_sql_engine_default_is_sqlglot(self) -> None:
        """
        GIVEN: Default FeatureFlags
        WHEN: sql_engine is read
        THEN: Default value is 'sqlglot'
        """
        flags = FeatureFlags()
        assert flags.sql_engine == "sqlglot"

    def test_sql_engine_can_be_sqlalchemy(self) -> None:
        """
        GIVEN: FeatureFlags with sql_engine='sqlalchemy'
        WHEN: sql_engine is read
        THEN: Value is 'sqlalchemy' (legacy rollback)
        """
        flags = FeatureFlags(sql_engine="sqlalchemy")
        assert flags.sql_engine == "sqlalchemy"

    def test_sql_engine_can_be_dual(self) -> None:
        """
        GIVEN: FeatureFlags with sql_engine='dual'
        WHEN: sql_engine is read
        THEN: Value is 'dual' (comparison mode)
        """
        flags = FeatureFlags(sql_engine="dual")
        assert flags.sql_engine == "dual"

    def test_egress_validation_default_enabled(self) -> None:
        """
        GIVEN: Default FeatureFlags
        WHEN: enable_sql_egress_validation is read
        THEN: Egress validation is enabled by default
        """
        flags = FeatureFlags()
        assert flags.enable_sql_egress_validation is True

    def test_egress_validation_can_be_disabled(self) -> None:
        """
        GIVEN: FeatureFlags with enable_sql_egress_validation=False
        WHEN: enable_sql_egress_validation is read
        THEN: Egress validation is disabled (dev/testing mode)
        """
        flags = FeatureFlags(enable_sql_egress_validation=False)
        assert flags.enable_sql_egress_validation is False

    def test_query_timeout_default(self) -> None:
        """
        GIVEN: Default FeatureFlags
        WHEN: sql_query_timeout_seconds is read
        THEN: Default timeout is 30.0 seconds
        """
        flags = FeatureFlags()
        assert flags.sql_query_timeout_seconds == 30.0

    def test_query_timeout_custom(self) -> None:
        """
        GIVEN: FeatureFlags with custom timeout
        WHEN: sql_query_timeout_seconds is read
        THEN: Custom timeout is used
        """
        flags = FeatureFlags(sql_query_timeout_seconds=60.0)
        assert flags.sql_query_timeout_seconds == 60.0

    def test_max_row_limit_default(self) -> None:
        """
        GIVEN: Default FeatureFlags
        WHEN: sql_max_row_limit is read
        THEN: Default max row limit is 10000
        """
        flags = FeatureFlags()
        assert flags.sql_max_row_limit == 10000

    def test_max_row_limit_custom(self) -> None:
        """
        GIVEN: FeatureFlags with custom row limit
        WHEN: sql_max_row_limit is read
        THEN: Custom row limit is used
        """
        flags = FeatureFlags(sql_max_row_limit=50000)
        assert flags.sql_max_row_limit == 50000

    def test_sql_flags_in_to_dict(self) -> None:
        """
        GIVEN: Default FeatureFlags
        WHEN: to_dict() is called
        THEN: SQL-related keys are present in the returned dict
        """
        flags = FeatureFlags()
        d = flags.to_dict()
        assert "sql_engine" in d
        assert "enable_sql_egress_validation" in d
        assert "sql_query_timeout_seconds" in d
        assert "sql_max_row_limit" in d

    def test_sql_flags_in_admin_ui_features(self) -> None:
        """
        GIVEN: Default FeatureFlags
        WHEN: get_ui_features_for_role('admin') is called
        THEN: SQL execution flags are included
        """
        flags = FeatureFlags()
        ui = flags.get_ui_features_for_role("admin")
        assert "sql_engine" in ui
        assert "sql_egress_validation" in ui
