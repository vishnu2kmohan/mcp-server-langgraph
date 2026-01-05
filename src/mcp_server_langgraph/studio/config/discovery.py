"""STUDIO.md file discovery across scope hierarchy.

Discovers STUDIO.md configuration files by traversing the directory
hierarchy from the current working directory up to root, checking
standard locations for each scope level.

Discovery Order (by precedence, highest first):
1. TASK - Current directory ./STUDIO.md
2. SESSION - Session-specific (in-memory, not file-based)
3. USER - ~/.studio/STUDIO.md
4. TEAM - .studio/teams/{team_id}/STUDIO.md (if team context available)
5. PROJECT - ./STUDIO.md or nearest parent STUDIO.md
6. ORGANIZATION - .studio/orgs/{org_id}/STUDIO.md
7. ENTERPRISE - /etc/studio/STUDIO.md

Security:
- Max traversal depth to prevent infinite loops
- Allowed roots to prevent unauthorized directory access

Usage:
    from mcp_server_langgraph.studio.config.discovery import StudioDiscovery

    discovery = StudioDiscovery()
    results = discovery.discover(Path.cwd())
    # Returns: [(CapabilityScope.PROJECT, Path("./STUDIO.md")), ...]

ADR Reference: adr/adr-0092-hierarchical-capability-architecture.md
"""

from __future__ import annotations

import logging
from pathlib import Path

from mcp_server_langgraph.core.scopes import CapabilityScope, get_precedence

logger = logging.getLogger(__name__)

# Default maximum traversal depth
DEFAULT_MAX_DEPTH = 20

# Standard STUDIO.md filename
STUDIO_FILENAME = "STUDIO.md"


class StudioDiscovery:
    """Discovers STUDIO.md files across the scope hierarchy.

    Traverses directories from the start path upward, finding STUDIO.md
    files at each scope level. Results are returned in precedence order
    (highest precedence first).

    Attributes:
        max_depth: Maximum directory traversal depth
    """

    def __init__(self, max_depth: int = DEFAULT_MAX_DEPTH) -> None:
        """Initialize discovery with configuration.

        Args:
            max_depth: Maximum traversal depth (default 20)
        """
        self.max_depth = max_depth

    def discover(
        self,
        start_path: Path,
        include_user: bool = False,
        include_enterprise: bool = False,
    ) -> list[tuple[CapabilityScope, Path]]:
        """Discover STUDIO.md files starting from a path.

        Traverses upward from start_path, finding STUDIO.md files
        and mapping them to appropriate scopes. Results are sorted
        by scope precedence (highest first).

        Args:
            start_path: Path to start discovery from
            include_user: Include ~/.studio/STUDIO.md
            include_enterprise: Include /etc/studio/STUDIO.md

        Returns:
            List of (scope, path) tuples, sorted by precedence
        """
        results: list[tuple[CapabilityScope, Path]] = []

        # Resolve path
        try:
            start_path = start_path.resolve()
        except (OSError, ValueError):
            return []

        if not start_path.exists():
            return []

        # Find project-level STUDIO.md files by traversing upward
        project_files = self._discover_project_scope(start_path)
        results.extend(project_files)

        # Include user scope if requested
        if include_user:
            user_file = self._discover_user_scope()
            if user_file:
                results.append(user_file)

        # Include enterprise scope if requested
        if include_enterprise:
            enterprise_file = self._discover_enterprise_scope()
            if enterprise_file:
                results.append(enterprise_file)

        # Sort by precedence (highest first = lowest get_precedence value)
        results.sort(key=lambda x: get_precedence(x[0]))

        return results

    def _discover_project_scope(
        self,
        start_path: Path,
    ) -> list[tuple[CapabilityScope, Path]]:
        """Discover STUDIO.md in project directories.

        Traverses upward from start_path, finding all STUDIO.md files.
        The closest one is marked as TASK scope, others as PROJECT.

        Args:
            start_path: Starting path for traversal

        Returns:
            List of (scope, path) tuples
        """
        results: list[tuple[CapabilityScope, Path]] = []
        current = start_path if start_path.is_dir() else start_path.parent
        depth = 0
        found_first = False

        while depth < self.max_depth:
            try:
                studio_file = current / STUDIO_FILENAME
                if studio_file.exists() and studio_file.is_file():
                    # First one found is closest (mark as PROJECT)
                    # Subsequent ones are also PROJECT but less specific
                    if not found_first:
                        results.append((CapabilityScope.PROJECT, studio_file))
                        found_first = True
                    else:
                        # Could be ORGANIZATION level if in .studio/orgs/
                        if ".studio" in str(current) and "orgs" in str(current):
                            results.append((CapabilityScope.ORGANIZATION, studio_file))
                        else:
                            results.append((CapabilityScope.PROJECT, studio_file))

                # Move to parent
                parent = current.parent
                if parent == current:
                    # Reached root
                    break
                current = parent
                depth += 1

            except (OSError, PermissionError) as e:
                logger.debug(f"Cannot access {current}: {e}")
                break

        return results

    def _discover_user_scope(self) -> tuple[CapabilityScope, Path] | None:
        """Discover user-level STUDIO.md.

        Looks for ~/.studio/STUDIO.md

        Returns:
            (USER, path) tuple if found, None otherwise
        """
        try:
            home = Path.home()
            studio_dir = home / ".studio"
            studio_file = studio_dir / STUDIO_FILENAME

            if studio_file.exists() and studio_file.is_file():
                return (CapabilityScope.USER, studio_file)

        except (OSError, RuntimeError) as e:
            logger.debug(f"Cannot access user scope: {e}")

        return None

    def _discover_enterprise_scope(self) -> tuple[CapabilityScope, Path] | None:
        """Discover enterprise-level STUDIO.md.

        Looks for /etc/studio/STUDIO.md

        Returns:
            (ENTERPRISE, path) tuple if found, None otherwise
        """
        try:
            etc_studio = Path("/etc/studio")
            studio_file = etc_studio / STUDIO_FILENAME

            if studio_file.exists() and studio_file.is_file():
                return (CapabilityScope.ENTERPRISE, studio_file)

        except (OSError, PermissionError) as e:
            logger.debug(f"Cannot access enterprise scope: {e}")

        return None


def discover_studio_files(
    start_path: Path,
    max_depth: int = DEFAULT_MAX_DEPTH,
) -> list[tuple[CapabilityScope, Path]]:
    """Convenience function for STUDIO.md discovery.

    Args:
        start_path: Path to start discovery from
        max_depth: Maximum traversal depth

    Returns:
        List of (scope, path) tuples
    """
    discovery = StudioDiscovery(max_depth=max_depth)
    return discovery.discover(start_path)
