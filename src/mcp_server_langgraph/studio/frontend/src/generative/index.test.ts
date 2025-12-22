/**
 * Generative Module Export Tests
 *
 * Verifies that all expected exports are accessible from the module's index.
 * This ensures module organization and prevents accidental breaking changes.
 */
import { describe, it, expect } from "vitest";
import * as generativeModule from "./index";

describe("Generative Module Exports", () => {
  describe("Components", () => {
    it("should export GenerativeWidget", () => {
      expect(generativeModule.GenerativeWidget).toBeDefined();
      expect(typeof generativeModule.GenerativeWidget).toBe("function");
    });

    it("should export InteractiveForm", () => {
      expect(generativeModule.InteractiveForm).toBeDefined();
      expect(typeof generativeModule.InteractiveForm).toBe("function");
    });

    it("should export DataExplorer", () => {
      expect(generativeModule.DataExplorer).toBeDefined();
      expect(typeof generativeModule.DataExplorer).toBe("function");
    });

    it("should export ExecutableCanvas", () => {
      expect(generativeModule.ExecutableCanvas).toBeDefined();
      expect(typeof generativeModule.ExecutableCanvas).toBe("function");
    });
  });

  describe("Module Completeness", () => {
    it("should export exactly 4 components", () => {
      const componentExports = [
        "GenerativeWidget",
        "InteractiveForm",
        "DataExplorer",
        "ExecutableCanvas",
      ];

      for (const name of componentExports) {
        expect(generativeModule).toHaveProperty(name);
      }
    });

    it("should have stable public API", () => {
      // Snapshot of expected exports - update when intentionally changing API
      const expectedExports = [
        "GenerativeWidget",
        "InteractiveForm",
        "DataExplorer",
        "ExecutableCanvas",
      ];

      const actualExports = Object.keys(generativeModule).filter(
        (key) =>
          typeof generativeModule[key as keyof typeof generativeModule] ===
          "function",
      );

      expect(actualExports.sort()).toEqual(expectedExports.sort());
    });
  });
});
