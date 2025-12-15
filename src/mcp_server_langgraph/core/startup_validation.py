"""
Startup validation module for external service connectivity.

This module provides functions to validate that required external services
(Qdrant, Redis, PostgreSQL, etc.) are available before the application
starts serving requests.

Early failure detection prevents cascading errors in E2E tests and
improves debugging by clearly identifying which service is unavailable.

Usage:
    from mcp_server_langgraph.core.startup_validation import (
        validate_qdrant_connection,
        bootstrap_qdrant_collection,
    )

    # Validate connectivity
    result = await validate_qdrant_connection(url="http://qdrant:6333")
    if not result.success:
        raise RuntimeError(f"Qdrant unavailable: {result.error}")

    # Bootstrap default collection
    bootstrap = await bootstrap_qdrant_collection(
        url="http://qdrant:6333",
        collection_name="mcp_context",
        vector_size=384,
    )
"""

from dataclasses import dataclass
from typing import Any

from mcp_server_langgraph.observability.telemetry import logger


@dataclass
class ValidationResult:
    """Result of a service validation check."""

    service: str
    success: bool
    message: str | None = None
    error: str | None = None

    def __post_init__(self) -> None:
        """Validate that either success with message or failure with error."""
        if self.success and self.error:
            raise ValueError("Successful validation should not have an error")


@dataclass
class BootstrapResult:
    """Result of a collection bootstrap operation."""

    collection_name: str
    success: bool
    created: bool
    error: str | None = None

    def __post_init__(self) -> None:
        """Validate result consistency."""
        if not self.success and self.created:
            raise ValueError("Cannot be created if not successful")


async def validate_qdrant_connection(
    url: str = "http://localhost:6333",
    timeout: int = 5,
) -> ValidationResult:
    """
    Validate Qdrant vector database connectivity.

    Args:
        url: Qdrant server URL (default: http://localhost:6333)
        timeout: Connection timeout in seconds

    Returns:
        ValidationResult with success status and any error message
    """
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=url, timeout=timeout)

        # Test connectivity by listing collections
        collections = client.get_collections()
        collection_count = len(collections.collections)

        logger.info(
            "Qdrant connection validated",
            extra={
                "url": url,
                "collection_count": collection_count,
            },
        )

        return ValidationResult(
            service="qdrant",
            success=True,
            message=f"Connected successfully. Found {collection_count} collection(s).",
        )

    except ConnectionError as e:
        logger.error(
            "Qdrant connection failed",
            extra={"url": url, "error": str(e)},
        )
        return ValidationResult(
            service="qdrant",
            success=False,
            error=f"Connection refused: {e}",
        )

    except TimeoutError as e:
        logger.error(
            "Qdrant connection timeout",
            extra={"url": url, "timeout": timeout},
        )
        return ValidationResult(
            service="qdrant",
            success=False,
            error=f"Connection timeout after {timeout}s: {e}",
        )

    except Exception as e:
        logger.error(
            "Qdrant validation error",
            extra={"url": url, "error": str(e), "error_type": type(e).__name__},
        )
        return ValidationResult(
            service="qdrant",
            success=False,
            error=str(e),
        )


async def bootstrap_qdrant_collection(
    url: str = "http://localhost:6333",
    collection_name: str = "mcp_context",
    vector_size: int = 384,
    distance: str = "Cosine",
    timeout: int = 10,
) -> BootstrapResult:
    """
    Bootstrap a Qdrant collection if it doesn't exist.

    Creates the collection with the specified vector configuration.
    Skips creation if the collection already exists.

    Args:
        url: Qdrant server URL
        collection_name: Name of the collection to create
        vector_size: Dimension of vectors (384 for MiniLM, 1536 for OpenAI)
        distance: Distance metric (Cosine, Euclidean, Dot)
        timeout: Operation timeout in seconds

    Returns:
        BootstrapResult with creation status
    """
    try:
        from qdrant_client import QdrantClient
        from qdrant_client.models import Distance, VectorParams

        client = QdrantClient(url=url, timeout=timeout)

        # Check if collection already exists
        if client.collection_exists(collection_name=collection_name):
            logger.info(
                "Qdrant collection already exists",
                extra={"collection": collection_name},
            )
            return BootstrapResult(
                collection_name=collection_name,
                success=True,
                created=False,
            )

        # Map distance string to enum
        distance_map: dict[str, Any] = {
            "Cosine": Distance.COSINE,
            "Euclidean": Distance.EUCLID,
            "Dot": Distance.DOT,
        }
        distance_enum = distance_map.get(distance, Distance.COSINE)

        # Create collection
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=distance_enum,
            ),
        )

        logger.info(
            "Qdrant collection created",
            extra={
                "collection": collection_name,
                "vector_size": vector_size,
                "distance": distance,
            },
        )

        return BootstrapResult(
            collection_name=collection_name,
            success=True,
            created=True,
        )

    except Exception as e:
        logger.error(
            "Qdrant bootstrap failed",
            extra={
                "collection": collection_name,
                "error": str(e),
                "error_type": type(e).__name__,
            },
        )
        return BootstrapResult(
            collection_name=collection_name,
            success=False,
            created=False,
            error=str(e),
        )


async def validate_all_services(
    qdrant_url: str | None = None,
    skip_qdrant: bool = False,
) -> dict[str, ValidationResult]:
    """
    Validate all required external services.

    Args:
        qdrant_url: Optional Qdrant URL override
        skip_qdrant: Skip Qdrant validation if not required

    Returns:
        Dictionary mapping service names to validation results
    """
    import os

    results: dict[str, ValidationResult] = {}

    # Qdrant validation
    if not skip_qdrant:
        url = qdrant_url or os.getenv("QDRANT_URL", "http://localhost:6333")
        results["qdrant"] = await validate_qdrant_connection(url=url)

    return results


async def validate_loki_connection(
    url: str = "http://localhost:3100",
    timeout: int = 5,
) -> ValidationResult:
    """
    Validate Loki log aggregation service connectivity.

    Args:
        url: Loki server URL (default: http://localhost:3100)
        timeout: Connection timeout in seconds

    Returns:
        ValidationResult with success status and any error message
    """
    if not url:
        return ValidationResult(
            service="loki",
            success=True,
            message="Loki disabled - not configured",
        )

    try:
        import httpx

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{url}/ready")

            if response.status_code == 200:
                logger.info(
                    "Loki connection validated",
                    extra={"url": url},
                )
                return ValidationResult(
                    service="loki",
                    success=True,
                    message="Connected successfully",
                )
            else:
                return ValidationResult(
                    service="loki",
                    success=False,
                    error=f"Loki not ready: status {response.status_code}",
                )

    except Exception as e:
        logger.error(
            "Loki validation error",
            extra={"url": url, "error": str(e), "error_type": type(e).__name__},
        )
        return ValidationResult(
            service="loki",
            success=False,
            error=str(e),
        )


async def validate_tempo_connection(
    url: str = "http://localhost:3200",
    timeout: int = 5,
) -> ValidationResult:
    """
    Validate Tempo distributed tracing service connectivity.

    Args:
        url: Tempo server URL (default: http://localhost:3200)
        timeout: Connection timeout in seconds

    Returns:
        ValidationResult with success status and any error message
    """
    if not url:
        return ValidationResult(
            service="tempo",
            success=True,
            message="Tempo disabled - not configured",
        )

    try:
        import httpx

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{url}/ready")

            if response.status_code == 200:
                logger.info(
                    "Tempo connection validated",
                    extra={"url": url},
                )
                return ValidationResult(
                    service="tempo",
                    success=True,
                    message="Connected successfully",
                )
            else:
                return ValidationResult(
                    service="tempo",
                    success=False,
                    error=f"Tempo not ready: status {response.status_code}",
                )

    except Exception as e:
        logger.error(
            "Tempo validation error",
            extra={"url": url, "error": str(e), "error_type": type(e).__name__},
        )
        return ValidationResult(
            service="tempo",
            success=False,
            error=str(e),
        )


async def validate_mimir_connection(
    url: str = "http://localhost:9009",
    timeout: int = 5,
) -> ValidationResult:
    """
    Validate Mimir metrics service connectivity.

    Args:
        url: Mimir server URL (default: http://localhost:9009)
        timeout: Connection timeout in seconds

    Returns:
        ValidationResult with success status and any error message
    """
    if not url:
        return ValidationResult(
            service="mimir",
            success=True,
            message="Mimir disabled - not configured",
        )

    try:
        import httpx

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(f"{url}/ready")

            if response.status_code == 200:
                logger.info(
                    "Mimir connection validated",
                    extra={"url": url},
                )
                return ValidationResult(
                    service="mimir",
                    success=True,
                    message="Connected successfully",
                )
            else:
                return ValidationResult(
                    service="mimir",
                    success=False,
                    error=f"Mimir not ready: status {response.status_code}",
                )

    except Exception as e:
        logger.error(
            "Mimir validation error",
            extra={"url": url, "error": str(e), "error_type": type(e).__name__},
        )
        return ValidationResult(
            service="mimir",
            success=False,
            error=str(e),
        )
