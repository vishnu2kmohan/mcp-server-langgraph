/**
 * StudioShellLayout - Navigation Tests
 *
 * Tests for Navigation Interactivity (clicking nav items triggers navigation).
 * These tests were migrated from the main StudioShellLayout.test.tsx as part of
 * OOM prevention sharding (see: docs-internal/frontend/testing/TESTING_OOM_PREVENTION.md).
 *
 * NOTE: Tests for SessionNav (new chat button, search input) are in SessionNav.test.tsx.
 * Tests for ConversationPanel and CanvasPanel visibility are in StudioShellLayout.panels.test.tsx.
 *
 * @see layout/__tests__/README.md for shard structure documentation
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import React from "react";

// Import shared setup
import {
  resetAllMocks,
  createStoreWithPersona,
  flushPromises,
  mockImplementations,
  mockResizablePanels,
  mockReactRouter,
  resetPanelCounter,
  mockFns,
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
  store: ReturnType<typeof createStoreWithPersona>,
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
// TESTS
// =============================================================================

describe("StudioShellLayout - Navigation", () => {
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

  // ===========================================================================
  // Navigation Interactivity (Phase 7)
  // These tests require admin persona to see all nav items
  // ===========================================================================
  describe("Navigation Interactivity", () => {
    const user = userEvent.setup();

    it("navigates to workflows when workflows icon is clicked", async () => {
      // Use admin persona to see all nav items
      renderWithProviders(createStoreWithPersona("admin"));

      const workflowsButton = screen.getByTestId("nav-workflows");
      await user.click(workflowsButton);

      await waitFor(() => {
        expect(mockFns.navigate).toHaveBeenCalledWith("/studio/workflows");
      });
    });

    it("navigates to observability when observability icon is clicked", async () => {
      // Use admin persona to see observability nav
      renderWithProviders(createStoreWithPersona("admin"));

      const observabilityButton = screen.getByTestId("nav-observability");
      await user.click(observabilityButton);

      await waitFor(() => {
        expect(mockFns.navigate).toHaveBeenCalledWith("/studio/observability");
      });
    });

    it("navigates to admin when admin icon is clicked", async () => {
      // Use admin persona to see admin nav
      renderWithProviders(createStoreWithPersona("admin"));

      const adminButton = screen.getByTestId("nav-admin");
      await user.click(adminButton);

      await waitFor(() => {
        expect(mockFns.navigate).toHaveBeenCalledWith("/studio/admin");
      });
    });

    it("navigates to settings when settings icon is clicked", async () => {
      // Use admin persona to see settings nav
      renderWithProviders(createStoreWithPersona("admin"));

      const settingsButton = screen.getByTestId("nav-settings");
      await user.click(settingsButton);

      await waitFor(() => {
        expect(mockFns.navigate).toHaveBeenCalledWith("/studio/settings");
      });
    });
  });
});
