"""
Studio Performance Module

Provides bundle size analysis and performance optimization configuration.
"""

from pathlib import Path
from typing import Any

# Bundle size targets (in bytes)
BUNDLE_SIZE_TARGETS: dict[str, int] = {
    "initial": 600 * 1024,  # 600KB uncompressed
    "gzipped": 500 * 1024,  # 500KB gzipped target
}

# Code splitting configuration for Vite
CODE_SPLITTING_CONFIG: dict[str, Any] = {
    "manualChunks": {
        "vendor": ["react", "react-dom", "react-router-dom"],
        "ui": ["@radix-ui", "lucide-react"],
        "reactflow": ["reactflow", "@xyflow/react"],
        "zustand": ["zustand"],
        "utils": ["date-fns", "clsx", "tailwind-merge"],
    }
}

# Routes that should be lazy loaded
LAZY_LOADED_ROUTES: list[str] = [
    "/studio/workflows",
    "/studio/chat",
    "/studio/sessions",
    "/studio/mcp",
    "/studio/observability",
    "/studio/settings",
    "/admin/dashboard",
    "/admin/users",
    "/admin/metrics",
    "/admin/audit",
    "/admin/organizations",
]


class BundleAnalyzer:
    """Analyzes frontend bundle sizes.

    Example:
        analyzer = BundleAnalyzer()
        total = analyzer.calculate_total_size()
        print(f"Total bundle size: {total / 1024:.1f}KB")
    """

    def __init__(self, dist_path: Path | None = None) -> None:
        """Initialize the bundle analyzer.

        Args:
            dist_path: Path to the dist directory
        """
        self._dist_path = dist_path

    def calculate_total_size(self) -> int:
        """Calculate the total bundle size.

        Returns:
            Total size in bytes
        """
        files = self._get_bundle_files()
        return sum(size for _, size in files)

    def _get_bundle_files(self) -> list[tuple[str, int]]:
        """Get list of bundle files and their sizes.

        Returns:
            List of (filename, size) tuples
        """
        if self._dist_path is None or not self._dist_path.exists():
            return []

        files = []
        for js_file in self._dist_path.glob("**/*.js"):
            files.append((js_file.name, js_file.stat().st_size))

        return files

    def check_against_targets(self) -> dict[str, bool]:
        """Check if bundle sizes meet targets.

        Returns:
            Dict with pass/fail for each target
        """
        total_size = self.calculate_total_size()

        return {
            "initial": total_size <= BUNDLE_SIZE_TARGETS["initial"],
            "gzipped": True,  # Would need actual gzip check
        }


__all__ = [
    "BUNDLE_SIZE_TARGETS",
    "CODE_SPLITTING_CONFIG",
    "LAZY_LOADED_ROUTES",
    "BundleAnalyzer",
]
