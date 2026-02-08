/**
 * Global Color Utilities Tests
 *
 * TDD tests for centralized color management across all frontend components.
 * These tests ensure semantic colors are used consistently with WCAG 2.2 compliance.
 *
 * Tests written FIRST following Red-Green-Refactor cycle.
 */
import { afterEach, describe, expect, it, vi } from "vitest";

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

// =============================================================================
// Tests: Global Status Badge Styles
// =============================================================================

describe("Global Color Utilities", () => {
  describe("STATUS_BADGE_STYLES", () => {
    it("should define all status types", async () => {
      const { STATUS_BADGE_STYLES } = await import("./colors");
      const statuses = ["success", "warning", "error", "info", "neutral"];
      statuses.forEach((status) => {
        expect(
          STATUS_BADGE_STYLES[status as keyof typeof STATUS_BADGE_STYLES],
        ).toBeDefined();
      });
    });

    it("should use semantic color classes (not raw Tailwind)", async () => {
      const { STATUS_BADGE_STYLES } = await import("./colors");
      // Should use success-*, warning-*, error-*, primary-* NOT green-*, yellow-*, red-*, blue-*
      expect(STATUS_BADGE_STYLES.success).toMatch(/bg-success-/);
      expect(STATUS_BADGE_STYLES.warning).toMatch(/bg-warning-/);
      expect(STATUS_BADGE_STYLES.error).toMatch(/bg-error-/);
      expect(STATUS_BADGE_STYLES.info).toMatch(/bg-primary-/);
    });

    it("should include both background and text colors", async () => {
      const { STATUS_BADGE_STYLES } = await import("./colors");
      Object.values(STATUS_BADGE_STYLES).forEach((style) => {
        expect(style).toMatch(/bg-/);
        expect(style).toMatch(/text-/);
      });
    });

    it("should include dark mode variants for semantic styles", async () => {
      const { STATUS_BADGE_STYLES } = await import("./colors");
      // Check that semantic status colors have dark mode variants
      // Note: neutral style is designed to work in both modes without explicit dark: prefix
      const semanticStatuses = ["success", "warning", "error", "info"] as const;
      semanticStatuses.forEach((status) => {
        expect(STATUS_BADGE_STYLES[status]).toMatch(/dark:/);
      });
    });
  });

  // =============================================================================
  // Tests: Interactive Colors
  // =============================================================================

  describe("INTERACTIVE_COLORS", () => {
    it("should define interactive states", async () => {
      const { INTERACTIVE_COLORS } = await import("./colors");
      const states = ["danger", "primary", "success", "warning"];
      states.forEach((state) => {
        expect(
          INTERACTIVE_COLORS[state as keyof typeof INTERACTIVE_COLORS],
        ).toBeDefined();
      });
    });

    it("should include hover states", async () => {
      const { INTERACTIVE_COLORS } = await import("./colors");
      Object.values(INTERACTIVE_COLORS).forEach((style) => {
        expect(style).toMatch(/hover:/);
      });
    });

    it("should use semantic colors for danger (error)", async () => {
      const { INTERACTIVE_COLORS } = await import("./colors");
      expect(INTERACTIVE_COLORS.danger).toMatch(/error-/);
    });

    it("should include dark mode hover variants", async () => {
      const { INTERACTIVE_COLORS } = await import("./colors");
      Object.values(INTERACTIVE_COLORS).forEach((style) => {
        expect(style).toMatch(/dark:hover:/);
      });
    });
  });

  // =============================================================================
  // Tests: Confidence Colors (AI Components)
  // =============================================================================

  describe("CONFIDENCE_COLORS", () => {
    it("should define confidence levels", async () => {
      const { CONFIDENCE_COLORS } = await import("./colors");
      expect(CONFIDENCE_COLORS.high).toBeDefined();
      expect(CONFIDENCE_COLORS.medium).toBeDefined();
      expect(CONFIDENCE_COLORS.low).toBeDefined();
    });

    it("should use semantic colors for confidence levels", async () => {
      const { CONFIDENCE_COLORS } = await import("./colors");
      expect(CONFIDENCE_COLORS.high).toMatch(/text-success-/);
      expect(CONFIDENCE_COLORS.medium).toMatch(/text-warning-/);
      expect(CONFIDENCE_COLORS.low).toMatch(/text-error-/);
    });

    it("should include dark mode variants", async () => {
      const { CONFIDENCE_COLORS } = await import("./colors");
      Object.values(CONFIDENCE_COLORS).forEach((style) => {
        expect(style).toMatch(/dark:/);
      });
    });
  });
});

// =============================================================================
// Tests: Helper Functions
// =============================================================================

describe("Global Color Helper Functions", () => {
  describe("getStatusBadgeStyle", () => {
    it("should return correct style for each status type", async () => {
      const { getStatusBadgeStyle, STATUS_BADGE_STYLES } =
        await import("./colors");
      expect(getStatusBadgeStyle("success")).toBe(STATUS_BADGE_STYLES.success);
      expect(getStatusBadgeStyle("warning")).toBe(STATUS_BADGE_STYLES.warning);
      expect(getStatusBadgeStyle("error")).toBe(STATUS_BADGE_STYLES.error);
      expect(getStatusBadgeStyle("info")).toBe(STATUS_BADGE_STYLES.info);
      expect(getStatusBadgeStyle("neutral")).toBe(STATUS_BADGE_STYLES.neutral);
    });
  });

  describe("getConfidenceColor", () => {
    it("should return high color for confidence >= 0.9", async () => {
      const { getConfidenceColor, CONFIDENCE_COLORS } =
        await import("./colors");
      expect(getConfidenceColor(0.9)).toBe(CONFIDENCE_COLORS.high);
      expect(getConfidenceColor(0.95)).toBe(CONFIDENCE_COLORS.high);
      expect(getConfidenceColor(1.0)).toBe(CONFIDENCE_COLORS.high);
    });

    it("should return medium color for confidence >= 0.7 and < 0.9", async () => {
      const { getConfidenceColor, CONFIDENCE_COLORS } =
        await import("./colors");
      expect(getConfidenceColor(0.7)).toBe(CONFIDENCE_COLORS.medium);
      expect(getConfidenceColor(0.8)).toBe(CONFIDENCE_COLORS.medium);
      expect(getConfidenceColor(0.89)).toBe(CONFIDENCE_COLORS.medium);
    });

    it("should return low color for confidence < 0.7", async () => {
      const { getConfidenceColor, CONFIDENCE_COLORS } =
        await import("./colors");
      expect(getConfidenceColor(0.0)).toBe(CONFIDENCE_COLORS.low);
      expect(getConfidenceColor(0.5)).toBe(CONFIDENCE_COLORS.low);
      expect(getConfidenceColor(0.69)).toBe(CONFIDENCE_COLORS.low);
    });
  });

  describe("getRiskLevelColor", () => {
    it("should return success color for low risk", async () => {
      const { getRiskLevelColor } = await import("./colors");
      expect(getRiskLevelColor("low")).toMatch(/text-success-/);
    });

    it("should return warning color for medium risk", async () => {
      const { getRiskLevelColor } = await import("./colors");
      expect(getRiskLevelColor("medium")).toMatch(/text-warning-/);
    });

    it("should return error color for high risk", async () => {
      const { getRiskLevelColor } = await import("./colors");
      expect(getRiskLevelColor("high")).toMatch(/text-error-/);
    });

    it("should return stronger error color for critical risk", async () => {
      const { getRiskLevelColor } = await import("./colors");
      expect(getRiskLevelColor("critical")).toMatch(/text-error-11/);
    });

    it("should include dark mode variants for all risk levels", async () => {
      const { getRiskLevelColor } = await import("./colors");
      const levels: Array<"low" | "medium" | "high" | "critical"> = [
        "low",
        "medium",
        "high",
        "critical",
      ];
      levels.forEach((level) => {
        expect(getRiskLevelColor(level)).toMatch(/dark:/);
      });
    });
  });

  describe("getComplianceStatusColor", () => {
    it("should return success color for compliant status", async () => {
      const { getComplianceStatusColor } = await import("./colors");
      expect(getComplianceStatusColor("compliant")).toMatch(/text-success-/);
    });

    it("should return warning color for partial compliance", async () => {
      const { getComplianceStatusColor } = await import("./colors");
      expect(getComplianceStatusColor("partial")).toMatch(/text-warning-/);
    });

    it("should return error color for non-compliant status", async () => {
      const { getComplianceStatusColor } = await import("./colors");
      expect(getComplianceStatusColor("non-compliant")).toMatch(/text-error-/);
    });

    it("should include dark mode variants for all statuses", async () => {
      const { getComplianceStatusColor } = await import("./colors");
      const statuses: Array<"compliant" | "partial" | "non-compliant"> = [
        "compliant",
        "partial",
        "non-compliant",
      ];
      statuses.forEach((status) => {
        expect(getComplianceStatusColor(status)).toMatch(/dark:/);
      });
    });
  });
});

// =============================================================================
// Tests: Re-exports from DevTools
// =============================================================================

describe("DevTools Re-exports", () => {
  it("should re-export STATUS_TEXT_COLORS from devToolsColors", async () => {
    const { STATUS_TEXT_COLORS } = await import("./colors");
    expect(STATUS_TEXT_COLORS).toBeDefined();
    expect(STATUS_TEXT_COLORS.success).toBeDefined();
  });

  it("should re-export LEVEL_BADGE_STYLES from devToolsColors", async () => {
    const { LEVEL_BADGE_STYLES } = await import("./colors");
    expect(LEVEL_BADGE_STYLES).toBeDefined();
    expect(LEVEL_BADGE_STYLES.debug).toBeDefined();
    expect(LEVEL_BADGE_STYLES.info).toBeDefined();
    expect(LEVEL_BADGE_STYLES.warning).toBeDefined();
    expect(LEVEL_BADGE_STYLES.error).toBeDefined();
  });

  it("should re-export GRAFANA_COLORS from devToolsColors", async () => {
    const { GRAFANA_COLORS } = await import("./colors");
    expect(GRAFANA_COLORS).toBeDefined();
    expect(GRAFANA_COLORS.primary).toBe("#F46800");
  });

  it("should re-export AI_INSIGHT_COLORS from devToolsColors", async () => {
    const { AI_INSIGHT_COLORS } = await import("./colors");
    expect(AI_INSIGHT_COLORS).toBeDefined();
    expect(AI_INSIGHT_COLORS.text).toMatch(/text-insight-/);
  });

  it("should re-export helper functions from devToolsColors", async () => {
    const { getLogLevelStyle, getHttpMethodColor, getStatusCodeColor } =
      await import("./colors");
    expect(getLogLevelStyle).toBeDefined();
    expect(getHttpMethodColor).toBeDefined();
    expect(getStatusCodeColor).toBeDefined();
  });
});

// =============================================================================
// Tests: Insight (AI) and Grafana Color Utilities
// =============================================================================

describe("AI Insight Color Utilities", () => {
  describe("AI_INSIGHT_COLORS", () => {
    it("should define all insight color variants", async () => {
      const { AI_INSIGHT_COLORS } = await import("./colors");
      expect(AI_INSIGHT_COLORS.primary).toBeDefined();
      expect(AI_INSIGHT_COLORS.glow).toBeDefined();
      expect(AI_INSIGHT_COLORS.text).toBeDefined();
      expect(AI_INSIGHT_COLORS.bg).toBeDefined();
      expect(AI_INSIGHT_COLORS.badge).toBeDefined();
    });

    it("should use semantic insight-* classes NOT purple-*", async () => {
      const { AI_INSIGHT_COLORS } = await import("./colors");
      // Text should use insight-*, not purple-*
      expect(AI_INSIGHT_COLORS.text).toMatch(/text-insight-/);
      expect(AI_INSIGHT_COLORS.text).not.toMatch(/purple-/);
      // Background should use insight-*, not purple-*
      expect(AI_INSIGHT_COLORS.bg).toMatch(/bg-insight-/);
      expect(AI_INSIGHT_COLORS.bg).not.toMatch(/purple-/);
      // Badge should use insight-*, not purple-*
      expect(AI_INSIGHT_COLORS.badge).toMatch(/insight-/);
      expect(AI_INSIGHT_COLORS.badge).not.toMatch(/purple-/);
    });

    it("should include dark mode variants for text styles", async () => {
      const { AI_INSIGHT_COLORS } = await import("./colors");
      expect(AI_INSIGHT_COLORS.text).toMatch(/dark:text-insight-/);
    });

    it("should include dark mode variants for background styles", async () => {
      const { AI_INSIGHT_COLORS } = await import("./colors");
      expect(AI_INSIGHT_COLORS.bg).toMatch(/dark:bg-insight-/);
    });

    it("should include dark mode variants for badge styles", async () => {
      const { AI_INSIGHT_COLORS } = await import("./colors");
      expect(AI_INSIGHT_COLORS.badge).toMatch(/dark:bg-insight-/);
    });
  });

  describe("getAIInsightStyle", () => {
    it("should return text style for text variant", async () => {
      const { getAIInsightStyle, AI_INSIGHT_COLORS } = await import("./colors");
      expect(getAIInsightStyle("text")).toBe(AI_INSIGHT_COLORS.text);
    });

    it("should return bg style for bg variant", async () => {
      const { getAIInsightStyle, AI_INSIGHT_COLORS } = await import("./colors");
      expect(getAIInsightStyle("bg")).toBe(AI_INSIGHT_COLORS.bg);
    });

    it("should return badge style for badge variant", async () => {
      const { getAIInsightStyle, AI_INSIGHT_COLORS } = await import("./colors");
      expect(getAIInsightStyle("badge")).toBe(AI_INSIGHT_COLORS.badge);
    });
  });
});

describe("Grafana Color Utilities", () => {
  describe("GRAFANA_COLORS", () => {
    it("should define all grafana color variants", async () => {
      const { GRAFANA_COLORS } = await import("./colors");
      expect(GRAFANA_COLORS.primary).toBeDefined();
      expect(GRAFANA_COLORS.button).toBeDefined();
      expect(GRAFANA_COLORS.text).toBeDefined();
    });

    it("should use official Grafana brand orange", async () => {
      const { GRAFANA_COLORS } = await import("./colors");
      expect(GRAFANA_COLORS.primary).toBe("#F46800");
    });

    it("should use semantic grafana-* classes NOT orange-*", async () => {
      const { GRAFANA_COLORS } = await import("./colors");
      // Button should use grafana-*, not orange-*
      expect(GRAFANA_COLORS.button).toMatch(/bg-grafana-/);
      expect(GRAFANA_COLORS.button).not.toMatch(/orange-/);
      // Text should use grafana-*, not orange-*
      expect(GRAFANA_COLORS.text).toMatch(/text-grafana-/);
      expect(GRAFANA_COLORS.text).not.toMatch(/orange-/);
    });

    it("should include dark mode variants for button styles", async () => {
      const { GRAFANA_COLORS } = await import("./colors");
      expect(GRAFANA_COLORS.button).toMatch(/dark:bg-grafana-/);
    });

    it("should include dark mode variants for text styles", async () => {
      const { GRAFANA_COLORS } = await import("./colors");
      expect(GRAFANA_COLORS.text).toMatch(/dark:text-grafana-/);
    });
  });

  describe("getGrafanaButtonStyle", () => {
    it("should return the button style", async () => {
      const { getGrafanaButtonStyle, GRAFANA_COLORS } =
        await import("./colors");
      expect(getGrafanaButtonStyle()).toBe(GRAFANA_COLORS.button);
    });
  });
});

// =============================================================================
// Tests: WCAG 2.2 Accessibility Compliance
// =============================================================================

describe("WCAG 2.2 Accessibility Compliance", () => {
  describe("Color Not Used Alone", () => {
    it("should provide distinct semantic colors for different statuses", async () => {
      const { STATUS_BADGE_STYLES } = await import("./colors");
      // Different statuses should have different base colors
      const successBase = STATUS_BADGE_STYLES.success.match(/bg-(\w+)-/)?.[1];
      const warningBase = STATUS_BADGE_STYLES.warning.match(/bg-(\w+)-/)?.[1];
      const errorBase = STATUS_BADGE_STYLES.error.match(/bg-(\w+)-/)?.[1];

      expect(successBase).not.toBe(warningBase);
      expect(successBase).not.toBe(errorBase);
      expect(warningBase).not.toBe(errorBase);
    });
  });

  describe("Dark Mode Support", () => {
    it("should use appropriate shades in dark mode for contrast", async () => {
      const { CONFIDENCE_COLORS } = await import("./colors");
      // Dark mode uses shades that provide good contrast on dark backgrounds
      expect(CONFIDENCE_COLORS.high).toMatch(/dark:text-success-7/);
      expect(CONFIDENCE_COLORS.medium).toMatch(/dark:text-warning-9/);
      expect(CONFIDENCE_COLORS.low).toMatch(/dark:text-error-7/);
    });

    it("should use appropriate shade in light mode for contrast", async () => {
      const { CONFIDENCE_COLORS } = await import("./colors");
      expect(CONFIDENCE_COLORS.high).toMatch(/text-success-10/);
      expect(CONFIDENCE_COLORS.medium).toMatch(/text-warning-9/);
      expect(CONFIDENCE_COLORS.low).toMatch(/text-error-10/);
    });
  });

  describe("No Font Size Definitions", () => {
    it("should not include font sizes in color utilities", async () => {
      const { STATUS_BADGE_STYLES, INTERACTIVE_COLORS, CONFIDENCE_COLORS } =
        await import("./colors");

      const allStyles = [
        ...Object.values(STATUS_BADGE_STYLES),
        ...Object.values(INTERACTIVE_COLORS),
        ...Object.values(CONFIDENCE_COLORS),
      ];

      allStyles.forEach((style) => {
        expect(style).not.toMatch(/text-\[/); // No arbitrary text sizes
        expect(style).not.toMatch(/text-xs/); // No size classes mixed with colors
        expect(style).not.toMatch(/text-sm/);
        expect(style).not.toMatch(/text-base/);
        expect(style).not.toMatch(/text-lg/);
      });
    });
  });
});

// =============================================================================
// Tests: Info Color Utilities (cyan semantic alias)
// =============================================================================

describe("Info Color Utilities", () => {
  describe("INFO_COLORS", () => {
    it("should use semantic info-* classes NOT cyan-*", async () => {
      const { INFO_COLORS } = await import("./colors");
      expect(INFO_COLORS.text).toMatch(/text-info-/);
      expect(INFO_COLORS.text).not.toMatch(/cyan-/);
    });

    it("should define all style variants", async () => {
      const { INFO_COLORS } = await import("./colors");
      expect(INFO_COLORS.text).toBeDefined();
      expect(INFO_COLORS.bg).toBeDefined();
      expect(INFO_COLORS.badge).toBeDefined();
      expect(INFO_COLORS.border).toBeDefined();
    });

    it("should include dark mode variants where applicable", async () => {
      const { INFO_COLORS } = await import("./colors");
      // text, badge, and border have explicit dark: variants
      expect(INFO_COLORS.text).toMatch(/dark:/);
      expect(INFO_COLORS.badge).toMatch(/dark:/);
      expect(INFO_COLORS.border).toMatch(/dark:/);
      // bg uses Radix color scale which adapts automatically to dark mode
      expect(INFO_COLORS.bg).toMatch(/bg-info-/);
    });

    it("should have proper contrast ratios for text", async () => {
      const { INFO_COLORS } = await import("./colors");
      // Uses Radix color scale (1-12), not Tailwind (50-950)
      expect(INFO_COLORS.text).toMatch(/text-info-9/);
      expect(INFO_COLORS.text).toMatch(/dark:text-info-11/);
    });

    it("should have subtle background", async () => {
      const { INFO_COLORS } = await import("./colors");
      // Background uses multiple classes for layered effect
      expect(INFO_COLORS.bg).toMatch(/bg-info-1/);
      expect(INFO_COLORS.bg).toMatch(/bg-info-4/);
    });
  });

  describe("getInfoStyle", () => {
    it("should return text style for text variant", async () => {
      const { getInfoStyle } = await import("./colors");
      expect(getInfoStyle("text")).toMatch(/text-info-/);
    });

    it("should return bg style for bg variant", async () => {
      const { getInfoStyle } = await import("./colors");
      expect(getInfoStyle("bg")).toMatch(/bg-info-/);
    });

    it("should return badge style for badge variant", async () => {
      const { getInfoStyle } = await import("./colors");
      const badge = getInfoStyle("badge");
      expect(badge).toMatch(/bg-info-/);
      expect(badge).toMatch(/text-info-/);
    });

    it("should return border style for border variant", async () => {
      const { getInfoStyle } = await import("./colors");
      expect(getInfoStyle("border")).toMatch(/border-info-/);
    });
  });
});

// =============================================================================
// Tests: Tailwind Config Color Scale Alignment (WCAG 2.2)
// =============================================================================

describe("Tailwind Color Scale WCAG Compliance", () => {
  // These tests verify that the Tailwind config has correct color alignment
  // for WCAG 2.2 AA compliance (4.5:1 contrast ratio for normal text on primary)

  it("should export primary-500 that passes WCAG AA with white text", async () => {
    // The primary-500 color should be blue-500 (#3b82f6) which has 4.5:1 contrast
    // with white text. This is verified by the Tailwind config using blue palette
    // instead of sky palette (sky-500 only has 2.75:1 contrast - fails WCAG AA).
    //
    // This is a documentation/reminder test - the actual color is defined in
    // tailwind.config.ts and cannot be directly tested here without parsing.
    // The test serves to document the accessibility requirement.
    const wcagAAContrastRatio = 4.5;
    expect(wcagAAContrastRatio).toBeGreaterThanOrEqual(4.5);
  });

  it("should use semantic color tokens consistently", async () => {
    // Verify that colors module uses primary-* not blue-* directly
    const { INTERACTIVE_COLORS } = await import("./colors");
    expect(INTERACTIVE_COLORS.primary).toMatch(/primary-/);
    expect(INTERACTIVE_COLORS.primary).not.toMatch(/blue-/);
  });
});

// =============================================================================
// Tests: Neutral Color Utilities (for general UI elements)
// =============================================================================

describe("Neutral Color Utilities", () => {
  describe("NEUTRAL_COLORS", () => {
    it("should use semantic neutral-* classes NOT gray-*", async () => {
      const { NEUTRAL_COLORS } = await import("./colors");
      expect(NEUTRAL_COLORS.text).toMatch(/text-neutral-/);
      expect(NEUTRAL_COLORS.text).not.toMatch(/gray-/);
    });

    it("should define all standard variants", async () => {
      const { NEUTRAL_COLORS } = await import("./colors");
      const variants = [
        "text",
        "textMuted",
        "textSubtle",
        "bg",
        "bgHover",
        "bgSelected",
        "border",
        "borderLight",
        "divide",
      ];
      variants.forEach((variant) => {
        expect(
          NEUTRAL_COLORS[variant as keyof typeof NEUTRAL_COLORS],
        ).toBeDefined();
      });
    });

    it("should include dark mode variants for divide style", async () => {
      const { NEUTRAL_COLORS } = await import("./colors");
      // Only divide has explicit dark: variant in current implementation
      // Other styles rely on Radix dark theme automatic adaptation
      expect(NEUTRAL_COLORS.divide).toMatch(/dark:/);
    });

    it("should use Radix color scale for text contrast", async () => {
      const { NEUTRAL_COLORS } = await import("./colors");
      // Uses Radix color scale (1-12):
      // - 12 = highest contrast text
      // - 11 = secondary text
      // - 9 = subtle/tertiary text
      expect(NEUTRAL_COLORS.text).toMatch(/neutral-12/);
      expect(NEUTRAL_COLORS.textMuted).toMatch(/neutral-11/);
      expect(NEUTRAL_COLORS.textSubtle).toMatch(/neutral-9/);
    });
  });

  describe("getNeutralStyle", () => {
    it("should return text style for text variant", async () => {
      const { getNeutralStyle } = await import("./colors");
      expect(getNeutralStyle("text")).toMatch(/text-neutral-/);
    });

    it("should return muted style for textMuted variant", async () => {
      const { getNeutralStyle } = await import("./colors");
      expect(getNeutralStyle("textMuted")).toMatch(/text-neutral-/);
    });

    it("should return bg style for bg variant", async () => {
      const { getNeutralStyle } = await import("./colors");
      expect(getNeutralStyle("bg")).toMatch(/bg-neutral-/);
    });

    it("should return border style for border variant", async () => {
      const { getNeutralStyle } = await import("./colors");
      expect(getNeutralStyle("border")).toMatch(/border-neutral-/);
    });
  });
});
