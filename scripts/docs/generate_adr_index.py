#!/usr/bin/env python3
"""
ADR Index Generator - Automatically generate adr/README.md with ADR listing.

This script creates a comprehensive index of all Architecture Decision Records (ADRs)
in the adr/ directory, organized by category and sorted by number.

Features:
- Auto-generates adr/README.md with table of all ADRs
- Categorizes ADRs by topic (infrastructure, authentication, testing, etc.)
- Validates ADR numbering sequence
- Detects duplicate ADR numbers
- Can be used in pre-commit hooks or CI/CD

Usage:
    python scripts/generate_adr_index.py                  # Generate adr/README.md
    python scripts/generate_adr_index.py --check          # Check if README is up-to-date
    python scripts/generate_adr_index.py --validate       # Validate ADR numbering

Author: Documentation Audit Remediation (2025-11-12)
Related: REC-001 from documentation audit
"""

import argparse
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path


class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


class ADRMetadata:
    """Metadata extracted from an ADR file."""

    def __init__(
        self,
        number: int,
        filename: str,
        title: str,
        status: str,
        date: str,
        tags: list[str],
        category: str = "",
    ):
        self.number = number
        self.filename = filename
        self.title = title
        self.status = status
        self.date = date
        self.tags = tags
        self.category = category

    def __repr__(self):
        return f"ADR-{self.number:04d}: {self.title} ({self.status})"


def extract_adr_metadata(file_path: Path) -> ADRMetadata:
    """
    Extract metadata from an ADR file.

    Args:
        file_path: Path to ADR markdown file

    Returns:
        ADRMetadata object with extracted information

    Raises:
        ValueError: If ADR file format is invalid
    """
    content = file_path.read_text(encoding="utf-8")

    # Extract ADR number from filename (e.g., "adr-0045-title.md" -> 45)
    match = re.match(r"adr-(\d+)-", file_path.name)
    if not match:
        raise ValueError(f"Invalid ADR filename format: {file_path.name}")

    number = int(match.group(1))

    # Extract title (first # heading)
    title_match = re.search(r"^# (?:ADR-\d+: )?(.+)$", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Unknown Title"

    # Extract status (try heading format first, then inline format)
    status_match = re.search(r"^## Status\s*\n\n(\w+)", content, re.MULTILINE)
    if not status_match:
        status_match = re.search(r"^\*\*Status[:\*]*\s*(.+)$", content, re.MULTILINE)
    status = status_match.group(1).strip() if status_match else "Unknown"

    # Extract date (try "Date: YYYY-MM-DD" format first, then inline format)
    date_match = re.search(r"^Date:\s*(.+)$", content, re.MULTILINE)
    if not date_match:
        date_match = re.search(r"^\*\*Date\*\*:\s*(.+)$", content, re.MULTILINE)
    date = date_match.group(1).strip() if date_match else "Unknown"

    # Extract category (heading format: ## Category\n\nCategory Name)
    category_match = re.search(r"^## Category\s*\n\n(.+?)$", content, re.MULTILINE)
    category = category_match.group(1).strip() if category_match else ""

    # Extract tags (inline format)
    tags_match = re.search(r"^\*\*Tags\*\*:\s*(.+)$", content, re.MULTILINE)
    tags = []
    if tags_match:
        tags_text = tags_match.group(1).strip()
        # Split by comma and clean up
        tags = [tag.strip() for tag in tags_text.split(",")]

    return ADRMetadata(
        number=number,
        filename=file_path.name,
        title=title,
        status=status,
        date=date,
        tags=tags,
        category=category,
    )


def categorize_adrs(adrs: list[ADRMetadata]) -> dict[str, list[ADRMetadata]]:
    """
    Categorize ADRs by topic.

    Uses the explicit Category field if present in the ADR, otherwise falls back
    to keyword matching based on title and tags.

    Args:
        adrs: List of ADR metadata objects

    Returns:
        Dictionary mapping category names to lists of ADRs
    """
    categories = defaultdict(list)

    # Define category keywords (fallback for ADRs without explicit category)
    category_keywords = {
        "Core Architecture": ["architecture", "llm", "provider", "observability", "mcp"],
        "Authentication & Authorization": ["auth", "keycloak", "jwt", "openfga", "permission", "scim", "identity"],
        "Infrastructure & Deployment": [
            "infrastructure",
            "deployment",
            "gcp",
            "gke",
            "aws",
            "eks",
            "kubernetes",
            "docker",
            "terraform",
        ],
        "Security & Compliance": ["security", "gdpr", "hipaa", "soc2", "compliance", "secrets"],
        "Testing & Quality": ["test", "testing", "quality", "property-based", "fixture", "pytest"],
        "Development & Tooling": [
            "ci-cd",
            "cicd",
            "pipeline",
            "git",
            "development",
            "tooling",
            "template",
        ],
        "Data & Storage": ["database", "postgres", "redis", "storage", "session", "checkpointing", "cache"],
        "Performance & Resilience": ["performance", "resilience", "rate-limiting", "caching", "circuit-breaker"],
        "Other": [],  # Catch-all category
    }

    for adr in adrs:
        # Use explicit category if present
        if adr.category:
            categories[adr.category].append(adr)
            continue

        # Fall back to keyword matching
        text = f"{adr.title.lower()} {' '.join(adr.tags).lower()}"

        # Find matching category
        matched_category = None
        for category, keywords in category_keywords.items():
            if category == "Other":
                continue
            if any(keyword in text for keyword in keywords):
                matched_category = category
                break

        # Add to appropriate category
        if matched_category:
            categories[matched_category].append(adr)
        else:
            categories["Other"].append(adr)

    # Remove empty categories
    return {cat: adrs for cat, adrs in categories.items() if adrs}


def generate_readme_content(adrs: list[ADRMetadata]) -> str:
    """
    Generate README.md content with ADR index.

    Args:
        adrs: List of ADR metadata objects

    Returns:
        Markdown content for README.md
    """
    # Header
    content = f"""# Architecture Decision Records (ADRs)

**Last Updated**: {datetime.now().strftime("%Y-%m-%d")}
**Total ADRs**: {len(adrs)}

## Overview

This directory contains all Architecture Decision Records (ADRs) for the MCP Server LangGraph project.
ADRs document significant architectural decisions, their context, rationale, and consequences.

## Format

Each ADR follows this structure:
- **Title**: Brief description of the decision
- **Status**: Proposed, Accepted, Deprecated, or Superseded
- **Date**: When the decision was made
- **Context**: The problem or opportunity
- **Decision**: What was decided
- **Consequences**: Positive and negative outcomes

## Index

"""

    # Categorize ADRs
    categorized = categorize_adrs(adrs)

    # Generate table for each category
    for category in sorted(categorized.keys()):
        category_adrs = sorted(categorized[category], key=lambda x: x.number)

        content += f"### {category}\n\n"
        content += "| ADR | Title | Status | Date |\n"
        content += "|-----|-------|--------|------|\n"

        for adr in category_adrs:
            # Create link to file
            link = f"[ADR-{adr.number:04d}]({adr.filename})"
            content += f"| {link} | {adr.title} | {adr.status} | {adr.date} |\n"

        content += "\n"

    # Footer
    content += """## Creating a New ADR

1. Determine the next ADR number:
   ```bash
   ls adr/adr-*.md | sort -V | tail -1
   ```

2. Create a new file:
   ```bash
   cp adr/adr-0001-llm-multi-provider.md adr/adr-XXXX-your-title.md
   ```

3. Update the content:
   - Change the ADR number and title
   - Fill in Status, Date, Context, Decision, and Consequences
   - Add relevant tags

4. Sync to Mintlify documentation:
   ```bash
   python scripts/docs/sync-adrs.py
   ```

5. Update this index:
   ```bash
   python scripts/generate_adr_index.py
   ```

## Validation

To validate ADR numbering and sync status:

```bash
# Check for duplicate ADR numbers
pytest tests/regression/test_documentation_structure.py::TestADRNumbering::test_no_duplicate_adr_numbers

# Check ADR sync status
python scripts/docs/sync-adrs.py --check

# Validate this index is up-to-date
python scripts/generate_adr_index.py --check
```

## Related Documentation

- [Architecture Overview](../docs/architecture/overview.mdx) - High-level system architecture
- [Mintlify ADRs](../docs/architecture/) - User-friendly ADR documentation
- [ADR Sync Script](../scripts/docs/sync-adrs.py) - Keep ADRs in sync with Mintlify

---

**Auto-generated by**: `scripts/generate_adr_index.py`
**Do not edit manually**: Run the script to regenerate this file.
"""

    return content


def find_all_adrs() -> list[ADRMetadata]:
    """
    Find and parse all ADR files.

    Returns:
        List of ADRMetadata objects, sorted by number

    Raises:
        FileNotFoundError: If adr/ directory doesn't exist
    """
    adr_dir = Path("adr")

    if not adr_dir.exists():
        raise FileNotFoundError(f"ADR directory not found: {adr_dir}")

    adr_files = sorted(adr_dir.glob("adr-*.md"))

    adrs = []
    for adr_file in adr_files:
        try:
            metadata = extract_adr_metadata(adr_file)
            adrs.append(metadata)
        except Exception as e:
            print(f"{Colors.YELLOW}⚠ Warning: Could not parse {adr_file.name}: {e}{Colors.RESET}")

    return sorted(adrs, key=lambda x: x.number)


def validate_adr_numbering(adrs: list[ADRMetadata]) -> list[str]:
    """
    Validate ADR numbering for duplicates and gaps.

    Args:
        adrs: List of ADR metadata objects

    Returns:
        List of validation errors (empty if no errors)
    """
    errors = []

    # Check for duplicates
    numbers = [adr.number for adr in adrs]
    duplicates = [n for n in numbers if numbers.count(n) > 1]

    if duplicates:
        for dup in set(duplicates):
            dup_adrs = [adr for adr in adrs if adr.number == dup]
            errors.append(f"Duplicate ADR number {dup:04d}: {', '.join(a.filename for a in dup_adrs)}")

    # Check for gaps (informational, not an error)
    if adrs:
        gaps = []
        for i in range(len(adrs) - 1):
            current = adrs[i].number
            next_num = adrs[i + 1].number
            if next_num - current > 1:
                missing = list(range(current + 1, next_num))
                gaps.extend(missing)

        if gaps:
            print(f"{Colors.BLUE}ℹ Info: Gaps in ADR numbering: {', '.join(f'{n:04d}' for n in gaps[:5])}")
            if len(gaps) > 5:
                print(f"       ... and {len(gaps) - 5} more{Colors.RESET}")

    return errors


def generate_index(dry_run: bool = False) -> bool:
    """
    Generate the ADR index README.md.

    Args:
        dry_run: If True, only preview changes

    Returns:
        True if successful, False otherwise
    """
    try:
        # Find all ADRs
        print(f"{Colors.BOLD}Finding ADRs...{Colors.RESET}")
        adrs = find_all_adrs()
        print(f"Found {len(adrs)} ADRs")

        # Validate numbering
        print(f"\n{Colors.BOLD}Validating ADR numbering...{Colors.RESET}")
        errors = validate_adr_numbering(adrs)

        if errors:
            for error in errors:
                print(f"{Colors.RED}✗ {error}{Colors.RESET}")
            return False

        print(f"{Colors.GREEN}✓ ADR numbering is valid{Colors.RESET}")

        # Generate content
        print(f"\n{Colors.BOLD}Generating README content...{Colors.RESET}")
        content = generate_readme_content(adrs)

        # Write to file
        readme_path = Path("adr/README.md")

        if dry_run:
            print(f"{Colors.YELLOW}Dry run - would write to {readme_path}{Colors.RESET}")
            print("\nPreview (first 20 lines):\n")
            for line in content.splitlines()[:20]:
                print(f"  {line}")
            print("  ...")
        else:
            readme_path.write_text(content, encoding="utf-8")
            print(f"{Colors.GREEN}✓ Generated {readme_path}{Colors.RESET}")

        return True

    except Exception as e:
        print(f"{Colors.RED}✗ Error: {e}{Colors.RESET}")
        return False


def check_index_up_to_date() -> bool:
    """
    Check if the ADR index is up-to-date.

    Returns:
        True if up-to-date, False otherwise
    """
    try:
        print(f"{Colors.BOLD}Checking if ADR index is up-to-date...{Colors.RESET}\n")

        # Generate expected content
        adrs = find_all_adrs()
        expected_content = generate_readme_content(adrs)

        # Read current content
        readme_path = Path("adr/README.md")

        if not readme_path.exists():
            print(f"{Colors.RED}✗ {readme_path} does not exist{Colors.RESET}")
            print(f"\nRun: {Colors.BOLD}python scripts/generate_adr_index.py{Colors.RESET}")
            return False

        current_content = readme_path.read_text(encoding="utf-8")

        # Compare
        if current_content.strip() == expected_content.strip():
            print(f"{Colors.GREEN}✓ ADR index is up-to-date{Colors.RESET}")
            return True
        else:
            print(f"{Colors.YELLOW}⚠ ADR index is out of date{Colors.RESET}")
            print(f"\nRun: {Colors.BOLD}python scripts/generate_adr_index.py{Colors.RESET}")
            return False

    except Exception as e:
        print(f"{Colors.RED}✗ Error: {e}{Colors.RESET}")
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate ADR index (adr/README.md)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                    Generate adr/README.md
  %(prog)s --check            Check if README is up-to-date
  %(prog)s --validate         Validate ADR numbering only
  %(prog)s --dry-run          Preview changes
        """,
    )
    parser.add_argument("--check", action="store_true", help="Check if index is up-to-date")
    parser.add_argument("--validate", action="store_true", help="Validate ADR numbering only")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing files")

    args = parser.parse_args()

    # Change to repo root
    repo_root = Path(__file__).parent.parent.parent
    import os

    os.chdir(repo_root)

    print(f"\n{Colors.BOLD}{Colors.BLUE}ADR Index Generator{Colors.RESET}\n")

    if args.check:
        # Check if up-to-date
        up_to_date = check_index_up_to_date()
        sys.exit(0 if up_to_date else 1)

    elif args.validate:
        # Validate only
        print(f"{Colors.BOLD}Validating ADR numbering...{Colors.RESET}\n")
        adrs = find_all_adrs()
        errors = validate_adr_numbering(adrs)

        if errors:
            for error in errors:
                print(f"{Colors.RED}✗ {error}{Colors.RESET}")
            sys.exit(1)
        else:
            print(f"{Colors.GREEN}✓ All ADRs validated successfully{Colors.RESET}")
            sys.exit(0)

    else:
        # Generate index
        success = generate_index(args.dry_run)
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
