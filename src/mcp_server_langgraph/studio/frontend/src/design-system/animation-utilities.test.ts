/**
 * Animation Utilities Tests
 *
 * TDD tests for animation delay and dynamic styling utilities.
 */

import { afterEach, describe, expect, it, vi } from "vitest";

// =============================================================================
// Animation Delay Utilities
// =============================================================================

afterEach(() => {
  vi.clearAllMocks();
});

describe("Animation Delay Classes", () => {
  it("should have animation-delay-0 class defined in Tailwind config", async () => {
    // Test that Tailwind generates the expected animation-delay classes
    const config = await import("../../tailwind.config");
    const animationDelay = config.default.theme?.extend?.animationDelay;

    expect(animationDelay).toBeDefined();
    expect(animationDelay?.["0"]).toBe("0ms");
    expect(animationDelay?.["75"]).toBe("75ms");
    expect(animationDelay?.["150"]).toBe("150ms");
    expect(animationDelay?.["300"]).toBe("300ms");
    expect(animationDelay?.["500"]).toBe("500ms");
  });
});

// =============================================================================
// Dynamic Height Utilities
// =============================================================================

describe("Dynamic Height CSS Utilities", () => {
  it("should have dynamic-height class in index.css", async () => {
    // This test validates the CSS utility exists
    // The actual CSS is tested via Storybook visual tests
    const fs = await import("fs");
    const path = await import("path");
    const cssPath = path.resolve(__dirname, "../index.css");
    const css = fs.readFileSync(cssPath, "utf-8");

    expect(css).toContain(".dynamic-height");
    expect(css).toContain("var(--height");
  });

  it("should have dynamic-min-height class in index.css", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const cssPath = path.resolve(__dirname, "../index.css");
    const css = fs.readFileSync(cssPath, "utf-8");

    expect(css).toContain(".dynamic-min-height");
    expect(css).toContain("var(--min-height");
  });
});

// =============================================================================
// Dynamic Grid Utilities
// =============================================================================

describe("Dynamic Grid CSS Utilities", () => {
  it("should have grid-dynamic-cols class in index.css", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const cssPath = path.resolve(__dirname, "../index.css");
    const css = fs.readFileSync(cssPath, "utf-8");

    expect(css).toContain(".grid-dynamic-cols");
    expect(css).toContain("var(--cols");
  });
});

// =============================================================================
// Tree Indent Utilities
// =============================================================================

describe("Tree Indent CSS Utilities", () => {
  it("should have tree-indent class in index.css", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const cssPath = path.resolve(__dirname, "../index.css");
    const css = fs.readFileSync(cssPath, "utf-8");

    expect(css).toContain(".tree-indent");
    expect(css).toContain("var(--indent");
  });
});

// =============================================================================
// Position Utilities
// =============================================================================

describe("Dynamic Position CSS Utilities", () => {
  it("should have position-left class in index.css", async () => {
    const fs = await import("fs");
    const path = await import("path");
    const cssPath = path.resolve(__dirname, "../index.css");
    const css = fs.readFileSync(cssPath, "utf-8");

    expect(css).toContain(".position-left");
    expect(css).toContain("var(--left");
  });
});
