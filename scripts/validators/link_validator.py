#!/usr/bin/env python3
"""
Link Validator (Optional)

Validates links in MDX files.
This is a lightweight validator that checks for:
1. Broken internal links (relative paths)
2. Malformed URLs

Note: External link validation is resource-intensive and should be run separately.

Exit codes:
- 0: All validations passed
- 1: Broken links found
- 2: Critical error
"""

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Set
from urllib.parse import urlparse


class LinkError(Exception):
    """Base exception for link validation errors."""

    pass


class BrokenInternalLinkError(LinkError):
    """Exception raised when an internal link is broken."""

    def __init__(self, file_path: str, link: str):
        self.file_path = file_path
        self.link = link
        super().__init__(f"Broken internal link in {file_path}: {link}")


class MalformedURLError(LinkError):
    """Exception raised when a URL is malformed."""

    def __init__(self, file_path: str, url: str):
        self.file_path = file_path
        self.url = url
        super().__init__(f"Malformed URL in {file_path}: {url}")


@dataclass
class ValidationResult:
    """Result of link validation."""

    is_valid: bool
    errors: List[LinkError] = field(default_factory=list)
    warnings: List[Exception] = field(default_factory=list)
    stats: Dict[str, int] = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        """Get exit code for CLI."""
        if not self.is_valid:
            return 1
        return 0


class LinkValidator:
    """Validates links in MDX files."""

    # Patterns to exclude
    EXCLUDE_PATTERNS = [
        ".mintlify/templates/",
        "node_modules/",
        ".git/",
        "__pycache__/",
    ]

    # Regex patterns
    MARKDOWN_LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^\)]+)\)')
    MDX_LINK_PATTERN = re.compile(r'<a\s+href=["\']([^"\']+)["\']')

    def __init__(self, docs_dir: Path):
        """
        Initialize validator.

        Args:
            docs_dir: Path to docs directory
        """
        self.docs_dir = Path(docs_dir)

    def validate(self) -> ValidationResult:
        """
        Run validation checks.

        Returns:
            ValidationResult with errors and statistics
        """
        errors: List[LinkError] = []
        stats: Dict[str, int] = {
            "total_files": 0,
            "total_links": 0,
            "internal_links": 0,
            "external_links": 0,
            "broken_links": 0,
        }

        if not self.docs_dir.exists():
            return ValidationResult(is_valid=True, stats=stats)

        # Find all MDX files
        mdx_files = self._find_mdx_files()
        stats["total_files"] = len(mdx_files)

        for mdx_file in mdx_files:
            relative_path = mdx_file.relative_to(self.docs_dir)
            file_errors = self._validate_file(mdx_file, str(relative_path), stats)
            errors.extend(file_errors)

        stats["broken_links"] = len(errors)

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            stats=stats,
        )

    def _find_mdx_files(self) -> Set[Path]:
        """Find all MDX files."""
        files = set()

        for mdx_path in self.docs_dir.rglob("*.mdx"):
            relative_path = mdx_path.relative_to(self.docs_dir)
            if any(
                pattern in str(relative_path) for pattern in self.EXCLUDE_PATTERNS
            ):
                continue

            files.add(mdx_path)

        return files

    def _validate_file(
        self, file_path: Path, relative_path: str, stats: Dict[str, int]
    ) -> List[LinkError]:
        """Validate links in a single file."""
        errors = []

        try:
            content = file_path.read_text()
        except Exception:
            return errors

        # Find all links
        links = self._extract_links(content)
        stats["total_links"] += len(links)

        for link in links:
            # Skip anchors and special links
            if link.startswith('#') or link.startswith('mailto:') or link.startswith('tel:'):
                continue

            # Check if internal or external
            if self._is_internal_link(link):
                stats["internal_links"] += 1
                # Validate internal link
                if not self._validate_internal_link(file_path, link):
                    errors.append(BrokenInternalLinkError(relative_path, link))
            else:
                stats["external_links"] += 1
                # Basic URL validation
                if not self._is_valid_url(link):
                    errors.append(MalformedURLError(relative_path, link))

        return errors

    def _extract_links(self, content: str) -> List[str]:
        """Extract all links from content."""
        links = []

        # Markdown links
        for match in self.MARKDOWN_LINK_PATTERN.finditer(content):
            links.append(match.group(2))

        # HTML links
        for match in self.MDX_LINK_PATTERN.finditer(content):
            links.append(match.group(1))

        return links

    def _is_internal_link(self, link: str) -> bool:
        """Check if link is internal (relative path)."""
        return not link.startswith(('http://', 'https://', '//', 'www.'))

    def _validate_internal_link(self, source_file: Path, link: str) -> bool:
        """Validate that internal link target exists."""
        # Remove anchor if present
        link = link.split('#')[0]
        if not link:  # Just an anchor
            return True

        # Resolve relative to source file's directory
        source_dir = source_file.parent
        target = source_dir / link

        # Check if target exists (try with .mdx extension if not specified)
        if target.exists():
            return True

        # Try with .mdx extension
        if not link.endswith('.mdx'):
            target_mdx = source_dir / f"{link}.mdx"
            if target_mdx.exists():
                return True

        return False

    def _is_valid_url(self, url: str) -> bool:
        """Basic URL validation."""
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) or url.startswith('//')
        except Exception:
            return False

    def print_report(self, result: ValidationResult) -> None:
        """Print validation report to stdout."""
        print("\n" + "=" * 80)
        print("🔗 Link Validation Report")
        print("=" * 80)

        # Statistics
        print("\n📊 Statistics:")
        print(f"  Total files scanned: {result.stats.get('total_files', 0)}")
        print(f"  Total links found: {result.stats.get('total_links', 0)}")
        print(f"  Internal links: {result.stats.get('internal_links', 0)}")
        print(f"  External links: {result.stats.get('external_links', 0)}")
        print(f"  Broken links: {result.stats.get('broken_links', 0)}")

        # Errors
        if result.errors:
            print(f"\n❌ Errors ({len(result.errors)}):")

            broken = [e for e in result.errors if isinstance(e, BrokenInternalLinkError)]
            malformed = [e for e in result.errors if isinstance(e, MalformedURLError)]

            if broken:
                print(f"\n  Broken internal links ({len(broken)}):")
                for error in broken:
                    print(f"    ❌ {error.file_path}: {error.link}")

            if malformed:
                print(f"\n  Malformed URLs ({len(malformed)}):")
                for error in malformed:
                    print(f"    ❌ {error.file_path}: {error.url}")

        # Summary
        print("\n" + "=" * 80)
        if result.is_valid:
            print("✅ All links are valid!")
        else:
            print("❌ Validation failed - fix broken links above")
        print("=" * 80 + "\n")


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Validate links in MDX files")
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("docs"),
        help="Path to docs directory (default: docs/)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress output (only use exit code)",
    )

    args = parser.parse_args()

    # Run validation
    validator = LinkValidator(args.docs_dir)
    result = validator.validate()

    # Print report
    if not args.quiet:
        validator.print_report(result)

    # Exit with appropriate code
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
