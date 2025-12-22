/**
 * AI Module Export Tests
 *
 * Verifies that all expected exports are accessible from the module's index.
 * This ensures module organization and prevents accidental breaking changes.
 */
import { describe, it, expect } from "vitest";
import * as aiModule from "./index";

describe("AI Module Exports", () => {
  describe("Components", () => {
    it("should export InlineSuggestions", () => {
      expect(aiModule.InlineSuggestions).toBeDefined();
      expect(typeof aiModule.InlineSuggestions).toBe("function");
    });

    it("should export BackgroundAgentPanel", () => {
      expect(aiModule.BackgroundAgentPanel).toBeDefined();
      expect(typeof aiModule.BackgroundAgentPanel).toBe("function");
    });

    it("should export AICommandPalette", () => {
      expect(aiModule.AICommandPalette).toBeDefined();
      expect(typeof aiModule.AICommandPalette).toBe("function");
    });

    it("should export AIEditOverlay", () => {
      expect(aiModule.AIEditOverlay).toBeDefined();
      expect(typeof aiModule.AIEditOverlay).toBe("function");
    });

    it("should export SuggestionChip", () => {
      expect(aiModule.SuggestionChip).toBeDefined();
      expect(typeof aiModule.SuggestionChip).toBe("function");
    });

    it("should export AgentTaskQueue", () => {
      expect(aiModule.AgentTaskQueue).toBeDefined();
      expect(typeof aiModule.AgentTaskQueue).toBe("function");
    });
  });

  describe("Module Completeness", () => {
    it("should export exactly 6 components", () => {
      const componentExports = [
        "InlineSuggestions",
        "BackgroundAgentPanel",
        "AICommandPalette",
        "AIEditOverlay",
        "SuggestionChip",
        "AgentTaskQueue",
      ];

      for (const name of componentExports) {
        expect(aiModule).toHaveProperty(name);
      }
    });

    it("should have stable public API", () => {
      // Snapshot of expected exports - update when intentionally changing API
      const expectedExports = [
        "InlineSuggestions",
        "BackgroundAgentPanel",
        "AICommandPalette",
        "AIEditOverlay",
        "SuggestionChip",
        "AgentTaskQueue",
      ];

      const actualExports = Object.keys(aiModule).filter(
        (key) => typeof aiModule[key as keyof typeof aiModule] === "function",
      );

      expect(actualExports.sort()).toEqual(expectedExports.sort());
    });
  });
});
