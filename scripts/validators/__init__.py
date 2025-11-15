"""Documentation validators package.

ACTIVE VALIDATORS:
- frontmatter_validator: YAML frontmatter validation (complementary to Mintlify)
- codeblock_validator: Code block language tag validation
- mdx_extension_validator: MDX file extension enforcement

ARCHIVED VALIDATORS (2025-11-15):
Most validators have been archived to scripts/validators/archive/ as we've
simplified documentation validation. Archived validators were replaced by
Mintlify's built-in validation:
- image_validator → Replaced by Mintlify validation
- link_validator → Replaced by Mintlify validation
- navigation_validator → Replaced by Mintlify validation

See: docs-internal/DOCS_VALIDATION_SIMPLIFICATION.md
"""

from .codeblock_validator import CodeBlockError, CodeBlockValidator
from .frontmatter_validator import FrontmatterError, FrontmatterValidator
from .mdx_extension_validator import ExtensionError, MDXExtensionValidator

__all__ = [
    "FrontmatterValidator",
    "FrontmatterError",
    "MDXExtensionValidator",
    "ExtensionError",
    "CodeBlockValidator",
    "CodeBlockError",
]
