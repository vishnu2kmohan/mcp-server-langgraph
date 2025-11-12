#!/usr/bin/env python3
"""
Master Documentation Validator

Runs all documentation validators and provides a unified report.

Validators:
1. Navigation Validator - Checks docs.json consistency
2. MDX Extension Validator - Ensures .mdx extension usage
3. Frontmatter Validator - Validates YAML frontmatter
4. Link Validator - Checks for broken links (optional)

Exit codes:
- 0: All validations passed
- 1: One or more validations failed
- 2: Critical error
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict

from navigation_validator import NavigationValidator
from mdx_extension_validator import MDXExtensionValidator
from frontmatter_validator import FrontmatterValidator

try:
    from link_validator import LinkValidator

    LINK_VALIDATOR_AVAILABLE = True
except ImportError:
    LINK_VALIDATOR_AVAILABLE = False


@dataclass
class MasterValidationResult:
    """Combined result from all validators."""

    is_valid: bool
    results: Dict[str, object] = field(default_factory=dict)
    summary: Dict[str, bool] = field(default_factory=dict)

    @property
    def exit_code(self) -> int:
        """Get exit code for CLI."""
        if not self.is_valid:
            return 1
        return 0


class DocumentationValidator:
    """Master validator that runs all documentation checks."""

    def __init__(self, docs_dir: Path, skip_links: bool = False):
        """
        Initialize master validator.

        Args:
            docs_dir: Path to docs directory
            skip_links: Skip link validation (can be slow)
        """
        self.docs_dir = Path(docs_dir)
        self.skip_links = skip_links

    def validate(self) -> MasterValidationResult:
        """
        Run all validators.

        Returns:
            MasterValidationResult with all validation results
        """
        results = {}
        summary = {}

        print("\n" + "=" * 80)
        print("🔍 Running Documentation Validation Suite")
        print("=" * 80)

        # 1. Navigation Validator
        print("\n[1/4] Running Navigation Validator...")
        nav_validator = NavigationValidator(self.docs_dir)
        nav_result = nav_validator.validate()
        results["navigation"] = nav_result
        summary["navigation"] = nav_result.is_valid

        if nav_result.is_valid:
            print("  ✅ Navigation validation passed")
        else:
            print(f"  ❌ Navigation validation failed ({len(nav_result.errors)} errors)")

        # 2. MDX Extension Validator
        print("\n[2/4] Running MDX Extension Validator...")
        ext_validator = MDXExtensionValidator(self.docs_dir)
        ext_result = ext_validator.validate()
        results["extension"] = ext_result
        summary["extension"] = ext_result.is_valid

        if ext_result.is_valid:
            print("  ✅ Extension validation passed")
        else:
            print(
                f"  ❌ Extension validation failed ({len(ext_result.errors)} errors)"
            )

        # 3. Frontmatter Validator
        print("\n[3/4] Running Frontmatter Validator...")
        fm_validator = FrontmatterValidator(self.docs_dir)
        fm_result = fm_validator.validate()
        results["frontmatter"] = fm_result
        summary["frontmatter"] = fm_result.is_valid

        if fm_result.is_valid:
            print("  ✅ Frontmatter validation passed")
        else:
            print(
                f"  ❌ Frontmatter validation failed ({len(fm_result.errors)} errors)"
            )

        # 4. Link Validator (optional)
        if not self.skip_links and LINK_VALIDATOR_AVAILABLE:
            print("\n[4/4] Running Link Validator...")
            link_validator = LinkValidator(self.docs_dir)
            link_result = link_validator.validate()
            results["links"] = link_result
            summary["links"] = link_result.is_valid

            if link_result.is_valid:
                print("  ✅ Link validation passed")
            else:
                print(
                    f"  ❌ Link validation failed ({len(link_result.errors)} errors)"
                )
        else:
            if self.skip_links:
                print("\n[4/4] Skipping Link Validator (--skip-links)")
            else:
                print("\n[4/4] Link Validator not available (optional)")
            summary["links"] = True  # Don't fail if skipped

        # Determine overall validity
        is_valid = all(summary.values())

        return MasterValidationResult(
            is_valid=is_valid, results=results, summary=summary
        )

    def print_summary(self, result: MasterValidationResult) -> None:
        """Print overall validation summary."""
        print("\n" + "=" * 80)
        print("📊 Validation Summary")
        print("=" * 80)

        # Print status for each validator
        for validator_name, is_valid in result.summary.items():
            status = "✅ PASS" if is_valid else "❌ FAIL"
            print(f"  {validator_name.capitalize():20s} {status}")

        # Overall status
        print("\n" + "=" * 80)
        if result.is_valid:
            print("✅ All validations passed!")
            print("\nYour documentation is in excellent condition!")
        else:
            print("❌ Some validations failed")
            print("\nPlease review the errors above and fix them.")
            print("Run validators individually for detailed reports:")
            print("  - python scripts/validators/navigation_validator.py")
            print("  - python scripts/validators/mdx_extension_validator.py")
            print("  - python scripts/validators/frontmatter_validator.py")
        print("=" * 80 + "\n")


def main():
    """Main CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run all documentation validators"
    )
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=Path("docs"),
        help="Path to docs directory (default: docs/)",
    )
    parser.add_argument(
        "--skip-links",
        action="store_true",
        help="Skip link validation (faster)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed reports from each validator",
    )

    args = parser.parse_args()

    # Run validation
    validator = DocumentationValidator(args.docs_dir, skip_links=args.skip_links)
    result = validator.validate()

    # Print detailed reports if verbose
    if args.verbose:
        for name, val_result in result.results.items():
            if hasattr(val_result, "errors") and val_result.errors:
                print(f"\n{'=' * 80}")
                print(f"Detailed {name.capitalize()} Report:")
                print('=' * 80)
                for error in val_result.errors:
                    print(f"  ❌ {error}")

    # Print summary
    validator.print_summary(result)

    # Exit with appropriate code
    sys.exit(result.exit_code)


if __name__ == "__main__":
    main()
