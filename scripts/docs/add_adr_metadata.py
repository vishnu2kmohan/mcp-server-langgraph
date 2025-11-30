#!/usr/bin/env python3
"""Add missing SEO and contentType metadata to ADR files.

This script adds:
- contentType: "reference" (Diátaxis framework)
- seoTitle: "{title} - Architecture Decision Record"
- seoDescription: Expanded description for SEO
- keywords: Relevant keywords extracted from title and category
"""

import re
from pathlib import Path


def extract_category(content: str) -> str:
    """Extract the Category from ADR content."""
    match = re.search(r"## Category\s*\n+([^\n#]+)", content)
    if match:
        return match.group(1).strip()
    return "Architecture"


def generate_keywords(title: str, category: str) -> list[str]:
    """Generate relevant keywords from title and category."""
    # Base keywords
    keywords = ["architecture", "decision", "record", "ADR", "MCP Server", "LangGraph"]

    # Add category-based keywords
    category_lower = category.lower()
    if "auth" in category_lower:
        keywords.extend(["authentication", "authorization", "security"])
    elif "deploy" in category_lower or "infrastructure" in category_lower:
        keywords.extend(["deployment", "infrastructure", "kubernetes"])
    elif "test" in category_lower:
        keywords.extend(["testing", "quality", "pytest"])
    elif "observ" in category_lower:
        keywords.extend(["observability", "monitoring", "tracing"])
    elif "compliance" in category_lower:
        keywords.extend(["compliance", "GDPR", "security"])

    # Extract key terms from title
    title_words = re.findall(r"\b[A-Z][a-z]+(?:[A-Z][a-z]+)*\b|\b[A-Z]{2,}\b", title)
    for word in title_words:
        if word.lower() not in [k.lower() for k in keywords] and len(word) > 2:
            keywords.append(word)

    # Deduplicate and limit
    seen = set()
    unique_keywords = []
    for k in keywords:
        if k.lower() not in seen:
            seen.add(k.lower())
            unique_keywords.append(k)

    return unique_keywords[:10]


def add_metadata_to_adr(file_path: Path) -> bool:
    """Add missing metadata to an ADR file."""
    content = file_path.read_text()

    # Check if already has contentType
    if "contentType:" in content:
        return False

    # Parse existing frontmatter
    fm_match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    if not fm_match:
        print(f"  ⚠️ No frontmatter found in {file_path.name}")
        return False

    frontmatter = fm_match.group(1)
    rest_of_content = content[fm_match.end() :]

    # Extract title from frontmatter
    title_match = re.search(r'title:\s*["\']?([^"\'\n]+)["\']?', frontmatter)
    if not title_match:
        print(f"  ⚠️ No title found in {file_path.name}")
        return False

    title = title_match.group(1).strip()

    # Extract category from content
    category = extract_category(content)

    # Generate SEO metadata
    seo_title = f"{title} - Architecture Decision Record"
    seo_description = (
        f"Architecture Decision Record for {title}. Category: {category}. Part of MCP Server with LangGraph documentation."
    )
    keywords = generate_keywords(title, category)

    # Build new frontmatter
    new_fields = f"""contentType: "reference"
seoTitle: "{seo_title}"
seoDescription: "{seo_description}"
keywords:
{chr(10).join(f'  - "{k}"' for k in keywords)}"""

    # Insert new fields before closing ---
    new_frontmatter = frontmatter.rstrip() + "\n" + new_fields
    new_content = f"---\n{new_frontmatter}\n---{rest_of_content}"

    file_path.write_text(new_content)
    return True


def main():
    """Process all ADR files missing metadata."""
    docs_dir = Path(__file__).parent.parent.parent / "docs" / "architecture"

    if not docs_dir.exists():
        print(f"❌ Directory not found: {docs_dir}")
        return

    adr_files = sorted(docs_dir.glob("adr-*.mdx"))

    print(f"📝 Processing {len(adr_files)} ADR files...")

    updated = 0
    skipped = 0

    for adr_file in adr_files:
        if add_metadata_to_adr(adr_file):
            print(f"  ✅ Updated: {adr_file.name}")
            updated += 1
        else:
            skipped += 1

    print("\n📊 Summary:")
    print(f"  Updated: {updated}")
    print(f"  Skipped (already has metadata): {skipped}")


if __name__ == "__main__":
    main()
