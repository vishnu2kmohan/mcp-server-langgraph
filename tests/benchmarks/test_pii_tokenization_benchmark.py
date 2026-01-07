"""
PII Tokenization Performance Benchmarks

Tests performance characteristics of PII detection and tokenization
to ensure acceptable latency for real-time processing.

Performance Targets:
- Detection: <5ms for 1KB text
- Tokenization: <10ms for 1KB text with 10 PII items
- Round-trip: <15ms for tokenize + untokenize cycle
"""

import gc

import pytest

# Domain marker only - benchmark/performance markers auto-applied by conftest.py
pytestmark = pytest.mark.pii


def generate_text_with_pii(length: int, pii_count: int = 5) -> str:
    """Generate test text with embedded PII.

    Args:
        length: Approximate total length in characters
        pii_count: Number of PII items to embed

    Returns:
        Text string with embedded PII
    """
    pii_items = [
        "john.doe@example.com",
        "555-123-4567",
        "123-45-6789",
        "4111-1111-1111-1111",
        "192.168.100.50",
        "1990-05-15",
        "jane.smith@company.org",
        "(800) 555-0100",
        "987-65-4321",
        "2000-12-25",
    ]

    # Generate filler text
    words = ["lorem", "ipsum", "dolor", "sit", "amet", "consectetur", "adipiscing"]
    filler_parts = []
    current_length = 0

    max(1, pii_count // 5)
    pii_index = 0

    while current_length < length:
        # Add some filler words
        segment = " ".join(words[i % len(words)] for i in range(10))
        filler_parts.append(segment)
        current_length += len(segment)

        # Add PII periodically
        if pii_index < pii_count and current_length > (length * pii_index / pii_count):
            filler_parts.append(pii_items[pii_index % len(pii_items)])
            pii_index += 1
            current_length += 20  # Approximate PII length

    return " ".join(filler_parts)[:length]


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmark_pii_detection")
class TestPIIDetectionBenchmarks:
    """Benchmark suite for PII detection performance."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_benchmark_detection_small_text(self, benchmark):
        """Benchmark PII detection on small text (~256 bytes)."""
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = generate_text_with_pii(256, pii_count=2)

        result = benchmark(detect_pii, text)

        assert isinstance(result, list)

    def test_benchmark_detection_medium_text(self, benchmark):
        """Benchmark PII detection on medium text (~1KB)."""
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = generate_text_with_pii(1024, pii_count=5)

        result = benchmark(detect_pii, text)

        assert isinstance(result, list)

    def test_benchmark_detection_large_text(self, benchmark):
        """Benchmark PII detection on large text (~10KB)."""
        from mcp_server_langgraph.privacy.detectors import detect_pii

        text = generate_text_with_pii(10240, pii_count=20)

        result = benchmark(detect_pii, text)

        assert isinstance(result, list)

    def test_benchmark_detection_no_pii(self, benchmark):
        """Benchmark PII detection on text with no PII (best case)."""
        from mcp_server_langgraph.privacy.detectors import detect_pii

        # Clean text with no PII
        text = " ".join(["lorem ipsum dolor sit amet"] * 50)

        result = benchmark(detect_pii, text)

        assert result == []


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmark_pii_tokenization")
class TestPIITokenizationBenchmarks:
    """Benchmark suite for PII tokenization performance."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_benchmark_tokenize_small_text(self, benchmark):
        """Benchmark tokenization on small text."""
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        text = generate_text_with_pii(256, pii_count=2)

        result = benchmark(tokenizer.tokenize, text)

        tokenized_text, lookup = result
        assert isinstance(tokenized_text, str)
        assert isinstance(lookup, dict)

    def test_benchmark_tokenize_medium_text(self, benchmark):
        """Benchmark tokenization on medium text (~1KB)."""
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        text = generate_text_with_pii(1024, pii_count=5)

        result = benchmark(tokenizer.tokenize, text)

        tokenized_text, lookup = result
        assert len(lookup) > 0

    def test_benchmark_tokenize_large_text(self, benchmark):
        """Benchmark tokenization on large text (~10KB)."""
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        text = generate_text_with_pii(10240, pii_count=20)

        result = benchmark(tokenizer.tokenize, text)

        tokenized_text, lookup = result
        assert len(lookup) > 0

    def test_benchmark_tokenize_high_pii_density(self, benchmark):
        """Benchmark tokenization with high PII density."""
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        # High density: many PII items in small text
        text = """
        Contact list:
        john@example.com, 555-111-1111
        jane@example.com, 555-222-2222
        bob@example.com, 555-333-3333
        alice@example.com, 555-444-4444
        SSN: 111-22-3333, 222-33-4444, 333-44-5555
        Cards: 4111-1111-1111-1111, 5500-0000-0000-0004
        IPs: 192.168.1.1, 10.0.0.1, 172.16.0.1
        DOBs: 1990-01-01, 1985-06-15, 2000-12-31
        """

        result = benchmark(tokenizer.tokenize, text)

        tokenized_text, lookup = result
        assert len(lookup) >= 10  # Multiple PII items


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmark_pii_roundtrip")
class TestPIIRoundtripBenchmarks:
    """Benchmark suite for full tokenize/untokenize round-trip."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_benchmark_roundtrip_medium_text(self, benchmark):
        """Benchmark full round-trip on medium text."""
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        text = generate_text_with_pii(1024, pii_count=5)

        def roundtrip():
            tokenized, lookup = tokenizer.tokenize(text)
            restored = tokenizer.untokenize(tokenized, lookup)
            return restored

        result = benchmark(roundtrip)

        # Verify correctness
        assert result == text

    def test_benchmark_roundtrip_large_text(self, benchmark):
        """Benchmark full round-trip on large text."""
        from mcp_server_langgraph.privacy.tokenizer import PIITokenizer

        tokenizer = PIITokenizer()
        text = generate_text_with_pii(10240, pii_count=20)

        def roundtrip():
            tokenized, lookup = tokenizer.tokenize(text)
            restored = tokenizer.untokenize(tokenized, lookup)
            return restored

        result = benchmark(roundtrip)

        # Verify correctness
        assert result == text


@pytest.mark.benchmark
@pytest.mark.xdist_group(name="benchmark_encrypted_lookup")
class TestEncryptedLookupBenchmarks:
    """Benchmark suite for encrypted lookup table operations."""

    def teardown_method(self) -> None:
        """Force GC to prevent memory accumulation."""
        gc.collect()

    def test_benchmark_lookup_store(self, benchmark):
        """Benchmark storing values in encrypted lookup."""
        from mcp_server_langgraph.privacy.lookup_table import EncryptedLookupTable

        table = EncryptedLookupTable()

        def store_values():
            for i in range(100):
                table.store(f"token_{i}", f"value_{i}")
            return table

        result = benchmark(store_values)

        assert len(result) == 100

    def test_benchmark_lookup_retrieve(self, benchmark):
        """Benchmark retrieving values from encrypted lookup."""
        from mcp_server_langgraph.privacy.lookup_table import EncryptedLookupTable

        table = EncryptedLookupTable()
        for i in range(100):
            table.store(f"token_{i}", f"value_{i}")

        def retrieve_values():
            results = []
            for i in range(100):
                results.append(table.retrieve(f"token_{i}"))
            return results

        result = benchmark(retrieve_values)

        assert len(result) == 100
        assert all(r is not None for r in result)

    def test_benchmark_lookup_export_import(self, benchmark):
        """Benchmark export/import cycle for encrypted lookup."""
        from mcp_server_langgraph.privacy.lookup_table import EncryptedLookupTable

        table = EncryptedLookupTable()
        for i in range(50):
            table.store(f"token_{i}", f"secret_value_{i}")

        def export_import_cycle():
            exported = table.export_encrypted()
            restored = EncryptedLookupTable.from_encrypted(exported)
            return restored

        result = benchmark(export_import_cycle)

        assert result.retrieve("token_0") == "secret_value_0"
