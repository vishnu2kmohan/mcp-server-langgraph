"""Performance benchmarks for critical system components."""

import asyncio
import gc
import time
from datetime import datetime, timedelta
from unittest.mock import Mock

import jwt
import pytest


# Benchmark utilities
class BenchmarkTimer:
    """Context manager for timing operations."""

    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.duration = None

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.perf_counter()
        self.duration = self.end_time - self.start_time


# JWT Authentication Benchmarks
@pytest.mark.benchmark
@pytest.mark.xdist_group(name="performance_benchmarks_tests")
class TestJWTBenchmarks:
    """Benchmark JWT token operations."""

    def setup_method(self):
        """Reset state BEFORE test to prevent MCP_SKIP_AUTH pollution"""
        import os

        import mcp_server_langgraph.auth.middleware as middleware_module

        middleware_module._global_auth_middleware = None
        os.environ["MCP_SKIP_AUTH"] = "false"

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def jwt_config(self):
        """JWT configuration for benchmarks."""
        return {
            "secret_key": "test-secret-key-for-benchmarking-purposes-only",
            "algorithm": "HS256",
        }

    @pytest.fixture
    def sample_payload(self):
        """Sample JWT payload."""
        from datetime import timezone

        now = datetime.now(timezone.utc)
        return {
            "sub": "test-user",
            "exp": now + timedelta(hours=1),
            "iat": now,
            "roles": ["user", "developer"],
        }

    def test_jwt_encoding_performance(self, jwt_config, sample_payload, percentile_benchmark):
        """Benchmark JWT token encoding.

        Requirement: Token encoding p95 < 1.5ms, p99 < 2ms (more stable than mean < 1ms).
        """

        def encode_token():
            return jwt.encode(sample_payload, jwt_config["secret_key"], algorithm=jwt_config["algorithm"])

        # Run benchmark
        result = percentile_benchmark(encode_token)

        # Verify token is valid
        assert isinstance(result, str)
        assert len(result) > 0

        # Performance assertions: percentile-based for stability
        percentile_benchmark.assert_percentile(95, 0.0015, "JWT encoding p95")  # p95 < 1.5ms
        percentile_benchmark.assert_percentile(99, 0.002, "JWT encoding p99")  # p99 < 2ms

    def test_jwt_decoding_performance(self, jwt_config, sample_payload, percentile_benchmark):
        """Benchmark JWT token decoding.

        Requirement: Token decoding p95 < 1.5ms, p99 < 2ms (more stable than mean < 1ms).
        """
        # Pre-generate token
        token = jwt.encode(sample_payload, jwt_config["secret_key"], algorithm=jwt_config["algorithm"])

        def decode_token():
            return jwt.decode(token, jwt_config["secret_key"], algorithms=[jwt_config["algorithm"]])

        # Run benchmark
        result = percentile_benchmark(decode_token)

        # Verify payload
        assert result["sub"] == sample_payload["sub"]

        # Performance assertions: percentile-based for stability
        percentile_benchmark.assert_percentile(95, 0.0015, "JWT decoding p95")  # p95 < 1.5ms
        percentile_benchmark.assert_percentile(99, 0.002, "JWT decoding p99")  # p99 < 2ms

    def test_jwt_validation_performance(self, jwt_config, sample_payload, percentile_benchmark):
        """Benchmark JWT token validation with expiration check.

        Requirement: Token validation p95 < 2.5ms, p99 < 3ms (more stable than mean < 2ms).
        """
        from datetime import timezone

        # Create tokens with various expiration times
        token = jwt.encode(sample_payload, jwt_config["secret_key"], algorithm=jwt_config["algorithm"])

        def validate_token():
            try:
                decoded = jwt.decode(token, jwt_config["secret_key"], algorithms=[jwt_config["algorithm"]])
                # Verify expiration
                exp = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
                now = datetime.now(timezone.utc)
                return exp > now
            except jwt.ExpiredSignatureError:
                return False

        # Run benchmark
        result = percentile_benchmark(validate_token)

        assert result is True

        # Performance assertions: percentile-based for stability
        percentile_benchmark.assert_percentile(95, 0.0025, "JWT validation p95")  # p95 < 2.5ms
        percentile_benchmark.assert_percentile(99, 0.003, "JWT validation p99")  # p99 < 3ms


# OpenFGA Authorization Benchmarks
@pytest.mark.benchmark
@pytest.mark.openfga
@pytest.mark.xdist_group(name="performance_benchmarks_tests")
class TestOpenFGABenchmarks:
    """Benchmark OpenFGA authorization checks."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def mock_openfga_client(self):
        """Mock OpenFGA client for benchmarking."""
        client = Mock()

        # Mock check response
        async def mock_check(*args, **kwargs):
            # Simulate network latency
            await asyncio.sleep(0.005)  # 5ms simulated latency
            return {"allowed": True}

        client.check = mock_check
        return client

    def test_authorization_check_performance(self, mock_openfga_client, percentile_benchmark):
        """Benchmark OpenFGA authorization check.

        Requirement: Authorization check p95 < 60ms, p99 < 75ms (more stable than mean < 50ms).

        Note: Uses async function directly - PercentileBenchmark creates a single event loop
        for all iterations, preventing event loop creation overhead from inflating measurements.
        """

        async def check_authorization():
            return await mock_openfga_client.check(user="user:test-user", relation="viewer", object="document:test-doc")

        # Run benchmark directly with async function (single event loop for all iterations)
        result = percentile_benchmark(check_authorization)

        assert result["allowed"] is True

        # Performance assertions: percentile-based for stability (includes network simulation)
        percentile_benchmark.assert_percentile(95, 0.060, "OpenFGA check p95")  # p95 < 60ms
        percentile_benchmark.assert_percentile(99, 0.075, "OpenFGA check p99")  # p99 < 75ms

    def test_batch_authorization_performance(self, mock_openfga_client, percentile_benchmark):
        """Benchmark batch authorization checks.

        Requirement: 10 batch checks p95 < 250ms, p99 < 300ms (more stable than mean < 200ms).

        Note: Uses async function directly - PercentileBenchmark creates a single event loop
        for all iterations, providing accurate measurements without event loop overhead.
        """

        async def batch_check():
            results = []
            for i in range(10):
                result = await mock_openfga_client.check(
                    user=f"user:test-user-{i}", relation="viewer", object=f"document:doc-{i}"
                )
                results.append(result)
            return results

        # Run benchmark directly with async function (single event loop for all iterations)
        results = percentile_benchmark(batch_check)

        assert len(results) == 10
        assert all(r["allowed"] for r in results)

        # Performance assertions: percentile-based for stability
        percentile_benchmark.assert_percentile(95, 0.250, "Batch check p95")  # p95 < 250ms
        percentile_benchmark.assert_percentile(99, 0.300, "Batch check p99")  # p99 < 300ms


# LLM Request Benchmarks
@pytest.mark.benchmark
@pytest.mark.xdist_group(name="performance_benchmarks_tests")
class TestLLMBenchmarks:
    """Benchmark LLM request handling."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    @pytest.fixture
    def mock_llm_client(self):
        """Mock LiteLLM client for benchmarking."""
        client = Mock()

        async def mock_completion(*args, **kwargs):
            # Simulate LLM response time
            await asyncio.sleep(0.100)  # 100ms simulated latency
            return {
                "choices": [{"message": {"content": "Test response", "role": "assistant"}}],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            }

        client.acompletion = mock_completion
        return client

    def test_llm_request_performance(self, mock_llm_client, percentile_benchmark):
        """Benchmark single LLM request.

        Requirement: LLM request handling overhead p95 < 15ms, p99 < 20ms (excluding actual LLM call).

        Note: Uses async function directly - PercentileBenchmark creates a single event loop
        for all iterations, providing accurate measurements.
        """
        timer = BenchmarkTimer()

        async def make_request():
            with timer:
                # Simulate pre-processing
                messages = [{"role": "user", "content": "Test message"}]
                # Make LLM call
                response = await mock_llm_client.acompletion(model="gpt-4", messages=messages)
                # Simulate post-processing
                return response["choices"][0]["message"]["content"]

        # Run benchmark directly with async function (single event loop for all iterations)
        result = percentile_benchmark(make_request)

        assert result == "Test response"

        # The total time includes 100ms simulated LLM latency
        # We're measuring the overhead using percentiles for stability
        stats = percentile_benchmark.stats
        overhead_p95 = stats["p95"] - 0.100
        overhead_p99 = stats["p99"] - 0.100

        assert overhead_p95 < 0.015, f"LLM overhead p95: {overhead_p95 * 1000:.2f}ms (target: < 15ms)"
        assert overhead_p99 < 0.020, f"LLM overhead p99: {overhead_p99 * 1000:.2f}ms (target: < 20ms)"


# Agent Execution Benchmarks
@pytest.mark.benchmark
@pytest.mark.xdist_group(name="performance_benchmarks_tests")
class TestAgentBenchmarks:
    """Benchmark agent execution performance."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_agent_initialization_performance(self, percentile_benchmark):
        """Benchmark agent initialization time.

        Requirement: Agent initialization p95 < 120ms, p99 < 150ms (more stable than mean < 100ms).
        """

        def initialize_agent():
            # Simulate agent initialization
            config = {"model": "gpt-4", "temperature": 0.7, "max_tokens": 1000}

            # Simulate state initialization
            state = {"messages": [], "context": {}}

            return {"config": config, "state": state}

        # Run benchmark
        result = percentile_benchmark(initialize_agent)

        assert "config" in result
        assert "state" in result

        # Performance assertions: percentile-based for stability
        percentile_benchmark.assert_percentile(95, 0.120, "Agent init p95")  # p95 < 120ms
        percentile_benchmark.assert_percentile(99, 0.150, "Agent init p99")  # p99 < 150ms

    def test_message_processing_performance(self, percentile_benchmark):
        """Benchmark message processing throughput.

        Requirement: Process 100 messages p95 < 1.2s, p99 < 1.5s (more stable than mean < 1s).

        Note: Uses async function directly - PercentileBenchmark creates a single event loop
        for all iterations, providing accurate measurements.
        """

        async def process_messages():
            messages = [{"role": "user", "content": f"Message {i}"} for i in range(100)]

            processed = []
            for msg in messages:
                # Simulate message validation and processing
                processed_msg = {
                    "id": hash(msg["content"]),
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": time.time(),
                }
                processed.append(processed_msg)

            return processed

        # Run benchmark directly with async function (single event loop for all iterations)
        results = percentile_benchmark(process_messages)

        assert len(results) == 100

        # Performance assertions: percentile-based for stability
        percentile_benchmark.assert_percentile(95, 1.2, "Message processing p95")  # p95 < 1.2s
        percentile_benchmark.assert_percentile(99, 1.5, "Message processing p99")  # p99 < 1.5s


# Memory and Resource Benchmarks
@pytest.mark.benchmark
@pytest.mark.xdist_group(name="performance_benchmarks_tests")
class TestResourceBenchmarks:
    """Benchmark memory and resource usage."""

    def teardown_method(self):
        """Force GC to prevent mock accumulation in xdist workers"""
        gc.collect()

    def test_state_serialization_performance(self, percentile_benchmark):
        """Benchmark state serialization for checkpointing.

        Requirement: Serialize 1000-message state p95 < 60ms, p99 < 75ms (more stable than mean < 50ms).
        """
        import json

        # Create large state
        state = {
            "messages": [{"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"} for i in range(1000)],
            "context": {"session_id": "test-session", "user_id": "test-user", "metadata": {"key": "value"}},
        }

        def serialize_state():
            return json.dumps(state)

        # Run benchmark
        result = percentile_benchmark(serialize_state)

        assert isinstance(result, str)
        assert len(result) > 0

        # Performance assertions: percentile-based for stability
        percentile_benchmark.assert_percentile(95, 0.060, "State serialization p95")  # p95 < 60ms
        percentile_benchmark.assert_percentile(99, 0.075, "State serialization p99")  # p99 < 75ms

    def test_state_deserialization_performance(self, percentile_benchmark):
        """Benchmark state deserialization for checkpointing.

        Requirement: Deserialize 1000-message state p95 < 60ms, p99 < 75ms (more stable than mean < 50ms).
        """
        import json

        # Create serialized state
        state = {
            "messages": [{"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"} for i in range(1000)],
            "context": {"session_id": "test-session", "user_id": "test-user"},
        }
        serialized = json.dumps(state)

        def deserialize_state():
            return json.loads(serialized)

        # Run benchmark
        result = percentile_benchmark(deserialize_state)

        assert isinstance(result, dict)
        assert len(result["messages"]) == 1000

        # Performance assertions: percentile-based for stability
        percentile_benchmark.assert_percentile(95, 0.060, "State deserialization p95")  # p95 < 60ms
        percentile_benchmark.assert_percentile(99, 0.075, "State deserialization p99")  # p99 < 75ms


# Benchmark configuration
pytestmark = pytest.mark.benchmark
