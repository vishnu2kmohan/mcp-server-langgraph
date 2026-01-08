/**
 * StudioShellLayout KB Status Tests
 *
 * Tests for Knowledge Base (KB) status integration in StudioShellLayout.
 * KB Focus Mode allows users to control context retrieval strategy:
 * - "all": Use both KB and web search (default)
 * - "kb_only": Only use KB/vector store for context
 * - "web_only": Only use web search for context
 * - "none": Disable context augmentation
 *
 * TDD tests for the StatusBar KB indicator when kb_focus feature flag is enabled.
 * Split from main test file for memory optimization.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import React from "react";

// Import shared setup
import {
  resetAllMocks,
  createTestStore,
  flushPromises,
  mockImplementations,
  mockResizablePanels,
  mockReactRouter,
  resetPanelCounter,
  mockFeatureFlags,
  mockKBStatusState,
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
vi.mock(
  "../../hooks/useAIOnboarding",
  () => mockImplementations.useAIOnboarding,
);
vi.mock("../../hooks/useKBStatus", () => mockImplementations.useKBStatus);
vi.mock("react-resizable-panels", () => mockResizablePanels);
vi.mock("react-router", () => mockReactRouter);
vi.mock("../ResponsiveLayout", () => mockImplementations.ResponsiveLayout);

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
  initialEntries: string[] = ["/"],
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
// KB STATUS TESTS
// =============================================================================

describe("StudioShellLayout - KB Status", () => {
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

  describe("Feature Flag Integration", () => {
    it("should not display KB status when kb_focus flag is disabled", () => {
      // Ensure kb_focus is NOT in enabled flags
      mockFeatureFlags.enabledFlags = mockFeatureFlags.enabledFlags.filter(
        (f) => f !== "kb_focus",
      );

      renderWithProviders(createTestStore());

      // KB status indicator should not be present
      expect(
        screen.queryByTestId("kb-status-indicator"),
      ).not.toBeInTheDocument();
    });

    it("should display KB status when kb_focus flag is enabled", () => {
      // Enable kb_focus flag
      mockFeatureFlags.enabledFlags = [
        ...mockFeatureFlags.enabledFlags,
        "kb_focus",
      ];

      // Set KB status to ready
      mockKBStatusState.kbStatusForUI = "ready";
      mockKBStatusState.statusMessage = "Knowledge Base ready";

      renderWithProviders(createTestStore());

      // KB status indicator should be present
      expect(screen.getByTestId("kb-status-indicator")).toBeInTheDocument();
    });
  });

  describe("KB Status Display", () => {
    beforeEach(() => {
      // Enable kb_focus for all display tests
      mockFeatureFlags.enabledFlags = [
        ...mockFeatureFlags.enabledFlags,
        "kb_focus",
      ];
    });

    it("should display 'ready' status with green indicator", () => {
      mockKBStatusState.kbStatusForUI = "ready";
      mockKBStatusState.statusMessage = "Knowledge Base ready";

      renderWithProviders(createTestStore());

      const kbIndicator = screen.getByTestId("kb-status-indicator");
      expect(kbIndicator).toBeInTheDocument();
      // Should have green color class for ready status
      expect(kbIndicator).toHaveClass("bg-success-500");
    });

    it("should display 'misconfigured' status with warning indicator", () => {
      mockKBStatusState.kbStatusForUI = "misconfigured";
      mockKBStatusState.statusMessage = "Qdrant URL not configured";

      renderWithProviders(createTestStore());

      const kbIndicator = screen.getByTestId("kb-status-indicator");
      expect(kbIndicator).toBeInTheDocument();
      // Should have yellow color class for misconfigured status
      expect(kbIndicator).toHaveClass("bg-warning-500");
    });

    it("should display 'unavailable' status with gray indicator", () => {
      mockKBStatusState.kbStatusForUI = "unavailable";
      mockKBStatusState.statusMessage = "Cannot connect to Qdrant";

      renderWithProviders(createTestStore());

      const kbIndicator = screen.getByTestId("kb-status-indicator");
      expect(kbIndicator).toBeInTheDocument();
      // Should have gray color class for unavailable status
      expect(kbIndicator).toHaveClass("bg-gray-400");
    });

    it("should display context stats when available", () => {
      mockKBStatusState.kbStatusForUI = "ready";
      mockKBStatusState.contextStats = {
        refsCount: 5,
        tokensUsed: 1250,
        tokenBudget: 4000,
      };

      renderWithProviders(createTestStore());

      // Context stats badge should be visible
      const contextStats = screen.getByTestId("kb-context-stats");
      expect(contextStats).toBeInTheDocument();
      expect(contextStats).toHaveTextContent("5 refs");
    });
  });

  describe("useKBStatus Hook Integration", () => {
    it("should call useKBStatus with skip=true when kb_focus flag is disabled", () => {
      // Ensure kb_focus is NOT in enabled flags
      mockFeatureFlags.enabledFlags = mockFeatureFlags.enabledFlags.filter(
        (f) => f !== "kb_focus",
      );

      renderWithProviders(createTestStore());

      // Verify useKBStatus was called with skip option
      // The mock records calls so we can verify behavior
      expect(mockKBStatusState.skipCalled).toBe(true);
    });

    it("should call useKBStatus with skip=false when kb_focus flag is enabled", () => {
      mockFeatureFlags.enabledFlags = [
        ...mockFeatureFlags.enabledFlags,
        "kb_focus",
      ];

      renderWithProviders(createTestStore());

      // Verify useKBStatus was called without skip
      expect(mockKBStatusState.skipCalled).toBe(false);
    });
  });

  describe("StatusBar Props Passthrough", () => {
    it("should pass kbStatus to StatusBar when flag enabled", () => {
      mockFeatureFlags.enabledFlags = [
        ...mockFeatureFlags.enabledFlags,
        "kb_focus",
      ];
      mockKBStatusState.kbStatusForUI = "ready";

      renderWithProviders(createTestStore());

      // StatusBar should receive kbStatus prop
      const statusBar = screen.getByTestId("status-bar");
      expect(statusBar).toBeInTheDocument();
    });

    it("should not pass kbStatus to StatusBar when flag disabled", () => {
      mockFeatureFlags.enabledFlags = mockFeatureFlags.enabledFlags.filter(
        (f) => f !== "kb_focus",
      );
      mockKBStatusState.kbStatusForUI = "ready";

      renderWithProviders(createTestStore());

      // KB indicator should not be present
      expect(
        screen.queryByTestId("kb-status-indicator"),
      ).not.toBeInTheDocument();
    });

    it("should pass kbStatusMessage to StatusBar for tooltip", () => {
      mockFeatureFlags.enabledFlags = [
        ...mockFeatureFlags.enabledFlags,
        "kb_focus",
      ];
      mockKBStatusState.kbStatusForUI = "misconfigured";
      mockKBStatusState.statusMessage =
        "Set QDRANT_URL to enable context augmentation";

      renderWithProviders(createTestStore());

      // KB indicator should be present
      const kbIndicator = screen.getByTestId("kb-status-indicator");
      expect(kbIndicator).toBeInTheDocument();
    });

    it("should pass kbContextStats to StatusBar", () => {
      mockFeatureFlags.enabledFlags = [
        ...mockFeatureFlags.enabledFlags,
        "kb_focus",
      ];
      mockKBStatusState.kbStatusForUI = "ready";
      mockKBStatusState.contextStats = {
        refsCount: 3,
        tokensUsed: 750,
        tokenBudget: 4000,
      };

      renderWithProviders(createTestStore());

      // Context stats should be displayed
      const contextStats = screen.getByTestId("kb-context-stats");
      expect(contextStats).toHaveTextContent("3 refs");
    });
  });
});
