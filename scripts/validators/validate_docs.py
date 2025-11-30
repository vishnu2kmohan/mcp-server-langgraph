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
import json
import re
import subprocess
import sys
import urllib.request
from dataclasses import dataclass, field
from functools import lru_cache
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
    mermaid_errors: list[tuple[Path, int, str]] = field(default_factory=list)  # (file, line, error)
    list_errors: list[tuple[Path, int, str]] = field(default_factory=list)  # (file, line, error)
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
# Font Awesome Icon Validation
# =============================================================================
#
# We validate icons against the official Font Awesome 6.x metadata.
# Source: https://github.com/FortAwesome/Font-Awesome/blob/6.x/metadata/icons.json
#
# The ADR_ICON_MAPPING below MUST only contain valid Font Awesome icon names.
# Run `python scripts/validators/validate_docs.py --validate-icons` to verify.
#
# =============================================================================

FONT_AWESOME_ICONS_URL = "https://raw.githubusercontent.com/FortAwesome/Font-Awesome/6.x/metadata/icons.json"

# Cache file for offline validation (updated periodically)
FA_ICONS_CACHE_FILE = Path(__file__).parent / ".fa-icons-cache.json"


@lru_cache(maxsize=1)
def get_valid_fontawesome_icons() -> set[str]:
    """
    Fetch valid Font Awesome 6.x icon names from official metadata.

    Returns a cached set of valid icon names. Falls back to cached file
    if network is unavailable.
    """
    # Try cached file first (for offline/CI use)
    if FA_ICONS_CACHE_FILE.exists():
        try:
            with open(FA_ICONS_CACHE_FILE) as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 1000:  # Sanity check
                    return set(data)
        except (json.JSONDecodeError, OSError):
            pass  # Cache corrupted or inaccessible - will fetch from network

    # Fetch from official source (HTTPS only - safe URL)
    try:
        with urllib.request.urlopen(FONT_AWESOME_ICONS_URL, timeout=10) as response:  # noqa: S310
            icons_data = json.loads(response.read().decode())
            icon_names = set(icons_data.keys())

            # Cache for future use
            try:
                with open(FA_ICONS_CACHE_FILE, "w") as f:
                    json.dump(sorted(icon_names), f)
            except OSError:
                pass  # Ignore cache write failures

            return icon_names
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        print(f"Warning: Could not fetch Font Awesome icons: {e}")
        # Return a minimal known-good set as fallback
        return {
            "file-lines",
            "rocket",
            "shield",
            "key",
            "database",
            "chart-line",
            "code",
            "bug",
            "flask",
            "cube",
            "cubes",
            "book",
            "gear",
            "bolt",
            "microchip",
            "brain",
            "robot",
            "plug",
            "lock",
            "tag",
            "flag",
        }


def validate_adr_icon_mapping() -> list[tuple[str, str]]:
    """
    Validate that all icons in ADR_ICON_MAPPING are valid Font Awesome 6.x icons.

    Returns:
        List of (keyword, invalid_icon) tuples for any invalid icons found.
    """
    valid_icons = get_valid_fontawesome_icons()
    invalid = []

    for keyword, icon in ADR_ICON_MAPPING.items():
        if icon not in valid_icons:
            invalid.append((keyword, icon))

    return invalid


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
    "uv": "cube",
    "dependency": "cube",
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
# Mermaid Diagram Validation Functions
# =============================================================================

# ColorBrewer Set3 palette colors that must appear in styled diagrams
COLORBREWER_SET3_COLORS = {
    "#8dd3c7",  # teal - client/request
    "#fdb462",  # orange - validation/processing
    "#bebada",  # purple - service/auth
    "#fb8072",  # coral - errors/failures
    "#b3de69",  # green - success/response
    "#80b1d3",  # blue - storage/database
    "#ffffb3",  # yellow - secondary
    "#bc80bd",  # pink - additional
    "#d9d9d9",  # gray - neutral
}


def extract_mermaid_blocks(content: str) -> list[tuple[int, str]]:
    """
    Extract all mermaid code blocks from MDX content.

    Returns:
        List of (line_number, mermaid_content) tuples
    """
    blocks = []
    pattern = r"```mermaid\n(.*?)```"
    matches = re.finditer(pattern, content, re.DOTALL)

    for match in matches:
        # Calculate line number
        line_num = content[: match.start()].count("\n") + 1
        blocks.append((line_num, match.group(1)))

    return blocks


def validate_mermaid_colorbrewer_styling(mermaid_content: str) -> tuple[bool, str | None]:
    """
    Validate that a mermaid diagram uses ColorBrewer Set3 styling.

    A diagram is considered properly styled if it has:
    1. Uses 'flowchart' syntax (not deprecated 'graph')
    2. A ColorBrewer comment OR
    3. At least 2 classDef statements with ColorBrewer Set3 colors

    Args:
        mermaid_content: The content of a mermaid code block

    Returns:
        Tuple of (is_valid, error_message)
    """
    content_lower = mermaid_content.lower()
    lines = mermaid_content.strip().split("\n")

    # Check for deprecated 'graph' syntax (should use 'flowchart')
    for line in lines:
        stripped = line.strip()
        # Skip comments
        if stripped.startswith("%%"):
            continue
        # First non-comment line should be the diagram type
        if stripped.lower().startswith("graph "):
            return False, "Uses deprecated 'graph' syntax - use 'flowchart TD/TB/LR/BT' instead"
        # Found the diagram type declaration, stop checking
        if stripped:
            break

    # Check for ColorBrewer comment (case-insensitive)
    if "colorbrewer" in content_lower:
        return True, None

    # Check for classDef with ColorBrewer Set3 colors
    classdef_pattern = r"classDef\s+\w+\s+fill:(#[a-fA-F0-9]{6})"
    colors_found = re.findall(classdef_pattern, mermaid_content, re.IGNORECASE)

    # Check if at least 2 ColorBrewer Set3 colors are used
    cb_colors_used = [c.lower() for c in colors_found if c.lower() in COLORBREWER_SET3_COLORS]

    if len(cb_colors_used) >= 2:
        return True, None

    # Check if diagram is simple (no subgraphs, less than 5 nodes)
    # Simple diagrams don't require styling
    has_subgraph = "subgraph" in content_lower
    node_count = len(re.findall(r"^\s*\w+[\[\(\{]", mermaid_content, re.MULTILINE))

    if not has_subgraph and node_count < 5:
        return True, None  # Simple diagrams exempt

    return False, "Missing ColorBrewer Set3 styling (add classDef with Set3 colors or ColorBrewer comment)"


def validate_file_mermaid_diagrams(file_path: Path) -> list[tuple[int, str]]:
    """
    Validate all mermaid diagrams in a file for ColorBrewer Set3 styling.

    Args:
        file_path: Path to the MDX file

    Returns:
        List of (line_number, error_message) tuples for invalid diagrams
    """
    errors = []

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return errors

    blocks = extract_mermaid_blocks(content)

    for line_num, mermaid_content in blocks:
        is_valid, error_msg = validate_mermaid_colorbrewer_styling(mermaid_content)
        if not is_valid:
            errors.append((line_num, error_msg))

    return errors


# =============================================================================
# List Formatting Validation Functions
# =============================================================================

# Emojis that typically start list items and need proper `- ` prefix
LIST_INDICATOR_EMOJIS = {"✅", "❌", "⚠️", "📚", "💡", "🔒", "🚀", "⭐", "🔥", "📝", "🎯"}

# Files excluded from list validation (contain intentional formatting examples)
LIST_VALIDATION_EXCLUDE_FILES = {
    "mdx-syntax-guide.mdx",  # Contains intentional wrong/correct formatting examples
}


def validate_list_formatting(file_path: Path) -> list[tuple[int, str]]:
    """
    Validate that lines starting with list-indicator emojis are properly formatted.

    Detects lines like:
        ✅ **Feature**: Description  <- WRONG (not a list item)
        - ✅ **Feature**: Description  <- CORRECT (proper list item)

    Args:
        file_path: Path to the MDX file

    Returns:
        List of (line_number, error_message) tuples for formatting issues
    """
    errors = []

    # Skip excluded files (contain intentional formatting examples)
    if file_path.name in LIST_VALIDATION_EXCLUDE_FILES:
        return errors

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return errors

    lines = content.split("\n")
    in_code_block = False
    in_frontmatter = False

    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        # Track frontmatter
        if stripped == "---":
            in_frontmatter = not in_frontmatter
            continue

        if in_frontmatter:
            continue

        # Track code blocks (```mermaid, ```python, etc.)
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            continue

        if in_code_block:
            continue

        # Skip lines inside JSX components (Mintlify callouts like <Note>, <Warning>)
        if stripped.startswith("<") and not stripped.startswith("</"):
            continue

        # Check if line starts with a list-indicator emoji but not as a list item
        for emoji in LIST_INDICATOR_EMOJIS:
            if stripped.startswith(emoji):
                # Check if it's NOT already a proper list item
                # Proper list items: "- ✅", "* ✅", "  - ✅", etc.
                leading_whitespace = len(line) - len(line.lstrip())
                after_whitespace = line[leading_whitespace:] if leading_whitespace < len(line) else ""

                # Check for list prefix patterns
                is_list_item = (
                    after_whitespace.startswith("- ")
                    or after_whitespace.startswith("* ")
                    or after_whitespace.startswith("+ ")
                    # Also check numbered lists: "1. ✅"
                    or (len(after_whitespace) > 2 and after_whitespace[0].isdigit() and after_whitespace[1:3] == ". ")
                )

                if not is_list_item:
                    errors.append((i, f"Line starts with '{emoji}' but is not a list item. Add '- ' prefix: - {stripped}"))
                break  # Only check first matching emoji per line

    return errors


# =============================================================================
# Icon Validation Functions
# =============================================================================


def validate_icon_format(icon_value: str) -> tuple[bool, str | None, str | None]:
    """
    Validate icon format and value against official Font Awesome 6.x icons.

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

    # Get valid Font Awesome icons for validation
    valid_icons = get_valid_fontawesome_icons()

    # Check for single quotes (preferred format)
    if icon_value.startswith("'") and icon_value.endswith("'"):
        icon_name = icon_value[1:-1]
        if not icon_name:
            return False, None, "Icon value is empty inside quotes"
        if icon_name not in valid_icons:
            return False, icon_name, f"Icon '{icon_name}' is not a valid Font Awesome 6.x icon"
        return True, icon_name, None

    # Check for double quotes (should be single quotes)
    if icon_value.startswith('"') and icon_value.endswith('"'):
        icon_name = icon_value[1:-1]
        return False, icon_name, f"Icon uses double quotes (should use single quotes): {icon_value}"

    # Unquoted value
    if icon_value not in valid_icons:
        return (
            False,
            icon_value,
            f"Icon '{icon_value}' is unquoted and not a valid Font Awesome 6.x icon. Use single quotes: icon: '{icon_value}'",
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


def validate_mdx_files(
    docs_dir: Path,
    quiet: bool = False,
    validate_icons: bool = False,
    validate_mermaid: bool = False,
    validate_lists: bool = False,
) -> MDXValidationResult:
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
    5. Mermaid validation (when validate_mermaid=True):
       - Diagrams use ColorBrewer Set3 styling
    6. List validation (when validate_lists=True):
       - Lines starting with emojis use proper list formatting
    """
    result = MDXValidationResult()
    result.stats = {
        "total_files": 0,
        "md_files": 0,
        "invalid_names": 0,
        "frontmatter_issues": 0,
        "icon_errors": 0,
        "mermaid_errors": 0,
        "list_errors": 0,
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

            # Mermaid diagram validation (when validate_mermaid=True)
            if validate_mermaid:
                mermaid_errors = validate_file_mermaid_diagrams(mdx_file)
                for line_num, error_msg in mermaid_errors:
                    result.mermaid_errors.append((mdx_file, line_num, error_msg))
                    result.stats["mermaid_errors"] += 1
                    result.is_valid = False

            # List formatting validation (when validate_lists=True)
            if validate_lists:
                list_errors = validate_list_formatting(mdx_file)
                for line_num, error_msg in list_errors:
                    result.list_errors.append((mdx_file, line_num, error_msg))
                    result.stats["list_errors"] += 1
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
    print(f"  Mermaid errors: {result.stats.get('mermaid_errors', 0)}")
    print(f"  List format errors: {result.stats.get('list_errors', 0)}")

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

    if result.mermaid_errors:
        print("\n❌ Mermaid diagram styling errors (blocking):")
        for file_path, line_num, error in result.mermaid_errors[:20]:
            print(f"    ❌ {file_path.relative_to(docs_dir)}:{line_num}: {error}")
        if len(result.mermaid_errors) > 20:
            print(f"    ... and {len(result.mermaid_errors) - 20} more")
        print("  💡 Solution: Add ColorBrewer Set3 classDef styling to mermaid diagrams")
        print("  📖 Reference: docs/reference/mermaid-guide.mdx")

    if result.list_errors:
        print("\n❌ List formatting errors (blocking):")
        for file_path, line_num, error in result.list_errors[:20]:
            print(f"    ❌ {file_path.relative_to(docs_dir)}:{line_num}: {error}")
        if len(result.list_errors) > 20:
            print(f"    ... and {len(result.list_errors) - 20} more")
        print("  💡 Solution: Add '- ' prefix before lines starting with status emojis")

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
  --mermaid   Validate mermaid diagrams use ColorBrewer Set3 styling
  --lists     Validate list formatting (emoji lines should have - prefix)
  --adr       Validate ADR synchronization (adr/ <-> docs/architecture/)
  --tests     Run documentation validation pytest tests
  --all       Run all validations

Examples:
  %(prog)s --all                           # Run all validations
  %(prog)s --mdx --docs-dir docs/          # Validate MDX files only
  %(prog)s --mdx --icons --mermaid --lists # Validate MDX with all checks
  %(prog)s --adr --repo-root .             # Validate ADR sync only
  %(prog)s --tests --dry-run               # Show what tests would run
""",
    )

    parser.add_argument("--mdx", action="store_true", help="Validate MDX files (extension, naming, frontmatter)")
    parser.add_argument("--icons", action="store_true", help="Validate icon consistency (requires --mdx or --all)")
    parser.add_argument("--mermaid", action="store_true", help="Validate mermaid diagrams use ColorBrewer Set3 styling")
    parser.add_argument("--lists", action="store_true", help="Validate list formatting (emojis should have - prefix)")
    parser.add_argument(
        "--validate-icon-mapping", action="store_true", help="Validate ADR_ICON_MAPPING against Font Awesome 6.x"
    )
    parser.add_argument("--adr", action="store_true", help="Validate ADR synchronization")
    parser.add_argument("--tests", action="store_true", help="Run documentation validation tests")
    parser.add_argument("--all", action="store_true", help="Run all validations")
    parser.add_argument("--docs-dir", type=Path, default=Path("docs"), help="Path to docs directory")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd(), help="Path to repository root")
    parser.add_argument("--quiet", action="store_true", help="Suppress output (only use exit code)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be validated without running")

    args = parser.parse_args()

    # Default to --all if no specific validation type specified
    if not any([args.mdx, args.adr, args.tests, args.all, args.validate_icon_mapping, args.mermaid, args.lists]):
        args.all = True

    # --icons, --mermaid, and --lists imply --mdx
    if (args.icons or args.mermaid or args.lists) and not args.mdx and not args.all:
        args.mdx = True

    exit_code = 0

    # Validate ADR_ICON_MAPPING against Font Awesome 6.x
    if args.validate_icon_mapping or args.all:
        if args.dry_run:
            print("[DRY RUN] Would validate ADR_ICON_MAPPING against Font Awesome 6.x")
        else:
            invalid_icons = validate_adr_icon_mapping()
            if invalid_icons:
                if not args.quiet:
                    print("\n❌ Invalid icons in ADR_ICON_MAPPING:")
                    for keyword, icon in invalid_icons:
                        print(f"  - '{keyword}' → '{icon}' (not a valid Font Awesome 6.x icon)")
                    print("\nFix: Update ADR_ICON_MAPPING in scripts/validators/validate_docs.py")
                exit_code = 1
            elif not args.quiet:
                print("✅ All icons in ADR_ICON_MAPPING are valid Font Awesome 6.x icons")

    # MDX validation
    if args.mdx or args.all:
        if args.dry_run:
            print(f"[DRY RUN] Would validate MDX files in {args.docs_dir}")
            if args.icons or args.all:
                print("[DRY RUN] Icon validation enabled")
            if args.mermaid or args.all:
                print("[DRY RUN] Mermaid diagram validation enabled")
            if args.lists or args.all:
                print("[DRY RUN] List formatting validation enabled")
        else:
            # Enable icon, mermaid, and list validation when corresponding flags or --all is specified
            validate_icons = args.icons or args.all
            validate_mermaid = args.mermaid or args.all
            validate_lists = args.lists or args.all
            result = validate_mdx_files(
                args.docs_dir,
                args.quiet,
                validate_icons=validate_icons,
                validate_mermaid=validate_mermaid,
                validate_lists=validate_lists,
            )
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
