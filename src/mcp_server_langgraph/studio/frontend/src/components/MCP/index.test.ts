/**
 * MCP Module Export Tests
 *
 * Verifies that all expected exports are accessible from the module's index.
 * This ensures module organization and prevents accidental breaking changes.
 */
import { describe, it, expect } from "vitest";
import * as mcpModule from "./index";

describe("MCP Module Exports", () => {
  describe("Synchronous Components", () => {
    it("should export AddConnectionDialog", () => {
      expect(mcpModule.AddConnectionDialog).toBeDefined();
      expect(typeof mcpModule.AddConnectionDialog).toBe("function");
    });

    it("should export ToolInvocationDialog", () => {
      expect(mcpModule.ToolInvocationDialog).toBeDefined();
      expect(typeof mcpModule.ToolInvocationDialog).toBe("function");
    });

    it("should export ResourceViewer", () => {
      expect(mcpModule.ResourceViewer).toBeDefined();
      expect(typeof mcpModule.ResourceViewer).toBe("function");
    });

    it("should export PromptTester", () => {
      expect(mcpModule.PromptTester).toBeDefined();
      expect(typeof mcpModule.PromptTester).toBe("function");
    });

    it("should export ElicitationDialog", () => {
      expect(mcpModule.ElicitationDialog).toBeDefined();
      expect(typeof mcpModule.ElicitationDialog).toBe("function");
    });
  });

  describe("Lazy Components", () => {
    it("should export LazyAddConnectionDialog", () => {
      expect(mcpModule.LazyAddConnectionDialog).toBeDefined();
    });

    it("should export LazyToolInvocationDialog", () => {
      expect(mcpModule.LazyToolInvocationDialog).toBeDefined();
    });

    it("should export LazyResourceViewer", () => {
      expect(mcpModule.LazyResourceViewer).toBeDefined();
    });

    it("should export LazyPromptTester", () => {
      expect(mcpModule.LazyPromptTester).toBeDefined();
    });

    it("should export LazyElicitationDialog", () => {
      expect(mcpModule.LazyElicitationDialog).toBeDefined();
    });
  });

  describe("Module Completeness", () => {
    it("should export all expected components", () => {
      const expectedExports = [
        // Synchronous exports
        "AddConnectionDialog",
        "ToolInvocationDialog",
        "ResourceViewer",
        "PromptTester",
        "ElicitationDialog",
        // Lazy exports
        "LazyAddConnectionDialog",
        "LazyToolInvocationDialog",
        "LazyResourceViewer",
        "LazyPromptTester",
        "LazyElicitationDialog",
      ];

      for (const name of expectedExports) {
        expect(mcpModule).toHaveProperty(name);
      }
    });

    it("should have stable public API with 10 exports", () => {
      const exportCount = Object.keys(mcpModule).length;
      expect(exportCount).toBe(10);
    });
  });
});
