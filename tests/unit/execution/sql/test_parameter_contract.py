"""
Unit tests for ParameterContract.

Tests driver-specific parameter translation, positional vs named styles,
placeholder validation, missing/unused parameter detection, and parse error handling.
"""

import gc
import logging

import pytest

from mcp_server_langgraph.execution.sql.exceptions import SQLParseError
from mcp_server_langgraph.execution.sql.parameter_contract import ParameterContract

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Constructor / driver validation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParameterContractConstructor:
    """Verify constructor validates driver names and sets up styles correctly."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_valid_driver_asyncpg(self):
        pc = ParameterContract("asyncpg")
        assert pc.driver == "asyncpg"
        assert pc.style["style"] == "positional"
        assert pc.style["format"] == "${}"

    def test_valid_driver_aiosqlite(self):
        pc = ParameterContract("aiosqlite")
        assert pc.driver == "aiosqlite"
        assert pc.style["style"] == "positional"
        assert pc.style["format"] == "?"

    def test_valid_driver_psycopg(self):
        pc = ParameterContract("psycopg")
        assert pc.driver == "psycopg"
        assert pc.style["style"] == "named"
        assert pc.style["format"] == "%({})s"

    def test_valid_driver_bigquery(self):
        pc = ParameterContract("bigquery")
        assert pc.driver == "bigquery"
        assert pc.style["style"] == "named"
        assert pc.style["format"] == "@{}"

    def test_valid_driver_snowflake(self):
        pc = ParameterContract("snowflake")
        assert pc.driver == "snowflake"
        assert pc.style["style"] == "named"
        assert pc.style["format"] == ":{}"

    def test_valid_driver_sqljs(self):
        pc = ParameterContract("sql.js")
        assert pc.driver == "sql.js"
        assert pc.style["style"] == "positional"
        assert pc.style["format"] == "?"

    def test_unknown_driver_raises_value_error(self):
        with pytest.raises(ValueError, match="Unknown driver"):
            ParameterContract("nonexistent_driver")

    def test_unknown_driver_error_lists_valid_drivers(self):
        with pytest.raises(ValueError, match="asyncpg"):
            ParameterContract("invalid")

    def test_default_dialect_is_postgres(self):
        pc = ParameterContract("asyncpg")
        assert pc.dialect == "postgres"

    def test_contract_with_custom_dialect_binding(self):
        pc = ParameterContract("bigquery", dialect="bigquery")
        assert pc.dialect == "bigquery"


# ---------------------------------------------------------------------------
# translate() - positional drivers (asyncpg, aiosqlite, sql.js)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParameterContractTranslatePositional:
    """Verify translate() for positional-style drivers."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    def asyncpg_contract(self):
        return ParameterContract("asyncpg")

    @pytest.fixture
    def aiosqlite_contract(self):
        return ParameterContract("aiosqlite")

    @pytest.fixture
    def sqljs_contract(self):
        return ParameterContract("sql.js")

    def test_asyncpg_single_placeholder(self, asyncpg_contract):
        sql = "SELECT * FROM users WHERE id = :id"
        translated_sql, params = asyncpg_contract.translate(sql, {"id": 42})
        assert "$1" in translated_sql
        assert params == [42]

    def test_asyncpg_multiple_placeholders(self, asyncpg_contract):
        sql = "SELECT * FROM users WHERE id = :id AND name = :name"
        translated_sql, params = asyncpg_contract.translate(sql, {"id": 42, "name": "alice"})
        assert "$1" in translated_sql
        assert "$2" in translated_sql
        assert len(params) == 2

    def test_aiosqlite_single_placeholder(self, aiosqlite_contract):
        sql = "SELECT * FROM users WHERE id = :id"
        translated_sql, params = aiosqlite_contract.translate(sql, {"id": 42})
        assert "?" in translated_sql
        assert params == [42]

    def test_sqljs_single_placeholder(self, sqljs_contract):
        sql = "SELECT * FROM users WHERE id = :id"
        translated_sql, params = sqljs_contract.translate(sql, {"id": 42})
        assert "?" in translated_sql
        assert params == [42]

    def test_positional_returns_list(self, asyncpg_contract):
        sql = "SELECT * FROM users WHERE id = :id"
        _, params = asyncpg_contract.translate(sql, {"id": 1})
        assert isinstance(params, list)

    def test_no_placeholders_no_params_returns_empty_list(self, asyncpg_contract):
        sql = "SELECT * FROM users"
        translated_sql, params = asyncpg_contract.translate(sql, {})
        assert params == []

    def test_no_placeholders_with_params_raises(self, asyncpg_contract):
        sql = "SELECT * FROM users"
        with pytest.raises(SQLParseError, match="no placeholders"):
            asyncpg_contract.translate(sql, {"id": 1})


# ---------------------------------------------------------------------------
# translate() - named drivers (psycopg, bigquery, snowflake)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParameterContractTranslateNamed:
    """Verify translate() for named-style drivers."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    def psycopg_contract(self):
        return ParameterContract("psycopg")

    @pytest.fixture
    def bigquery_contract(self):
        return ParameterContract("bigquery", dialect="bigquery")

    @pytest.fixture
    def snowflake_contract(self):
        return ParameterContract("snowflake", dialect="snowflake")

    def test_psycopg_single_placeholder(self, psycopg_contract):
        sql = "SELECT * FROM users WHERE id = :id"
        translated_sql, params = psycopg_contract.translate(sql, {"id": 42})
        assert "%(ids)" in translated_sql or "%(id" in translated_sql
        assert params == {"id": 42}

    def test_psycopg_returns_original_params_dict(self, psycopg_contract):
        original_params = {"id": 42, "name": "alice"}
        sql = "SELECT * FROM users WHERE id = :id AND name = :name"
        _, params = psycopg_contract.translate(sql, original_params)
        assert isinstance(params, dict)
        assert params == original_params

    def test_bigquery_single_placeholder(self, bigquery_contract):
        sql = "SELECT * FROM users WHERE id = :id"
        translated_sql, params = bigquery_contract.translate(sql, {"id": 42})
        assert isinstance(params, dict)

    def test_snowflake_single_placeholder(self, snowflake_contract):
        sql = "SELECT * FROM users WHERE id = :id"
        translated_sql, params = snowflake_contract.translate(sql, {"id": 42})
        assert isinstance(params, dict)

    def test_named_no_placeholders_no_params_returns_empty_dict(self, psycopg_contract):
        sql = "SELECT * FROM users"
        translated_sql, params = psycopg_contract.translate(sql, {})
        assert params == {}

    def test_named_no_placeholders_with_params_raises(self, psycopg_contract):
        sql = "SELECT * FROM users"
        with pytest.raises(SQLParseError, match="no placeholders"):
            psycopg_contract.translate(sql, {"id": 1})


# ---------------------------------------------------------------------------
# translate() - missing parameters
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParameterContractTranslateMissingParams:
    """Verify translate() raises on missing parameters."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    def contract(self):
        return ParameterContract("asyncpg")

    def test_missing_single_param_raises(self, contract):
        sql = "SELECT * FROM users WHERE id = :id"
        with pytest.raises(SQLParseError, match="Missing parameters"):
            contract.translate(sql, {})

    def test_missing_one_of_multiple_params_raises(self, contract):
        sql = "SELECT * FROM users WHERE id = :id AND name = :name"
        with pytest.raises(SQLParseError, match="Missing parameters"):
            contract.translate(sql, {"id": 1})


# ---------------------------------------------------------------------------
# translate() - SQL parse error
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParameterContractTranslateSQLParseError:
    """Verify translate() wraps ParseError as SQLParseError."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    def contract(self):
        return ParameterContract("asyncpg")

    def test_unparseable_sql_raises_sql_parse_error(self, contract):
        # sqlglot raises ParseError on structurally invalid SQL
        # The implementation catches ParseError and wraps it as SQLParseError
        with pytest.raises(SQLParseError, match="Failed to parse SQL"):
            contract.translate("SELECT FROM WHERE", {"x": 1})


# ---------------------------------------------------------------------------
# validate_param_count()
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParameterContractValidateParamCount:
    """Verify validate_param_count() detects missing and unused params."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.fixture
    def contract(self):
        return ParameterContract("asyncpg")

    def test_all_params_present_no_error(self, contract):
        sql = "SELECT * FROM users WHERE id = :id AND name = :name"
        # Should not raise
        contract.validate_param_count(sql, {"id": 1, "name": "alice"})

    def test_no_placeholders_no_params_no_error(self, contract):
        sql = "SELECT * FROM users"
        contract.validate_param_count(sql, {})

    def test_missing_params_raises(self, contract):
        sql = "SELECT * FROM users WHERE id = :id AND name = :name"
        with pytest.raises(SQLParseError, match="Missing parameters"):
            contract.validate_param_count(sql, {"id": 1})

    def test_all_params_missing_raises(self, contract):
        sql = "SELECT * FROM users WHERE id = :id"
        with pytest.raises(SQLParseError, match="Missing parameters"):
            contract.validate_param_count(sql, {})

    def test_unused_params_logs_warning(self, contract, caplog):
        sql = "SELECT * FROM users WHERE id = :id"
        with caplog.at_level(logging.WARNING):
            contract.validate_param_count(sql, {"id": 1, "extra": "unused"})
        assert "Unused parameters" in caplog.text

    def test_unused_params_does_not_raise(self, contract):
        sql = "SELECT * FROM users WHERE id = :id"
        # Should not raise, just warn
        contract.validate_param_count(sql, {"id": 1, "extra": "unused"})

    def test_validate_parse_error_raises(self, contract):
        with pytest.raises(SQLParseError, match="Failed to parse SQL"):
            contract.validate_param_count("SELECT FROM WHERE", {"x": 1})


# ---------------------------------------------------------------------------
# All driver styles parameterized
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParameterContractAllDriverStyles:
    """Parameterized tests across all supported driver styles."""

    def teardown_method(self) -> None:
        gc.collect()

    @pytest.mark.parametrize(
        "driver",
        ["asyncpg", "aiosqlite", "psycopg", "bigquery", "snowflake", "sql.js"],
    )
    def test_driver_has_style_and_format(self, driver):
        pc = ParameterContract(driver)
        assert pc.style["style"] in ("positional", "named")
        assert isinstance(pc.style["format"], str)

    @pytest.mark.parametrize(
        "driver,expected_style",
        [
            ("asyncpg", "positional"),
            ("aiosqlite", "positional"),
            ("sql.js", "positional"),
            ("psycopg", "named"),
            ("bigquery", "named"),
            ("snowflake", "named"),
        ],
    )
    def test_driver_style_classification(self, driver, expected_style):
        pc = ParameterContract(driver)
        assert pc.style["style"] == expected_style

    @pytest.mark.parametrize(
        "driver",
        ["asyncpg", "aiosqlite", "psycopg", "sql.js"],
    )
    def test_translate_no_params_no_placeholders(self, driver):
        """All drivers should handle parameterless queries."""
        pc = ParameterContract(driver)
        translated_sql, params = pc.translate("SELECT 1", {})
        assert translated_sql  # Non-empty
        if pc.style["style"] == "positional":
            assert isinstance(params, list)
        else:
            assert isinstance(params, dict)


# ---------------------------------------------------------------------------
# New driver styles (mysql, duckdb, redshift, clickhouse, trino)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestParameterContractNewDriverStyles:
    """Verify DRIVER_STYLES entries for newly added drivers."""

    def teardown_method(self) -> None:
        gc.collect()

    def test_aiomysql_driver_style(self):
        pc = ParameterContract("aiomysql")
        assert pc.style["style"] == "positional"
        assert pc.style["format"] == "%s"

    def test_duckdb_driver_style(self):
        pc = ParameterContract("duckdb")
        assert pc.style["style"] == "positional"
        assert pc.style["format"] == "?"

    def test_redshift_connector_driver_style(self):
        pc = ParameterContract("redshift_connector")
        assert pc.style["style"] == "named"
        assert pc.style["format"] == "%({})s"

    def test_asynch_driver_style(self):
        pc = ParameterContract("asynch")
        assert pc.style["style"] == "named"
        assert pc.style["format"] == "%({})s"

    def test_trino_driver_style(self):
        pc = ParameterContract("trino")
        assert pc.style["style"] == "positional"
        assert pc.style["format"] == "?"

    def test_aiomysql_translate_positional(self):
        pc = ParameterContract("aiomysql")
        sql = "SELECT * FROM users WHERE id = :id"
        translated_sql, params = pc.translate(sql, {"id": 42})
        assert "%s" in translated_sql
        assert params == [42]

    def test_duckdb_translate_positional(self):
        pc = ParameterContract("duckdb")
        sql = "SELECT * FROM users WHERE id = :id"
        translated_sql, params = pc.translate(sql, {"id": 42})
        assert "?" in translated_sql
        assert params == [42]

    def test_redshift_translate_named(self):
        pc = ParameterContract("redshift_connector")
        sql = "SELECT * FROM users WHERE id = :id"
        translated_sql, params = pc.translate(sql, {"id": 42})
        assert isinstance(params, dict)
        assert params == {"id": 42}

    def test_asynch_translate_named(self):
        pc = ParameterContract("asynch")
        sql = "SELECT * FROM users WHERE id = :id"
        translated_sql, params = pc.translate(sql, {"id": 42})
        assert isinstance(params, dict)

    def test_trino_translate_positional(self):
        pc = ParameterContract("trino")
        sql = "SELECT * FROM users WHERE id = :id"
        translated_sql, params = pc.translate(sql, {"id": 42})
        assert "?" in translated_sql
        assert params == [42]

    @pytest.mark.parametrize(
        "driver,expected_style",
        [
            ("aiomysql", "positional"),
            ("duckdb", "positional"),
            ("trino", "positional"),
            ("redshift_connector", "named"),
            ("asynch", "named"),
        ],
    )
    def test_new_driver_style_classification(self, driver, expected_style):
        pc = ParameterContract(driver)
        assert pc.style["style"] == expected_style

    @pytest.mark.parametrize(
        "driver",
        ["aiomysql", "duckdb", "redshift_connector", "asynch", "trino"],
    )
    def test_new_driver_translate_no_params(self, driver):
        """New drivers should handle parameterless queries."""
        pc = ParameterContract(driver)
        translated_sql, params = pc.translate("SELECT 1", {})
        assert translated_sql
        if pc.style["style"] == "positional":
            assert isinstance(params, list)
        else:
            assert isinstance(params, dict)
