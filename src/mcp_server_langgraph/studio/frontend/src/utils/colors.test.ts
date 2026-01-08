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

    it("should include dark mode variants for all styles", async () => {
      const { STATUS_BADGE_STYLES } = await import("./colors");
      Object.values(STATUS_BADGE_STYLES).forEach((style) => {
        expect(style).toMatch(/dark:/);
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
      expect(getRiskLevelColor("critical")).toMatch(/text-error-700/);
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
    it("should use lighter shades in dark mode for contrast", async () => {
      const { CONFIDENCE_COLORS } = await import("./colors");
      // Dark mode should use 400 shade (lighter) for readability on dark backgrounds
      expect(CONFIDENCE_COLORS.high).toMatch(/dark:text-success-400/);
      expect(CONFIDENCE_COLORS.medium).toMatch(/dark:text-warning-400/);
      expect(CONFIDENCE_COLORS.low).toMatch(/dark:text-error-400/);
    });

    it("should use 600 shade in light mode for contrast", async () => {
      const { CONFIDENCE_COLORS } = await import("./colors");
      expect(CONFIDENCE_COLORS.high).toMatch(/text-success-600/);
      expect(CONFIDENCE_COLORS.medium).toMatch(/text-warning-600/);
      expect(CONFIDENCE_COLORS.low).toMatch(/text-error-600/);
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
