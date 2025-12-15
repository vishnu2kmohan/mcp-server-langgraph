"""
Cost Storage Backend Factory.

Provides factory function for creating cost storage backends based on
environment configuration. Supports multiple backends:

- memory: In-memory storage (testing, development)
- postgres: PostgreSQL with optional TimescaleDB (self-hosted, Cloud SQL, RDS, Azure PostgreSQL)
- timescaledb: PostgreSQL with TimescaleDB features (same as postgres, explicit)
- timestream: AWS Timestream (EKS deployments)
- adx: Azure Data Explorer / Kusto (AKS deployments)
- bigquery: GCP BigQuery (GKE deployments)

Configuration is via environment variables:
- COST_STORAGE_BACKEND: Backend type (default: "postgres")
- DATABASE_URL: PostgreSQL connection URL (postgres, timescaledb)
- AWS_REGION, TIMESTREAM_DATABASE, TIMESTREAM_TABLE: AWS Timestream config
- ADX_CLUSTER_URI, ADX_DATABASE: Azure Data Explorer config
- GCP_PROJECT_ID, BIGQUERY_DATASET, BIGQUERY_TABLE: GCP BigQuery config
"""

from __future__ import annotations

import os
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from mcp_server_langgraph.monitoring.cost_storage import CostStorageBackend


class CostStorageBackendType(str, Enum):
    """Supported cost storage backend types."""

    MEMORY = "memory"
    POSTGRES = "postgres"
    TIMESCALEDB = "timescaledb"
    TIMESTREAM = "timestream"  # AWS
    ADX = "adx"  # Azure Data Explorer
    BIGQUERY = "bigquery"  # GCP


# Required environment variables per backend
REQUIRED_CONFIG = {
    CostStorageBackendType.MEMORY: [],
    CostStorageBackendType.POSTGRES: ["DATABASE_URL"],
    CostStorageBackendType.TIMESCALEDB: ["DATABASE_URL"],
    CostStorageBackendType.TIMESTREAM: [
        "AWS_REGION",
        "TIMESTREAM_DATABASE",
        "TIMESTREAM_TABLE",
    ],
    CostStorageBackendType.ADX: [
        "ADX_CLUSTER_URI",
        "ADX_DATABASE",
    ],
    CostStorageBackendType.BIGQUERY: [
        "GCP_PROJECT_ID",
        "BIGQUERY_DATASET",
    ],
}


class CostStorageConfigError(Exception):
    """Raised when cost storage configuration is invalid."""

    pass


def get_backend_type() -> CostStorageBackendType:
    """
    Get the configured backend type from environment.

    Returns:
        CostStorageBackendType from COST_STORAGE_BACKEND env var,
        defaults to POSTGRES
    """
    backend_str = os.environ.get("COST_STORAGE_BACKEND", "postgres").lower()

    try:
        return CostStorageBackendType(backend_str)
    except ValueError:
        valid_types = [t.value for t in CostStorageBackendType]
        msg = f"Invalid COST_STORAGE_BACKEND: {backend_str}. Valid options: {valid_types}"
        raise CostStorageConfigError(msg) from None


def validate_backend_config(backend_type: CostStorageBackendType) -> dict[str, str]:
    """
    Validate required configuration for the backend type.

    Args:
        backend_type: The backend type to validate

    Returns:
        Dictionary of configuration values

    Raises:
        CostStorageConfigError: If required config is missing
    """
    required_vars = REQUIRED_CONFIG.get(backend_type, [])
    config: dict[str, str] = {}
    missing: list[str] = []

    for var in required_vars:
        value = os.environ.get(var)
        if value:
            config[var] = value
        else:
            missing.append(var)

    if missing:
        msg = f"Missing required config for {backend_type.value}: {missing}"
        raise CostStorageConfigError(msg)

    return config


def create_cost_storage_backend(
    backend_type: CostStorageBackendType | None = None,
    **kwargs: Any,
) -> CostStorageBackend:
    """
    Create a cost storage backend based on configuration.

    Args:
        backend_type: Override backend type (uses env var if None)
        **kwargs: Additional configuration to pass to backend

    Returns:
        CostStorageBackend implementation

    Raises:
        CostStorageConfigError: If configuration is invalid
        ImportError: If required SDK is not installed
    """
    if backend_type is None:
        backend_type = get_backend_type()

    config = validate_backend_config(backend_type)

    if backend_type == CostStorageBackendType.MEMORY:
        from mcp_server_langgraph.monitoring.cost_storage import MemoryCostStorage

        return MemoryCostStorage()

    if backend_type in (CostStorageBackendType.POSTGRES, CostStorageBackendType.TIMESCALEDB):
        from mcp_server_langgraph.monitoring.cost_storage import PostgresCostStorage

        database_url = kwargs.get("database_url") or config.get("DATABASE_URL", "")
        return PostgresCostStorage(database_url=database_url)  # type: ignore[return-value]

    if backend_type == CostStorageBackendType.TIMESTREAM:
        from mcp_server_langgraph.monitoring.cost_storage_aws import (
            TimestreamCostStorage,
        )

        return TimestreamCostStorage(  # type: ignore[return-value]
            region=config["AWS_REGION"],
            database=config["TIMESTREAM_DATABASE"],
            table=config.get("TIMESTREAM_TABLE", "token_usage"),
            **kwargs,
        )

    if backend_type == CostStorageBackendType.ADX:
        from mcp_server_langgraph.monitoring.cost_storage_azure import (
            ADXCostStorage,
        )

        return ADXCostStorage(  # type: ignore[return-value]
            cluster_uri=config["ADX_CLUSTER_URI"],
            database=config["ADX_DATABASE"],
            table=config.get("ADX_TABLE", "TokenUsage"),
            **kwargs,
        )

    if backend_type == CostStorageBackendType.BIGQUERY:
        from mcp_server_langgraph.monitoring.cost_storage_gcp import (
            BigQueryCostStorage,
        )

        return BigQueryCostStorage(  # type: ignore[return-value]
            project_id=config["GCP_PROJECT_ID"],
            dataset=config["BIGQUERY_DATASET"],
            table=config.get("BIGQUERY_TABLE", "token_usage"),
            **kwargs,
        )

    msg = f"Unsupported backend type: {backend_type}"
    raise CostStorageConfigError(msg)


# Singleton instance
_backend_instance: CostStorageBackend | None = None


def get_cost_storage_backend() -> CostStorageBackend:
    """
    Get the singleton cost storage backend.

    Creates the backend on first call, returns cached instance thereafter.

    Returns:
        CostStorageBackend implementation
    """
    global _backend_instance

    if _backend_instance is None:
        _backend_instance = create_cost_storage_backend()

    return _backend_instance


def reset_cost_storage_backend() -> None:
    """
    Reset the singleton backend instance.

    Useful for testing or reconfiguration.
    """
    global _backend_instance
    _backend_instance = None


def set_cost_storage_backend(backend: CostStorageBackend) -> None:
    """
    Set the singleton backend instance.

    Useful for testing with mock backends.

    Args:
        backend: Backend instance to use
    """
    global _backend_instance
    _backend_instance = backend
