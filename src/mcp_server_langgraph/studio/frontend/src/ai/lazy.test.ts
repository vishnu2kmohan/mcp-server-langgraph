/**
 * Lazy AI Components Tests
 *
 * TDD tests for lazy-loaded AI components to reduce bundle size.
 * These components are code-split and loaded on-demand.
 */

import { describe, it, expect } from "vitest";

describe("Lazy AI Components", () => {
  describe("LazyAICommandPalette", () => {
    it("should export LazyAICommandPalette", async () => {
      const { LazyAICommandPalette } = await import("./lazy");
      expect(LazyAICommandPalette).toBeDefined();
    });

    it("should be a lazy component (has $$typeof for lazy)", async () => {
      const { LazyAICommandPalette } = await import("./lazy");
      // React.lazy components have $$typeof Symbol(react.lazy)
      expect(LazyAICommandPalette).toHaveProperty("$$typeof");
    });
  });

  describe("LazyBackgroundAgentPanel", () => {
    it("should export LazyBackgroundAgentPanel", async () => {
      const { LazyBackgroundAgentPanel } = await import("./lazy");
      expect(LazyBackgroundAgentPanel).toBeDefined();
    });

    it("should be a lazy component", async () => {
      const { LazyBackgroundAgentPanel } = await import("./lazy");
      expect(LazyBackgroundAgentPanel).toHaveProperty("$$typeof");
    });
  });

  describe("LazyAgentTaskQueue", () => {
    it("should export LazyAgentTaskQueue", async () => {
      const { LazyAgentTaskQueue } = await import("./lazy");
      expect(LazyAgentTaskQueue).toBeDefined();
    });

    it("should be a lazy component", async () => {
      const { LazyAgentTaskQueue } = await import("./lazy");
      expect(LazyAgentTaskQueue).toHaveProperty("$$typeof");
    });
  });

  describe("LazyAIEditOverlay", () => {
    it("should export LazyAIEditOverlay", async () => {
      const { LazyAIEditOverlay } = await import("./lazy");
      expect(LazyAIEditOverlay).toBeDefined();
    });

    it("should be a lazy component", async () => {
      const { LazyAIEditOverlay } = await import("./lazy");
      expect(LazyAIEditOverlay).toHaveProperty("$$typeof");
    });
  });

  describe("LazyInlineSuggestions", () => {
    it("should export LazyInlineSuggestions", async () => {
      const { LazyInlineSuggestions } = await import("./lazy");
      expect(LazyInlineSuggestions).toBeDefined();
    });

    it("should be a lazy component", async () => {
      const { LazyInlineSuggestions } = await import("./lazy");
      expect(LazyInlineSuggestions).toHaveProperty("$$typeof");
    });
  });
});
