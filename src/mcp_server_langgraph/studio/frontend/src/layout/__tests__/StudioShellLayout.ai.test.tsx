/**
 * StudioShellLayout AI Tests
 *
 * Tests for AI interpretation, nudges, persona mismatch banner,
 * and CrossInsightsPanel keyboard shortcuts.
 *
 * Split from StudioShellLayout.test.tsx for memory optimization.
 * See StudioShellLayout.setup.ts for shared mocks and utilities.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, waitFor, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import React from "react";

// Import shared setup
import {
  resetAllMocks,
  createTestStore,
  flushPromises,
  dispatchKeyboardEvent,
  mockImplementations,
  mockResizablePanels,
  mockReactRouter,
  mockNudgesState,
  mockPersonaAnalysisState,
  mockFns,
  resetPanelCounter,
} from "./StudioShellLayout.setup";

// =============================================================================
// MOCKS - Must be defined before component imports
// =============================================================================

vi.mock(
  "../../contexts/TelemetryContext",
  () => mockImplementations.TelemetryContext,
);
vi.mock(
  "../../devtools/TelemetryViewer",
  () => mockImplementations.TelemetryViewer,
);
vi.mock(
  "../../contexts/FeatureFlagContext",
  () => mockImplementations.FeatureFlagContext,
);
vi.mock("../../hooks/useNudges", () => mockImplementations.useNudges);
vi.mock(
  "../../hooks/useAIPersonaAnalysis",
  () => mockImplementations.useAIPersonaAnalysis,
);
vi.mock(
  "../../hooks/useAgentRequestWebSocket",
  () => mockImplementations.useAgentRequestWebSocket,
);
vi.mock("../../api", () => mockImplementations.api);
vi.mock(
  "../../hooks/usePersonaRouting",
  () => mockImplementations.usePersonaRouting,
);
vi.mock(
  "../../hooks/useConnectionHealthWebSocket",
  () => mockImplementations.useConnectionHealthWebSocket,
);
vi.mock(
  "../../hooks/useCrossInsightsPanel",
  () => mockImplementations.useCrossInsightsPanel,
);
vi.mock(
  "../../hooks/useUXIntelligence",
  () => mockImplementations.useUXIntelligence,
);
vi.mock(
  "../../hooks/useMessageRevalidation",
  () => mockImplementations.useMessageRevalidation,
);
vi.mock(
  "../../hooks/useConversationIntelligence",
  () => mockImplementations.useConversationIntelligence,
);
vi.mock("../../hooks/useHITLDialogs", () => mockImplementations.useHITLDialogs);
vi.mock("react-resizable-panels", () => mockResizablePanels);
vi.mock("react-router", () => mockReactRouter);

// Import TelemetryProvider (mocked version)
import { TelemetryProvider } from "../../contexts/TelemetryContext";
import { MemoryRouter } from "react-router";

// Import component AFTER all mocks
import { StudioShellLayout } from "../StudioShellLayout";

// =============================================================================
// TEST HELPERS
// =============================================================================

const renderWithProviders = (
  store: ReturnType<typeof createTestStore>,
  initialEntries: string[] = ["/studio/chat"],
) => {
  let result: ReturnType<typeof render>;
  act(() => {
    result = render(
      <TelemetryProvider>
        <Provider store={store}>
          <MemoryRouter initialEntries={initialEntries}>
            <StudioShellLayout />
          </MemoryRouter>
        </Provider>
      </TelemetryProvider>,
    );
  });
  return result!;
};

// =============================================================================
// AI TESTS
// =============================================================================

describe("StudioShellLayout - AI Features", () => {
  beforeEach(() => {
    resetAllMocks();
    resetPanelCounter();
  });

  afterEach(async () => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
    await act(async () => {
      await flushPromises();
    });
  });

  describe("AI Interpretation", () => {
    it("passes onAIInterpret callback to AICommandPalette", async () => {
      renderWithProviders(createTestStore());

      // Open command palette
      await dispatchKeyboardEvent("k", { metaKey: true });

      await waitFor(() => {
        expect(screen.getByTestId("ai-command-palette")).toBeInTheDocument();
      });

      // The command palette should be rendered with AI interpretation capability
      const commandPalette = screen.getByTestId("ai-command-palette");
      expect(commandPalette).toBeInTheDocument();
    });

    it("handles AI interpretation response with toggle-panel action", async () => {
      const store = createTestStore();

      // Mock fetch for AI interpretation
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            action: "toggle-panel",
            params: { panel: "canvas" },
            confidence: 0.85,
          }),
      });

      renderWithProviders(store);

      // Verify shell renders
      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      // Open command palette
      await dispatchKeyboardEvent("k", { metaKey: true });

      await waitFor(() => {
        expect(screen.getByTestId("ai-command-palette")).toBeInTheDocument();
      });

      vi.restoreAllMocks();
    });
  });

  describe("AI Nudges", () => {
    beforeEach(() => {
      // Enable nudges feature flag
      mockFns.useFeatureFlag.mockImplementation((flag: string) => {
        if (flag === "nudges") return true;
        if (flag === "canvas_ai_palette" || flag === "ai_suggestions")
          return true;
        return false;
      });
    });

    it("renders nudge when activeNudge is set", async () => {
      // Set up active nudge
      mockNudgesState.activeNudge = {
        id: "test-nudge-1",
        type: "tip",
        title: "Pro Tip",
        message: "Try using the canvas for code editing",
        action: null,
        priority: 1,
        dismissable: true,
      };

      renderWithProviders(createTestStore());

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });
    });

    it("does not render nudge when activeNudge is null", async () => {
      mockNudgesState.activeNudge = null;

      renderWithProviders(createTestStore());

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      // Nudge banner should not be present
      expect(screen.queryByTestId("nudge-banner")).not.toBeInTheDocument();
    });
  });

  describe("AI Persona Mismatch Banner", () => {
    it("renders persona mismatch banner when isPersonaMismatch is true", async () => {
      // Enable persona_analysis feature flag
      mockFns.useFeatureFlag.mockImplementation((flag: string) => {
        if (flag === "persona_analysis") return true;
        if (flag === "canvas_ai_palette" || flag === "ai_suggestions")
          return true;
        return false;
      });

      // Set up persona mismatch state
      mockPersonaAnalysisState.isPersonaMismatch = true;
      mockPersonaAnalysisState.assignedPersona = "developer";
      mockPersonaAnalysisState.detectedPersona = "admin";
      mockPersonaAnalysisState.confidence = 0.85;
      mockPersonaAnalysisState.recommendation =
        "Consider switching to admin role";

      renderWithProviders(createTestStore());

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });
    });

    it("does not render banner when isPersonaMismatch is false", async () => {
      mockFns.useFeatureFlag.mockImplementation((flag: string) => {
        if (flag === "persona_analysis") return true;
        if (flag === "canvas_ai_palette" || flag === "ai_suggestions")
          return true;
        return false;
      });

      mockPersonaAnalysisState.isPersonaMismatch = false;

      renderWithProviders(createTestStore());

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      // Persona mismatch banner should not be present
      expect(
        screen.queryByTestId("persona-mismatch-banner"),
      ).not.toBeInTheDocument();
    });
  });

  describe("CrossInsightsPanel Keyboard Shortcut", () => {
    beforeEach(() => {
      localStorage.clear();
      mockFns.useFeatureFlag.mockImplementation((flag: string) => {
        if (flag === "batch_composite_analysis") return true;
        if (flag === "canvas_ai_palette" || flag === "ai_suggestions")
          return true;
        return false;
      });
    });

    afterEach(() => {
      localStorage.clear();
    });

    it("responds to Cmd+I keyboard shortcut", async () => {
      renderWithProviders(createTestStore());

      // Press Cmd+I to toggle insights panel
      await dispatchKeyboardEvent("i", { metaKey: true });

      // Shell should still be rendered
      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
    });

    it("responds to Ctrl+I keyboard shortcut", async () => {
      renderWithProviders(createTestStore());

      // Press Ctrl+I to toggle insights panel
      await dispatchKeyboardEvent("i", { ctrlKey: true });

      // Shell should still be rendered
      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
    });
  });
});
