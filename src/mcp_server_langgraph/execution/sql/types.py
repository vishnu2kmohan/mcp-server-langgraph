"""Shared types for SQL execution module."""

from dataclasses import dataclass, field


@dataclass
class ValidationResult:
    """Result of SQL validation."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
