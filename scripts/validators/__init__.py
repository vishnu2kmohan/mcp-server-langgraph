"""Documentation validators package.

ACTIVE VALIDATORS (2025-11-29):
- validate_docs: Consolidated documentation validator (MDX, naming, ADR, tests)
- frontmatter_validator: YAML frontmatter validation (complementary to Mintlify)

CONSOLIDATED (2025-11-29):
The following were consolidated into validate_docs.py:
- mdx_extension_validator → validate_docs.py --mdx
- file_naming_validator → validate_docs.py --mdx
- adr_sync_validator → validate_docs.py --adr

ARCHIVED VALIDATORS (2025-11-15):
Most validators have been archived to scripts/validators/archive/ as we've
simplified documentation validation. Archived validators were replaced by
Mintlify's built-in validation:
- image_validator → Replaced by Mintlify validation
- link_validator → Replaced by Mintlify validation
- navigation_validator → Replaced by Mintlify validation

See: docs-internal/DOCS_VALIDATION_SIMPLIFICATION.md
"""

from .frontmatter_validator import FrontmatterError, FrontmatterValidator

__all__ = [
    "FrontmatterValidator",
    "FrontmatterError",
]
