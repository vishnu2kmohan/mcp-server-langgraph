"""Unified SQLAlchemy DeclarativeBase for all models.

All ORM models in the project inherit from this single Base class,
ensuring a unified metadata registry for Alembic autogenerate,
cross-model relationships, and simplified integration test setup.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Unified SQLAlchemy base for all models."""

    pass
