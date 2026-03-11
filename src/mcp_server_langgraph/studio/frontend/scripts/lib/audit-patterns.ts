/**
 * Design System Audit Patterns
 *
 * Pattern definitions, categorization, and auto-fix mappings for the design
 * system audit tool. This module is imported by audit-design-system.ts and
 * tested by tests/scripts/audit-patterns.test.ts.
 */

// =============================================================================
// Types
// =============================================================================

export type ViolationCategory =
  | "sizing"
  | "color"
  | "spacing"
  | "typography"
  | "border"
  | "shadow"
  | "zindex"
  | "animation"
  | "component"
  | "testid";

export type ViolationSeverity = "error" | "warning" | "info";

// =============================================================================
// Ripgrep Patterns
// =============================================================================

export const RIPGREP_PATTERNS: Record<ViolationCategory, string[]> = {
  sizing: [
    "h-\\[[0-9]+(px|rem)\\]",
    "w-\\[[0-9]+(px|rem)\\]",
    "size-\\[[0-9]+\\]",
    "min-h-\\[[0-9]+(px|rem)\\]",
    "max-h-\\[[0-9]+(px|rem)\\]",
    "min-w-\\[[0-9]+(px|rem)\\]",
    "max-w-\\[[0-9]+(px|rem)\\]",
  ],
  color: [
    "(bg|text|border)-(blue|red|green|yellow|purple|pink|indigo|teal|cyan|orange|lime|emerald|violet|fuchsia|rose|amber|sky)-(50|100|200|300|400|500|600|700|800|900|950)",
    "neutral-(50|100|200|300|400|500|600|700|800|900|950)",
    "(bg|text|border)-(gray|slate|zinc|stone)-(50|100|200|300|400|500|600|700|800|900|950)",
  ],
  spacing: [
    "(m|p)(t|b|l|r|x|y)?-\\[[0-9]+(px|rem)\\]",
    "gap-\\[[0-9]+(px|rem)\\]",
    "space-(x|y)-\\[[0-9]+(px|rem)\\]",
  ],
  typography: [
    "text-\\[[0-9.]+(?:px|rem)\\]",
    "leading-\\[[0-9.]+\\]",
    "tracking-\\[[0-9.]+(?:em|rem)\\]",
  ],
  border: [
    "rounded-\\[[0-9]+(px|rem)\\]",
    "border-\\[[0-9]+(px)\\]",
  ],
  shadow: [
    "shadow-\\[[^\\]]+rgba\\([^)]+\\)[^\\]]*\\]",
  ],
  zindex: [
    "z-\\[[0-9]+\\]",
    "z-index:\\s*[0-9]+",
  ],
  animation: [
    "duration-\\[[0-9]+(ms|s)\\]",
    "delay-\\[[0-9]+(ms|s)\\]",
    "transition:\\s*all\\s+[0-9]+(ms|s)",
  ],
  component: [
    // Primary variant with menu/dropdown roles (variant first)
    '<Button[^>]*variant="primary"[^>]*role="(option|menuitem|menuitemradio|menuitemcheckbox)"',
    // Primary variant with menu/dropdown roles (role first)
    '<Button[^>]*role="(option|menuitem|menuitemradio|menuitemcheckbox)"[^>]*variant="primary"',
    // Primary variant in navigation list items (variant first)
    '<Button[^>]*variant="primary"[^>]*(className="[^"]*w-full[^"]*text-left[^"]*"|className="[^"]*text-left[^"]*w-full[^"]*")',
    // Primary variant in navigation list items (className first)
    '<Button[^>]*className="[^"]*(w-full[^"]*text-left|text-left[^"]*w-full)[^"]*"[^>]*variant="primary"',
  ],
  testid: [
    // Detect camelCase test IDs (should be kebab-case per convention)
    'data-testid="[a-z]+[A-Z][a-zA-Z]*"',
  ],
};

// =============================================================================
// Exclusion Patterns
// =============================================================================

export const EXCLUSION_PATTERNS: string[] = [
  "**/*.test.tsx",
  "**/*.test.ts",
  "**/*.spec.tsx",
  "**/*.spec.ts",
  "**/*.stories.tsx",
  "**/*.stories.ts",
  "**/dist/**",
  "**/build/**",
  "**/node_modules/**",
  "**/.vite/**",
  "**/design-system/**",
  "**/radix-colors.ts",
  "**/tailwind.config.ts",
  "**/__mocks__/**",
];

// =============================================================================
// Severity Mapping
// =============================================================================

export function getSeverity(category: ViolationCategory): ViolationSeverity {
  switch (category) {
    case "color":
      return "error";
    case "sizing":
    case "spacing":
    case "zindex":
    case "typography":
      return "warning";
    case "shadow":
    case "border":
    case "animation":
    case "component":
      return "info";
  }
}

// =============================================================================
// Categorization
// =============================================================================

export function categorizeViolation(match: string): ViolationCategory | null {
  // Sizing
  if (
    /[hw]-\[[0-9]+(px|rem)\]/.test(match) ||
    /size-\[[0-9]+\]/.test(match) ||
    /min-[hw]-\[[0-9]+(px|rem)\]/.test(match) ||
    /max-[hw]-\[[0-9]+(px|rem)\]/.test(match)
  ) {
    return "sizing";
  }

  // Color
  if (
    /(bg|text|border)-(blue|red|green|yellow|purple|pink|indigo|teal|cyan|orange|lime|emerald|violet|fuchsia|rose|amber|sky)-(50|100|200|300|400|500|600|700|800|900|950)/.test(
      match
    ) ||
    /neutral-(50|100|200|300|400|500|600|700|800|900|950)/.test(match) ||
    /(bg|text|border)-(gray|slate|zinc|stone)-(50|100|200|300|400|500|600|700|800|900|950)/.test(
      match
    )
  ) {
    return "color";
  }

  // Spacing
  if (
    /(m|p)(t|b|l|r|x|y)?-\[[0-9]+(px|rem)\]/.test(match) ||
    /gap-\[[0-9]+(px|rem)\]/.test(match)
  ) {
    return "spacing";
  }

  // Typography
  if (
    /text-\[[0-9]+(px|rem)\]/.test(match) ||
    /leading-\[[0-9.]+\]/.test(match) ||
    /tracking-\[[0-9.]+(em|rem)\]/.test(match)
  ) {
    return "typography";
  }

  // Border
  if (/rounded-\[[0-9]+(px|rem)\]/.test(match) || /border-\[[0-9]+(px)\]/.test(match)) {
    return "border";
  }

  // Shadow
  if (/shadow-\[[^\]]+rgba\([^)]+\)[^\]]*\]/.test(match)) {
    return "shadow";
  }

  // Z-index
  if (/z-\[[0-9]+\]/.test(match) || /z-index:\s*[0-9]+/.test(match)) {
    return "zindex";
  }

  // Animation
  if (
    /duration-\[[0-9]+(ms|s)\]/.test(match) ||
    /delay-\[[0-9]+(ms|s)\]/.test(match) ||
    /transition:\s*all\s+[0-9]+(ms|s)/.test(match)
  ) {
    return "animation";
  }

  // Component (primary variant violations in menu/nav contexts)
  if (
    /<Button[^>]*variant="primary"[^>]*role="(option|menuitem|menuitemradio|menuitemcheckbox)"/.test(
      match
    ) ||
    /<Button[^>]*role="(option|menuitem|menuitemradio|menuitemcheckbox)"[^>]*variant="primary"/.test(
      match
    ) ||
    /<Button[^>]*variant="primary"[^>]*(className="[^"]*w-full[^"]*text-left[^"]*"|className="[^"]*text-left[^"]*w-full[^"]*")/.test(
      match
    ) ||
    /<Button[^>]*className="[^"]*(w-full[^"]*text-left|text-left[^"]*w-full)[^"]*"[^>]*variant="primary"/.test(
      match
    )
  ) {
    return "component";
  }

  // Test ID (camelCase instead of kebab-case)
  if (/data-testid="[a-z]+[A-Z][a-zA-Z]*"/.test(match)) {
    return "testid";
  }

  return null;
}

// =============================================================================
// Suggestions
// =============================================================================

export function getSuggestion(match: string, category: ViolationCategory): string {
  switch (category) {
    case "color":
      if (/neutral-(50|100|200|300|400|500|600|700|800|900|950)/.test(match)) {
        return "Use Radix neutral scale (neutral-1 to neutral-12)";
      }
      if (/(bg|text|border)-(gray|slate|zinc|stone)-/.test(match)) {
        return "Use semantic color tokens or Radix neutral scale";
      }
      return "Use semantic color tokens (primary-*, success-*, danger-*, etc.)";
    case "sizing":
      return "Use Tailwind spacing scale (h-4, w-8, etc.) instead of arbitrary values";
    case "spacing":
      return "Use Tailwind spacing scale (p-4, m-2, gap-6, etc.)";
    case "typography":
      return "Use Tailwind typography scale (text-sm, text-base, text-lg, etc.)";
    case "component":
      if (/role="(option|menuitem|menuitemradio|menuitemcheckbox)"/.test(match)) {
        return 'Use variant="ghost" for menu items and dropdown options';
      }
      if (/(w-full[^"]*text-left|text-left[^"]*w-full)/.test(match)) {
        return 'Use variant="ghost" for navigation list items';
      }
      return "Follow component variant guidelines in STYLE.md";
    case "testid":
      return 'Use kebab-case for data-testid values (e.g., "file-upload-button" not "fileUploadButton")';
    default:
      return "Use Tailwind design tokens instead of arbitrary values";
  }
}

// =============================================================================
// Legitimate Pattern Filters
// =============================================================================

export function isLegitimateSizing(context: string): boolean {
  return (
    // SVG/canvas dimensions
    /viewBox|canvas|Chart|<svg|<img|<Image|<video/.test(context) ||
    // Component width/height props
    /(width|height)=\{[0-9]+\}/.test(context) ||
    // CSS custom properties
    /var\(--/.test(context) ||
    // calc expressions
    /calc\(/.test(context) ||
    // Viewport-based sizing
    /[hw]-\[[0-9]+(vh|vw)\]/.test(context) ||
    /max-[hw]-\[[0-9]+(vh|vw)\]/.test(context) ||
    /min-[hw]-\[[0-9]+(vh|vw)\]/.test(context) ||
    // Small functional widths (dividers, borders)
    /[hw]-\[(1|2|4)px\]/.test(context) ||
    // Workflow node widths
    (/(LLMNode|ApprovalNode|ConditionalNode|ToolNode|StartNode|EndNode)/.test(context) &&
      /w-\[180px\]/.test(context)) ||
    // Dialog/modal heights (match Dialog, Modal, or OnboardingModal)
    (/(Dialog|Modal|Drawer|OnboardingModal)/.test(context) &&
      /[hw]-\[(400px|500px|600px|90vh)\]/.test(context)) ||
    // Artifact viewer heights
    (/(MermaidArtifact|JSONViewer|CodeViewer)/.test(context) &&
      /h-\[(400|600)px\]/.test(context)) ||
    // Common layout widths
    /w-\[(200|300|320|400|500|600|800)px\]/.test(context)
  );
}

export function isLegitimateSpacing(context: string): boolean {
  return (
    // Negative margins
    /-m(t|b|l|r|x|y)?-\[/.test(context) ||
    // CSS custom properties
    /var\(--/.test(context) ||
    // calc expressions
    /calc\(/.test(context) ||
    // transform/translate
    /(transform|translate)/.test(context) ||
    // Viewport-based spacing
    /p(t|b|l|r|x|y)?-\[[0-9]+(vh|vw)\]/.test(context) ||
    // Command palette padding
    /(AICommandPalette|GenericCommandPalette)[^>]*pt-\[20vh\]/.test(context)
  );
}

export function isLegitimateBorder(context: string): boolean {
  return (
    // CSS custom properties
    /var\(--/.test(context) ||
    // calc expressions
    /calc\(/.test(context)
  );
}

export function isLegitimateComponent(context: string): boolean {
  // Check for primary variant violations in menu/dropdown contexts
  const hasPrimaryWithMenuRole =
    /<Button[^>]*variant="primary"[^>]*role="(option|menuitem|menuitemradio|menuitemcheckbox)"/.test(
      context
    ) ||
    /<Button[^>]*role="(option|menuitem|menuitemradio|menuitemcheckbox)"[^>]*variant="primary"/.test(
      context
    );

  // Check for primary variant violations in navigation list items
  const hasPrimaryWithNavLayout =
    /<Button[^>]*variant="primary"[^>]*(className="[^"]*w-full[^"]*text-left[^"]*"|className="[^"]*text-left[^"]*w-full[^"]*")/.test(
      context
    ) ||
    /<Button[^>]*className="[^"]*(w-full[^"]*text-left|text-left[^"]*w-full)[^"]*"[^>]*variant="primary"/.test(
      context
    );

  // Return false if violations found, true otherwise
  return !hasPrimaryWithMenuRole && !hasPrimaryWithNavLayout;
}

// =============================================================================
// Auto-Fix Mappings
// =============================================================================

export interface AutoFixMapping {
  pattern: RegExp;
  replacement: string;
  description: string;
  category: ViolationCategory;
}

export const AUTO_FIX_MAPPINGS: AutoFixMapping[] = [
  // Legacy neutral scale (50-950) -> Radix neutral scale (1-12)
  {
    pattern: /neutral-50\b/g,
    replacement: "neutral-1",
    description: "neutral-50 -> neutral-1",
    category: "color",
  },
  {
    pattern: /neutral-100\b/g,
    replacement: "neutral-2",
    description: "neutral-100 -> neutral-2",
    category: "color",
  },
  {
    pattern: /neutral-200\b/g,
    replacement: "neutral-3",
    description: "neutral-200 -> neutral-3",
    category: "color",
  },
  {
    pattern: /neutral-300\b/g,
    replacement: "neutral-4",
    description: "neutral-300 -> neutral-4",
    category: "color",
  },
  {
    pattern: /neutral-400\b/g,
    replacement: "neutral-6",
    description: "neutral-400 -> neutral-6",
    category: "color",
  },
  {
    pattern: /neutral-500\b/g,
    replacement: "neutral-8",
    description: "neutral-500 -> neutral-8",
    category: "color",
  },
  {
    pattern: /neutral-600\b/g,
    replacement: "neutral-9",
    description: "neutral-600 -> neutral-9",
    category: "color",
  },
  {
    pattern: /neutral-700\b/g,
    replacement: "neutral-10",
    description: "neutral-700 -> neutral-10",
    category: "color",
  },
  {
    pattern: /neutral-800\b/g,
    replacement: "neutral-11",
    description: "neutral-800 -> neutral-11",
    category: "color",
  },
  {
    pattern: /neutral-900\b/g,
    replacement: "neutral-12",
    description: "neutral-900 -> neutral-12",
    category: "color",
  },
  {
    pattern: /neutral-950\b/g,
    replacement: "neutral-12",
    description: "neutral-950 -> neutral-12",
    category: "color",
  },

  // Gray scale -> Radix neutral
  {
    pattern: /(bg|text|border)-gray-50\b/g,
    replacement: "$1-neutral-1",
    description: "gray-50 -> neutral-1",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-gray-100\b/g,
    replacement: "$1-neutral-2",
    description: "gray-100 -> neutral-2",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-gray-200\b/g,
    replacement: "$1-neutral-3",
    description: "gray-200 -> neutral-3",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-gray-300\b/g,
    replacement: "$1-neutral-4",
    description: "gray-300 -> neutral-4",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-gray-400\b/g,
    replacement: "$1-neutral-6",
    description: "gray-400 -> neutral-6",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-gray-500\b/g,
    replacement: "$1-neutral-8",
    description: "gray-500 -> neutral-8",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-gray-600\b/g,
    replacement: "$1-neutral-9",
    description: "gray-600 -> neutral-9",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-gray-700\b/g,
    replacement: "$1-neutral-10",
    description: "gray-700 -> neutral-10",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-gray-800\b/g,
    replacement: "$1-neutral-11",
    description: "gray-800 -> neutral-11",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-gray-900\b/g,
    replacement: "$1-neutral-12",
    description: "gray-900 -> neutral-12",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-gray-950\b/g,
    replacement: "$1-neutral-12",
    description: "gray-950 -> neutral-12",
    category: "color",
  },

  // Slate scale -> Radix neutral
  {
    pattern: /(bg|text|border)-slate-50\b/g,
    replacement: "$1-neutral-1",
    description: "slate-50 -> neutral-1",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-slate-100\b/g,
    replacement: "$1-neutral-2",
    description: "slate-100 -> neutral-2",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-slate-200\b/g,
    replacement: "$1-neutral-3",
    description: "slate-200 -> neutral-3",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-slate-300\b/g,
    replacement: "$1-neutral-4",
    description: "slate-300 -> neutral-4",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-slate-400\b/g,
    replacement: "$1-neutral-6",
    description: "slate-400 -> neutral-6",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-slate-500\b/g,
    replacement: "$1-neutral-8",
    description: "slate-500 -> neutral-8",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-slate-600\b/g,
    replacement: "$1-neutral-9",
    description: "slate-600 -> neutral-9",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-slate-700\b/g,
    replacement: "$1-neutral-10",
    description: "slate-700 -> neutral-10",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-slate-800\b/g,
    replacement: "$1-neutral-11",
    description: "slate-800 -> neutral-11",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-slate-900\b/g,
    replacement: "$1-neutral-12",
    description: "slate-900 -> neutral-12",
    category: "color",
  },
  {
    pattern: /(bg|text|border)-slate-950\b/g,
    replacement: "$1-neutral-12",
    description: "slate-950 -> neutral-12",
    category: "color",
  },
];

// =============================================================================
// Auto-Fix Getter
// =============================================================================

export function getAutoFix(context: string): {
  fixed: string;
  description: string;
} | null {
  for (const mapping of AUTO_FIX_MAPPINGS) {
    if (mapping.pattern.test(context)) {
      // Reset regex state
      mapping.pattern.lastIndex = 0;
      const fixed = context.replace(mapping.pattern, mapping.replacement);
      return {
        fixed,
        description: mapping.description,
      };
    }
  }
  return null;
}
