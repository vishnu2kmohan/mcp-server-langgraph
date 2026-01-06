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

  // Note: MCP module only exports lazy components for code-splitting
  // Synchronous component exports were removed in favor of lazy-only pattern
  // Type exports (e.g., AddConnectionDialogProps) are type-only and don't appear at runtime

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

  describe("Lazy Aggregated Capabilities Components (MCP 2025-11-25)", () => {
    it("should export LazyAggregatedCapabilitiesPanel", () => {
      expect(mcpModule.LazyAggregatedCapabilitiesPanel).toBeDefined();
    });

    it("should export LazyMCPServerCard", () => {
      expect(mcpModule.LazyMCPServerCard).toBeDefined();
    });

    it("should export LazyToolExplorer", () => {
      expect(mcpModule.LazyToolExplorer).toBeDefined();
    });

    it("should export LazyResourceBrowser", () => {
      expect(mcpModule.LazyResourceBrowser).toBeDefined();
    });

    it("should export LazyPromptLibrary", () => {
      expect(mcpModule.LazyPromptLibrary).toBeDefined();
    });
  });

  describe("Module Completeness", () => {
    it("should export all expected lazy components", () => {
      // Note: Only lazy exports appear at runtime
      // Type-only exports (e.g., AddConnectionDialogProps) don't appear
      const expectedExports = [
        // Lazy exports (code-split, loaded on demand)
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

    it("should have stable public API with 10 lazy exports", () => {
      // Note: Type-only exports (10) don't appear at runtime
      // Only the 10 lazy component exports are counted
      const exportCount = Object.keys(mcpModule).length;
      expect(exportCount).toBe(10);
    });
  });
});
