"""
Tests for startup validation module.

This module validates that required external services are available
at application startup, providing early failure detection.

TDD RED Phase: These tests define expected behavior for startup_validation.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import gc


pytestmark = [pytest.mark.unit, pytest.mark.core, pytest.mark.health]


@pytest.mark.xdist_group(name="startup_validation")
class TestQdrantValidation:
    """Tests for Qdrant connectivity validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_validate_qdrant_connection_success(self) -> None:
        """Test successful Qdrant connection validation."""
        from mcp_server_langgraph.core.startup_validation import validate_qdrant_connection

        # Mock successful Qdrant connection
        mock_client = MagicMock()
        mock_client.get_collections.return_value = MagicMock(collections=[])

        with patch(
            "qdrant_client.QdrantClient",
            return_value=mock_client,
        ):
            result = await validate_qdrant_connection(
                url="http://localhost:6333",
                timeout=5,
            )

        assert result.success is True
        assert result.service == "qdrant"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_validate_qdrant_connection_failure(self) -> None:
        """Test Qdrant connection failure handling."""
        from mcp_server_langgraph.core.startup_validation import validate_qdrant_connection

        # Mock connection failure
        mock_client = MagicMock()
        mock_client.get_collections.side_effect = ConnectionError("Connection refused")

        with patch(
            "qdrant_client.QdrantClient",
            return_value=mock_client,
        ):
            result = await validate_qdrant_connection(
                url="http://localhost:6333",
                timeout=5,
            )

        assert result.success is False
        assert result.service == "qdrant"
        assert "Connection refused" in str(result.error)

    @pytest.mark.asyncio
    async def test_validate_qdrant_connection_timeout(self) -> None:
        """Test Qdrant connection timeout handling."""
        from mcp_server_langgraph.core.startup_validation import validate_qdrant_connection

        # Mock timeout

        mock_client = MagicMock()
        mock_client.get_collections.side_effect = TimeoutError("Timeout")

        with patch(
            "qdrant_client.QdrantClient",
            return_value=mock_client,
        ):
            result = await validate_qdrant_connection(
                url="http://localhost:6333",
                timeout=1,
            )

        assert result.success is False
        assert result.service == "qdrant"
        assert result.error is not None


@pytest.mark.xdist_group(name="startup_validation")
class TestQdrantBootstrap:
    """Tests for Qdrant collection bootstrap."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_bootstrap_default_collection_creates_if_missing(self) -> None:
        """Test that bootstrap creates default collection if it doesn't exist."""
        from mcp_server_langgraph.core.startup_validation import bootstrap_qdrant_collection

        mock_client = MagicMock()
        # Simulate collection doesn't exist
        mock_client.collection_exists.return_value = False
        mock_client.create_collection.return_value = True

        with patch(
            "qdrant_client.QdrantClient",
            return_value=mock_client,
        ):
            result = await bootstrap_qdrant_collection(
                url="http://localhost:6333",
                collection_name="test_collection",
                vector_size=384,
            )

        assert result.success is True
        assert result.created is True
        mock_client.create_collection.assert_called_once()

    @pytest.mark.asyncio
    async def test_bootstrap_default_collection_skips_if_exists(self) -> None:
        """Test that bootstrap skips creation if collection already exists."""
        from mcp_server_langgraph.core.startup_validation import bootstrap_qdrant_collection

        mock_client = MagicMock()
        # Simulate collection already exists
        mock_client.collection_exists.return_value = True

        with patch(
            "qdrant_client.QdrantClient",
            return_value=mock_client,
        ):
            result = await bootstrap_qdrant_collection(
                url="http://localhost:6333",
                collection_name="test_collection",
                vector_size=384,
            )

        assert result.success is True
        assert result.created is False
        mock_client.create_collection.assert_not_called()

    @pytest.mark.asyncio
    async def test_bootstrap_tenant_collection_uses_tenant_prefix(self) -> None:
        """Test that tenant collection uses correct naming convention."""
        from mcp_server_langgraph.core.startup_validation import bootstrap_qdrant_collection

        mock_client = MagicMock()
        mock_client.collection_exists.return_value = False
        mock_client.create_collection.return_value = True

        with patch(
            "qdrant_client.QdrantClient",
            return_value=mock_client,
        ):
            result = await bootstrap_qdrant_collection(
                url="http://localhost:6333",
                collection_name="tenant_123_vectors",
                vector_size=384,
            )

        assert result.success is True
        # Verify collection name is passed correctly
        call_args = mock_client.create_collection.call_args
        assert call_args[1]["collection_name"] == "tenant_123_vectors"


@pytest.mark.xdist_group(name="startup_validation")
class TestValidationResult:
    """Tests for ValidationResult data class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_validation_result_success(self) -> None:
        """Test ValidationResult for successful validation."""
        from mcp_server_langgraph.core.startup_validation import ValidationResult

        result = ValidationResult(
            service="qdrant",
            success=True,
            message="Connected successfully",
        )

        assert result.service == "qdrant"
        assert result.success is True
        assert result.error is None

    def test_validation_result_failure(self) -> None:
        """Test ValidationResult for failed validation."""
        from mcp_server_langgraph.core.startup_validation import ValidationResult

        result = ValidationResult(
            service="qdrant",
            success=False,
            error="Connection refused",
        )

        assert result.service == "qdrant"
        assert result.success is False
        assert result.error == "Connection refused"


@pytest.mark.xdist_group(name="startup_validation")
class TestBootstrapResult:
    """Tests for BootstrapResult data class."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    def test_bootstrap_result_created(self) -> None:
        """Test BootstrapResult when collection is created."""
        from mcp_server_langgraph.core.startup_validation import BootstrapResult

        result = BootstrapResult(
            collection_name="test_collection",
            success=True,
            created=True,
        )

        assert result.collection_name == "test_collection"
        assert result.success is True
        assert result.created is True

    def test_bootstrap_result_already_exists(self) -> None:
        """Test BootstrapResult when collection already exists."""
        from mcp_server_langgraph.core.startup_validation import BootstrapResult

        result = BootstrapResult(
            collection_name="test_collection",
            success=True,
            created=False,
        )

        assert result.success is True
        assert result.created is False


@pytest.mark.xdist_group(name="startup_validation")
class TestLokiValidation:
    """Tests for Loki connectivity validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_validate_loki_connection_success(self) -> None:
        """Test successful Loki connection validation."""
        from mcp_server_langgraph.core.startup_validation import validate_loki_connection

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "ready"
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await validate_loki_connection(
                url="http://localhost:3100",
                timeout=5,
            )

        assert result.success is True
        assert result.service == "loki"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_validate_loki_connection_failure(self) -> None:
        """Test Loki connection failure handling."""
        from mcp_server_langgraph.core.startup_validation import validate_loki_connection

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_client.get = AsyncMock(side_effect=ConnectionError("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await validate_loki_connection(
                url="http://localhost:3100",
                timeout=5,
            )

        assert result.success is False
        assert result.service == "loki"
        assert "Connection refused" in str(result.error) or result.error is not None

    @pytest.mark.asyncio
    async def test_validate_loki_skipped_when_disabled(self) -> None:
        """Test that Loki validation is skipped when URL is empty."""
        from mcp_server_langgraph.core.startup_validation import validate_loki_connection

        result = await validate_loki_connection(
            url="",
            timeout=5,
        )

        assert result.success is True
        assert "disabled" in result.message.lower() or "not configured" in result.message.lower()


@pytest.mark.xdist_group(name="startup_validation")
class TestTempoValidation:
    """Tests for Tempo connectivity validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_validate_tempo_connection_success(self) -> None:
        """Test successful Tempo connection validation."""
        from mcp_server_langgraph.core.startup_validation import validate_tempo_connection

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "ready"
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await validate_tempo_connection(
                url="http://localhost:3200",
                timeout=5,
            )

        assert result.success is True
        assert result.service == "tempo"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_validate_tempo_connection_failure(self) -> None:
        """Test Tempo connection failure handling."""
        from mcp_server_langgraph.core.startup_validation import validate_tempo_connection

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_client.get = AsyncMock(side_effect=ConnectionError("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await validate_tempo_connection(
                url="http://localhost:3200",
                timeout=5,
            )

        assert result.success is False
        assert result.service == "tempo"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_validate_tempo_skipped_when_disabled(self) -> None:
        """Test that Tempo validation is skipped when URL is empty."""
        from mcp_server_langgraph.core.startup_validation import validate_tempo_connection

        result = await validate_tempo_connection(
            url="",
            timeout=5,
        )

        assert result.success is True
        assert "disabled" in result.message.lower() or "not configured" in result.message.lower()


@pytest.mark.xdist_group(name="startup_validation")
class TestMimirValidation:
    """Tests for Mimir connectivity validation."""

    def teardown_method(self) -> None:
        """Force GC to prevent mock accumulation in xdist workers."""
        gc.collect()

    @pytest.mark.asyncio
    async def test_validate_mimir_connection_success(self) -> None:
        """Test successful Mimir connection validation."""
        from mcp_server_langgraph.core.startup_validation import validate_mimir_connection

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.text = "ready"
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await validate_mimir_connection(
                url="http://localhost:9009",
                timeout=5,
            )

        assert result.success is True
        assert result.service == "mimir"
        assert result.error is None

    @pytest.mark.asyncio
    async def test_validate_mimir_connection_failure(self) -> None:
        """Test Mimir connection failure handling."""
        from mcp_server_langgraph.core.startup_validation import validate_mimir_connection

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock(return_value=None)  # noqa: async-mock-config
            mock_client.get = AsyncMock(side_effect=ConnectionError("Connection refused"))
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=None)
            mock_client_class.return_value = mock_client

            result = await validate_mimir_connection(
                url="http://localhost:9009",
                timeout=5,
            )

        assert result.success is False
        assert result.service == "mimir"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_validate_mimir_skipped_when_disabled(self) -> None:
        """Test that Mimir validation is skipped when URL is empty."""
        from mcp_server_langgraph.core.startup_validation import validate_mimir_connection

        result = await validate_mimir_connection(
            url="",
            timeout=5,
        )

        assert result.success is True
        assert "disabled" in result.message.lower() or "not configured" in result.message.lower()
