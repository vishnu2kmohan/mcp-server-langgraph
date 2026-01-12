"""
TDD Tests for Alembic Migration Dockerfile.

These tests validate that the Alembic Dockerfile follows the minimal dependency
approach and correctly handles model imports for database migrations.

Issue Fixed: Dockerfile.alembic was updated to use --no-install-project to avoid
pulling in heavy dependencies (LangGraph, LiteLLM, Anthropic SDK, etc.) which
would make the image 500MB+ instead of ~50MB.

Solution: Copy only the models.py file (self-contained SQLAlchemy models) and
use a fallback import in alembic/env.py that works in both local development
(full package) and Docker (minimal package).

Reference: ADR-0101, config/openfga/compose_model.py
"""

import gc
from pathlib import Path

import pytest

# Module-level pytest markers for test categorization
pytestmark = [pytest.mark.unit, pytest.mark.docker]


@pytest.fixture(scope="module")
def alembic_dockerfile_path() -> Path:
    """Path to the Alembic Dockerfile."""
    return Path(__file__).parent.parent.parent / "docker" / "Dockerfile.alembic"


@pytest.fixture(scope="module")
def alembic_dockerfile_content(alembic_dockerfile_path: Path) -> str:
    """Content of the Alembic Dockerfile."""
    if not alembic_dockerfile_path.exists():
        pytest.skip(f"Alembic Dockerfile not found at {alembic_dockerfile_path}")
    return alembic_dockerfile_path.read_text()


@pytest.fixture(scope="module")
def alembic_env_path() -> Path:
    """Path to the alembic/env.py file."""
    return Path(__file__).parent.parent.parent / "alembic" / "env.py"


@pytest.fixture(scope="module")
def alembic_env_content(alembic_env_path: Path) -> str:
    """Content of the alembic/env.py file."""
    if not alembic_env_path.exists():
        pytest.skip(f"alembic/env.py not found at {alembic_env_path}")
    return alembic_env_path.read_text()


@pytest.fixture(scope="module")
def models_path() -> Path:
    """Path to the database models file."""
    return Path(__file__).parent.parent.parent / "src" / "mcp_server_langgraph" / "database" / "models.py"


@pytest.fixture(scope="module")
def models_content(models_path: Path) -> str:
    """Content of the database models file."""
    if not models_path.exists():
        pytest.skip(f"models.py not found at {models_path}")
    return models_path.read_text()


@pytest.mark.xdist_group(name="alembic_dockerfile")
class TestAlembicDockerfileStructure:
    """Tests for Dockerfile structure and multi-stage build."""

    def teardown_method(self) -> None:
        """Clean up after each test to prevent memory issues in xdist."""
        gc.collect()

    def test_dockerfile_exists_at_expected_path(self, alembic_dockerfile_path: Path) -> None:
        """Verify Alembic Dockerfile exists at the expected path."""
        assert alembic_dockerfile_path.exists(), (
            f"Alembic Dockerfile should exist at {alembic_dockerfile_path}. "
            "This is required for building the database migration image."
        )

    def test_uses_multistage_build(self, alembic_dockerfile_content: str) -> None:
        """
        Verify Dockerfile uses multi-stage build.

        Multi-stage builds are required to:
        1. Use uv for fast dependency installation in builder stage
        2. Remove uv from runtime stage (saves ~52MB)
        """
        from_count = alembic_dockerfile_content.lower().count("from ")
        assert from_count >= 2, (
            f"Dockerfile should use multi-stage build (found {from_count} FROM statements). "
            "First stage installs deps with uv, second stage is minimal runtime."
        )

    def test_has_builder_stage_named_correctly(self, alembic_dockerfile_content: str) -> None:
        """Verify Dockerfile has a named builder stage."""
        assert "as builder" in alembic_dockerfile_content.lower(), "Dockerfile should have a named 'builder' stage"

    def test_uses_minimal_dependency_approach(self, alembic_dockerfile_content: str) -> None:
        """
        Verify Dockerfile uses --no-install-project to avoid heavy dependencies.

        This is critical: Installing the full mcp_server_langgraph package would
        pull in LangGraph, LiteLLM, Anthropic SDK, etc. (~500MB+). By using
        --no-install-project --only-group alembic, we only install minimal deps
        (alembic, sqlalchemy, asyncpg, pyyaml) keeping the image ~50MB.
        """
        assert "--no-install-project" in alembic_dockerfile_content, (
            "Dockerfile should use --no-install-project to avoid heavy dependencies. "
            "This keeps the image ~50MB instead of 500MB+."
        )
        assert "--only-group alembic" in alembic_dockerfile_content, (
            "Dockerfile should use --only-group alembic for minimal dependencies"
        )

    def test_copies_models_file_directly(self, alembic_dockerfile_content: str) -> None:
        """
        Verify Dockerfile copies only the models.py file, not the entire package.

        The models.py file is self-contained (only SQLAlchemy imports), so we
        can copy it directly instead of installing the full package.
        """
        assert "models.py" in alembic_dockerfile_content, "Dockerfile should copy models.py directly for env.py imports"

    def test_uses_python_slim_base_image(self, alembic_dockerfile_content: str) -> None:
        """Verify Dockerfile uses slim Python image for minimal size."""
        assert "python:" in alembic_dockerfile_content.lower(), "Dockerfile should use official Python image"
        assert "-slim" in alembic_dockerfile_content, "Dockerfile should use slim variant for minimal image size"


@pytest.mark.xdist_group(name="alembic_dockerfile")
class TestAlembicEnvPyImportFallback:
    """Tests for alembic/env.py import fallback mechanism."""

    def teardown_method(self) -> None:
        """Clean up after each test to prevent memory issues in xdist."""
        gc.collect()

    def test_env_py_has_import_fallback(self, alembic_env_content: str) -> None:
        """
        Verify env.py has try/except fallback for models import.

        env.py needs to work in two scenarios:
        1. Local development: import from mcp_server_langgraph.database.models
        2. Docker container: import from local models.py (fallback)
        """
        assert "try:" in alembic_env_content, "env.py should have try/except for import fallback"
        assert "except ImportError:" in alembic_env_content, "env.py should catch ImportError and fallback to local models"
        assert "from models import Base" in alembic_env_content, "env.py should have fallback import: from models import Base"

    def test_env_py_imports_base_from_package(self, alembic_env_content: str) -> None:
        """Verify env.py tries to import from the full package first."""
        assert "from mcp_server_langgraph.database.models import Base" in alembic_env_content, (
            "env.py should try to import from full package first (for local dev)"
        )

    def test_env_py_sets_target_metadata(self, alembic_env_content: str) -> None:
        """Verify env.py sets target_metadata for autogenerate support."""
        assert "target_metadata = Base.metadata" in alembic_env_content, (
            "env.py should set target_metadata = Base.metadata for autogenerate"
        )


@pytest.mark.xdist_group(name="alembic_dockerfile")
class TestModelsFileIsStandalone:
    """Tests that models.py is self-contained and doesn't import from the main package."""

    def teardown_method(self) -> None:
        """Clean up after each test to prevent memory issues in xdist."""
        gc.collect()

    def test_models_file_exists(self, models_path: Path) -> None:
        """Verify models.py exists at the expected path."""
        assert models_path.exists(), f"models.py should exist at {models_path}"

    def test_models_file_does_not_import_from_package(self, models_content: str) -> None:
        """
        Verify models.py doesn't import from mcp_server_langgraph.

        This is critical for the minimal Dockerfile approach. If models.py
        imported from other parts of the package, we'd need to install the
        full package in the Docker image.
        """
        # Check for any imports from the main package
        package_import_patterns = [
            "from mcp_server_langgraph",
            "import mcp_server_langgraph",
        ]

        for pattern in package_import_patterns:
            assert pattern not in models_content, (
                f"models.py should NOT import from mcp_server_langgraph. "
                f"Found: {pattern}. "
                f"This would break the minimal Dockerfile approach."
            )

    def test_models_file_only_imports_standard_and_sqlalchemy(self, models_content: str) -> None:
        """
        Verify models.py only imports from standard library and SQLAlchemy.

        Allowed imports:
        - Standard library (datetime, decimal, typing, etc.)
        - SQLAlchemy (sqlalchemy, sqlalchemy.orm)

        Forbidden imports:
        - LangGraph, LangChain, LiteLLM, etc.
        - Anything from mcp_server_langgraph
        """
        # Extract import lines
        import_lines = [line.strip() for line in models_content.split("\n") if line.strip().startswith(("import ", "from "))]

        # Allowed package prefixes
        allowed_prefixes = [
            "from datetime",
            "from decimal",
            "from typing",
            "import datetime",
            "import decimal",
            "from sqlalchemy",
            "import sqlalchemy",
        ]

        for import_line in import_lines:
            is_allowed = any(import_line.startswith(prefix) for prefix in allowed_prefixes)
            assert is_allowed, (
                f"models.py has forbidden import: {import_line}. "
                f"Only standard library and SQLAlchemy imports are allowed "
                f"to keep the Alembic Docker image minimal."
            )

    def test_models_defines_base(self, models_content: str) -> None:
        """Verify models.py defines Base using declarative_base."""
        assert "Base = declarative_base()" in models_content, (
            "models.py should define Base = declarative_base() for SQLAlchemy models"
        )

    def test_models_defines_at_least_one_table(self, models_content: str) -> None:
        """Verify models.py defines at least one SQLAlchemy table."""
        assert "__tablename__" in models_content, "models.py should define at least one SQLAlchemy model with __tablename__"
