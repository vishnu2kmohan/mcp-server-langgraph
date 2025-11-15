"""Documentation validators package.

DEPRECATION NOTICE (2025-11-15):
Most validators have been archived to scripts/validators/archive/ as we've
simplified documentation validation. Only active validators remain here.

Archived validators (now using Mintlify's built-in validation):
- frontmatter_validator → Replaced by Mintlify validation
- image_validator → Replaced by Mintlify validation
- link_validator → Replaced by Mintlify validation
- navigation_validator → Replaced by Mintlify validation

See: docs-internal/DOCS_VALIDATION_SIMPLIFICATION.md
"""

from .codeblock_validator import CodeBlockError, CodeBlockValidator
from .mdx_extension_validator import ExtensionError, MDXExtensionValidator

__all__ = [
    "MDXExtensionValidator",
    "ExtensionError",
    "CodeBlockValidator",
    "CodeBlockError",
]
