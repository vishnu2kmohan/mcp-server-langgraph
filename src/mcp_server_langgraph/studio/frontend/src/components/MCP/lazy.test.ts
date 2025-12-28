/**
 * Lazy MCP Components Tests (TDD)
 *
 * Tests for lazy-loaded MCP components to ensure code splitting works correctly.
 *
 * Following TDD: RED phase - write failing tests first
 */

import { describe, it, expect, vi, afterEach } from "vitest";

describe("Lazy MCP Components", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("exports LazyAddConnectionDialog", async () => {
    const lazyModule = await import("./lazy");
    expect(lazyModule.LazyAddConnectionDialog).toBeDefined();
    expect(typeof lazyModule.LazyAddConnectionDialog).toBe("object");
  });

  it("exports LazyToolInvocationDialog", async () => {
    const lazyModule = await import("./lazy");
    expect(lazyModule.LazyToolInvocationDialog).toBeDefined();
    expect(typeof lazyModule.LazyToolInvocationDialog).toBe("object");
  });

  it("exports LazyResourceViewer", async () => {
    const lazyModule = await import("./lazy");
    expect(lazyModule.LazyResourceViewer).toBeDefined();
    expect(typeof lazyModule.LazyResourceViewer).toBe("object");
  });

  it("exports LazyPromptTester", async () => {
    const lazyModule = await import("./lazy");
    expect(lazyModule.LazyPromptTester).toBeDefined();
    expect(typeof lazyModule.LazyPromptTester).toBe("object");
  });

  it("exports LazyElicitationDialog", async () => {
    const lazyModule = await import("./lazy");
    expect(lazyModule.LazyElicitationDialog).toBeDefined();
    expect(typeof lazyModule.LazyElicitationDialog).toBe("object");
  });

  // Aggregated Capabilities Components (MCP 2025-11-25)
  it("exports LazyAggregatedCapabilitiesPanel", async () => {
    const lazyModule = await import("./lazy");
    expect(lazyModule.LazyAggregatedCapabilitiesPanel).toBeDefined();
    expect(typeof lazyModule.LazyAggregatedCapabilitiesPanel).toBe("object");
  });

  it("exports LazyMCPServerCard", async () => {
    const lazyModule = await import("./lazy");
    expect(lazyModule.LazyMCPServerCard).toBeDefined();
    expect(typeof lazyModule.LazyMCPServerCard).toBe("object");
  });

  it("exports LazyToolExplorer", async () => {
    const lazyModule = await import("./lazy");
    expect(lazyModule.LazyToolExplorer).toBeDefined();
    expect(typeof lazyModule.LazyToolExplorer).toBe("object");
  });

  it("exports LazyResourceBrowser", async () => {
    const lazyModule = await import("./lazy");
    expect(lazyModule.LazyResourceBrowser).toBeDefined();
    expect(typeof lazyModule.LazyResourceBrowser).toBe("object");
  });

  it("exports LazyPromptLibrary", async () => {
    const lazyModule = await import("./lazy");
    expect(lazyModule.LazyPromptLibrary).toBeDefined();
    expect(typeof lazyModule.LazyPromptLibrary).toBe("object");
  });

  it("lazy components can be dynamically imported", async () => {
    // Verify the underlying components can be imported
    const addConnectionModule = await import("./AddConnectionDialog");
    expect(addConnectionModule.AddConnectionDialog).toBeDefined();

    const toolInvocationModule = await import("./ToolInvocationDialog");
    expect(toolInvocationModule.ToolInvocationDialog).toBeDefined();

    const resourceViewerModule = await import("./ResourceViewer");
    expect(resourceViewerModule.ResourceViewer).toBeDefined();

    const promptTesterModule = await import("./PromptTester");
    expect(promptTesterModule.PromptTester).toBeDefined();

    const elicitationModule = await import("./ElicitationDialog");
    expect(elicitationModule.ElicitationDialog).toBeDefined();

    // Aggregated Capabilities Components (MCP 2025-11-25)
    const aggregatedCapabilitiesModule =
      await import("./AggregatedCapabilities");
    expect(
      aggregatedCapabilitiesModule.AggregatedCapabilitiesPanel,
    ).toBeDefined();

    const mcpServerCardModule = await import("./MCPServerCard");
    expect(mcpServerCardModule.MCPServerCard).toBeDefined();

    const toolExplorerModule = await import("./ToolExplorer");
    expect(toolExplorerModule.ToolExplorer).toBeDefined();

    const resourceBrowserModule = await import("./ResourceBrowser");
    expect(resourceBrowserModule.ResourceBrowser).toBeDefined();

    const promptLibraryModule = await import("./PromptLibrary");
    expect(promptLibraryModule.PromptLibrary).toBeDefined();
  });
});
