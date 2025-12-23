/**
 * Help Module Export Tests
 *
 * Verifies that all expected exports are accessible from the module's index.
 * This ensures module organization and prevents accidental breaking changes.
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import * as helpModule from "./index";

describe("Help Module Exports", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("Components", () => {
    it("should export HelpPane", () => {
      expect(helpModule.HelpPane).toBeDefined();
      expect(typeof helpModule.HelpPane).toBe("function");
    });

    it("should export ContextualHelp", () => {
      expect(helpModule.ContextualHelp).toBeDefined();
      expect(typeof helpModule.ContextualHelp).toBe("function");
    });

    it("should export KeyboardShortcuts", () => {
      expect(helpModule.KeyboardShortcuts).toBeDefined();
      expect(typeof helpModule.KeyboardShortcuts).toBe("function");
    });

    it("should export ComplianceGuides", () => {
      expect(helpModule.ComplianceGuides).toBeDefined();
      expect(typeof helpModule.ComplianceGuides).toBe("function");
    });
  });

  describe("Module Completeness", () => {
    it("should export exactly 4 components", () => {
      const componentExports = [
        "HelpPane",
        "ContextualHelp",
        "KeyboardShortcuts",
        "ComplianceGuides",
      ];

      for (const name of componentExports) {
        expect(helpModule).toHaveProperty(name);
      }
    });

    it("should have stable public API", () => {
      // Snapshot of expected exports - update when intentionally changing API
      const expectedExports = [
        "HelpPane",
        "ContextualHelp",
        "KeyboardShortcuts",
        "ComplianceGuides",
      ];

      const actualExports = Object.keys(helpModule).filter(
        (key) =>
          typeof helpModule[key as keyof typeof helpModule] === "function",
      );

      expect(actualExports.sort()).toEqual(expectedExports.sort());
    });
  });
});
