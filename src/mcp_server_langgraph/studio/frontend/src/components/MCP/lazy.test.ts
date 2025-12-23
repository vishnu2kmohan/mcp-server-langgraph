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
  });
});
