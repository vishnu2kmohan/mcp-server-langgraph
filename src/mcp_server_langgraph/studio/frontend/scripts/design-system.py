#!/usr/bin/env python3
"""
Unified Design System Tool

Consolidated tool for design system compliance checking, migration, and fixing.
Replaces multiple fragmented scripts with a single, efficient interface.

Subcommands:
  check   - Quick validation for pre-commit (fast, only blocking errors)
  audit   - Comprehensive audit with detailed report
  fix     - Auto-fix violations in place
  report  - Generate compliance report (JSON/markdown)

Usage:
  python scripts/design-system.py check [files...]
  python scripts/design-system.py audit [--category=color] [--strict]
  python scripts/design-system.py fix [--dry-run] [--category=all]
  python scripts/design-system.py report [--format=json|md]

Categories: color, spacing, typography, border, shadow, zindex, animation, all

Performance Optimizations:
  - Regex patterns compiled once at import time
  - File processing with early exit on first blocking error (check mode)
  - Parallel processing for audit/fix modes (optional)
  - Incremental mode for pre-commit (only checks staged files)

Exit Codes:
  0: Success (no blocking violations)
  1: Blocking violations found
  2: Usage error
"""

import argparse
import json
import re
import sys
from collections import defaultdict
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Callable

# =============================================================================
# Configuration
# =============================================================================

FRONTEND_SRC = Path(__file__).parent.parent / "src"

EXTENSIONS = {".tsx", ".ts", ".jsx", ".js"}

SKIP_DIRS = {"node_modules", "dist", ".storybook", "coverage", "__snapshots__"}

# Files that legitimately define design tokens or have documented exceptions
SKIP_FILES = {
    # Design token definitions
    "radix-colors.ts",
    "chart-colors.ts",
    "animation-tokens.ts",
    "design-tokens.ts",
    "tailwind.config.ts",
    "index.css",
    # Sandboxed code generation (runs in isolated iframe without Tailwind)
    "SandpackExecutor.tsx",
    # Error boundary fallback UI (must work even if CSS fails)
    "AIErrorBoundary.tsx",
}


class Severity(Enum):
    ERROR = "error"  # Blocks commit
    WARNING = "warning"  # Logged but doesn't block
    INFO = "info"  # Informational only


class Category(Enum):
    COLOR = "color"
    SPACING = "spacing"
    TYPOGRAPHY = "typography"
    BORDER = "border"
    SHADOW = "shadow"
    ZINDEX = "zindex"
    ANIMATION = "animation"
    COMPONENT = "component"  # Component usage patterns
    FOCUS = "focus"  # Focus ring accessibility
    TOUCH = "touch"  # Touch target size (WCAG 2.5.8)
    ARIA = "aria"  # ARIA attributes
    MOTION = "motion"  # Reduced motion compliance


@dataclass
class Violation:
    file: Path
    line_no: int
    column: int
    category: Category
    severity: Severity
    rule: str
    match: str
    message: str
    fix: str | None = None


@dataclass
class ViolationPattern:
    regex: re.Pattern[str]
    category: Category
    severity: Severity
    rule: str
    message: str
    fix_template: str | None = None  # Replacement pattern or None
    fix_fn: Callable[[str], str] | None = None  # Custom fix function


# =============================================================================
# Pattern[str] Definitions - SINGLE SOURCE OF TRUTH
# =============================================================================

# Legacy to Radix color mappings
LEGACY_TO_RADIX = {
    "50": "1",
    "100": "2",
    "200": "3",
    "300": "4",
    "400": "5",
    "500": "9",
    "600": "10",
    "700": "11",
    "800": "11",
    "900": "12",
    "950": "12",
}

SEMANTIC_COLORS = ["primary", "error", "success", "warning", "info", "insight", "grafana"]
COLOR_UTILITIES = ["bg", "text", "border", "ring", "divide", "outline", "fill", "stroke"]

# Opacity to Radix alpha step mapping
# Tailwind /XX opacity maps to Radix alpha steps (a1-a12)
OPACITY_TO_ALPHA_STEP = {
    # Very low opacity → very transparent alpha steps
    "5": "1",
    "10": "2",
    "15": "2",
    "20": "3",
    "25": "3",
    # Low-medium opacity
    "30": "4",
    "35": "4",
    "40": "5",
    "45": "5",
    # Medium opacity
    "50": "6",
    "55": "6",
    "60": "7",
    "65": "7",
    # Medium-high opacity
    "70": "8",
    "75": "8",
    "80": "9",
    "85": "9",
    # High opacity → just use solid color (no alpha needed)
    "90": None,
    "95": None,
    "100": None,
}


def fix_opacity_modifier(match_str: str) -> str:
    """
    Convert Tailwind opacity modifier to Radix alpha color.

    Examples:
        bg-neutral-12/50 → bg-neutral-a6
        border-warning-6/30 → border-warning-a4
        dark:bg-primary-9/80 → dark:bg-primary-a9
        bg-neutral-3/90 → bg-neutral-3 (high opacity = solid)
    """
    import re

    # Match[str] pattern: (dark:)?(utility)-(color)-(step)/(opacity)
    pattern = re.compile(r"^(dark:)?(\w+)-(\w+)-(\d{1,2})/(\d+)$")
    m = pattern.match(match_str)
    if not m:
        return match_str  # Can't parse, return unchanged

    dark_prefix = m.group(1) or ""
    utility = m.group(2)
    color = m.group(3)
    _step = m.group(4)  # Original step (we ignore this for alpha colors)
    opacity = m.group(5)

    alpha_step = OPACITY_TO_ALPHA_STEP.get(opacity)

    if alpha_step is None:
        # High opacity (90+): just use solid color at original step
        return f"{dark_prefix}{utility}-{color}-{_step}"
    else:
        # Use alpha color at mapped step
        return f"{dark_prefix}{utility}-{color}-a{alpha_step}"


def _build_patterns() -> list[ViolationPattern]:
    """Build all violation detection patterns. Called once at import."""
    patterns: list[ViolationPattern] = []

    # =========================================================================
    # COLOR PATTERNS
    # =========================================================================

    # 1. Raw Tailwind colors (text-white, bg-black)
    # NOTE: text-white is often legitimate for button text on solid backgrounds (primary-9)
    # bg-black is often used for overlays. These are INFO level, not errors.
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\b(text|bg|border|ring)-(white|black)\b"),
            category=Category.COLOR,
            severity=Severity.INFO,
            rule="raw-tailwind-color",
            message="Consider if this needs a semantic alternative (text-white on solid buttons is OK)",
            fix_template=None,  # Needs context-aware fix
        )
    )

    # 2. Raw Tailwind with opacity (bg-black/50)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\b(text|bg|border|ring)-(white|black)/\d+"),
            category=Category.COLOR,
            severity=Severity.ERROR,
            rule="raw-tailwind-color-opacity",
            message="Use Radix semantic token with opacity",
            fix_template=None,
        )
    )

    # 3. Raw gray/slate colors
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\b(bg|text|border)-(gray|slate|zinc|stone)-\d{2,3}\b"),
            category=Category.COLOR,
            severity=Severity.ERROR,
            rule="raw-gray-color",
            message="Use neutral-N instead of gray/slate colors",
            fix_template=None,
        )
    )

    # 4. Legacy semantic colors (warning-500, success-100, etc.)
    for color in SEMANTIC_COLORS:
        for legacy, radix in LEGACY_TO_RADIX.items():
            for util in COLOR_UTILITIES:
                patterns.append(
                    ViolationPattern(
                        regex=re.compile(rf"\b{util}-{color}-{legacy}\b"),
                        category=Category.COLOR,
                        severity=Severity.ERROR,
                        rule=f"legacy-{color}-scale",
                        message=f"Use Radix scale: {util}-{color}-{radix}",
                        fix_template=f"{util}-{color}-{radix}",
                    )
                )

    # 5. Legacy neutral scale
    for legacy, radix in LEGACY_TO_RADIX.items():
        for util in COLOR_UTILITIES:
            patterns.append(
                ViolationPattern(
                    regex=re.compile(rf"\b{util}-neutral-{legacy}\b"),
                    category=Category.COLOR,
                    severity=Severity.ERROR,
                    rule="legacy-neutral-scale",
                    message=f"Use Radix scale: {util}-neutral-{radix}",
                    fix_template=f"{util}-neutral-{radix}",
                )
            )

    # 6. Inline hex colors in style props
    patterns.append(
        ViolationPattern(
            regex=re.compile(r'style\s*=\s*\{\s*\{[^}]*(?:color|background|backgroundColor)\s*:\s*["\']?#[0-9a-fA-F]{3,8}'),
            category=Category.COLOR,
            severity=Severity.ERROR,
            rule="inline-hex-color",
            message="No inline hex colors - use className with design tokens",
            fix_template=None,
        )
    )

    # 7. Hex colors in JSX props (stroke, fill, color, backgroundColor, etc.)
    patterns.append(
        ViolationPattern(
            regex=re.compile(
                r'\b(?:stroke|fill|color|backgroundColor|bgColor|textColor|borderColor|nodeColor|maskColor)\s*=\s*["{]["\']?#[0-9a-fA-F]{3,8}'
            ),
            category=Category.COLOR,
            severity=Severity.ERROR,
            rule="jsx-prop-hex-color",
            message="Use CSS custom properties (var(--color-N)) instead of hex colors in JSX props",
            fix_template=None,
        )
    )

    # 8. RGB/RGBA inline colors
    patterns.append(
        ViolationPattern(
            regex=re.compile(
                r'\b(?:stroke|fill|color|backgroundColor|bgColor|textColor|borderColor|nodeColor|maskColor)\s*=\s*["\'`]rgba?\([^)]+\)'
            ),
            category=Category.COLOR,
            severity=Severity.ERROR,
            rule="jsx-prop-rgba-color",
            message="Use CSS custom properties with opacity instead of rgba() in JSX props",
            fix_template=None,
        )
    )

    # 9. HSL/HSLA colors in JSX props
    patterns.append(
        ViolationPattern(
            regex=re.compile(
                r'\b(?:stroke|fill|color|backgroundColor|bgColor|textColor|borderColor|nodeColor|maskColor)\s*=\s*["\'`]hsla?\([^)]+\)'
            ),
            category=Category.COLOR,
            severity=Severity.ERROR,
            rule="jsx-prop-hsl-color",
            message="Use CSS custom properties instead of hsl() in JSX props",
            fix_template=None,
        )
    )

    # 10. Named CSS colors in JSX props (excluding 'inherit', 'transparent', 'currentColor', 'none', 'var(')
    # Note: Uses `="` (no spaces) to only match JSX props, not TypeScript parameter defaults like `color = "blue"`
    NAMED_COLORS = r"red|blue|green|yellow|orange|purple|pink|cyan|magenta|brown|black|white|gray|grey|navy|maroon|olive|teal|aqua|lime|fuchsia|silver"
    patterns.append(
        ViolationPattern(
            regex=re.compile(
                rf'\b(?:stroke|fill|backgroundColor|bgColor|textColor|borderColor|nodeColor|maskColor)="(?:{NAMED_COLORS})"'
            ),
            category=Category.COLOR,
            severity=Severity.ERROR,
            rule="jsx-prop-named-color",
            message="Use CSS custom properties (var(--color-N)) instead of named colors in JSX props",
            fix_template=None,
        )
    )

    # 11. Tailwind arbitrary color classes (bg-[#fff], text-[#000], border-[#abc])
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\b(?:bg|text|border|ring|fill|stroke)-\[#[0-9a-fA-F]{3,8}\]"),
            category=Category.COLOR,
            severity=Severity.ERROR,
            rule="arbitrary-hex-class",
            message="Use design token class instead of arbitrary hex color",
            fix_template=None,
        )
    )

    # 12. Tailwind arbitrary rgba/rgb classes
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\b(?:bg|text|border|ring|fill|stroke)-\[rgba?\([^\]]+\)\]"),
            category=Category.COLOR,
            severity=Severity.ERROR,
            rule="arbitrary-rgba-class",
            message="Use design token class instead of arbitrary rgba color",
            fix_template=None,
        )
    )

    # 13. Inline hex in style objects (broader pattern)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r'style\s*=\s*\{\{[^}]*:\s*["\']#[0-9a-fA-F]{3,8}["\']'),
            category=Category.COLOR,
            severity=Severity.ERROR,
            rule="inline-style-hex",
            message="No inline hex colors in style objects - use className with design tokens",
            fix_template=None,
        )
    )

    # 14. Redundant dark mode overrides
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\bdark:(text|bg|border|ring)-(white|black)\b"),
            category=Category.COLOR,
            severity=Severity.WARNING,
            rule="redundant-dark-override",
            message="Remove redundant dark: prefix - Radix handles dark mode",
            fix_template="",  # Remove entirely
        )
    )

    # 15. Tailwind opacity modifier on semantic/neutral colors (bg-neutral-2/50, border-primary-6/50)
    # These should use Radix alpha colors (e.g., neutral-a2) or solid colors instead
    # NOTE: Changed to WARNING - opacity modifiers work but Radix alpha colors are preferred
    patterns.append(
        ViolationPattern(
            regex=re.compile(
                r"\b(?:bg|text|border|ring|divide|outline|fill|stroke)-(?:neutral|primary|error|success|warning|info|insight)-\d{1,2}/\d+"
            ),
            category=Category.COLOR,
            severity=Severity.WARNING,
            rule="tailwind-opacity-modifier",
            message="Prefer Radix alpha colors (e.g., neutral-a2) over Tailwind opacity modifier (/XX) for better dark mode",
            fix_template=None,
            fix_fn=fix_opacity_modifier,
        )
    )

    # 16. Tailwind opacity modifier with dark: prefix
    patterns.append(
        ViolationPattern(
            regex=re.compile(
                r"\bdark:(?:bg|text|border|ring|divide|outline|fill|stroke)-(?:neutral|primary|error|success|warning|info|insight)-\d{1,2}/\d+"
            ),
            category=Category.COLOR,
            severity=Severity.ERROR,
            rule="tailwind-opacity-modifier-dark",
            message="Use Radix alpha colors (e.g., neutral-a2) instead of Tailwind opacity modifier in dark mode",
            fix_template=None,
            fix_fn=fix_opacity_modifier,
        )
    )

    # =========================================================================
    # SPACING PATTERNS
    # =========================================================================

    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\b[mp][trblxy]?-\[\d+px\]"),
            category=Category.SPACING,
            severity=Severity.WARNING,
            rule="arbitrary-spacing",
            message="Use design token spacing instead of arbitrary pixel values",
            fix_template=None,
        )
    )

    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\bgap-\[\d+px\]"),
            category=Category.SPACING,
            severity=Severity.WARNING,
            rule="arbitrary-gap",
            message="Use design token gap instead of arbitrary pixel values",
            fix_template=None,
        )
    )

    # 15. Inline style with pixel spacing (margin, padding)
    # Excludes dynamic values (template literals with variables)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r'style\s*=\s*\{\{[^}]*(?:margin|padding)[^:]*:\s*["\']?(?:\d+px|0\s+0\s+\d+px)'),
            category=Category.SPACING,
            severity=Severity.WARNING,
            rule="inline-style-spacing",
            message="Consider using Tailwind spacing classes (m-*, p-*) instead of inline style pixels",
            fix_template=None,
        )
    )

    # =========================================================================
    # TYPOGRAPHY PATTERNS
    # =========================================================================

    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\btext-\[\d+px\]"),
            category=Category.TYPOGRAPHY,
            severity=Severity.WARNING,
            rule="arbitrary-font-size",
            message="Use design token font size (text-xs, text-sm, etc.)",
            fix_template=None,
        )
    )

    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\bleading-\[\d+"),
            category=Category.TYPOGRAPHY,
            severity=Severity.WARNING,
            rule="arbitrary-line-height",
            message="Use design token line height (leading-tight, leading-normal, etc.)",
            fix_template=None,
        )
    )

    # =========================================================================
    # BORDER PATTERNS
    # =========================================================================

    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\brounded-\[\d+px\]"),
            category=Category.BORDER,
            severity=Severity.WARNING,
            rule="arbitrary-border-radius",
            message="Use design token border radius (rounded-sm, rounded-md, etc.)",
            fix_template=None,
        )
    )

    # =========================================================================
    # SHADOW PATTERNS
    # =========================================================================

    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\bshadow-\[[^\]]+\]"),
            category=Category.SHADOW,
            severity=Severity.WARNING,
            rule="arbitrary-shadow",
            message="Use design token shadow (shadow-sm, shadow-md, etc.)",
            fix_template=None,
        )
    )

    # =========================================================================
    # Z-INDEX PATTERNS
    # =========================================================================

    # Arbitrary z-index values (z-[100], z-[999])
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\bz-\[\d+\]"),
            category=Category.ZINDEX,
            severity=Severity.WARNING,
            rule="arbitrary-zindex",
            message="Use semantic z-index token (z-tooltip, z-dropdown, z-modal, etc.)",
            fix_template=None,
        )
    )

    # Raw Tailwind z-index values that should use semantic tokens per STYLE.md
    # z-10/20/30/40/50 should use z-tooltip, z-dropdown, z-panel, z-modal, etc.
    # Excludes z-0, z-auto, and negative values which are valid base utilities
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\bz-(10|20|30|40|50)\b"),
            category=Category.ZINDEX,
            severity=Severity.WARNING,
            rule="raw-zindex-value",
            message="Use semantic z-index token (z-tooltip, z-dropdown, z-panel, z-modal, z-notification, z-toast) per STYLE.md",
            fix_template=None,
        )
    )

    # =========================================================================
    # ANIMATION PATTERNS
    # =========================================================================

    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\bduration-\[\d+ms\]"),
            category=Category.ANIMATION,
            severity=Severity.WARNING,
            rule="arbitrary-duration",
            message="Use design token duration (duration-fast, duration-normal, etc.)",
            fix_template=None,
        )
    )

    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\bdelay-\[\d+ms\]"),
            category=Category.ANIMATION,
            severity=Severity.WARNING,
            rule="arbitrary-delay",
            message="Use design token delay values",
            fix_template=None,
        )
    )

    # =========================================================================
    # COMPONENT PATTERNS
    # =========================================================================

    # Button without explicit variant (defaults to primary, causing style conflicts)
    # Detects: <Button ... without variant="..." on same line
    # Excludes: Lines starting with * (JSDoc), // (comments)
    # This is a WARNING because not all cases are bugs, but many menu/list items
    # incorrectly use Button without variant, inheriting primary styling
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"^\s*(?!\s*\*|\s*//).*<Button\b(?![^>]*\bvariant=)[^>]*>"),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="button-missing-variant",
            message="Button without explicit variant defaults to 'primary'. Add variant='ghost' or 'secondary' for non-CTA buttons",
            fix_template=None,  # Requires manual review - context dependent
        )
    )

    # Multi-line Button without variant - catches <Button followed by type=
    # when variant= is NOT on the same line. Important for multi-line JSX.
    # Uses negative lookahead at start to reject lines that do have variant.
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<Button\s+type=(?!.*\bvariant=)"),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="button-missing-variant-multiline",
            message="Button without explicit variant defaults to 'primary'. Add variant='ghost' or 'secondary' for toolbar/icon buttons",
            fix_template=None,
        )
    )

    # Button with Cancel/Close/Back text without variant="secondary"
    # These buttons should have secondary variant for proper visual hierarchy
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<Button\b(?![^>]*\bvariant=)[^>]*>\s*(Cancel|Close|Back|Dismiss|No)\s*</Button>"),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="button-cancel-missing-secondary",
            message='Cancel/Close/Back buttons should use variant="secondary"',
            fix_template=None,  # Context-dependent - could add variant="secondary"
        )
    )

    # Button with Delete/Remove/Clear text without variant="danger"
    # These destructive actions should have danger variant
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<Button\b(?![^>]*\bvariant=)[^>]*>\s*(Delete|Remove|Clear|Destroy|Discard)\s*</Button>"),
            category=Category.COMPONENT,
            severity=Severity.ERROR,
            rule="button-destructive-missing-danger",
            message='Delete/Remove/Clear buttons MUST use variant="danger"',
            fix_template=None,  # Context-dependent
        )
    )

    # Button with className color override (bypassing variant system)
    # This is an anti-pattern - use the variant prop instead
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<Button\b[^>]*className=[^>]*\bbg-(warning|error|success|info|primary)-\d+"),
            category=Category.COMPONENT,
            severity=Severity.ERROR,
            rule="button-className-color-override",
            message="Use Button variant prop instead of className color override",
            fix_template=None,
        )
    )

    # Icon-only button missing size="icon" prop
    # Icon buttons (with single Lucide icon like <X size={14} />) should use size="icon"
    # for proper touch target sizing (44x44 minimum per WCAG 2.2)
    # Matches: <Button ...>...<IconName size={...} /></Button> without size="icon"
    # Pattern[str] handles single-letter icons (X, I) and multi-letter (Copy, ZoomIn, ChevronDown)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r'<Button\b(?![^>]*\bsize=["\']icon["\'])[^>]*>\s*<[A-Z][a-zA-Z0-9]*\s+size='),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="icon-button-missing-size-icon",
            message='Icon-only buttons should use size="icon" for proper touch target sizing',
            fix_template=None,  # Context-dependent - add size="icon"
        )
    )

    # Icon-only button missing aria-label (accessibility violation)
    # Icon buttons must have aria-label for screen readers
    patterns.append(
        ViolationPattern(
            regex=re.compile(r'<Button\b[^>]*size=["\']icon["\'][^>]*(?<!aria-label=)[^>]*>'),
            category=Category.COMPONENT,
            severity=Severity.ERROR,
            rule="icon-button-missing-aria-label",
            message="Icon-only buttons MUST have aria-label for accessibility (WCAG 2.1)",
            fix_template=None,  # Requires human-readable label
        )
    )

    # onClick on non-button elements (accessibility violation)
    # div/span with onClick should use Button or proper keyboard handling
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<(div|span)\b[^>]*\bonClick="),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="onclick-on-non-button",
            message="Consider using Button component instead of div/span with onClick for keyboard accessibility",
            fix_template=None,
        )
    )

    # Toggle/Checkbox without label association
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<(Toggle|Checkbox)\b[^>]*(?<!\bid=)[^>]*/>"),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="form-control-missing-label",
            message="Toggle/Checkbox should have an associated label for accessibility",
            fix_template=None,
        )
    )

    # Input with redundant text-neutral-12 class (already in Input default variant)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<Input\b[^>]*className=[^>]*\btext-neutral-12\b"),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="input-redundant-text-color",
            message="Remove redundant text-neutral-12 - Input default variant already provides this",
            fix_template=None,
        )
    )

    # Input with redundant focus:ring-primary-* class (already in Input default variant)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<Input\b[^>]*className=[^>]*\bfocus:ring-primary-\d+"),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="input-redundant-focus-ring",
            message="Remove redundant focus:ring-primary-* - Input default variant already provides focus styling",
            fix_template=None,
        )
    )

    # Select with redundant text-neutral-* class (Select component provides this)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<Select\b[^>]*className=[^>]*\btext-neutral-\d+"),
            category=Category.COMPONENT,
            severity=Severity.INFO,
            rule="select-redundant-text-color",
            message="Consider removing text-neutral-* - Select component provides text color",
            fix_template=None,
        )
    )

    # Dropdown menu without semantic z-index token
    # Catches: shadow-lg z-10 but not shadow-lg z-dropdown/z-modal
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"shadow-lg\s+z-(?:10|20|30|40|50)\b"),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="dropdown-missing-semantic-zindex",
            message="Dropdown menus should use z-dropdown semantic token instead of raw z-index",
            fix_template=None,
        )
    )

    # =========================================================================
    # FIELD SIZING CONSISTENCY PATTERNS
    # Design system components (Input, Select, Textarea) use size prop (sm, md, lg)
    # Do not override sizing via className - use size prop for consistency
    # =========================================================================

    # Input with className overriding padding (should use size prop)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<Input\b[^>]*className=[^>]*\b(py-\d+|px-\d+|p-\d+)\b"),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="input-padding-override",
            message="Use Input size prop (sm, md, lg) instead of className padding override",
            fix_template=None,
        )
    )

    # Input with className overriding text size (should use size prop)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<Input\b[^>]*className=[^>]*\btext-(xs|sm|base|lg|xl)\b"),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="input-text-size-override",
            message="Use Input size prop (sm, md, lg) instead of className text-size override",
            fix_template=None,
        )
    )

    # Input with className overriding height (should use size prop)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<Input\b[^>]*className=[^>]*\bh-\d+\b"),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="input-height-override",
            message="Use Input size prop (sm, md, lg) instead of className height override",
            fix_template=None,
        )
    )

    # Select with className overriding padding (should use size prop)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<Select\b[^>]*className=[^>]*\b(py-\d+|px-\d+|p-\d+)\b"),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="select-padding-override",
            message="Use Select size prop (sm, md, lg) instead of className padding override",
            fix_template=None,
        )
    )

    # Select with className overriding text size (should use size prop)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<Select\b[^>]*className=[^>]*\btext-(xs|sm|base|lg|xl)\b"),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="select-text-size-override",
            message="Use Select size prop (sm, md, lg) instead of className text-size override",
            fix_template=None,
        )
    )

    # Select with className overriding height (should use size prop)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<Select\b[^>]*className=[^>]*\bh-\d+\b"),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="select-height-override",
            message="Use Select size prop (sm, md, lg) instead of className height override",
            fix_template=None,
        )
    )

    # Textarea with className overriding padding (should use size prop)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<Textarea\b[^>]*className=[^>]*\b(py-\d+|px-\d+|p-\d+)\b"),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="textarea-padding-override",
            message="Use Textarea size prop (sm, md, lg) instead of className padding override",
            fix_template=None,
        )
    )

    # Textarea with className overriding text size (should use size prop)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<Textarea\b[^>]*className=[^>]*\btext-(xs|sm|base|lg|xl)\b"),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="textarea-text-size-override",
            message="Use Textarea size prop (sm, md, lg) instead of className text-size override",
            fix_template=None,
        )
    )

    # Textarea with className overriding height (should use size prop)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<Textarea\b[^>]*className=[^>]*\bh-\d+\b"),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="textarea-height-override",
            message="Use Textarea size prop (sm, md, lg) instead of className height override",
            fix_template=None,
        )
    )

    # Raw input with arbitrary sizing classes (should use Input component)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<input\b[^>]*className=[^>]*\b(py-\[|px-\[|h-\[)"),
            category=Category.COMPONENT,
            severity=Severity.ERROR,
            rule="raw-input-arbitrary-sizing",
            message="Use Input component with size prop instead of raw <input> with arbitrary sizing",
            fix_template=None,
        )
    )

    # Raw select with arbitrary sizing classes (should use Select component)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<select\b[^>]*className=[^>]*\b(py-\[|px-\[|h-\[)"),
            category=Category.COMPONENT,
            severity=Severity.ERROR,
            rule="raw-select-arbitrary-sizing",
            message="Use Select component with size prop instead of raw <select> with arbitrary sizing",
            fix_template=None,
        )
    )

    # Raw textarea with arbitrary sizing classes (should use Textarea component)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<textarea\b[^>]*className=[^>]*\b(py-\[|px-\[|h-\[)"),
            category=Category.COMPONENT,
            severity=Severity.ERROR,
            rule="raw-textarea-arbitrary-sizing",
            message="Use Textarea component with size prop instead of raw <textarea> with arbitrary sizing",
            fix_template=None,
        )
    )

    # SearchInput has hardcoded sizing - should accept size prop
    # Note: SearchInput component itself needs refactoring, this pattern catches usage issues
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<SearchInput\b[^>]*className=[^>]*\b(py-|px-|h-|text-)"),
            category=Category.COMPONENT,
            severity=Severity.WARNING,
            rule="searchinput-sizing-override",
            message="Avoid overriding SearchInput sizing via className - component uses fixed md sizing",
            fix_template=None,
        )
    )

    # =========================================================================
    # FOCUS PATTERNS (WCAG 2.4.7, 2.4.11, 2.4.13)
    # =========================================================================

    # outline-none without any visible focus indicator
    # Accept: focus:ring-*, focus-visible:ring-*, focus:bg-*, focus:border-* as valid
    # All of these provide visible focus indication for WCAG 2.4.7
    patterns.append(
        ViolationPattern(
            regex=re.compile(r'\boutline-none\b(?![^"\']*(?:focus-visible|focus):(?:ring|bg-|border-))'),
            category=Category.FOCUS,
            severity=Severity.ERROR,
            rule="outline-none-without-focus-indicator",
            message="outline-none MUST be paired with visible focus indicator (ring, bg, or border) (WCAG 2.4.7)",
            fix_template=None,  # Context-dependent fix
        )
    )

    # focus:outline-none without any visible focus indicator
    # Accept ring, background, or border changes as valid focus indicators
    patterns.append(
        ViolationPattern(
            regex=re.compile(r'\bfocus:outline-none\b(?![^"\']*(?:focus-visible:ring|focus:(?:ring|bg-|border-)))'),
            category=Category.FOCUS,
            severity=Severity.ERROR,
            rule="focus-outline-none-without-indicator",
            message="focus:outline-none MUST be paired with visible focus indicator (WCAG 2.4.7)",
            fix_template=None,
        )
    )

    # Missing focus-visible on interactive elements (Button, Link, Input without it)
    # NOTE: Disabled - too many false positives. The outline-none patterns above are more precise.
    # This pattern was intended to catch elements without focus styles, but the regex doesn't
    # correctly handle negative lookaheads for class content.
    # patterns.append(ViolationPattern(
    #     regex=re.compile(r'<(button|a|input)\b[^>]*className=[^>]*(?!focus-visible)[^>]*>'),
    #     category=Category.FOCUS,
    #     severity=Severity.INFO,
    #     rule="missing-focus-visible",
    #     message="Consider adding focus-visible:ring-* for keyboard accessibility",
    #     fix_template=None,
    # ))

    # =========================================================================
    # TOUCH TARGET PATTERNS (WCAG 2.5.8)
    # =========================================================================

    # Interactive elements with height below 24px (fails WCAG 2.5.8 AA)
    # Matches arbitrary values 1-23px like h-[20px], h-[18px], min-h-[22px]
    # Pattern[str]: [1-9] for 1-9, 1[0-9] for 10-19, 2[0-3] for 20-23
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\b(?:min-)?h-\[([1-9]|1[0-9]|2[0-3])px\]"),
            category=Category.TOUCH,
            severity=Severity.WARNING,
            rule="touch-target-below-24px",
            message="Touch target below 24px may fail WCAG 2.5.8 (AA requires 24x24 minimum)",
            fix_template=None,
        )
    )

    # Using h-5 (20px) or smaller on interactive elements
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<(Button|button|a|input)\b[^>]*className=[^>]*\bh-[1-5]\b"),
            category=Category.TOUCH,
            severity=Severity.WARNING,
            rule="small-interactive-height",
            message="Interactive element with h-5 or smaller may fail WCAG 2.5.8 touch target requirements",
            fix_template=None,
        )
    )

    # Icon buttons without adequate size (size="icon" should have min-h-8 or min-h-touch)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r'<Button\b[^>]*size=["\']icon["\'][^>]*(?<!min-h-)[^>]*>'),
            category=Category.TOUCH,
            severity=Severity.INFO,
            rule="icon-button-size-check",
            message="Icon button should have min-h-8 (32px) for desktop or min-h-touch (44px) for mobile",
            fix_template=None,
        )
    )

    # =========================================================================
    # ARIA PATTERNS
    # =========================================================================

    # Clickable div without role="button" or tabIndex
    patterns.append(
        ViolationPattern(
            regex=re.compile(r'<div\b[^>]*onClick=[^>]*(?<!role=["\']button["\'])[^>]*>'),
            category=Category.ARIA,
            severity=Severity.WARNING,
            rule="clickable-div-missing-role",
            message='div with onClick should have role="button" and tabIndex={0} for accessibility',
            fix_template=None,
        )
    )

    # Loading state without aria-busy (JSX conditionals only, not type declarations)
    # Matches: isLoading && (...) or isLoading ? ... : ...
    # Excludes: isLoading?: boolean; (type declarations)
    # NOTE: INFO level because parent/container may have aria-busy - hard to verify statically
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\bisLoading\s*&&\s*[(<]"),
            category=Category.ARIA,
            severity=Severity.INFO,
            rule="loading-missing-aria-busy",
            message='Verify aria-busy="true" is on container for screen reader announcements',
            fix_template=None,
        )
    )
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"\bisLoading\s*\?\s*[(<]"),
            category=Category.ARIA,
            severity=Severity.INFO,
            rule="loading-missing-aria-busy-ternary",
            message='Verify aria-busy="true" is on container for screen reader announcements',
            fix_template=None,
        )
    )

    # Skeleton component without aria-hidden on decorative elements
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<(?:Skeleton|div[^>]*animate-shimmer)[^>]*(?<!aria-hidden)[^>]*>"),
            category=Category.ARIA,
            severity=Severity.INFO,
            rule="skeleton-missing-aria-hidden",
            message='Skeleton shimmer decorations should use aria-hidden="true"',
            fix_template=None,
        )
    )

    # Progress bar without role="progressbar"
    # NOTE: INFO level because static analysis cannot reliably detect if parent has role
    # Inner fill divs often have "progress-fill" class but role is correctly on parent
    # Pattern[str] excludes common fill patterns: progress-fill, progress-bar-fill, progressColor
    patterns.append(
        ViolationPattern(
            regex=re.compile(
                r'className=[^>]*(?<![\-])progress(?!-(?:fill|bar-fill|Color))[^>]*(?<!role=["\']progressbar["\'])'
            ),
            category=Category.ARIA,
            severity=Severity.INFO,
            rule="progress-missing-role",
            message='Verify progress indicators have role="progressbar" on container with aria-valuenow',
            fix_template=None,
        )
    )

    # Dialog/Modal without aria-modal
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"<(?:Dialog|Modal)\b[^>]*(?<!aria-modal)[^>]*>"),
            category=Category.ARIA,
            severity=Severity.INFO,
            rule="dialog-missing-aria-modal",
            message='Consider adding aria-modal="true" for modal dialogs',
            fix_template=None,
        )
    )

    # =========================================================================
    # REDUCED MOTION PATTERNS (WCAG 2.3.3 - AAA level, recommended but not blocking)
    # Per STYLE.md: AAA compliance is aspirational, not blocking for merge.
    # =========================================================================

    # animate-* without motion-safe variant or prefersReducedMotion check
    # Accept: motion-safe:, motion-reduce:, or prefersReducedMotion conditional
    # Note: prefersReducedMotion filtering is done in check_file() by checking the whole line
    # INFO level: AAA requirement, not AA-blocking
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"(?<!motion-safe:)(?<!motion-reduce:)\banimate-(?!none)[a-z]+\b"),
            category=Category.MOTION,
            severity=Severity.INFO,
            rule="animation-without-motion-safe",
            message="Consider wrapping animation with motion-safe: or prefersReducedMotion check for reduced motion users (WCAG 2.3.3 AAA)",
            fix_template=None,
        )
    )

    # transition-* without motion consideration (INFO level - many are fine)
    patterns.append(
        ViolationPattern(
            regex=re.compile(r'\btransition-(?!none)[a-z]+\b.*\bduration-[a-z0-9-]+\b(?![^"\']*motion-)'),
            category=Category.MOTION,
            severity=Severity.INFO,
            rule="transition-without-motion-safe",
            message="Long transitions should respect reduced motion preference",
            fix_template=None,
        )
    )

    # Motion.dev animation without useReducedMotion check (harder to detect statically)
    # This is a soft check for files importing motion but not useReducedMotion
    patterns.append(
        ViolationPattern(
            regex=re.compile(r'from\s+["\']motion/react["\'](?![^}]+useReducedMotion)'),
            category=Category.MOTION,
            severity=Severity.INFO,
            rule="motion-without-reduced-motion-hook",
            message="Consider using useReducedMotion() hook from motion/react for accessibility",
            fix_template=None,
        )
    )

    # Shimmer/pulse animations that should be disabled for reduced motion
    # Accept: motion-reduce:, motion-safe:, or prefersReducedMotion conditional
    # INFO level: While looping animations are more problematic, WCAG 2.3.3 is AAA level
    # and per STYLE.md, AAA is aspirational, not blocking for merge.
    patterns.append(
        ViolationPattern(
            regex=re.compile(r"(?<!motion-safe:)(?<!motion-reduce:)\banimate-(?:shimmer|pulse|spin|bounce)\b"),
            category=Category.MOTION,
            severity=Severity.INFO,
            rule="looping-animation-without-motion-reduce",
            message="Looping animations (shimmer, pulse, spin, bounce) should respect reduced motion preference (WCAG 2.3.3 AAA)",
            fix_template=None,
        )
    )

    return patterns


# Compile patterns once at import time
ALL_PATTERNS = _build_patterns()


# =============================================================================
# File Processing
# =============================================================================


def should_skip(path: Path) -> bool:
    """Check if path should be skipped."""
    if any(skip in path.parts for skip in SKIP_DIRS):
        return True
    if path.name in SKIP_FILES:
        return True
    return False


def check_file(
    file_path: Path,
    patterns: list[ViolationPattern],
    skip_tests: bool = True,
    skip_stories: bool = True,
) -> list[Violation]:
    """Check a single file for violations."""
    # Skip test and story files if requested
    if skip_tests and ".test." in file_path.name:
        return []
    if skip_stories and ".stories." in file_path.name:
        return []

    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception:
        return []

    violations = []
    lines = content.splitlines()

    for line_no, line in enumerate(lines, 1):
        # Skip comments
        stripped = line.strip()
        if stripped.startswith("//") or stripped.startswith("/*"):
            continue

        for pattern in patterns:
            for match in pattern.regex.finditer(line):
                # Skip motion violations when prefersReducedMotion is on the same line
                # This handles the pattern: !prefersReducedMotion && "animate-spin"
                if pattern.category == Category.MOTION and "prefersReducedMotion" in line:
                    continue

                violations.append(
                    Violation(
                        file=file_path,
                        line_no=line_no,
                        column=match.start() + 1,
                        category=pattern.category,
                        severity=pattern.severity,
                        rule=pattern.rule,
                        match=match.group(),
                        message=pattern.message,
                        fix=pattern.fix_template,
                    )
                )

    return violations


def fix_file(file_path: Path, patterns: list[ViolationPattern], dry_run: bool = False) -> dict[str, Any]:
    """Fix violations in a file. Returns stats."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except Exception as e:
        return {"error": str(e)}

    original = content
    replacements: dict[str, int] = defaultdict(int)

    for pattern in patterns:
        # Handle fix_fn (custom function-based fixes)
        if pattern.fix_fn is not None:
            matches = list(pattern.regex.finditer(content))
            if matches:
                replacements[pattern.rule] += len(matches)
                # Apply fix_fn to each match (process in reverse to preserve positions)
                for match in reversed(matches):
                    fixed = pattern.fix_fn(match.group())
                    content = content[: match.start()] + fixed + content[match.end() :]
        # Handle fix_template (simple string replacement)
        elif pattern.fix_template is not None:
            matches = pattern.regex.findall(content)
            if matches:
                replacements[pattern.rule] += len(matches)
                content = pattern.regex.sub(pattern.fix_template, content)

    if content != original:
        if not dry_run:
            file_path.write_text(content, encoding="utf-8")
        return {"modified": True, "replacements": dict(replacements)}

    return {"modified": False}


# =============================================================================
# Subcommands
# =============================================================================


def cmd_check(args: argparse.Namespace) -> int:
    """Quick check for pre-commit. Exits on first blocking error."""
    if args.files:
        files = [Path(f) for f in args.files if Path(f).suffix in EXTENSIONS]
    else:
        files = list(FRONTEND_SRC.rglob("*.tsx")) + list(FRONTEND_SRC.rglob("*.ts"))

    files = [f for f in files if f.exists() and not should_skip(f)]

    # Filter patterns to only blocking (ERROR severity)
    blocking_patterns = [p for p in ALL_PATTERNS if p.severity == Severity.ERROR]

    blocking_violations = []

    for file_path in files:
        violations = check_file(file_path, blocking_patterns, skip_tests=True, skip_stories=True)
        blocking = [v for v in violations if v.severity == Severity.ERROR]
        if blocking:
            blocking_violations.extend(blocking)
            if not args.all:  # Early exit unless --all specified
                break

    if blocking_violations:
        print(f"\n❌ Design System Violations ({len(blocking_violations)} blocking):\n", file=sys.stderr)
        for v in blocking_violations[:10]:  # Show first 10
            print(f"  {v.file}:{v.line_no}:{v.column}", file=sys.stderr)
            print(f"    [{v.rule}] {v.match}", file=sys.stderr)
            print(f"    {v.message}", file=sys.stderr)
            if v.fix:
                print(f"    Fix: {v.fix}", file=sys.stderr)

        if len(blocking_violations) > 10:
            print(f"\n  ... and {len(blocking_violations) - 10} more violations", file=sys.stderr)

        print("\nRun 'python scripts/design-system.py fix' to auto-fix.", file=sys.stderr)
        return 1

    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    """Comprehensive audit with detailed report."""
    files = list(FRONTEND_SRC.rglob("*.tsx")) + list(FRONTEND_SRC.rglob("*.ts"))
    files = [f for f in files if f.exists() and not should_skip(f)]

    # Filter by category if specified
    patterns = ALL_PATTERNS
    if args.category and args.category != "all":
        cat = Category(args.category)
        patterns = [p for p in patterns if p.category == cat]

    all_violations: list[Violation] = []
    for file_path in files:
        violations = check_file(file_path, patterns, skip_tests=not args.include_tests, skip_stories=True)
        all_violations.extend(violations)

    # Group by category and severity
    by_category: dict[Category, list[Violation]] = defaultdict(list)
    by_severity: dict[Severity, int] = defaultdict(int)

    for v in all_violations:
        by_category[v.category].append(v)
        by_severity[v.severity] += 1

    # Print report
    print("\n" + "=" * 60)
    print("DESIGN SYSTEM AUDIT REPORT")
    print("=" * 60)
    print(f"\nFiles scanned: {len(files)}")
    print(f"Total violations: {len(all_violations)}")
    print(f"  Errors: {by_severity[Severity.ERROR]}")
    print(f"  Warnings: {by_severity[Severity.WARNING]}")
    print(f"  Info: {by_severity[Severity.INFO]}")

    print("\nBy Category:")
    for cat in Category:
        count = len(by_category[cat])
        if count > 0:
            print(f"  {cat.value}: {count}")

    if args.verbose:
        print("\nDetailed Violations:")
        for cat, violations in sorted(by_category.items(), key=lambda x: -len(x[1])):
            if violations:
                print(f"\n[{cat.value.upper()}]")
                for v in violations[:20]:  # Limit per category
                    print(f"  {v.file.name}:{v.line_no} [{v.rule}] {v.match}")

    if args.strict and by_severity[Severity.ERROR] > 0:
        return 1

    return 0


def cmd_fix(args: argparse.Namespace) -> int:
    """Auto-fix violations in place."""
    files = list(FRONTEND_SRC.rglob("*.tsx")) + list(FRONTEND_SRC.rglob("*.ts"))
    files = [f for f in files if f.exists() and not should_skip(f)]

    # Filter by category if specified
    patterns = ALL_PATTERNS
    if args.category and args.category != "all":
        cat = Category(args.category)
        patterns = [p for p in patterns if p.category == cat]

    # Only include patterns with fixes (either fix_template or fix_fn)
    fixable_patterns = [p for p in patterns if p.fix_template is not None or p.fix_fn is not None]

    total_replacements: dict[str, int] = defaultdict(int)
    files_modified = 0

    for file_path in files:
        result = fix_file(file_path, fixable_patterns, dry_run=args.dry_run)
        if result.get("modified"):
            files_modified += 1
            for rule, count in result.get("replacements", {}).items():
                total_replacements[rule] += count

    # Print summary
    print(f"\n{'[DRY RUN] ' if args.dry_run else ''}Design System Fix Summary")
    print("=" * 60)
    print(f"Files modified: {files_modified}")
    print(f"Total replacements: {sum(total_replacements.values())}")

    if total_replacements:
        print("\nBy rule:")
        for rule, count in sorted(total_replacements.items(), key=lambda x: -x[1]):
            print(f"  {rule}: {count}")

    if args.dry_run and total_replacements:
        print("\nRun without --dry-run to apply changes.")

    return 0


def cmd_report(args: argparse.Namespace) -> int:
    """Generate compliance report."""
    files = list(FRONTEND_SRC.rglob("*.tsx")) + list(FRONTEND_SRC.rglob("*.ts"))
    files = [f for f in files if f.exists() and not should_skip(f)]

    all_violations: list[Violation] = []
    for file_path in files:
        violations = check_file(file_path, ALL_PATTERNS, skip_tests=True, skip_stories=True)
        all_violations.extend(violations)

    by_severity: dict[str, int] = defaultdict(int)
    by_category: dict[str, int] = defaultdict(int)
    by_rule: dict[str, int] = defaultdict(int)

    for v in all_violations:
        by_severity[v.severity.value] += 1
        by_category[v.category.value] += 1
        by_rule[v.rule] += 1

    report = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "files_scanned": len(files),
        "total_violations": len(all_violations),
        "by_severity": dict(by_severity),
        "by_category": dict(by_category),
        "top_rules": dict(sorted(by_rule.items(), key=lambda x: -x[1])[:10]),
        "compliant": by_severity.get("error", 0) == 0,
    }

    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print("# Design System Compliance Report\n")
        print(f"**Generated:** {report['timestamp']}")
        print(f"**Files Scanned:** {report['files_scanned']}")
        print(f"**Compliant:** {'Yes' if report['compliant'] else 'No'}\n")
        print("## Summary\n")
        print("| Severity | Count |")
        print("|----------|-------|")
        for sev, count in report["by_severity"].items():
            print(f"| {sev} | {count} |")

    return 0


# =============================================================================
# Main Entry Point
# =============================================================================


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Unified Design System Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # check subcommand
    check_parser = subparsers.add_parser("check", help="Quick validation for pre-commit")
    check_parser.add_argument("files", nargs="*", help="Files to check (default: all)")
    check_parser.add_argument("--all", action="store_true", help="Show all violations (don't early exit)")

    # audit subcommand
    audit_parser = subparsers.add_parser("audit", help="Comprehensive audit")
    audit_parser.add_argument("--category", choices=[c.value for c in Category] + ["all"], default="all")
    audit_parser.add_argument("--strict", action="store_true", help="Exit 1 if any errors")
    audit_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed violations")
    audit_parser.add_argument("--include-tests", action="store_true", help="Include test files")

    # fix subcommand
    fix_parser = subparsers.add_parser("fix", help="Auto-fix violations")
    fix_parser.add_argument("--dry-run", action="store_true", help="Preview without modifying")
    fix_parser.add_argument("--category", choices=[c.value for c in Category] + ["all"], default="all")

    # report subcommand
    report_parser = subparsers.add_parser("report", help="Generate compliance report")
    report_parser.add_argument("--format", choices=["json", "md"], default="md")

    args = parser.parse_args()

    commands = {
        "check": cmd_check,
        "audit": cmd_audit,
        "fix": cmd_fix,
        "report": cmd_report,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
