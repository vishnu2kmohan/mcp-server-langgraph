/**
 * Tests for Numeric Utilities (NaN/Infinity Safety)
 *
 * Validates that all safe* functions properly handle edge cases
 * that could cause JSON serialization failures or UI crashes.
 */

import { afterEach, describe, expect, it, vi } from "vitest";
import {
  safeFloat,
  safeAverage,
  safeDivide,
  safeRound,
  safeSum,
  safePercentage,
  formatSafeNumber,
} from "./numeric";

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("safeFloat", () => {
  it("returns the value unchanged for normal numbers", () => {
    expect(safeFloat(42)).toBe(42);
    expect(safeFloat(3.14159)).toBe(3.14159);
    expect(safeFloat(-100)).toBe(-100);
    expect(safeFloat(0)).toBe(0);
  });

  it("returns default for NaN", () => {
    expect(safeFloat(NaN)).toBe(0.0);
    expect(safeFloat(NaN, 99)).toBe(99);
  });

  it("returns default for Infinity", () => {
    expect(safeFloat(Infinity)).toBe(0.0);
    expect(safeFloat(-Infinity)).toBe(0.0);
    expect(safeFloat(Infinity, -1)).toBe(-1);
  });

  it("returns default for null and undefined", () => {
    expect(safeFloat(null)).toBe(0.0);
    expect(safeFloat(undefined)).toBe(0.0);
    expect(safeFloat(null, 5)).toBe(5);
  });
});

describe("safeAverage", () => {
  it("calculates average for normal arrays", () => {
    expect(safeAverage([1, 2, 3, 4, 5])).toBe(3);
    expect(safeAverage([10, 20])).toBe(15);
    expect(safeAverage([100])).toBe(100);
  });

  it("returns 0 for empty arrays", () => {
    expect(safeAverage([])).toBe(0.0);
  });

  it("filters out NaN values", () => {
    expect(safeAverage([1, NaN, 3])).toBe(2); // (1+3)/2
    expect(safeAverage([NaN, NaN, NaN])).toBe(0.0);
  });

  it("filters out Infinity values", () => {
    expect(safeAverage([1, Infinity, 3])).toBe(2); // (1+3)/2
    expect(safeAverage([Infinity, -Infinity])).toBe(0.0);
  });

  it("handles mixed invalid values", () => {
    expect(safeAverage([NaN, 10, Infinity, 20, -Infinity])).toBe(15);
  });
});

describe("safeDivide", () => {
  it("performs normal division", () => {
    expect(safeDivide(10, 2)).toBe(5);
    expect(safeDivide(1, 3)).toBeCloseTo(0.333, 2);
    expect(safeDivide(0, 5)).toBe(0);
  });

  it("returns default for division by zero", () => {
    expect(safeDivide(10, 0)).toBe(0.0);
    expect(safeDivide(10, 0, -1)).toBe(-1);
  });

  it("returns default when numerator is NaN/Infinity", () => {
    expect(safeDivide(NaN, 2)).toBe(0.0);
    expect(safeDivide(Infinity, 2)).toBe(0.0);
  });

  it("returns default when denominator is NaN/Infinity", () => {
    expect(safeDivide(10, NaN)).toBe(0.0);
    expect(safeDivide(10, Infinity)).toBe(0.0);
  });
});

describe("safeRound", () => {
  it("rounds to specified decimal places", () => {
    expect(safeRound(3.14159, 2)).toBe(3.14);
    expect(safeRound(3.14159, 3)).toBe(3.142);
    expect(safeRound(3.14159, 0)).toBe(3);
  });

  it("uses default of 2 decimal places", () => {
    expect(safeRound(3.14159)).toBe(3.14);
  });

  it("returns default for NaN", () => {
    expect(safeRound(NaN)).toBe(0.0);
    expect(safeRound(NaN, 2, 99)).toBe(99);
  });

  it("returns default for Infinity", () => {
    expect(safeRound(Infinity)).toBe(0.0);
    expect(safeRound(-Infinity, 2, -1)).toBe(-1);
  });
});

describe("safeSum", () => {
  it("sums normal arrays", () => {
    expect(safeSum([1, 2, 3, 4, 5])).toBe(15);
    expect(safeSum([10, -10])).toBe(0);
    expect(safeSum([42])).toBe(42);
  });

  it("returns 0 for empty arrays", () => {
    expect(safeSum([])).toBe(0.0);
  });

  it("filters out NaN values", () => {
    expect(safeSum([1, NaN, 3])).toBe(4);
    expect(safeSum([NaN, NaN])).toBe(0);
  });

  it("filters out Infinity values", () => {
    expect(safeSum([1, Infinity, 3])).toBe(4);
  });
});

describe("safePercentage", () => {
  it("calculates percentage for valid values", () => {
    expect(safePercentage(50, 100)).toBe(50.0);
    expect(safePercentage(25, 100)).toBe(25.0);
    expect(safePercentage(100, 100)).toBe(100.0);
    expect(safePercentage(0, 100)).toBe(0.0);
    expect(safePercentage(1, 4)).toBe(25.0);
  });

  it("returns default for division by zero", () => {
    expect(safePercentage(50, 0)).toBe(0.0);
    expect(safePercentage(50, 0, { defaultValue: 50 })).toBe(50);
  });

  it("returns default for NaN values", () => {
    expect(safePercentage(NaN, 100)).toBe(0.0);
    expect(safePercentage(50, NaN)).toBe(0.0);
  });

  it("clamps to 0-100 by default", () => {
    expect(safePercentage(150, 100)).toBe(100.0);
    expect(safePercentage(-50, 100)).toBe(0.0);
  });

  it("allows unclamped values when clamp is false", () => {
    expect(safePercentage(150, 100, { clamp: false })).toBe(150.0);
    expect(safePercentage(-50, 100, { clamp: false })).toBe(-50.0);
  });

  it("supports custom bounds", () => {
    expect(safePercentage(150, 100, { minVal: 10, maxVal: 90 })).toBe(90);
    expect(safePercentage(5, 100, { minVal: 10, maxVal: 90 })).toBe(10);
    expect(safePercentage(50, 100, { minVal: 10, maxVal: 90 })).toBe(50);
  });

  it("rounds to specified precision", () => {
    expect(safePercentage(1, 3, { decimals: 2 })).toBe(33.33);
    expect(safePercentage(1, 3, { decimals: 1 })).toBe(33.3);
    expect(safePercentage(1, 3, { decimals: 0 })).toBe(33);
  });

  it("handles Infinity values", () => {
    expect(safePercentage(Infinity, 100)).toBe(0.0);
    expect(safePercentage(100, Infinity)).toBe(0.0);
    expect(safePercentage(-Infinity, 100)).toBe(0.0);
  });
});

describe("formatSafeNumber", () => {
  it("formats normal numbers", () => {
    expect(formatSafeNumber(3.14159)).toBe("3.14");
    expect(formatSafeNumber(42.5, "-", 1)).toBe("42.5");
    expect(formatSafeNumber(100, "-", 0)).toBe("100");
  });

  it("returns placeholder for null", () => {
    expect(formatSafeNumber(null)).toBe("-");
    expect(formatSafeNumber(null, "N/A")).toBe("N/A");
  });

  it("returns placeholder for undefined", () => {
    expect(formatSafeNumber(undefined)).toBe("-");
  });

  it("returns placeholder for NaN", () => {
    expect(formatSafeNumber(NaN)).toBe("-");
    expect(formatSafeNumber(NaN, "N/A")).toBe("N/A");
  });

  it("returns placeholder for Infinity", () => {
    expect(formatSafeNumber(Infinity)).toBe("-");
    expect(formatSafeNumber(-Infinity, "INF")).toBe("INF");
  });
});
