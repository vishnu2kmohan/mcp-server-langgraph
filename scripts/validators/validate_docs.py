#!/usr/bin/env python3
"""
Consolidated Documentation Validator for Pre-commit Hooks.

This script consolidates 6 documentation validation hooks into a single tool:
1. MDX extension validation (docs/ must use .mdx, not .md)
2. File naming conventions (kebab-case)
3. Frontmatter quote standardization
4. ADR synchronization (adr/ <-> docs/architecture/)
5. Documentation integrity tests
6. Documentation structure tests

Usage:
    python scripts/validators/validate_docs.py --all
    python scripts/validators/validate_docs.py --mdx --docs-dir docs/
    python scripts/validators/validate_docs.py --adr --repo-root .
    python scripts/validators/validate_docs.py --tests --dry-run

Exit codes:
    0: All validations passed
    1: Validation failures found
"""

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path


# =============================================================================
# MDX Extension Validation
# =============================================================================


@dataclass
class MDXValidationResult:
    """Result of MDX extension and naming validation."""

    is_valid: bool = True
    md_files: list[Path] = field(default_factory=list)
    invalid_names: list[tuple[Path, str]] = field(default_factory=list)
    frontmatter_issues: list[tuple[Path, str]] = field(default_factory=list)
    icon_errors: list[tuple[Path, str]] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)


# Conventional files allowed to have UPPERCASE names
CONVENTIONAL_FILES = {
    "README.md",
    "CHANGELOG.md",
    "CONTRIBUTING.md",
    "LICENSE",
    "LICENSE.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "TESTING.md",
    "ROADMAP.md",
    "MIGRATION.md",
}

# Patterns to exclude from validation
EXCLUDE_PATTERNS = [
    ".mintlify/",
    "node_modules/",
    ".git/",
    "__pycache__/",
    ".pytest_cache/",
    "venv/",
    ".venv/",
]

# =============================================================================
# Icon Registry for Mintlify (Font Awesome 6.x subset)
# =============================================================================

# Valid Mintlify icons - comprehensive set from Font Awesome 6.x
# Reference: docs/references/icon-selection-guide.mdx
VALID_ICONS: set[str] = {
    # Deployment & Infrastructure
    "rocket",
    "dharmachakra",
    "docker",
    "cubes",
    "server",
    "cloud",
    "network-wired",
    # Cloud Providers
    "google",
    "aws",
    "microsoft",
    # Security & Authentication
    "shield",
    "shield-halved",
    "shield-check",
    "lock",
    "key",
    "key-skeleton",
    "user-shield",
    "user-gear",
    "users-gear",
    "users",
    "vault",
    # Observability & Monitoring
    "chart-line",
    "chart-bar",
    "database",
    "arrow-up-right-dots",
    "magnifying-glass-chart",
    "gauge",
    "heart-pulse",
    # Resilience & Operations
    "life-ring",
    "clipboard-check",
    "list-check",
    "arrows-rotate",
    "rotate",
    # Development & Code
    "code",
    "terminal",
    "file-code",
    "bug",
    "flask",
    "vial",
    "wrench",
    "screwdriver-wrench",
    "gear",
    "toolbox",
    # Documentation & Reference
    "book",
    "book-open",
    "file-lines",
    "file-contract",
    "scroll",
    "icons",
    "newspaper",
    # Version & Releases
    "tag",
    "code-branch",
    # Architecture & Design
    "diagram-project",
    "sitemap",
    "layer-group",
    "cubes-stacked",
    "scale-balanced",
    # AI & Machine Learning
    "brain",
    "robot",
    "microchip",
    "wand-magic-sparkles",
    # Communication & Integration
    "plug",
    "link",
    # Time & Scheduling
    "clock",
    "calendar",
    "stopwatch",
    # Actions & Status
    "bolt",  # Font Awesome equivalent of Lucide 'zap'
    "infinity",
    "play",
    "stop",
    "refresh",
    "download",
    "upload",
    "check",
    "circle-check",
    "xmark",
    "exclamation",
    "triangle-exclamation",
    "info",
    "question",
    "trophy",
    # Navigation
    "arrow-right",
    "arrow-left",
    "arrow-up",
    "arrow-down",
    "map",
    # Misc
    "cookie",
    "floppy-disk",
    "memory",
    "broom",
    "package",
    "dollar-sign",
    "eye",
    "flag",
    # Additional valid Font Awesome 6.x icons
    "circle-exclamation",
    "ship",
    "code-pull-request",
    "shield-keyhole",
    "folder-tree",
    "gauge-high",
    "calculator",
    "file-signature",
    "money-bill-trend-up",
    "paper-plane",
    "sliders",
    "computer",
    "shuffle",
    "sparkles",
    "file",
    "plug-circle-bolt",
    "lightbulb",
    "message",
    "drafting-compass",
    "hospital",
    "user-lock",
    "file-medical",
    "pen-to-square",
    "trash",
    "file-export",
    "folder-open",
    "certificate",
    "cube",
    "bell",
    "route",
    "book-medical",
    "github",
    # Template placeholders - allowed for documentation examples only
    "icon-name",
    "font-awesome-icon-name",
    "semantic-font-awesome-icon",
}

# ADR topic-to-icon mapping for auto-assignment
# Maps keywords in ADR titles/filenames to appropriate icons
ADR_ICON_MAPPING: dict[str, str] = {
    # Default for all ADRs per icon-selection-guide.mdx
    "default": "file-lines",
    # LLM & AI
    "llm": "microchip",
    "litellm": "microchip",
    "anthropic": "brain",
    "pydantic": "code",
    "agentic": "robot",
    # Authorization & Security
    "openfga": "shield",
    "authorization": "shield",
    "authentication": "key",
    "keycloak": "key",
    "jwt": "key",
    "identity": "user-shield",
    "scim": "users-gear",
    "infisical": "lock",
    "secrets": "lock",
    "security": "shield-halved",
    "permission": "shield",
    "kong": "network-wired",
    # Observability
    "observability": "chart-line",
    "monitoring": "chart-line",
    "metrics": "chart-line",
    # Infrastructure
    "deployment": "rocket",
    "gke": "google",
    "autopilot": "google",
    "postgresql": "database",
    "redis": "database",
    "memorystore": "database",
    "session": "database",
    "checkpointing": "database",
    "storage": "database",
    # Performance
    "rate-limiting": "gauge",
    "caching": "memory",
    "resilience": "life-ring",
    "async": "bolt",
    # CI/CD & Testing
    "cicd": "arrows-rotate",
    "pipeline": "arrows-rotate",
    "testing": "flask",
    "pytest": "flask",
    "fixture": "flask",
    "xdist": "flask",
    # Errors & Handling
    "error": "bug",
    "exception": "bug",
    # Versioning & Standards
    "semantic-versioning": "tag",
    "versioning": "tag",
    # Architecture
    "langgraph": "diagram-project",
    "functional": "diagram-project",
    "diagram": "diagram-project",
    "visual": "diagram-project",
    "workflow": "diagram-project",
    "builder": "diagram-project",
    # Compliance
    "compliance": "scale-balanced",
    "gdpr": "scale-balanced",
    # Configuration & Tools
    "feature-flag": "flag",
    "cookiecutter": "cookie",
    "template": "cookie",
    "ruff": "broom",
    "mintlify": "book",
    "pre-commit": "code-branch",
    "fastapi": "bolt",
    "uv": "package",
    "dependency": "package",
    "singleton": "cubes",
    "helm": "cubes",
    # Transport & Protocol
    "mcp": "plug",
    "http": "plug",
    "transport": "plug",
    "protocol": "plug",
}


def is_kebab_case(filename: str) -> bool:
    """Check if filename follows kebab-case convention."""
    stem = Path(filename).stem

    if not stem:
        return False

    # Hidden files are allowed
    if stem.startswith("."):
        return True

    # No leading or trailing hyphens
    if stem.startswith("-") or stem.endswith("-"):
        return False

    # Kebab-case: lowercase letters, numbers, and hyphens
    pattern = r"^[a-z0-9]+(-[a-z0-9]+)*$"
    return bool(re.match(pattern, stem))


def to_kebab_case(filename: str) -> str:
    """Convert filename to kebab-case suggestion."""
    stem = Path(filename).stem
    extension = Path(filename).suffix

    suggested = stem.replace("_", "-").lower()
    suggested = re.sub(r"-+", "-", suggested).strip("-")

    return f"{suggested}{extension}"


def parse_frontmatter(content: str) -> tuple[dict | None, str, str]:
    """Parse YAML frontmatter from .mdx content."""
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", content, re.DOTALL)
    if not match:
        return None, "", content

    frontmatter_text = match.group(1)
    body_text = match.group(2)

    frontmatter = {}
    for line in frontmatter_text.split("\n"):
        if ":" in line:
            key, value = line.split(":", 1)
            frontmatter[key.strip()] = value.strip()

    return frontmatter, frontmatter_text, body_text


# =============================================================================
# Icon Validation Functions
# =============================================================================


def validate_icon_format(icon_value: str) -> tuple[bool, str | None, str | None]:
    """
    Validate icon format and value.

    Args:
        icon_value: The raw icon value from frontmatter (e.g., "'rocket'", '"rocket"', "rocket")

    Returns:
        Tuple of (is_valid, icon_name, error_message)
        - is_valid: True if icon format and value are valid
        - icon_name: The extracted icon name (without quotes) if valid
        - error_message: Error description if invalid, None otherwise
    """
    if not icon_value or icon_value.strip() == "":
        return False, None, "Icon value is empty"

    icon_value = icon_value.strip()

    # Check for empty quotes
    if icon_value in ("''", '""'):
        return False, None, "Icon value is empty (just quotes)"

    # Check for single quotes (preferred format)
    if icon_value.startswith("'") and icon_value.endswith("'"):
        icon_name = icon_value[1:-1]
        if not icon_name:
            return False, None, "Icon value is empty inside quotes"
        if icon_name not in VALID_ICONS:
            return False, icon_name, f"Icon '{icon_name}' not in valid icon registry"
        return True, icon_name, None

    # Check for double quotes (should be single quotes)
    if icon_value.startswith('"') and icon_value.endswith('"'):
        icon_name = icon_value[1:-1]
        return False, icon_name, f"Icon uses double quotes (should use single quotes): {icon_value}"

    # Unquoted value
    if icon_value not in VALID_ICONS:
        return (
            False,
            icon_value,
            f"Icon '{icon_value}' is unquoted and not in valid icon registry. Use single quotes: icon: '{icon_value}'",
        )
    return False, icon_value, f"Icon is unquoted (should use single quotes): icon: '{icon_value}'"


def validate_adr_has_icon(file_path: Path) -> tuple[bool, str | None]:
    """
    Validate that an ADR file has an icon in its frontmatter.

    Args:
        file_path: Path to the .mdx file

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check if this is an ADR file (in docs/architecture/ with adr-* prefix)
    is_adr = "architecture" in str(file_path) and file_path.name.startswith("adr-")

    if not is_adr:
        # Non-ADR files don't require icons (for now)
        return True, None

    try:
        content = file_path.read_text()
        frontmatter, fm_text, _ = parse_frontmatter(content)

        if not frontmatter:
            return False, f"ADR file has no frontmatter: {file_path.name}"

        # Check for icon in frontmatter
        icon_value = frontmatter.get("icon", "").strip()
        if not icon_value:
            return False, f"ADR file is missing icon in frontmatter: {file_path.name}"

        return True, None
    except Exception as e:
        return False, f"Error reading file {file_path.name}: {e}"


def get_suggested_adr_icon(file_path: Path) -> str:
    """
    Get suggested icon for an ADR based on its filename.

    Args:
        file_path: Path to the ADR file

    Returns:
        Suggested icon name from ADR_ICON_MAPPING
    """
    filename = file_path.stem.lower()  # e.g., "adr-0001-llm-multi-provider"

    # Check each keyword in the mapping
    for keyword, icon in ADR_ICON_MAPPING.items():
        if keyword != "default" and keyword in filename:
            return icon

    # Return default ADR icon
    return ADR_ICON_MAPPING.get("default", "file-lines")


def validate_mdx_files(docs_dir: Path, quiet: bool = False, validate_icons: bool = False) -> MDXValidationResult:
    """
    Validate MDX files in docs directory.

    Checks:
    1. All files use .mdx extension (not .md)
    2. Filenames follow kebab-case convention
    3. Frontmatter uses consistent quote style
    4. Icon validation (when validate_icons=True):
       - Icons use single quotes
       - Icons are in valid registry
       - ADR files have icons
    """
    result = MDXValidationResult()
    result.stats = {
        "total_files": 0,
        "md_files": 0,
        "invalid_names": 0,
        "frontmatter_issues": 0,
        "icon_errors": 0,
    }

    if not docs_dir.exists():
        return result

    # Find all .mdx and .md files
    mdx_files = list(docs_dir.rglob("*.mdx"))
    md_files = list(docs_dir.rglob("*.md"))

    # Filter out excluded patterns
    def should_include(file_path: Path) -> bool:
        relative_path = str(file_path.relative_to(docs_dir))
        return not any(pattern in relative_path for pattern in EXCLUDE_PATTERNS)

    mdx_files = [f for f in mdx_files if should_include(f)]
    md_files = [f for f in md_files if should_include(f)]

    result.stats["total_files"] = len(mdx_files) + len(md_files)

    # Check for .md files (invalid in docs/)
    for md_file in md_files:
        result.md_files.append(md_file)
        result.stats["md_files"] += 1
        result.is_valid = False

    # Check MDX files
    for mdx_file in mdx_files:
        filename = mdx_file.name

        # Check naming convention
        if not is_kebab_case(filename):
            suggested = to_kebab_case(filename)
            result.invalid_names.append((mdx_file, suggested))
            result.stats["invalid_names"] += 1
            result.is_valid = False

        # Check frontmatter
        try:
            content = mdx_file.read_text()
            frontmatter, fm_text, _ = parse_frontmatter(content)

            if frontmatter:
                # Check for inconsistent quoting (legacy check)
                for line in fm_text.split("\n"):
                    if ":" not in line:
                        continue
                    key, value = line.split(":", 1)
                    key = key.strip()
                    value = value.strip()

                    # description should use single quotes (warning only)
                    if key == "description" and value.startswith('"'):
                        result.frontmatter_issues.append((mdx_file, f"{key} uses double quotes (should use single quotes)"))
                        result.stats["frontmatter_issues"] += 1

                    # Icon validation (blocking when validate_icons=True)
                    if validate_icons and key == "icon":
                        is_valid_icon, icon_name, error = validate_icon_format(value)
                        if not is_valid_icon:
                            result.icon_errors.append((mdx_file, error or "Invalid icon"))
                            result.stats["icon_errors"] += 1
                            result.is_valid = False

                # Check ADR files for missing icons (when validate_icons=True)
                if validate_icons:
                    is_adr = "architecture" in str(mdx_file) and mdx_file.name.startswith("adr-")
                    if is_adr:
                        icon_value = frontmatter.get("icon", "").strip()
                        if not icon_value:
                            suggested = get_suggested_adr_icon(mdx_file)
                            result.icon_errors.append((mdx_file, f"ADR file is missing icon. Suggested: icon: '{suggested}'"))
                            result.stats["icon_errors"] += 1
                            result.is_valid = False

        except Exception:
            pass

    return result


def print_mdx_report(result: MDXValidationResult, docs_dir: Path) -> None:
    """Print MDX validation report."""
    print("\n" + "=" * 80)
    print("📝 MDX Extension & Naming Validation Report")
    print("=" * 80)

    print("\n📊 Statistics:")
    print(f"  Total files scanned: {result.stats.get('total_files', 0)}")
    print(f"  Invalid .md files: {result.stats.get('md_files', 0)}")
    print(f"  Invalid filenames: {result.stats.get('invalid_names', 0)}")
    print(f"  Frontmatter issues: {result.stats.get('frontmatter_issues', 0)}")
    print(f"  Icon errors: {result.stats.get('icon_errors', 0)}")

    if result.md_files:
        print("\n❌ .md files found in docs/ (should be .mdx):")
        for md_file in result.md_files:
            print(f"    ❌ {md_file.relative_to(docs_dir)}")
        print("  💡 Solution: Convert .md files to .mdx")

    if result.invalid_names:
        print("\n❌ Invalid filenames (should be kebab-case):")
        for file_path, suggested in result.invalid_names:
            print(f"    ❌ {file_path.relative_to(docs_dir)} → {suggested}")

    if result.frontmatter_issues:
        print("\n⚠️  Frontmatter issues (warnings):")
        for file_path, issue in result.frontmatter_issues[:10]:
            print(f"    ⚠️  {file_path.relative_to(docs_dir)}: {issue}")
        if len(result.frontmatter_issues) > 10:
            print(f"    ... and {len(result.frontmatter_issues) - 10} more")

    if result.icon_errors:
        print("\n❌ Icon errors (blocking):")
        for file_path, error in result.icon_errors[:20]:
            print(f"    ❌ {file_path.relative_to(docs_dir)}: {error}")
        if len(result.icon_errors) > 20:
            print(f"    ... and {len(result.icon_errors) - 20} more")
        print("  💡 Solution: Run 'python scripts/docs/standardize_frontmatter.py --fix' to auto-fix")

    print("\n" + "=" * 80)
    if result.is_valid:
        print("✅ All MDX files are valid!")
    else:
        print("❌ MDX validation failed")
    print("=" * 80 + "\n")


# =============================================================================
# ADR Synchronization Validation
# =============================================================================


@dataclass
class ADRValidationResult:
    """Result of ADR synchronization validation."""

    is_synced: bool = True
    source_adrs: set[str] = field(default_factory=set)
    docs_adrs: set[str] = field(default_factory=set)
    missing_in_docs: set[str] = field(default_factory=set)
    missing_in_source: set[str] = field(default_factory=set)
    uppercase_filenames: list[Path] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)


def validate_adr_sync(repo_root: Path, quiet: bool = False) -> ADRValidationResult:
    """
    Validate ADR synchronization between /adr and /docs/architecture.

    Checks:
    1. All ADRs in /adr have corresponding .mdx in /docs/architecture
    2. No orphaned ADRs in /docs/architecture
    3. No uppercase ADR-* filenames (should be adr-*)
    """
    result = ADRValidationResult()

    adr_dir = repo_root / "adr"
    docs_adr_dir = repo_root / "docs" / "architecture"

    # Find source ADRs (.md files)
    if adr_dir.exists():
        for adr_file in adr_dir.glob("adr-*.md"):
            result.source_adrs.add(adr_file.stem)

        # Check for uppercase ADR-* files
        for adr_file in adr_dir.glob("ADR-*.md"):
            result.uppercase_filenames.append(adr_file)

    # Find docs ADRs (.mdx files)
    if docs_adr_dir.exists():
        for adr_file in docs_adr_dir.glob("adr-*.mdx"):
            result.docs_adrs.add(adr_file.stem)

        # Check for uppercase ADR-* files
        for adr_file in docs_adr_dir.glob("ADR-*.mdx"):
            result.uppercase_filenames.append(adr_file)

    # Compare
    result.missing_in_docs = result.source_adrs - result.docs_adrs
    result.missing_in_source = result.docs_adrs - result.source_adrs

    result.is_synced = (
        len(result.missing_in_docs) == 0 and len(result.missing_in_source) == 0 and len(result.uppercase_filenames) == 0
    )

    result.stats = {
        "source_count": len(result.source_adrs),
        "docs_count": len(result.docs_adrs),
        "missing_in_docs": len(result.missing_in_docs),
        "missing_in_source": len(result.missing_in_source),
        "uppercase_count": len(result.uppercase_filenames),
    }

    return result


def print_adr_report(result: ADRValidationResult, repo_root: Path) -> None:
    """Print ADR synchronization report."""
    print("\n" + "=" * 80)
    print("🔄 ADR Synchronization Validation Report")
    print("=" * 80)

    print("\n📊 Statistics:")
    print(f"  ADRs in /adr: {result.stats['source_count']}")
    print(f"  ADRs in /docs/architecture: {result.stats['docs_count']}")

    if result.uppercase_filenames:
        print(f"\n⚠️  Uppercase filenames detected ({len(result.uppercase_filenames)}):")
        for f in sorted(result.uppercase_filenames):
            lowercase_name = f.name.replace("ADR-", "adr-")
            print(f"    • {f.relative_to(repo_root)} → {lowercase_name}")

    if result.missing_in_docs:
        print(f"\n❌ ADRs missing in /docs/architecture ({len(result.missing_in_docs)}):")
        for adr in sorted(result.missing_in_docs):
            print(f"    • {adr}.md → {adr}.mdx")

    if result.missing_in_source:
        print("\n⚠️  ADRs missing in /adr (orphaned in docs):")
        for adr in sorted(result.missing_in_source):
            print(f"    • {adr}.mdx")

    print("\n" + "=" * 80)
    if result.is_synced:
        print("✅ All ADRs are synchronized!")
    else:
        print("❌ ADRs are out of sync")
    print("=" * 80 + "\n")


# =============================================================================
# Documentation Tests Validation
# =============================================================================


def run_doc_tests(repo_root: Path, dry_run: bool = False) -> int:
    """
    Run documentation validation pytest tests.

    Tests:
    - tests/meta/validation/test_documentation_integrity.py
    - tests/regression/test_documentation_structure.py
    - tests/meta/validation/test_mdx_validation.py
    """
    test_files = [
        "tests/meta/validation/test_documentation_integrity.py",
        "tests/regression/test_documentation_structure.py",
        "tests/meta/validation/test_mdx_validation.py",
    ]

    existing_tests = [repo_root / t for t in test_files if (repo_root / t).exists()]

    if dry_run:
        print("\n" + "=" * 80)
        print("🧪 Documentation Tests (DRY RUN)")
        print("=" * 80)
        print("\nWould run pytest on:")
        for test_file in existing_tests:
            print(f"  • {test_file.relative_to(repo_root)}")
        print("=" * 80 + "\n")
        return 0

    if not existing_tests:
        print("⚠️  No documentation test files found")
        return 0

    print("\n" + "=" * 80)
    print("🧪 Running Documentation Tests")
    print("=" * 80 + "\n")

    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "-v",
        "--tb=short",
    ] + [str(t) for t in existing_tests]

    result = subprocess.run(cmd, cwd=repo_root)
    return result.returncode


# =============================================================================
# Main Entry Point
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Consolidated documentation validator for pre-commit hooks",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Validation Types:
  --mdx       Validate MDX extension, file naming, frontmatter
  --icons     Validate icon consistency (single quotes, valid registry, ADRs have icons)
  --adr       Validate ADR synchronization (adr/ <-> docs/architecture/)
  --tests     Run documentation validation pytest tests
  --all       Run all validations

Examples:
  %(prog)s --all                           # Run all validations
  %(prog)s --mdx --docs-dir docs/          # Validate MDX files only
  %(prog)s --mdx --icons                   # Validate MDX with icon checking
  %(prog)s --adr --repo-root .             # Validate ADR sync only
  %(prog)s --tests --dry-run               # Show what tests would run
""",
    )

    parser.add_argument("--mdx", action="store_true", help="Validate MDX files (extension, naming, frontmatter)")
    parser.add_argument("--icons", action="store_true", help="Validate icon consistency (requires --mdx or --all)")
    parser.add_argument("--adr", action="store_true", help="Validate ADR synchronization")
    parser.add_argument("--tests", action="store_true", help="Run documentation validation tests")
    parser.add_argument("--all", action="store_true", help="Run all validations")
    parser.add_argument("--docs-dir", type=Path, default=Path("docs"), help="Path to docs directory")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Path to repository root")
    parser.add_argument("--quiet", action="store_true", help="Suppress output (only use exit code)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be validated without running")

    args = parser.parse_args()

    # Default to --all if no specific validation type specified
    if not any([args.mdx, args.adr, args.tests, args.all]):
        args.all = True

    # --icons implies --mdx
    if args.icons and not args.mdx and not args.all:
        args.mdx = True

    exit_code = 0

    # MDX validation
    if args.mdx or args.all:
        if args.dry_run:
            print(f"[DRY RUN] Would validate MDX files in {args.docs_dir}")
            if args.icons or args.all:
                print("[DRY RUN] Icon validation enabled")
        else:
            # Enable icon validation when --icons or --all is specified
            validate_icons = args.icons or args.all
            result = validate_mdx_files(args.docs_dir, args.quiet, validate_icons=validate_icons)
            if not args.quiet:
                print_mdx_report(result, args.docs_dir)
            if not result.is_valid:
                exit_code = 1

    # ADR validation
    if args.adr or args.all:
        if args.dry_run:
            print(f"[DRY RUN] Would validate ADR sync in {args.repo_root}")
        else:
            result = validate_adr_sync(args.repo_root, args.quiet)
            if not args.quiet:
                print_adr_report(result, args.repo_root)
            if not result.is_synced:
                exit_code = 1

    # Tests validation
    if args.tests or args.all:
        test_exit = run_doc_tests(args.repo_root, args.dry_run)
        if test_exit != 0:
            exit_code = 1

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
