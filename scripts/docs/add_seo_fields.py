#!/usr/bin/env python3
"""
Add SEO fields to MDX files missing them.

This script reads MDX files, extracts existing frontmatter, generates appropriate
SEO fields (seoTitle, seoDescription, keywords) based on title/description, and
updates the files with the new frontmatter.
"""

import re
import sys
from pathlib import Path

import yaml


def extract_frontmatter(content: str) -> tuple[dict | None, str]:
    """Extract YAML frontmatter from MDX content.

    Returns:
        Tuple of (frontmatter_dict, remaining_content)
    """
    pattern = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.MULTILINE | re.DOTALL)
    match = pattern.match(content)

    if not match:
        return None, content

    frontmatter_text = match.group(1)
    remaining_content = content[match.end() :]

    try:
        frontmatter = yaml.safe_load(frontmatter_text)
        return frontmatter, remaining_content
    except yaml.YAMLError as e:
        print(f"Error parsing YAML: {e}", file=sys.stderr)
        return None, content


def generate_seo_title(title: str, category: str = "") -> str:
    """Generate SEO-optimized title (50-60 characters).

    Args:
        title: Original title from frontmatter
        category: Optional category (e.g., "Guide", "Reference", "Tutorial")

    Returns:
        SEO-optimized title
    """
    base = title.strip()
    suffix = " - MCP Server LangGraph"

    # If title + suffix < 60 chars, use as-is
    if len(base + suffix) <= 60:
        return base + suffix

    # Otherwise truncate base to fit
    max_base_len = 60 - len(suffix) - 3  # -3 for "..."
    if len(base) > max_base_len:
        base = base[:max_base_len].rsplit(" ", 1)[0] + "..."

    return base + suffix


def generate_seo_description(description: str, title: str) -> str:
    """Generate SEO-optimized description (150-160 characters).

    Args:
        description: Original description from frontmatter
        title: Original title for context

    Returns:
        SEO-optimized description
    """
    desc = description.strip()

    # If description is already in good range, use as-is
    if 140 <= len(desc) <= 160:
        return desc

    # If too short, expand with context
    if len(desc) < 140:
        suffix = " Learn more about MCP Server LangGraph."
        if len(desc + suffix) <= 160:
            return desc + suffix
        return desc

    # If too long, truncate at sentence boundary
    if len(desc) > 160:
        truncated = desc[:157].rsplit(".", 1)[0]
        if truncated:
            return truncated + "."
        # No sentence boundary, hard truncate
        return desc[:157] + "..."

    return desc


def extract_keywords(title: str, description: str, content: str) -> list[str]:
    """Extract relevant keywords from title, description, and content.

    Args:
        title: Page title
        description: Page description
        content: Full page content

    Returns:
        List of 5-10 relevant keywords
    """
    # Common words to exclude
    stopwords = {
        "the",
        "a",
        "an",
        "and",
        "or",
        "but",
        "in",
        "on",
        "at",
        "to",
        "for",
        "of",
        "with",
        "is",
        "are",
        "was",
        "were",
        "be",
        "been",
        "being",
        "have",
        "has",
        "had",
        "do",
        "does",
        "did",
        "will",
        "would",
        "should",
        "could",
        "may",
        "might",
        "must",
        "can",
        "this",
        "that",
        "these",
        "those",
    }

    # Extract words from title and description
    text = f"{title} {description}".lower()
    words = re.findall(r"\b[a-z][a-z0-9-]+\b", text)

    # Filter stopwords and get unique words
    keywords = []
    seen = set()
    for word in words:
        if word not in stopwords and word not in seen and len(word) > 2:
            keywords.append(word)
            seen.add(word)

    # Always include these relevant keywords if not already present
    domain_keywords = ["mcp server", "langgraph"]
    for keyword in domain_keywords:
        if keyword not in keywords:
            keywords.append(keyword)

    # Limit to 10 keywords
    return keywords[:10]


def update_frontmatter_with_seo(file_path: Path, dry_run: bool = False) -> bool:
    """Update MDX file with SEO fields.

    Args:
        file_path: Path to MDX file
        dry_run: If True, print changes without writing

    Returns:
        True if file was updated, False otherwise
    """
    try:
        content = file_path.read_text()
    except Exception as e:
        print(f"Error reading {file_path}: {e}", file=sys.stderr)
        return False

    frontmatter, remaining_content = extract_frontmatter(content)

    if not frontmatter:
        print(f"No frontmatter found in {file_path}", file=sys.stderr)
        return False

    # Check if SEO fields already exist
    if "seoTitle" in frontmatter and "seoDescription" in frontmatter and "keywords" in frontmatter:
        print(f"SEO fields already exist in {file_path}")
        return False

    # Get required fields
    title = frontmatter.get("title", "")
    description = frontmatter.get("description", "")

    if not title or not description:
        print(f"Missing title or description in {file_path}", file=sys.stderr)
        return False

    # Generate SEO fields
    seo_title = generate_seo_title(title)
    seo_description = generate_seo_description(description, title)
    keywords = extract_keywords(title, description, remaining_content[:1000])  # First 1000 chars

    # Add SEO fields to frontmatter
    frontmatter["seoTitle"] = seo_title
    frontmatter["seoDescription"] = seo_description
    frontmatter["keywords"] = keywords

    # Reconstruct content with updated frontmatter
    new_frontmatter_text = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False, allow_unicode=True)
    new_content = f"---\n{new_frontmatter_text}---\n{remaining_content}"

    if dry_run:
        print(f"\n{'=' * 80}")
        print(f"File: {file_path}")
        print(f"{'=' * 80}")
        print(f"seoTitle: {seo_title}")
        print(f"seoDescription: {seo_description}")
        print(f"keywords: {keywords}")
        return True

    # Write updated content
    try:
        file_path.write_text(new_content)
        print(f"✅ Updated {file_path}")
        return True
    except Exception as e:
        print(f"Error writing {file_path}: {e}", file=sys.stderr)
        return False


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Add SEO fields to MDX files")
    parser.add_argument("files", type=Path, nargs="*", help="MDX files to update (or read from stdin if not provided)")
    parser.add_argument("--dry-run", action="store_true", help="Print changes without writing files")

    args = parser.parse_args()

    # Get files from arguments or stdin
    if args.files:
        files = args.files
    else:
        # Read from stdin (one file per line)
        files = [Path(line.strip()) for line in sys.stdin if line.strip()]

    if not files:
        print("No files to process", file=sys.stderr)
        return 1

    # Process each file
    updated_count = 0
    for file_path in files:
        if not file_path.exists():
            print(f"File not found: {file_path}", file=sys.stderr)
            continue

        if update_frontmatter_with_seo(file_path, dry_run=args.dry_run):
            updated_count += 1

    print(f"\n{'=' * 80}")
    print(f"{'DRY RUN - ' if args.dry_run else ''}Processed {len(files)} files, updated {updated_count}")
    print(f"{'=' * 80}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
