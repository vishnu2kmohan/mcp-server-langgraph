/**
 * MCP Module Export Tests
 *
 * Verifies that all expected exports are accessible from the module's index.
 * This ensures module organization and prevents accidental breaking changes.
 */
import { describe, it, expect, vi, afterEach } from "vitest";
import * as mcpModule from "./index";

describe("MCP Module Exports", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

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

  describe("Aggregated Capabilities Components (MCP 2025-11-25)", () => {
    it("should export AggregatedCapabilitiesPanel", () => {
      expect(mcpModule.AggregatedCapabilitiesPanel).toBeDefined();
      expect(typeof mcpModule.AggregatedCapabilitiesPanel).toBe("function");
    });

    it("should export MCPServerCard", () => {
      expect(mcpModule.MCPServerCard).toBeDefined();
      expect(typeof mcpModule.MCPServerCard).toBe("function");
    });

    it("should export ToolExplorer", () => {
      expect(mcpModule.ToolExplorer).toBeDefined();
      expect(typeof mcpModule.ToolExplorer).toBe("function");
    });

    it("should export ResourceBrowser", () => {
      expect(mcpModule.ResourceBrowser).toBeDefined();
      expect(typeof mcpModule.ResourceBrowser).toBe("function");
    });

    it("should export PromptLibrary", () => {
      expect(mcpModule.PromptLibrary).toBeDefined();
      expect(typeof mcpModule.PromptLibrary).toBe("function");
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
        // Aggregated capabilities (MCP 2025-11-25)
        "AggregatedCapabilitiesPanel",
        "MCPServerCard",
        "ToolExplorer",
        "ResourceBrowser",
        "PromptLibrary",
        // Lazy exports
        "LazyAddConnectionDialog",
        "LazyToolInvocationDialog",
        "LazyResourceViewer",
        "LazyPromptTester",
        "LazyElicitationDialog",
        // Lazy aggregated capabilities (MCP 2025-11-25)
        "LazyAggregatedCapabilitiesPanel",
        "LazyMCPServerCard",
        "LazyToolExplorer",
        "LazyResourceBrowser",
        "LazyPromptLibrary",
      ];

      for (const name of expectedExports) {
        expect(mcpModule).toHaveProperty(name);
      }
    });

    it("should have stable public API with 20 exports", () => {
      const exportCount = Object.keys(mcpModule).length;
      expect(exportCount).toBe(20);
    });
  });
});
