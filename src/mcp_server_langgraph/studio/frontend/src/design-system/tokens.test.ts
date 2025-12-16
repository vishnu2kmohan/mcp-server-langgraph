/**
 * Design Tokens Tests
 *
 * TDD tests for the design system tokens.
 * Validates color palette, typography, spacing, and shadows.
 */

import { describe, it, expect } from "vitest";
import {
  colors,
  typography,
  spacing,
  shadows,
  borderRadius,
  breakpoints,
  zIndex,
  getColorValue,
  getSpacingValue,
} from "./tokens";

describe("Design Tokens", () => {
  describe("Colors", () => {
    it("should have primary brand colors", () => {
      expect(colors.primary).toBeDefined();
      expect(colors.primary[500]).toBeDefined();
      expect(colors.primary[600]).toBeDefined();
    });

    it("should have semantic colors", () => {
      expect(colors.success).toBeDefined();
      expect(colors.warning).toBeDefined();
      expect(colors.error).toBeDefined();
      expect(colors.info).toBeDefined();
    });

    it("should have neutral gray scale", () => {
      expect(colors.gray).toBeDefined();
      expect(colors.gray[50]).toBeDefined();
      expect(colors.gray[900]).toBeDefined();
    });

    it("should have valid hex color format", () => {
      const hexRegex = /^#[0-9A-Fa-f]{6}$/;
      expect(colors.primary[500]).toMatch(hexRegex);
      expect(colors.gray[500]).toMatch(hexRegex);
    });
  });

  describe("Typography", () => {
    it("should have font families", () => {
      expect(typography.fontFamily.sans).toBeDefined();
      expect(typography.fontFamily.mono).toBeDefined();
    });

    it("should have font sizes", () => {
      expect(typography.fontSize.xs).toBeDefined();
      expect(typography.fontSize.sm).toBeDefined();
      expect(typography.fontSize.base).toBeDefined();
      expect(typography.fontSize.lg).toBeDefined();
      expect(typography.fontSize.xl).toBeDefined();
    });

    it("should have font weights", () => {
      expect(typography.fontWeight.normal).toBe(400);
      expect(typography.fontWeight.medium).toBe(500);
      expect(typography.fontWeight.semibold).toBe(600);
      expect(typography.fontWeight.bold).toBe(700);
    });

    it("should have line heights", () => {
      expect(typography.lineHeight.tight).toBeDefined();
      expect(typography.lineHeight.normal).toBeDefined();
      expect(typography.lineHeight.relaxed).toBeDefined();
    });
  });

  describe("Spacing", () => {
    it("should have spacing scale", () => {
      expect(spacing[0]).toBe("0");
      expect(spacing[1]).toBeDefined();
      expect(spacing[2]).toBeDefined();
      expect(spacing[4]).toBeDefined();
      expect(spacing[8]).toBeDefined();
    });

    it("should use rem units", () => {
      expect(spacing[4]).toMatch(/rem$/);
    });
  });

  describe("Shadows", () => {
    it("should have shadow variants", () => {
      expect(shadows.sm).toBeDefined();
      expect(shadows.md).toBeDefined();
      expect(shadows.lg).toBeDefined();
      expect(shadows.xl).toBeDefined();
    });

    it("should have none shadow option", () => {
      expect(shadows.none).toBe("none");
    });
  });

  describe("Border Radius", () => {
    it("should have radius variants", () => {
      expect(borderRadius.none).toBe("0");
      expect(borderRadius.sm).toBeDefined();
      expect(borderRadius.md).toBeDefined();
      expect(borderRadius.lg).toBeDefined();
      expect(borderRadius.full).toBe("9999px");
    });
  });

  describe("Breakpoints", () => {
    it("should have responsive breakpoints", () => {
      expect(breakpoints.sm).toBeDefined();
      expect(breakpoints.md).toBeDefined();
      expect(breakpoints.lg).toBeDefined();
      expect(breakpoints.xl).toBeDefined();
    });

    it("should be in pixel format", () => {
      expect(breakpoints.sm).toMatch(/px$/);
    });
  });

  describe("Z-Index", () => {
    it("should have z-index scale", () => {
      expect(zIndex.base).toBe(0);
      expect(zIndex.dropdown).toBeGreaterThan(zIndex.base);
      expect(zIndex.modal).toBeGreaterThan(zIndex.dropdown);
      expect(zIndex.tooltip).toBeDefined();
    });

    it("should have proper stacking order", () => {
      expect(zIndex.modal).toBeGreaterThan(zIndex.dropdown);
      expect(zIndex.toast).toBeGreaterThan(zIndex.modal);
    });
  });

  describe("Helper Functions", () => {
    it("should get color value by path", () => {
      expect(getColorValue("primary.500")).toBe(colors.primary[500]);
      expect(getColorValue("gray.100")).toBe(colors.gray[100]);
    });

    it("should return undefined for invalid color path", () => {
      expect(getColorValue("invalid.path")).toBeUndefined();
    });

    it("should get spacing value by key", () => {
      expect(getSpacingValue(4)).toBe(spacing[4]);
      expect(getSpacingValue(8)).toBe(spacing[8]);
    });
  });
});
