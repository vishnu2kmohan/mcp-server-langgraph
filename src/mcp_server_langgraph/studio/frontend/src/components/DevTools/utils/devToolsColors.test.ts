/**
 * DevTools Color Utilities Tests
 *
 * TDD tests for centralized DevTools color management.
 * Ensures consistent semantic color usage across all DevTools tabs.
 *
 * WCAG 2.2 Accessibility Requirements:
 * - All text colors must have sufficient contrast (4.5:1 normal, 3:1 large)
 * - Status indicators must not rely on color alone (use icons + text)
 * - Dark mode variants must be provided for all colors
 */
import { afterEach, describe, expect, it, vi } from "vitest";

import {
  // Constants
  STATUS_TEXT_COLORS,
  STATUS_BG_COLORS,
  LEVEL_BADGE_STYLES,
  HTTP_METHOD_COLORS,
  STREAM_STATUS_STYLES,
  SPARKLINE_COLORS,
  // Helper functions
  getTrendTextColor,
  getSparklineColor,
  getLogLevelStyle,
  getHttpMethodColor,
  getStreamStatusStyle,
  getStatusCodeColor,
  // Types
  type StatusLevel,
  type LogLevel,
  type StreamStatus,
  type HttpMethod,
} from "./devToolsColors";

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

// =============================================================================
// Tests: Constant Definitions
// =============================================================================

describe("DevTools Color Utilities", () => {
  describe("STATUS_TEXT_COLORS", () => {
    it("should define all status levels", () => {
      const levels: StatusLevel[] = [
        "success",
        "warning",
        "error",
        "info",
        "neutral",
      ];
      levels.forEach((level) => {
        expect(STATUS_TEXT_COLORS[level]).toBeDefined();
      });
    });

    it("should use semantic color classes (not standard Tailwind)", () => {
      // Should use success-*, warning-*, error-*, primary-* NOT green-*, yellow-*, red-*, blue-*
      expect(STATUS_TEXT_COLORS.success).toMatch(/text-success-/);
      expect(STATUS_TEXT_COLORS.warning).toMatch(/text-warning-/);
      expect(STATUS_TEXT_COLORS.error).toMatch(/text-error-/);
      expect(STATUS_TEXT_COLORS.info).toMatch(/text-primary-/);
    });

    it("should include dark mode variants for all colors", () => {
      Object.values(STATUS_TEXT_COLORS).forEach((colorClass) => {
        expect(colorClass).toMatch(/dark:/);
      });
    });
  });

  describe("STATUS_BG_COLORS", () => {
    it("should define all status levels", () => {
      const levels: StatusLevel[] = [
        "success",
        "warning",
        "error",
        "info",
        "neutral",
      ];
      levels.forEach((level) => {
        expect(STATUS_BG_COLORS[level]).toBeDefined();
      });
    });

    it("should use semantic background classes", () => {
      expect(STATUS_BG_COLORS.success).toMatch(/bg-success-/);
      expect(STATUS_BG_COLORS.warning).toMatch(/bg-warning-/);
      expect(STATUS_BG_COLORS.error).toMatch(/bg-error-/);
      expect(STATUS_BG_COLORS.info).toMatch(/bg-primary-/);
    });

    it("should include dark mode variants", () => {
      Object.values(STATUS_BG_COLORS).forEach((colorClass) => {
        expect(colorClass).toMatch(/dark:/);
      });
    });
  });

  describe("LEVEL_BADGE_STYLES", () => {
    it("should define all log levels", () => {
      const levels: LogLevel[] = ["debug", "info", "warning", "error"];
      levels.forEach((level) => {
        expect(LEVEL_BADGE_STYLES[level]).toBeDefined();
      });
    });

    it("should use semantic colors for info, warning, error", () => {
      expect(LEVEL_BADGE_STYLES.info).toMatch(/bg-primary-/);
      expect(LEVEL_BADGE_STYLES.warning).toMatch(/bg-warning-/);
      expect(LEVEL_BADGE_STYLES.error).toMatch(/bg-error-/);
    });

    it("should use gray for debug level", () => {
      expect(LEVEL_BADGE_STYLES.debug).toMatch(/bg-neutral-/);
    });

    it("should include dark mode variants", () => {
      Object.values(LEVEL_BADGE_STYLES).forEach((style) => {
        expect(style).toMatch(/dark:/);
      });
    });

    it("should include both background and text colors", () => {
      Object.values(LEVEL_BADGE_STYLES).forEach((style) => {
        expect(style).toMatch(/bg-/);
        expect(style).toMatch(/text-/);
      });
    });
  });

  describe("HTTP_METHOD_COLORS", () => {
    it("should define colors for standard HTTP methods", () => {
      const methods: HttpMethod[] = ["GET", "POST", "PUT", "DELETE", "PATCH"];
      methods.forEach((method) => {
        expect(
          HTTP_METHOD_COLORS[method as keyof typeof HTTP_METHOD_COLORS],
        ).toBeDefined();
      });
    });

    it("should provide a DEFAULT fallback", () => {
      expect(HTTP_METHOD_COLORS.DEFAULT).toBeDefined();
    });

    it("should use semantic colors for methods", () => {
      // GET = success (green), POST = primary (blue), DELETE = error (red)
      expect(HTTP_METHOD_COLORS.GET).toMatch(/text-success-/);
      expect(HTTP_METHOD_COLORS.POST).toMatch(/text-primary-/);
      expect(HTTP_METHOD_COLORS.DELETE).toMatch(/text-error-/);
      expect(HTTP_METHOD_COLORS.PUT).toMatch(/text-warning-/);
    });

    it("should include dark mode variants", () => {
      Object.values(HTTP_METHOD_COLORS).forEach((color) => {
        expect(color).toMatch(/dark:/);
      });
    });
  });

  describe("STREAM_STATUS_STYLES", () => {
    it("should define all stream statuses", () => {
      const statuses: StreamStatus[] = [
        "active",
        "success",
        "error",
        "cancelled",
      ];
      statuses.forEach((status) => {
        expect(STREAM_STATUS_STYLES[status]).toBeDefined();
      });
    });

    it("should include border and background colors", () => {
      Object.values(STREAM_STATUS_STYLES).forEach((style) => {
        expect(style).toMatch(/border-/);
        expect(style).toMatch(/bg-/);
      });
    });

    it("should include dark mode variants", () => {
      Object.values(STREAM_STATUS_STYLES).forEach((style) => {
        expect(style).toMatch(/dark:/);
      });
    });
  });

  describe("SPARKLINE_COLORS", () => {
    it("should provide raw hex values for SVG usage", () => {
      expect(SPARKLINE_COLORS.success).toMatch(/^#[0-9a-fA-F]{6}$/);
      expect(SPARKLINE_COLORS.error).toMatch(/^#[0-9a-fA-F]{6}$/);
      expect(SPARKLINE_COLORS.neutral).toMatch(/^#[0-9a-fA-F]{6}$/);
      expect(SPARKLINE_COLORS.primary).toMatch(/^#[0-9a-fA-F]{6}$/);
    });

    it("should use colors from design tokens", () => {
      // These should match the design system tokens
      expect(SPARKLINE_COLORS.success).toBe("#22c55e");
      expect(SPARKLINE_COLORS.error).toBe("#ef4444");
      expect(SPARKLINE_COLORS.neutral).toBe("#6b7280");
      expect(SPARKLINE_COLORS.primary).toBe("#3b82f6");
    });
  });
});

// =============================================================================
// Tests: Helper Functions
// =============================================================================

describe("DevTools Color Helper Functions", () => {
  describe("getTrendTextColor", () => {
    it("should return success color for up trend", () => {
      const result = getTrendTextColor("up");
      expect(result).toBe(STATUS_TEXT_COLORS.success);
    });

    it("should return error color for down trend", () => {
      const result = getTrendTextColor("down");
      expect(result).toBe(STATUS_TEXT_COLORS.error);
    });

    it("should return neutral color for stable trend", () => {
      const result = getTrendTextColor("stable");
      expect(result).toBe(STATUS_TEXT_COLORS.neutral);
    });
  });

  describe("getSparklineColor", () => {
    it("should return success hex color for up trend", () => {
      const result = getSparklineColor("up");
      expect(result).toBe(SPARKLINE_COLORS.success);
    });

    it("should return error hex color for down trend", () => {
      const result = getSparklineColor("down");
      expect(result).toBe(SPARKLINE_COLORS.error);
    });

    it("should return neutral hex color for stable trend", () => {
      const result = getSparklineColor("stable");
      expect(result).toBe(SPARKLINE_COLORS.neutral);
    });
  });

  describe("getLogLevelStyle", () => {
    it("should return correct style for each log level", () => {
      expect(getLogLevelStyle("debug")).toBe(LEVEL_BADGE_STYLES.debug);
      expect(getLogLevelStyle("info")).toBe(LEVEL_BADGE_STYLES.info);
      expect(getLogLevelStyle("warning")).toBe(LEVEL_BADGE_STYLES.warning);
      expect(getLogLevelStyle("error")).toBe(LEVEL_BADGE_STYLES.error);
    });

    it("should return debug style as fallback for unknown levels", () => {
      // Cast to any to test edge case
      const result = getLogLevelStyle("unknown" as LogLevel);
      expect(result).toBe(LEVEL_BADGE_STYLES.debug);
    });
  });

  describe("getHttpMethodColor", () => {
    it("should return correct color for each HTTP method", () => {
      expect(getHttpMethodColor("GET")).toBe(HTTP_METHOD_COLORS.GET);
      expect(getHttpMethodColor("POST")).toBe(HTTP_METHOD_COLORS.POST);
      expect(getHttpMethodColor("PUT")).toBe(HTTP_METHOD_COLORS.PUT);
      expect(getHttpMethodColor("DELETE")).toBe(HTTP_METHOD_COLORS.DELETE);
      expect(getHttpMethodColor("PATCH")).toBe(HTTP_METHOD_COLORS.PATCH);
    });

    it("should return DEFAULT color for unknown methods", () => {
      expect(getHttpMethodColor("OPTIONS")).toBe(HTTP_METHOD_COLORS.DEFAULT);
      expect(getHttpMethodColor("HEAD")).toBe(HTTP_METHOD_COLORS.DEFAULT);
      expect(getHttpMethodColor("CUSTOM")).toBe(HTTP_METHOD_COLORS.DEFAULT);
    });
  });

  describe("getStreamStatusStyle", () => {
    it("should return correct style for each stream status", () => {
      expect(getStreamStatusStyle("active")).toBe(STREAM_STATUS_STYLES.active);
      expect(getStreamStatusStyle("success")).toBe(
        STREAM_STATUS_STYLES.success,
      );
      expect(getStreamStatusStyle("error")).toBe(STREAM_STATUS_STYLES.error);
      expect(getStreamStatusStyle("cancelled")).toBe(
        STREAM_STATUS_STYLES.cancelled,
      );
    });
  });

  describe("getStatusCodeColor", () => {
    it("should return neutral for undefined status code", () => {
      expect(getStatusCodeColor(undefined)).toBe(STATUS_TEXT_COLORS.neutral);
    });

    it("should return success for 2xx status codes", () => {
      expect(getStatusCodeColor(200)).toBe(STATUS_TEXT_COLORS.success);
      expect(getStatusCodeColor(201)).toBe(STATUS_TEXT_COLORS.success);
      expect(getStatusCodeColor(204)).toBe(STATUS_TEXT_COLORS.success);
      expect(getStatusCodeColor(299)).toBe(STATUS_TEXT_COLORS.success);
    });

    it("should return info for 3xx status codes", () => {
      expect(getStatusCodeColor(301)).toBe(STATUS_TEXT_COLORS.info);
      expect(getStatusCodeColor(302)).toBe(STATUS_TEXT_COLORS.info);
      expect(getStatusCodeColor(304)).toBe(STATUS_TEXT_COLORS.info);
    });

    it("should return warning for 4xx status codes", () => {
      expect(getStatusCodeColor(400)).toBe(STATUS_TEXT_COLORS.warning);
      expect(getStatusCodeColor(401)).toBe(STATUS_TEXT_COLORS.warning);
      expect(getStatusCodeColor(404)).toBe(STATUS_TEXT_COLORS.warning);
      expect(getStatusCodeColor(422)).toBe(STATUS_TEXT_COLORS.warning);
    });

    it("should return error for 5xx status codes", () => {
      expect(getStatusCodeColor(500)).toBe(STATUS_TEXT_COLORS.error);
      expect(getStatusCodeColor(502)).toBe(STATUS_TEXT_COLORS.error);
      expect(getStatusCodeColor(503)).toBe(STATUS_TEXT_COLORS.error);
      expect(getStatusCodeColor(504)).toBe(STATUS_TEXT_COLORS.error);
    });

    it("should return neutral for 1xx status codes", () => {
      expect(getStatusCodeColor(100)).toBe(STATUS_TEXT_COLORS.neutral);
      expect(getStatusCodeColor(101)).toBe(STATUS_TEXT_COLORS.neutral);
    });
  });
});

// =============================================================================
// Tests: Brand Colors (Grafana, AI/Insights)
// =============================================================================

describe("Brand Colors", () => {
  describe("GRAFANA_COLORS", () => {
    it("should define Grafana brand orange color", async () => {
      const { GRAFANA_COLORS } = await import("./devToolsColors");
      expect(GRAFANA_COLORS).toBeDefined();
      expect(GRAFANA_COLORS.primary).toBeDefined();
    });

    it("should use Grafana brand orange (#F46800)", async () => {
      const { GRAFANA_COLORS } = await import("./devToolsColors");
      // Grafana's official brand color
      expect(GRAFANA_COLORS.primary).toBe("#F46800");
    });

    it("should include button styles", async () => {
      const { GRAFANA_COLORS } = await import("./devToolsColors");
      expect(GRAFANA_COLORS.button).toBeDefined();
      expect(GRAFANA_COLORS.button).toMatch(/bg-grafana-/);
      expect(GRAFANA_COLORS.button).toMatch(/hover:bg-grafana-/);
    });

    it("should include dark mode variant for button", async () => {
      const { GRAFANA_COLORS } = await import("./devToolsColors");
      expect(GRAFANA_COLORS.button).toMatch(/dark:/);
    });
  });

  describe("AI_INSIGHT_COLORS", () => {
    it("should define AI/insights purple color scheme", async () => {
      const { AI_INSIGHT_COLORS } = await import("./devToolsColors");
      expect(AI_INSIGHT_COLORS).toBeDefined();
      expect(AI_INSIGHT_COLORS.primary).toBeDefined();
    });

    it("should use semantic purple for AI insights", async () => {
      const { AI_INSIGHT_COLORS } = await import("./devToolsColors");
      // AI/insights uses purple as the distinctive color
      expect(AI_INSIGHT_COLORS.text).toMatch(/text-insight-/);
      expect(AI_INSIGHT_COLORS.bg).toMatch(/bg-insight-/);
    });

    it("should include sparkle/glow effect color", async () => {
      const { AI_INSIGHT_COLORS } = await import("./devToolsColors");
      expect(AI_INSIGHT_COLORS.glow).toBeDefined();
      expect(AI_INSIGHT_COLORS.glow).toMatch(/^#[0-9a-fA-F]{6}$/);
    });

    it("should include dark mode variants", async () => {
      const { AI_INSIGHT_COLORS } = await import("./devToolsColors");
      expect(AI_INSIGHT_COLORS.text).toMatch(/dark:/);
      expect(AI_INSIGHT_COLORS.bg).toMatch(/dark:/);
    });

    it("should provide badge style for AI indicators", async () => {
      const { AI_INSIGHT_COLORS } = await import("./devToolsColors");
      expect(AI_INSIGHT_COLORS.badge).toBeDefined();
      expect(AI_INSIGHT_COLORS.badge).toMatch(/bg-/);
      expect(AI_INSIGHT_COLORS.badge).toMatch(/text-/);
    });
  });

  describe("getGrafanaButtonStyle helper", () => {
    it("should return Grafana brand button styles", async () => {
      const { getGrafanaButtonStyle, GRAFANA_COLORS } =
        await import("./devToolsColors");
      expect(getGrafanaButtonStyle()).toBe(GRAFANA_COLORS.button);
    });
  });

  describe("getAIInsightStyle helper", () => {
    it("should return text style by default", async () => {
      const { getAIInsightStyle, AI_INSIGHT_COLORS } =
        await import("./devToolsColors");
      expect(getAIInsightStyle("text")).toBe(AI_INSIGHT_COLORS.text);
    });

    it("should return background style when requested", async () => {
      const { getAIInsightStyle, AI_INSIGHT_COLORS } =
        await import("./devToolsColors");
      expect(getAIInsightStyle("bg")).toBe(AI_INSIGHT_COLORS.bg);
    });

    it("should return badge style when requested", async () => {
      const { getAIInsightStyle, AI_INSIGHT_COLORS } =
        await import("./devToolsColors");
      expect(getAIInsightStyle("badge")).toBe(AI_INSIGHT_COLORS.badge);
    });
  });
});

// =============================================================================
// Tests: WCAG 2.2 Accessibility Compliance
// =============================================================================

describe("WCAG 2.2 Accessibility Compliance", () => {
  describe("Color Not Used Alone", () => {
    it("should provide distinct colors for different statuses (visual differentiation)", () => {
      // Statuses should have different base colors, not just shades
      const successBase = STATUS_TEXT_COLORS.success.match(/text-(\w+)-/)?.[1];
      const warningBase = STATUS_TEXT_COLORS.warning.match(/text-(\w+)-/)?.[1];
      const errorBase = STATUS_TEXT_COLORS.error.match(/text-(\w+)-/)?.[1];

      expect(successBase).not.toBe(warningBase);
      expect(successBase).not.toBe(errorBase);
      expect(warningBase).not.toBe(errorBase);
    });
  });

  describe("Dark Mode Support", () => {
    it("should have consistent dark mode pattern (dark:*-400 for text)", () => {
      // Dark mode text should use lighter shades (400) for readability on dark backgrounds
      Object.values(STATUS_TEXT_COLORS).forEach((color) => {
        // Extract dark mode class
        const darkClass = color.match(/dark:([\w-]+)/)?.[1];
        expect(darkClass).toBeDefined();
      });
    });

    it("should have lighter shades in dark mode than light mode", () => {
      // Light mode uses 600, dark mode should use 400 (lighter for dark backgrounds)
      const lightShade =
        STATUS_TEXT_COLORS.success.match(/text-success-(\d+)/)?.[1];
      const darkShade = STATUS_TEXT_COLORS.success.match(
        /dark:text-success-(\d+)/,
      )?.[1];

      expect(Number(darkShade)).toBeLessThan(Number(lightShade));
    });
  });

  describe("Minimum Font Size Compliance", () => {
    it("should not define font sizes (handled at component level)", () => {
      // Color utilities should not include text size - that's component responsibility
      // This ensures we don't accidentally include text-xs or similar
      Object.values(STATUS_TEXT_COLORS).forEach((color) => {
        expect(color).not.toMatch(/text-\[/); // No arbitrary values
        expect(color).not.toMatch(/text-xs/); // No size classes
        expect(color).not.toMatch(/text-sm/);
        expect(color).not.toMatch(/text-base/);
      });
    });
  });
});
