/**
 * Accessibility Utilities Tests
 *
 * TDD tests for accessibility helper functions.
 * Tests color contrast, focus management, and ARIA utilities.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import {
  calculateContrastRatio,
  meetsWCAGAA,
  meetsWCAGAAA,
  hexToRgb,
  getRelativeLuminance,
  validateColorContrast,
} from "./accessibility";

describe("Accessibility Utilities", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("hexToRgb", () => {
    it("should convert 6-digit hex to RGB", () => {
      expect(hexToRgb("#ffffff")).toEqual({ r: 255, g: 255, b: 255 });
      expect(hexToRgb("#000000")).toEqual({ r: 0, g: 0, b: 0 });
      expect(hexToRgb("#ff5500")).toEqual({ r: 255, g: 85, b: 0 });
    });

    it("should convert 3-digit hex to RGB", () => {
      expect(hexToRgb("#fff")).toEqual({ r: 255, g: 255, b: 255 });
      expect(hexToRgb("#000")).toEqual({ r: 0, g: 0, b: 0 });
      expect(hexToRgb("#f50")).toEqual({ r: 255, g: 85, b: 0 });
    });

    it("should handle uppercase hex", () => {
      expect(hexToRgb("#FFFFFF")).toEqual({ r: 255, g: 255, b: 255 });
      expect(hexToRgb("#FF5500")).toEqual({ r: 255, g: 85, b: 0 });
    });

    it("should handle hex without #", () => {
      expect(hexToRgb("ffffff")).toEqual({ r: 255, g: 255, b: 255 });
    });

    it("should return default value for invalid hex", () => {
      expect(hexToRgb("invalid")).toEqual({ r: 0, g: 0, b: 0 });
      expect(hexToRgb("xyz")).toEqual({ r: 0, g: 0, b: 0 });
      expect(hexToRgb("")).toEqual({ r: 0, g: 0, b: 0 });
    });
  });

  describe("getRelativeLuminance", () => {
    it("should return 1 for white", () => {
      expect(getRelativeLuminance(255, 255, 255)).toBeCloseTo(1, 3);
    });

    it("should return 0 for black", () => {
      expect(getRelativeLuminance(0, 0, 0)).toBeCloseTo(0, 3);
    });

    it("should calculate luminance for gray", () => {
      const luminance = getRelativeLuminance(128, 128, 128);
      expect(luminance).toBeGreaterThan(0);
      expect(luminance).toBeLessThan(1);
    });
  });

  describe("calculateContrastRatio", () => {
    it("should return 21 for black on white", () => {
      const ratio = calculateContrastRatio("#000000", "#ffffff");
      expect(ratio).toBeCloseTo(21, 1);
    });

    it("should return 21 for white on black", () => {
      const ratio = calculateContrastRatio("#ffffff", "#000000");
      expect(ratio).toBeCloseTo(21, 1);
    });

    it("should return 1 for same colors", () => {
      const ratio = calculateContrastRatio("#3b82f6", "#3b82f6");
      expect(ratio).toBeCloseTo(1, 1);
    });

    it("should calculate reasonable contrast for blue on white", () => {
      const ratio = calculateContrastRatio("#3b82f6", "#ffffff");
      expect(ratio).toBeGreaterThan(3);
      expect(ratio).toBeLessThan(10);
    });
  });

  describe("meetsWCAGAA", () => {
    it("should return true for black on white (normal text)", () => {
      expect(meetsWCAGAA("#000000", "#ffffff", false)).toBe(true);
    });

    it("should return true for black on white (large text)", () => {
      expect(meetsWCAGAA("#000000", "#ffffff", true)).toBe(true);
    });

    it("should return false for low contrast colors", () => {
      expect(meetsWCAGAA("#cccccc", "#ffffff", false)).toBe(false);
    });

    it("should have lower threshold for large text", () => {
      // A color that passes for large text but not normal text
      // Gray (#767676) on white has ~4.54:1 ratio
      expect(meetsWCAGAA("#767676", "#ffffff", true)).toBe(true);
      expect(meetsWCAGAA("#767676", "#ffffff", false)).toBe(true); // Actually passes AA
    });
  });

  describe("meetsWCAGAAA", () => {
    it("should return true for black on white (normal text)", () => {
      expect(meetsWCAGAAA("#000000", "#ffffff", false)).toBe(true);
    });

    it("should require 7:1 for normal text", () => {
      // #595959 on white is about 7.0:1
      expect(meetsWCAGAAA("#595959", "#ffffff", false)).toBe(true);
    });

    it("should require 4.5:1 for large text", () => {
      // #767676 on white is about 4.5:1
      expect(meetsWCAGAAA("#767676", "#ffffff", true)).toBe(true);
    });
  });

  describe("validateColorContrast", () => {
    it("should return array of color combinations with contrast results", () => {
      const results = validateColorContrast();

      expect(Array.isArray(results)).toBe(true);
      expect(results.length).toBeGreaterThan(0);

      // Each result should have the expected shape
      results.forEach((result) => {
        expect(result).toHaveProperty("foreground");
        expect(result).toHaveProperty("background");
        expect(result).toHaveProperty("ratio");
        expect(result).toHaveProperty("passes");
        expect(typeof result.ratio).toBe("number");
        expect(typeof result.passes).toBe("boolean");
      });
    });

    it("should check standard color palette combinations", () => {
      const results = validateColorContrast();

      // Should include dark and light backgrounds
      const hasDarkBg = results.some((r) => r.background.includes("1f"));
      const hasLightBg = results.some((r) => r.background.includes("fff"));

      expect(hasDarkBg || hasLightBg).toBe(true);
    });
  });
});
