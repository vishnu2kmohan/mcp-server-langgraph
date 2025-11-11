"""
Worker utilities for pytest-xdist isolation.

Provides helper functions to identify and configure worker-specific resources
for parallel test execution with pytest-xdist.

Usage:
    from tests.utils.worker_utils import (
        get_worker_id,
        get_worker_num,
        get_worker_port_offset,
        get_worker_db_index,
        get_worker_postgres_schema,
        get_worker_redis_db,
        get_worker_openfga_store,
        worker_tmp_path,
    )

References:
- OpenAI Codex Findings: Worker isolation recommendations
- tests/regression/test_pytest_xdist_* - Regression tests
- tests/conftest.py - Fixture implementations using these utilities
"""

import os
from pathlib import Path


def get_worker_id() -> str:
    """
    Get the current pytest-xdist worker ID.

    Returns:
        str: Worker ID (e.g., "gw0", "gw1", "gw2")
             Returns "gw0" when not running with pytest-xdist

    Example:
        >>> # Running with: pytest -n 4
        >>> worker_id = get_worker_id()
        >>> # worker_id could be "gw0", "gw1", "gw2", or "gw3"
        >>> # Running with: pytest (no xdist)
        >>> worker_id = get_worker_id()
        >>> # worker_id is "gw0" (default)
    """
    return os.getenv("PYTEST_XDIST_WORKER", "gw0")


def get_worker_num() -> int:
    """
    Get the current pytest-xdist worker number.

    Returns:
        int: Worker number (0-based index)
             - gw0 → 0
             - gw1 → 1
             - gw2 → 2
             - Non-xdist → 0

    Example:
        >>> # Running with: pytest -n 4
        >>> worker_num = get_worker_num()
        >>> # worker_num is 0, 1, 2, or 3
    """
    worker_id = get_worker_id()
    return int(worker_id.replace("gw", "")) if worker_id.startswith("gw") else 0


def get_worker_port_offset() -> int:
    """
    Get the port offset for the current worker.

    Port offset formula: worker_num * 100

    This allows each worker to use a unique set of ports for docker-compose
    services, preventing "address already in use" errors.

    Returns:
        int: Port offset (0, 100, 200, 300, ...)

    Example:
        >>> # Worker gw0
        >>> offset = get_worker_port_offset()
        >>> # offset = 0
        >>> postgres_port = 9432 + offset  # 9432

        >>> # Worker gw1
        >>> offset = get_worker_port_offset()
        >>> # offset = 100
        >>> postgres_port = 9432 + offset  # 9532

    References:
        - tests/conftest.py:test_infrastructure_ports
        - tests/regression/test_pytest_xdist_port_conflicts.py
    """
    return get_worker_num() * 100


def get_worker_db_index() -> int:
    """
    Get the Redis database index for the current worker.

    DB index formula: worker_num + 1 (DB 0 reserved)

    Redis has 16 databases by default (0-15), supporting up to 15 concurrent
    xdist workers.

    Returns:
        int: Redis DB index (1, 2, 3, 4, ...)

    Example:
        >>> # Worker gw0
        >>> db_index = get_worker_db_index()
        >>> # db_index = 1

        >>> # Worker gw1
        >>> db_index = get_worker_db_index()
        >>> # db_index = 2

    References:
        - tests/conftest.py:redis_client_clean
        - tests/regression/test_pytest_xdist_worker_database_isolation.py
    """
    return get_worker_num() + 1


def get_worker_postgres_schema() -> str:
    """
    Get the PostgreSQL schema name for the current worker.

    Schema naming convention: test_worker_{worker_id}

    Each worker gets its own schema for complete isolation, preventing
    race conditions where one worker's TRUNCATE affects another worker's data.

    Returns:
        str: Schema name (e.g., "test_worker_gw0", "test_worker_gw1")

    Example:
        >>> # Worker gw0
        >>> schema = get_worker_postgres_schema()
        >>> # schema = "test_worker_gw0"

        >>> # Worker gw2
        >>> schema = get_worker_postgres_schema()
        >>> # schema = "test_worker_gw2"

    References:
        - tests/conftest.py:postgres_connection_clean
        - tests/regression/test_pytest_xdist_worker_database_isolation.py
    """
    worker_id = get_worker_id()
    return f"test_worker_{worker_id}"


def get_worker_redis_db() -> int:
    """
    Alias for get_worker_db_index() for clarity.

    Returns:
        int: Redis DB index for the current worker
    """
    return get_worker_db_index()


def get_worker_openfga_store() -> str:
    """
    Get the OpenFGA store name for the current worker.

    Store naming convention: test_store_{worker_id}

    Each worker should use its own store for complete isolation, preventing
    race conditions where one worker's tuple deletion affects another worker's data.

    Returns:
        str: Store name (e.g., "test_store_gw0", "test_store_gw1")

    Example:
        >>> # Worker gw0
        >>> store = get_worker_openfga_store()
        >>> # store = "test_store_gw0"

        >>> # Worker gw1
        >>> store = get_worker_openfga_store()
        >>> # store = "test_store_gw1"

    References:
        - tests/conftest.py:openfga_client_clean
        - tests/regression/test_pytest_xdist_worker_database_isolation.py
    """
    worker_id = get_worker_id()
    return f"test_store_{worker_id}"


def worker_tmp_path(tmp_path_factory, request=None) -> Path:
    """
    Create a worker-scoped temporary directory.

    This prevents file path collisions when multiple workers write to temp files
    with the same names.

    Args:
        tmp_path_factory: pytest's tmp_path_factory fixture
        request: pytest's request fixture (optional, for test name)

    Returns:
        Path: Worker-scoped temporary directory path

    Example:
        >>> # In a pytest test
        >>> @pytest.fixture
        >>> def my_temp_dir(tmp_path_factory, request):
        >>>     return worker_tmp_path(tmp_path_factory, request)

        >>> def test_with_temp_files(my_temp_dir):
        >>>     temp_file = my_temp_dir / "data.json"
        >>>     temp_file.write_text('{"key": "value"}')
        >>>     # Worker gw0: /tmp/pytest-gw0-*/data.json
        >>>     # Worker gw1: /tmp/pytest-gw1-*/data.json

    References:
        - OpenAI Codex Finding: test_builder_security.py:186
        - tests/regression/test_pytest_xdist_port_conflicts.py
    """
    worker_id = get_worker_id()

    # Create a base temp directory for this worker
    # Format: pytest-{worker_id}-{test_name}
    if request and hasattr(request, "node"):
        # Include test name for better debugging
        test_name = request.node.name
        base_name = f"{worker_id}_{test_name}"
    else:
        # Just worker ID
        base_name = worker_id

    return tmp_path_factory.mktemp(base_name, numbered=True)


def get_worker_resource_summary() -> dict:
    """
    Get a summary of all worker-specific resources.

    Useful for debugging and logging.

    Returns:
        dict: Summary of worker resources with keys:
            - worker_id (str)
            - worker_num (int)
            - port_offset (int)
            - postgres_schema (str)
            - redis_db (int)
            - openfga_store (str)
            - sample_ports (dict): Example ports with offsets

    Example:
        >>> summary = get_worker_resource_summary()
        >>> print(summary)
        {
            'worker_id': 'gw0',
            'worker_num': 0,
            'port_offset': 0,
            'postgres_schema': 'test_worker_gw0',
            'redis_db': 1,
            'openfga_store': 'test_store_gw0',
            'sample_ports': {
                'postgres': 9432,
                'redis': 9379,
                'qdrant': 9333,
            }
        }
    """
    worker_id = get_worker_id()
    worker_num = get_worker_num()
    port_offset = get_worker_port_offset()

    return {
        "worker_id": worker_id,
        "worker_num": worker_num,
        "port_offset": port_offset,
        "postgres_schema": get_worker_postgres_schema(),
        "redis_db": get_worker_redis_db(),
        "openfga_store": get_worker_openfga_store(),
        "sample_ports": {
            "postgres": 9432 + port_offset,
            "redis_checkpoints": 9379 + port_offset,
            "redis_sessions": 9380 + port_offset,
            "qdrant": 9333 + port_offset,
            "qdrant_grpc": 9334 + port_offset,
            "openfga_http": 9080 + port_offset,
            "openfga_grpc": 9081 + port_offset,
            "keycloak": 9082 + port_offset,
        },
    }


# Convenience exports
__all__ = [
    "get_worker_id",
    "get_worker_num",
    "get_worker_port_offset",
    "get_worker_db_index",
    "get_worker_postgres_schema",
    "get_worker_redis_db",
    "get_worker_openfga_store",
    "worker_tmp_path",
    "get_worker_resource_summary",
]
