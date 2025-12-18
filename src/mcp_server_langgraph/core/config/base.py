"""
Base Configuration Module.

Provides shared utilities and base classes for domain-specific settings.
"""

from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DomainSettings(BaseSettings):
    """
    Base class for domain-specific settings.

    Provides common configuration and utility methods.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @field_validator("*", mode="before")
    @classmethod
    def parse_comma_separated_list(cls, v: Any, info: Any) -> Any:
        """Parse comma-separated strings from environment variables into lists."""
        # Only apply to list fields
        field_type = cls.model_fields.get(info.field_name)
        if field_type is None:
            return v

        # Check if field annotation is a list type
        annotation = field_type.annotation
        if annotation is None:
            return v

        # Handle Optional[list[...]] and list[...]
        origin = getattr(annotation, "__origin__", None)
        if origin is list or (origin is not None and hasattr(origin, "__args__")):
            if isinstance(v, str):
                return [item.strip() for item in v.split(",") if item.strip()]

        return v


__all__ = ["DomainSettings", "BaseSettings", "SettingsConfigDict"]
