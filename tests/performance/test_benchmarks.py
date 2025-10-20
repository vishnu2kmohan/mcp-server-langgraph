"""Performance benchmarks for critical system components."""

import asyncio
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict
from unittest.mock import Mock, patch

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
class TestJWTBenchmarks:
    """Benchmark JWT token operations."""

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

    def test_jwt_encoding_performance(self, jwt_config, sample_payload, benchmark):
        """Benchmark JWT token encoding.

        Requirement: Token encoding should take < 1ms on average.
        """

        def encode_token():
            return jwt.encode(sample_payload, jwt_config["secret_key"], algorithm=jwt_config["algorithm"])

        # Run benchmark
        result = benchmark(encode_token)

        # Verify token is valid
        assert isinstance(result, str)
        assert len(result) > 0

        # Performance assertion: < 1ms average
        assert benchmark.stats["mean"] < 0.001, f"JWT encoding took {benchmark.stats['mean'] * 1000:.2f}ms (target: < 1ms)"

    def test_jwt_decoding_performance(self, jwt_config, sample_payload, benchmark):
        """Benchmark JWT token decoding.

        Requirement: Token decoding should take < 1ms on average.
        """
        # Pre-generate token
        token = jwt.encode(sample_payload, jwt_config["secret_key"], algorithm=jwt_config["algorithm"])

        def decode_token():
            return jwt.decode(token, jwt_config["secret_key"], algorithms=[jwt_config["algorithm"]])

        # Run benchmark
        result = benchmark(decode_token)

        # Verify payload
        assert result["sub"] == sample_payload["sub"]

        # Performance assertion: < 1ms average
        assert benchmark.stats["mean"] < 0.001, f"JWT decoding took {benchmark.stats['mean'] * 1000:.2f}ms (target: < 1ms)"

    def test_jwt_validation_performance(self, jwt_config, sample_payload, benchmark):
        """Benchmark JWT token validation with expiration check.

        Requirement: Token validation should take < 2ms on average.
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
        result = benchmark(validate_token)

        assert result is True

        # Performance assertion: < 2ms on average
        assert benchmark.stats["mean"] < 0.002, f"JWT validation took {benchmark.stats['mean'] * 1000:.2f}ms (target: < 2ms)"


# OpenFGA Authorization Benchmarks
@pytest.mark.benchmark
@pytest.mark.openfga
class TestOpenFGABenchmarks:
    """Benchmark OpenFGA authorization checks."""

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

    def test_authorization_check_performance(self, mock_openfga_client, benchmark):
        """Benchmark OpenFGA authorization check.

        Requirement: Authorization check should take < 50ms on average (including network).
        """

        async def check_authorization():
            return await mock_openfga_client.check(user="user:test-user", relation="viewer", object="document:test-doc")

        # Run benchmark with asyncio wrapper
        def run_async_check():
            return asyncio.run(check_authorization())

        result = benchmark(run_async_check)

        assert result["allowed"] is True

        # Performance assertion: < 50ms average (with network simulation)
        assert benchmark.stats["mean"] < 0.050, f"Auth check took {benchmark.stats['mean'] * 1000:.2f}ms (target: < 50ms)"

    def test_batch_authorization_performance(self, mock_openfga_client, benchmark):
        """Benchmark batch authorization checks.

        Requirement: 10 batch checks should take < 200ms on average.
        """

        async def batch_check():
            results = []
            for i in range(10):
                result = await mock_openfga_client.check(
                    user=f"user:test-user-{i}", relation="viewer", object=f"document:doc-{i}"
                )
                results.append(result)
            return results

        # Run benchmark with asyncio wrapper
        def run_async_batch():
            return asyncio.run(batch_check())

        results = benchmark(run_async_batch)

        assert len(results) == 10
        assert all(r["allowed"] for r in results)

        # Performance assertion: < 200ms for 10 checks
        assert benchmark.stats["mean"] < 0.200, f"Batch check took {benchmark.stats['mean'] * 1000:.2f}ms (target: < 200ms)"


# LLM Request Benchmarks
@pytest.mark.benchmark
class TestLLMBenchmarks:
    """Benchmark LLM request handling."""

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

    def test_llm_request_performance(self, mock_llm_client, benchmark):
        """Benchmark single LLM request.

        Requirement: LLM request handling overhead should be < 10ms (excluding actual LLM call).
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

        # Run benchmark with asyncio wrapper
        def run_async_request():
            return asyncio.run(make_request())

        result = benchmark(run_async_request)

        assert result == "Test response"

        # The total time includes 100ms simulated LLM latency
        # We're measuring the overhead, which should be minimal
        overhead = benchmark.stats["mean"] - 0.100
        assert overhead < 0.010, f"LLM request overhead: {overhead * 1000:.2f}ms (target: < 10ms)"


# Agent Execution Benchmarks
@pytest.mark.benchmark
class TestAgentBenchmarks:
    """Benchmark agent execution performance."""

    def test_agent_initialization_performance(self, benchmark):
        """Benchmark agent initialization time.

        Requirement: Agent initialization should take < 100ms.
        """

        def initialize_agent():
            # Simulate agent initialization
            config = {"model": "gpt-4", "temperature": 0.7, "max_tokens": 1000}

            # Simulate state initialization
            state = {"messages": [], "context": {}}

            return {"config": config, "state": state}

        # Run benchmark
        result = benchmark(initialize_agent)

        assert "config" in result
        assert "state" in result

        # Performance assertion: < 100ms
        assert benchmark.stats["mean"] < 0.100, f"Agent init took {benchmark.stats['mean'] * 1000:.2f}ms (target: < 100ms)"

    def test_message_processing_performance(self, benchmark):
        """Benchmark message processing throughput.

        Requirement: Process 100 messages in < 1 second.
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

        # Run benchmark with asyncio wrapper
        def run_async_processing():
            return asyncio.run(process_messages())

        results = benchmark(run_async_processing)

        assert len(results) == 100

        # Performance assertion: < 1 second for 100 messages
        assert benchmark.stats["mean"] < 1.0, f"Processing took {benchmark.stats['mean']:.2f}s (target: < 1s)"


# Memory and Resource Benchmarks
@pytest.mark.benchmark
class TestResourceBenchmarks:
    """Benchmark memory and resource usage."""

    def test_state_serialization_performance(self, benchmark):
        """Benchmark state serialization for checkpointing.

        Requirement: Serialize 1000-message state in < 50ms.
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
        result = benchmark(serialize_state)

        assert isinstance(result, str)
        assert len(result) > 0

        # Performance assertion: < 50ms
        assert benchmark.stats["mean"] < 0.050, f"Serialization took {benchmark.stats['mean'] * 1000:.2f}ms (target: < 50ms)"

    def test_state_deserialization_performance(self, benchmark):
        """Benchmark state deserialization for checkpointing.

        Requirement: Deserialize 1000-message state in < 50ms.
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
        result = benchmark(deserialize_state)

        assert isinstance(result, dict)
        assert len(result["messages"]) == 1000

        # Performance assertion: < 50ms
        assert benchmark.stats["mean"] < 0.050, f"Deserialization took {benchmark.stats['mean'] * 1000:.2f}ms (target: < 50ms)"


# Benchmark configuration
pytestmark = pytest.mark.benchmark
