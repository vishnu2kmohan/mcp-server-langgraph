"""StudioLoader for loading STUDIO.md configurations from files.

Provides a convenient interface for loading StudioConfig from file paths,
combining file reading with parsing.

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

import logging
from pathlib import Path

from mcp_server_langgraph.studio.config.models import StudioConfig
from mcp_server_langgraph.studio.config.parser import StudioParser, StudioParseError

logger = logging.getLogger(__name__)


class StudioLoader:
    """Loads StudioConfig from STUDIO.md files.

    Wraps the StudioParser with file reading functionality.

    Attributes:
        parser: The StudioParser instance used for parsing
    """

    def __init__(self, parser: StudioParser | None = None) -> None:
        """Initialize the loader.

        Args:
            parser: Optional custom parser instance
        """
        self.parser = parser or StudioParser()

    def load(self, file_path: Path) -> StudioConfig:
        """Load StudioConfig from a file.

        Args:
            file_path: Path to the STUDIO.md file

        Returns:
            Parsed StudioConfig

        Raises:
            FileNotFoundError: If file doesn't exist
            StudioParseError: If file content is invalid
        """
        if not file_path.exists():
            raise FileNotFoundError(f"STUDIO.md not found: {file_path}")

        content = file_path.read_text(encoding="utf-8")
        return self.parser.parse(content)

    def load_or_default(self, file_path: Path) -> StudioConfig:
        """Load StudioConfig from a file or return default.

        Args:
            file_path: Path to the STUDIO.md file

        Returns:
            Parsed StudioConfig or default config if file not found/invalid
        """
        try:
            return self.load(file_path)
        except (FileNotFoundError, StudioParseError) as e:
            logger.debug(f"Could not load {file_path}, using defaults: {e}")
            return StudioConfig(name="default")
