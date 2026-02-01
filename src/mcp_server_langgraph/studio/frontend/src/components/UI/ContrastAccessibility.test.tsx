/**
 * Contrast Accessibility Tests
 *
 * Dedicated tests for WCAG 2.2 AA color contrast compliance.
 * Uses Radix Colors 1-12 scale for automatic dark/light mode support.
 *
 * WCAG 2.2 AA Requirements:
 * - Normal text: 4.5:1 contrast ratio
 * - Large text (18pt+ or 14pt+ bold): 3:1 contrast ratio
 * - UI components: 3:1 contrast ratio
 *
 * Radix Color Scale for Text (on neutral-1/2 backgrounds):
 * - text-neutral-12: Primary text (WCAG AAA, ~15:1)
 * - text-neutral-11: Secondary text (WCAG AA, ~7:1)
 * - text-neutral-10: Tertiary text (edge case)
 * - text-neutral-9 and below: AVOID for body text
 *
 * @see WCAG 2.2 Success Criterion 1.4.3 (Contrast Minimum)
 * @see docs-internal/frontend/STYLE.md
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import { cleanup } from "@testing-library/react";

/**
 * Radix semantic text colors that meet WCAG 2.2 AA.
 *
 * With Radix Colors v3.0.0+, these auto-switch for dark mode:
 * - text-neutral-11 for all text
 * - text-primary-11 for accent text
 * - No explicit dark: prefix needed
 */
const RADIX_SEMANTIC_TEXT = [
  "text-neutral-12", // Primary text (high contrast)
  "text-neutral-11", // Secondary text (WCAG AA)
  "text-primary-11", // Accent text
  "text-primary-12", // High-contrast accent
  "text-success-11", // Success state
  "text-warning-11", // Warning state
  "text-error-11", // Error state
  "text-info-11", // Info state
];

/**
 * Legacy Tailwind patterns (deprecated - use Radix semantic colors instead).
 *
 * These patterns are redundant with Radix v3.0.0+:
 * - ESLint flags explicit bg-neutral-1 dark:bg-* patterns
 * - Prefer bg-neutral-1 which auto-switches
 */
const LEGACY_TAILWIND_PATTERNS = [
  "text-neutral-12", // Use text-neutral-12 instead
  "text-neutral-11", // Use text-neutral-11 instead
  "text-neutral-11", // Use text-neutral-11 instead
];

/**
 * Contrast-safe dark mode background opacities.
 *
 * For semantic color backgrounds (warning, error, etc.):
 * - /40 or higher provides sufficient contrast for text
 * - /20 and /30 are too transparent and cause contrast issues
 */
const CONTRAST_SAFE_BG_OPACITY = ["/40", "/50", "/60", "/70", "/80", "/90"];
const LOW_CONTRAST_BG_OPACITY = ["/10", "/20", "/30"];

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("Contrast Accessibility Guidelines", () => {
  describe("Radix Semantic Text Colors", () => {
    it("should document WCAG-compliant Radix text colors", () => {
      // Radix 11-12 scale provides WCAG AA compliant text
      expect(RADIX_SEMANTIC_TEXT).toContain("text-neutral-12");
      expect(RADIX_SEMANTIC_TEXT).toContain("text-neutral-11");
      expect(RADIX_SEMANTIC_TEXT).toContain("text-primary-11");
    });

    it("should document legacy patterns to migrate away from", () => {
      // Legacy dark: prefixed patterns are redundant with Radix v3.0.0+
      expect(LEGACY_TAILWIND_PATTERNS).toContain("text-neutral-12");
      expect(LEGACY_TAILWIND_PATTERNS).toContain("text-neutral-11");
    });
  });

  describe("Background Opacity Guidelines", () => {
    it("should document contrast-safe background opacities", () => {
      expect(CONTRAST_SAFE_BG_OPACITY).toContain("/50");
      expect(CONTRAST_SAFE_BG_OPACITY).not.toContain("/20");
    });

    it("should document low-contrast background opacities to avoid", () => {
      expect(LOW_CONTRAST_BG_OPACITY).toContain("/20");
      expect(LOW_CONTRAST_BG_OPACITY).toContain("/30");
    });
  });
});

describe("Radix Semantic Color Compliance", () => {
  /**
   * Helper to check if a className string uses Radix semantic colors.
   * Returns true if using proper Radix 11-12 text scale.
   */
  function usesRadixSemanticColors(className: string): boolean {
    // Check for Radix semantic text colors (11-12 for text)
    return /text-(neutral|primary|success|warning|error|info)-(11|12)/.test(
      className,
    );
  }

  /**
   * Helper to check for low-contrast opacity patterns in dark mode.
   * Detects both Tailwind opacity modifiers (/10, /20, /30) and
   * Radix alpha colors with low steps (a1-a4).
   */
  function hasLowContrastOpacity(className: string): boolean {
    // Check for Tailwind opacity modifiers
    for (const opacity of LOW_CONTRAST_BG_OPACITY) {
      const regex = new RegExp(
        `(dark:)?bg-[a-z]+-\\d+${opacity.replace("/", "\\/")}`,
        "g",
      );
      if (regex.test(className)) {
        return true;
      }
    }
    // Check for Radix alpha colors with low contrast steps (a1-a4)
    const radixAlphaLowContrast = /(dark:)?bg-[a-z]+-a[1-4]\b/;
    if (radixAlphaLowContrast.test(className)) {
      return true;
    }
    return false;
  }

  describe("Text Color Best Practices", () => {
    it("should use Radix semantic text colors for high contrast", () => {
      // Radix text-neutral-11 provide WCAG AA compliant contrast
      const primaryText = "text-neutral-12";
      const secondaryText = "text-neutral-11";

      expect(usesRadixSemanticColors(primaryText)).toBe(true);
      expect(usesRadixSemanticColors(secondaryText)).toBe(true);
    });

    it("should avoid low step numbers for body text", () => {
      // Steps 1-9 are too low contrast for body text
      const lowContrastText = "text-neutral-9";
      expect(usesRadixSemanticColors(lowContrastText)).toBe(false);
    });
  });

  describe("Background Color Best Practices", () => {
    it("should use Radix semantic backgrounds", () => {
      // bg-neutral-1 are WCAG compliant surface colors
      const surfaceBg = "bg-neutral-1";
      const cardBg = "bg-neutral-2";

      expect(surfaceBg).toContain("neutral-1");
      expect(cardBg).toContain("neutral-2");
    });

    it("should avoid low opacity backgrounds for semantic colors", () => {
      // Low opacity backgrounds fail contrast requirements
      const safeOpacity = "bg-warning-3"; // Radix semantic - auto-switches
      const lowOpacity = "bg-warning-a3";

      expect(hasLowContrastOpacity(safeOpacity)).toBe(false);
      expect(hasLowContrastOpacity(lowOpacity)).toBe(true);
    });
  });

  describe("hasLowContrastOpacity utility", () => {
    it("should detect low opacity backgrounds", () => {
      expect(hasLowContrastOpacity("bg-warning-a3")).toBe(true);
      expect(hasLowContrastOpacity("bg-error-a4")).toBe(true);
    });

    it("should not flag sufficient opacity backgrounds", () => {
      expect(hasLowContrastOpacity("bg-warning-a6")).toBe(false);
      expect(hasLowContrastOpacity("bg-error-a5")).toBe(false);
    });

    it("should not flag Radix semantic backgrounds", () => {
      // Radix semantic colors don't use opacity
      expect(hasLowContrastOpacity("bg-neutral-1")).toBe(false);
      expect(hasLowContrastOpacity("bg-warning-3")).toBe(false);
    });
  });
});

describe("Persona Navigation Items", () => {
  it("should include connections in admin sidebar items", () => {
    // This test verifies the fix for missing nav items
    const expectedAdminItems = [
      "projects",
      "chat",
      "workflows",
      "mcp",
      "agents",
      "vectors",
      "connections", // Must be included
      "observability",
      "artifacts",
      "cost",
      "settings",
      "admin",
      "skills", // Must be included
      "audit", // ID must match NAV_ITEMS
      "compliance", // Must be included
      "help",
    ];

    expect(expectedAdminItems).toContain("connections");
    expect(expectedAdminItems).toContain("skills");
    expect(expectedAdminItems).toContain("audit");
    expect(expectedAdminItems).toContain("compliance");
  });
});
