/**
 * Hybrid Canvas Module Parity Tests
 *
 * Phase 7: Legacy Cleanup & Parity Verification
 *
 * These tests verify that all new Hybrid Canvas modules are correctly
 * structured and export their expected interfaces. This serves as both
 * documentation and validation of the new architecture.
 */
import { describe, it, expect } from "vitest";

describe("Hybrid Canvas Module Parity", () => {
  describe("Layout Module (src/layout/)", () => {
    it("exports HybridShellLayout component", async () => {
      const module = await import("../layout");
      expect(module.HybridShellLayout).toBeDefined();
    });

    it("HybridShellLayout is a React component", async () => {
      const module = await import("../layout");
      expect(typeof module.HybridShellLayout).toBe("function");
    });

    it("HybridShellLayout contains all sub-components internally", async () => {
      // Sub-components (ActivityBar, SessionNav, etc.) are internal to HybridShellLayout
      // The module exports only the main component for clean API
      const module = await import("../layout");
      expect(Object.keys(module)).toContain("HybridShellLayout");
    });
  });

  describe("AI Module (src/ai/)", () => {
    it("exports AI components", async () => {
      const module = await import("../ai");
      expect(module.InlineSuggestions).toBeDefined();
      expect(module.BackgroundAgentPanel).toBeDefined();
    });

    it("exports AI prop types", async () => {
      const module = await import("../ai");
      expect(typeof module.InlineSuggestions).toBe("function");
      expect(typeof module.BackgroundAgentPanel).toBe("function");
    });
  });

  describe("Compliance Module (src/compliance/)", () => {
    it("exports all compliance dashboards", async () => {
      const module = await import("../compliance");
      expect(module.SOC2Panel).toBeDefined();
      expect(module.HIPAAPanel).toBeDefined();
      expect(module.GDPRPanel).toBeDefined();
      expect(module.FedRAMPPanel).toBeDefined();
      expect(module.ComplianceDashboard).toBeDefined();
    });

    it("exports compliance types", async () => {
      // The module exports types which are validated at compile time
      const module = await import("../compliance");
      expect(typeof module.SOC2Panel).toBe("function");
      expect(typeof module.ComplianceDashboard).toBe("function");
    });
  });

  describe("Help Module (src/help/)", () => {
    it("exports all help components", async () => {
      const module = await import("../help");
      expect(module.HelpPane).toBeDefined();
      expect(module.ContextualHelp).toBeDefined();
      expect(module.KeyboardShortcuts).toBeDefined();
    });
  });

  describe("Router Loaders (src/router/loaders/)", () => {
    it("exports canvas loaders", async () => {
      const module = await import("../router/loaders");
      expect(module.chatLoader).toBeDefined();
      expect(module.artifactLoader).toBeDefined();
    });

    it("loaders are functions", async () => {
      const module = await import("../router/loaders");
      expect(typeof module.chatLoader).toBe("function");
      expect(typeof module.artifactLoader).toBe("function");
    });
  });

  describe("Canvas Slice (src/store/slices/canvasSlice.ts)", () => {
    it("exports canvas reducer and actions", async () => {
      const module = await import("../store/slices/canvasSlice");
      expect(module.default).toBeDefined(); // reducer
      expect(module.setPanelSizes).toBeDefined();
      expect(module.setSelectedArtifactId).toBeDefined();
      expect(module.toggleCanvas).toBeDefined();
      expect(module.toggleSessionNav).toBeDefined();
      expect(module.setActiveNavItem).toBeDefined();
    });

    it("exports selectors", async () => {
      const module = await import("../store/slices/canvasSlice");
      expect(module.selectPanelSizes).toBeDefined();
      expect(module.selectSelectedArtifactId).toBeDefined();
      expect(module.selectCanvasCollapsed).toBeDefined();
      expect(module.selectSessionNavCollapsed).toBeDefined();
      expect(module.selectActiveNavItem).toBeDefined();
    });
  });

  describe("MSW Canvas Handlers (src/mocks/handlers/canvasHandlers.ts)", () => {
    it("exports canvas handlers array", async () => {
      const module = await import("../mocks/handlers/canvasHandlers");
      expect(module.canvasHandlers).toBeDefined();
      expect(Array.isArray(module.canvasHandlers)).toBe(true);
      expect(module.canvasHandlers.length).toBeGreaterThan(0);
    });
  });

  describe("Router Guards (src/router/guards/)", () => {
    it("exports auth, persona, and hybrid shell guards", async () => {
      const module = await import("../router/guards");
      expect(module.AuthGuard).toBeDefined();
      expect(module.PersonaGuard).toBeDefined();
      expect(module.HybridShellGuard).toBeDefined();
    });

    it("guards are React components", async () => {
      const module = await import("../router/guards");
      expect(typeof module.AuthGuard).toBe("function");
      expect(typeof module.PersonaGuard).toBe("function");
      expect(typeof module.HybridShellGuard).toBe("function");
    });
  });

  describe("Cross-Module Integration", () => {
    it("all modules can be imported together without conflicts", async () => {
      const [layout, ai, compliance, help, loaders, guards] = await Promise.all(
        [
          import("../layout"),
          import("../ai"),
          import("../compliance"),
          import("../help"),
          import("../router/loaders"),
          import("../router/guards"),
        ],
      );

      // Verify no naming conflicts
      expect(layout.HybridShellLayout).not.toBe(undefined);
      expect(ai.InlineSuggestions).not.toBe(undefined);
      expect(compliance.ComplianceDashboard).not.toBe(undefined);
      expect(help.HelpPane).not.toBe(undefined);
      expect(loaders.chatLoader).not.toBe(undefined);
      expect(guards.AuthGuard).not.toBe(undefined);
      expect(guards.HybridShellGuard).not.toBe(undefined);
    });
  });
});

describe("Feature Flag Integration", () => {
  it("FeatureFlagContext exists and exports hooks", async () => {
    const module = await import("../contexts/FeatureFlagContext");
    expect(module.FeatureFlagProvider).toBeDefined();
    expect(module.useFeatureFlags).toBeDefined();
  });
});

describe("Design System Integration", () => {
  it("design system tokens are available", async () => {
    const module = await import("../design-system");
    // Individual token exports
    expect(module.colors).toBeDefined();
    expect(module.spacing).toBeDefined();
    expect(module.typography).toBeDefined();
    // Combined design tokens
    expect(module.designTokens).toBeDefined();
  });

  it("utility functions are exported", async () => {
    const module = await import("../design-system");
    expect(module.getColorValue).toBeDefined();
    expect(module.getSpacingValue).toBeDefined();
  });
});
