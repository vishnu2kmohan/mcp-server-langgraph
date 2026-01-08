"""Tests for core.numeric module.

TDD: Tests for safe numeric utilities that handle NaN/Inf values
from Prometheus metrics and other external sources.
"""

from __future__ import annotations

import gc
import math

import pytest

pytestmark = pytest.mark.unit


@pytest.mark.xdist_group(name="core_numeric")
class TestSafeFloat:
    """Test suite for safe_float function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_returns_value_for_valid_float(self) -> None:
        """GIVEN valid float values
        WHEN safe_float() is called
        THEN it returns the original values
        """
        from mcp_server_langgraph.core.numeric import safe_float

        assert safe_float(1.5) == 1.5
        assert safe_float(0.0) == 0.0
        assert safe_float(100.123) == 100.123
        assert safe_float(-42.5) == -42.5

    def test_returns_default_for_none(self) -> None:
        """GIVEN None value
        WHEN safe_float() is called
        THEN it returns the default value
        """
        from mcp_server_langgraph.core.numeric import safe_float

        assert safe_float(None) == 0.0
        assert safe_float(None, default=1.0) == 1.0
        assert safe_float(None, default=-5.0) == -5.0

    def test_returns_default_for_nan(self) -> None:
        """GIVEN NaN value (from Prometheus histogram_quantile with no data)
        WHEN safe_float() is called
        THEN it returns the default value
        """
        from mcp_server_langgraph.core.numeric import safe_float

        assert safe_float(float("nan")) == 0.0
        assert safe_float(math.nan) == 0.0
        assert safe_float(float("nan"), default=5.0) == 5.0

    def test_returns_default_for_positive_inf(self) -> None:
        """GIVEN positive infinity value
        WHEN safe_float() is called
        THEN it returns the default value
        """
        from mcp_server_langgraph.core.numeric import safe_float

        assert safe_float(float("inf")) == 0.0
        assert safe_float(math.inf) == 0.0
        assert safe_float(float("inf"), default=-1.0) == -1.0

    def test_returns_default_for_negative_inf(self) -> None:
        """GIVEN negative infinity value
        WHEN safe_float() is called
        THEN it returns the default value
        """
        from mcp_server_langgraph.core.numeric import safe_float

        assert safe_float(float("-inf")) == 0.0
        assert safe_float(-math.inf) == 0.0


@pytest.mark.xdist_group(name="core_numeric")
class TestSafeAverage:
    """Test suite for safe_average function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_returns_average_for_valid_list(self) -> None:
        """GIVEN a list of valid float values
        WHEN safe_average() is called
        THEN it returns the correct average
        """
        from mcp_server_langgraph.core.numeric import safe_average

        assert safe_average([1.0, 2.0, 3.0]) == 2.0
        assert safe_average([10.0]) == 10.0
        assert safe_average([0.0, 0.0, 0.0]) == 0.0

    def test_returns_default_for_empty_list(self) -> None:
        """GIVEN an empty list
        WHEN safe_average() is called
        THEN it returns the default value
        """
        from mcp_server_langgraph.core.numeric import safe_average

        assert safe_average([]) == 0.0
        assert safe_average([], default=5.0) == 5.0

    def test_filters_out_nan_values(self) -> None:
        """GIVEN a list containing NaN values
        WHEN safe_average() is called
        THEN it filters out NaN and averages the rest
        """
        from mcp_server_langgraph.core.numeric import safe_average

        assert safe_average([float("nan"), 1.0, 2.0]) == 1.5
        assert safe_average([1.0, float("nan"), 3.0]) == 2.0

    def test_filters_out_inf_values(self) -> None:
        """GIVEN a list containing Inf values
        WHEN safe_average() is called
        THEN it filters out Inf and averages the rest
        """
        from mcp_server_langgraph.core.numeric import safe_average

        assert safe_average([float("inf"), 1.0, 2.0]) == 1.5
        assert safe_average([1.0, float("-inf"), 3.0]) == 2.0

    def test_returns_default_if_all_values_invalid(self) -> None:
        """GIVEN a list of only invalid values
        WHEN safe_average() is called
        THEN it returns the default
        """
        from mcp_server_langgraph.core.numeric import safe_average

        assert safe_average([float("nan"), float("inf")]) == 0.0
        assert safe_average([float("nan")], default=-1.0) == -1.0


@pytest.mark.xdist_group(name="core_numeric")
class TestSafeSum:
    """Test suite for safe_sum function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_returns_sum_for_valid_list(self) -> None:
        """GIVEN a list of valid float values
        WHEN safe_sum() is called
        THEN it returns the correct sum
        """
        from mcp_server_langgraph.core.numeric import safe_sum

        assert safe_sum([1.0, 2.0, 3.0]) == 6.0
        assert safe_sum([10.0]) == 10.0

    def test_filters_out_nan_values(self) -> None:
        """GIVEN a list containing NaN values
        WHEN safe_sum() is called
        THEN it filters out NaN and sums the rest
        """
        from mcp_server_langgraph.core.numeric import safe_sum

        assert safe_sum([float("nan"), 1.0, 2.0]) == 3.0

    def test_returns_default_for_empty_list(self) -> None:
        """GIVEN an empty list
        WHEN safe_sum() is called
        THEN it returns the default
        """
        from mcp_server_langgraph.core.numeric import safe_sum

        assert safe_sum([]) == 0.0
        assert safe_sum([], default=5.0) == 5.0


@pytest.mark.xdist_group(name="core_numeric")
class TestSafeRound:
    """Test suite for safe_round function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_rounds_valid_value(self) -> None:
        """GIVEN a valid float value
        WHEN safe_round() is called
        THEN it rounds correctly
        """
        from mcp_server_langgraph.core.numeric import safe_round

        assert safe_round(1.567, 2) == 1.57
        assert safe_round(1.5, 0) == 2.0
        assert safe_round(1.234, 1) == 1.2

    def test_returns_default_for_nan(self) -> None:
        """GIVEN a NaN value
        WHEN safe_round() is called
        THEN it returns the default rounded
        """
        from mcp_server_langgraph.core.numeric import safe_round

        assert safe_round(float("nan"), 2) == 0.0
        assert safe_round(float("nan"), 2, default=1.0) == 1.0

    def test_returns_default_for_none(self) -> None:
        """GIVEN a None value
        WHEN safe_round() is called
        THEN it returns the default rounded
        """
        from mcp_server_langgraph.core.numeric import safe_round

        assert safe_round(None, 1) == 0.0


@pytest.mark.xdist_group(name="core_numeric")
class TestSafeDivide:
    """Test suite for safe_divide function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_divides_valid_values(self) -> None:
        """GIVEN valid numerator and denominator
        WHEN safe_divide() is called
        THEN it returns the correct result
        """
        from mcp_server_langgraph.core.numeric import safe_divide

        assert safe_divide(10.0, 2.0) == 5.0
        assert safe_divide(1.0, 4.0) == 0.25

    def test_returns_default_for_zero_denominator(self) -> None:
        """GIVEN zero denominator
        WHEN safe_divide() is called
        THEN it returns the default (avoids ZeroDivisionError)
        """
        from mcp_server_langgraph.core.numeric import safe_divide

        assert safe_divide(1.0, 0.0) == 0.0
        assert safe_divide(10.0, 0.0, default=-1.0) == -1.0

    def test_returns_default_for_nan_numerator(self) -> None:
        """GIVEN NaN numerator
        WHEN safe_divide() is called
        THEN it returns the default
        """
        from mcp_server_langgraph.core.numeric import safe_divide

        assert safe_divide(float("nan"), 2.0) == 0.0

    def test_returns_default_for_nan_denominator(self) -> None:
        """GIVEN NaN denominator
        WHEN safe_divide() is called
        THEN it returns the default
        """
        from mcp_server_langgraph.core.numeric import safe_divide

        assert safe_divide(1.0, float("nan")) == 0.0

    def test_returns_default_for_none_values(self) -> None:
        """GIVEN None numerator or denominator
        WHEN safe_divide() is called
        THEN it returns the default
        """
        from mcp_server_langgraph.core.numeric import safe_divide

        assert safe_divide(None, 2.0) == 0.0
        assert safe_divide(1.0, None) == 0.0
        assert safe_divide(None, None) == 0.0

    def test_returns_default_for_inf_result(self) -> None:
        """GIVEN values that would produce Inf
        WHEN safe_divide() is called
        THEN it returns the default
        """
        from mcp_server_langgraph.core.numeric import safe_divide

        # Very small denominator could overflow
        assert safe_divide(float("inf"), 1.0) == 0.0


@pytest.mark.xdist_group(name="core_numeric")
class TestSafePercentage:
    """Test suite for safe_percentage function."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_calculates_percentage_for_valid_values(self) -> None:
        """GIVEN valid numerator and denominator
        WHEN safe_percentage() is called
        THEN it returns the correct percentage
        """
        from mcp_server_langgraph.core.numeric import safe_percentage

        assert safe_percentage(50, 100) == 50.0
        assert safe_percentage(25, 100) == 25.0
        assert safe_percentage(100, 100) == 100.0
        assert safe_percentage(0, 100) == 0.0
        assert safe_percentage(1, 4) == 25.0

    def test_returns_default_for_zero_denominator(self) -> None:
        """GIVEN zero denominator
        WHEN safe_percentage() is called
        THEN it returns the default (avoids ZeroDivisionError)
        """
        from mcp_server_langgraph.core.numeric import safe_percentage

        assert safe_percentage(50, 0) == 0.0
        assert safe_percentage(50, 0, default=50.0) == 50.0

    def test_returns_default_for_nan_numerator(self) -> None:
        """GIVEN NaN numerator
        WHEN safe_percentage() is called
        THEN it returns the default
        """
        from mcp_server_langgraph.core.numeric import safe_percentage

        assert safe_percentage(float("nan"), 100) == 0.0

    def test_returns_default_for_nan_denominator(self) -> None:
        """GIVEN NaN denominator
        WHEN safe_percentage() is called
        THEN it returns the default
        """
        from mcp_server_langgraph.core.numeric import safe_percentage

        assert safe_percentage(50, float("nan")) == 0.0

    def test_returns_default_for_none_values(self) -> None:
        """GIVEN None numerator or denominator
        WHEN safe_percentage() is called
        THEN it returns the default
        """
        from mcp_server_langgraph.core.numeric import safe_percentage

        assert safe_percentage(None, 100) == 0.0
        assert safe_percentage(50, None) == 0.0
        assert safe_percentage(None, None) == 0.0

    def test_clamps_to_bounds_by_default(self) -> None:
        """GIVEN values that would exceed 0-100 range
        WHEN safe_percentage() is called with default clamp=True
        THEN it clamps to 0-100
        """
        from mcp_server_langgraph.core.numeric import safe_percentage

        # Over 100%
        assert safe_percentage(150, 100) == 100.0
        # Negative (shouldn't happen but defensive)
        assert safe_percentage(-50, 100) == 0.0

    def test_no_clamp_when_disabled(self) -> None:
        """GIVEN values that would exceed 0-100 range
        WHEN safe_percentage() is called with clamp=False
        THEN it returns the actual percentage
        """
        from mcp_server_langgraph.core.numeric import safe_percentage

        assert safe_percentage(150, 100, clamp=False) == 150.0
        assert safe_percentage(-50, 100, clamp=False) == -50.0

    def test_safe_percentage_with_custom_bounds_clamps_to_range(self) -> None:
        """GIVEN custom min/max bounds
        WHEN safe_percentage() is called with bounds
        THEN it clamps to custom range
        """
        from mcp_server_langgraph.core.numeric import safe_percentage

        # Clamp to 10-90 range
        assert safe_percentage(150, 100, min_val=10.0, max_val=90.0) == 90.0
        assert safe_percentage(5, 100, min_val=10.0, max_val=90.0) == 10.0
        assert safe_percentage(50, 100, min_val=10.0, max_val=90.0) == 50.0

    def test_rounds_to_specified_precision(self) -> None:
        """GIVEN a percentage that needs rounding
        WHEN safe_percentage() is called with ndigits
        THEN it rounds correctly
        """
        from mcp_server_langgraph.core.numeric import safe_percentage

        assert safe_percentage(1, 3, ndigits=2) == 33.33
        assert safe_percentage(1, 3, ndigits=1) == 33.3
        assert safe_percentage(1, 3, ndigits=0) == 33.0

    def test_handles_inf_values(self) -> None:
        """GIVEN Inf numerator or denominator
        WHEN safe_percentage() is called
        THEN it returns the default
        """
        from mcp_server_langgraph.core.numeric import safe_percentage

        assert safe_percentage(float("inf"), 100) == 0.0
        assert safe_percentage(100, float("inf")) == 0.0
        assert safe_percentage(float("-inf"), 100) == 0.0


@pytest.mark.xdist_group(name="core_numeric")
class TestSafeFloatAnnotation:
    """Test suite for SafeFloat annotated type for OpenAPI documentation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_safe_float_type_exists(self) -> None:
        """GIVEN the core.numeric module
        WHEN importing SafeFloat
        THEN it should be available
        """
        from mcp_server_langgraph.core.numeric import SafeFloat

        assert SafeFloat is not None

    def test_safe_float_used_in_pydantic_model(self) -> None:
        """GIVEN a Pydantic model using SafeFloat
        WHEN the model is instantiated with NaN
        THEN the value is sanitized to 0.0
        """
        from pydantic import BaseModel

        from mcp_server_langgraph.core.numeric import SafeFloat

        class TestModel(BaseModel):
            value: SafeFloat

        model = TestModel(value=float("nan"))
        assert model.value == 0.0
        assert math.isfinite(model.value)

    def test_safe_float_preserves_valid_values(self) -> None:
        """GIVEN a Pydantic model using SafeFloat
        WHEN the model is instantiated with valid floats
        THEN the values are preserved
        """
        from pydantic import BaseModel

        from mcp_server_langgraph.core.numeric import SafeFloat

        class TestModel(BaseModel):
            value: SafeFloat

        model = TestModel(value=42.5)
        assert model.value == 42.5

    def test_safe_float_json_schema_has_description(self) -> None:
        """GIVEN a Pydantic model using SafeFloat
        WHEN generating JSON schema
        THEN the description indicates NaN-safety
        """
        from pydantic import BaseModel

        from mcp_server_langgraph.core.numeric import SafeFloat

        class TestModel(BaseModel):
            latency_ms: SafeFloat

        schema = TestModel.model_json_schema()
        props = schema.get("properties", {})
        latency_prop = props.get("latency_ms", {})

        # Should have description mentioning NaN safety
        description = latency_prop.get("description", "")
        assert "NaN" in description or "safe" in description.lower()

    def test_safe_float_handles_infinity(self) -> None:
        """GIVEN a Pydantic model using SafeFloat
        WHEN the model is instantiated with Infinity
        THEN the value is sanitized to 0.0
        """
        from pydantic import BaseModel

        from mcp_server_langgraph.core.numeric import SafeFloat

        class TestModel(BaseModel):
            value: SafeFloat

        model = TestModel(value=float("inf"))
        assert model.value == 0.0

        model2 = TestModel(value=float("-inf"))
        assert model2.value == 0.0

    def test_safe_float_handles_none(self) -> None:
        """GIVEN a Pydantic model using Optional[SafeFloat]
        WHEN the model is instantiated with None
        THEN the behavior is as expected
        """
        from pydantic import BaseModel

        from mcp_server_langgraph.core.numeric import SafeFloat

        class TestModel(BaseModel):
            value: SafeFloat | None = None

        model = TestModel(value=None)
        assert model.value is None

    def test_safe_float_json_serializable(self) -> None:
        """GIVEN a Pydantic model using SafeFloat with NaN input
        WHEN serialized to JSON
        THEN no error occurs
        """
        import json

        from pydantic import BaseModel

        from mcp_server_langgraph.core.numeric import SafeFloat

        class TestModel(BaseModel):
            value: SafeFloat

        model = TestModel(value=float("nan"))
        json_str = model.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["value"] == 0.0
