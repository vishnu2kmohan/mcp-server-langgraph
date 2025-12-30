/**
 * Canvas Utility Functions Tests
 *
 * Tests for utility functions in canvasUtils.ts.
 * Includes type alignment validation to ensure function behavior
 * matches the CanvasArtifact contentType union.
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import { getVisibleTabs } from "./canvasUtils";
import type { CanvasArtifact } from "../types/artifacts";

describe("canvasUtils", () => {
  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("getVisibleTabs", () => {
    // ==========================================================================
    // Type Alignment Tests
    // Ensures getVisibleTabs handles ALL valid contentTypes from CanvasArtifact
    // Valid contentTypes: "code" | "markdown" | "json" | "jsx" | "mermaid" | "html"
    // ==========================================================================

    describe("Type Alignment", () => {
      // Define the valid content types from CanvasArtifact type
      // This ensures test stays in sync with the type definition
      const validContentTypes: CanvasArtifact["contentType"][] = [
        "code",
        "markdown",
        "json",
        "jsx",
        "mermaid",
        "html",
      ];

      it("handles all valid content types without error", () => {
        // Verify function doesn't throw for any valid content type
        validContentTypes.forEach((contentType) => {
          expect(() => getVisibleTabs(contentType)).not.toThrow();
        });
      });

      it("returns array containing 'code' for all content types", () => {
        // All content types should always have the "code" tab
        validContentTypes.forEach((contentType) => {
          const tabs = getVisibleTabs(contentType);
          expect(tabs).toContain("code");
        });
      });

      it("returns correct tabs for each content type", () => {
        // Code: only code tab
        expect(getVisibleTabs("code")).toEqual(["code"]);

        // Previewable types: code + preview
        expect(getVisibleTabs("markdown")).toEqual(["code", "preview"]);
        expect(getVisibleTabs("mermaid")).toEqual(["code", "preview"]);
        expect(getVisibleTabs("html")).toEqual(["code", "preview"]);
        expect(getVisibleTabs("jsx")).toEqual(["code", "preview"]);

        // Data types: code + data
        expect(getVisibleTabs("json")).toEqual(["code", "data"]);
      });
    });

    // ==========================================================================
    // Case Insensitivity Tests
    // ==========================================================================

    describe("Case Insensitivity", () => {
      it("handles uppercase content types", () => {
        expect(getVisibleTabs("MERMAID")).toEqual(["code", "preview"]);
        expect(getVisibleTabs("JSON")).toEqual(["code", "data"]);
      });

      it("handles mixed case content types", () => {
        expect(getVisibleTabs("Markdown")).toEqual(["code", "preview"]);
        expect(getVisibleTabs("Html")).toEqual(["code", "preview"]);
      });
    });

    // ==========================================================================
    // Edge Cases
    // ==========================================================================

    describe("Edge Cases", () => {
      it("returns only code tab for unknown content types", () => {
        expect(getVisibleTabs("unknown")).toEqual(["code"]);
        expect(getVisibleTabs("")).toEqual(["code"]);
        expect(getVisibleTabs("typescript")).toEqual(["code"]);
      });

      it("handles content types that were removed from union", () => {
        // These types were previously in getVisibleTabs but not in CanvasArtifact union
        // They should gracefully fallback to code-only
        expect(getVisibleTabs("tsx")).toEqual(["code"]);
        expect(getVisibleTabs("svg")).toEqual(["code"]);
      });

      it("handles undefined contentType gracefully (runtime safety)", () => {
        // Runtime data may have undefined contentType even if TypeScript says required
        // This prevents "can't access property toLowerCase, e is undefined" crash
        expect(getVisibleTabs(undefined as unknown as string)).toEqual([
          "code",
        ]);
        expect(getVisibleTabs(null as unknown as string)).toEqual(["code"]);
      });
    });

    // ==========================================================================
    // Return Type Validation
    // ==========================================================================

    describe("Return Type", () => {
      it("returns an array of TabType values", () => {
        const tabs = getVisibleTabs("mermaid");
        expect(Array.isArray(tabs)).toBe(true);
        expect(tabs.every((t) => ["code", "preview", "data"].includes(t))).toBe(
          true,
        );
      });

      it("returns at least one tab", () => {
        const tabs = getVisibleTabs("any");
        expect(tabs.length).toBeGreaterThanOrEqual(1);
      });

      it("returns unique tabs (no duplicates)", () => {
        const tabs = getVisibleTabs("json");
        const uniqueTabs = [...new Set(tabs)];
        expect(tabs.length).toBe(uniqueTabs.length);
      });
    });
  });
});
