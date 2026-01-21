/**
 * StudioShellLayout RBAC Tests
 *
 * Tests for persona-based navigation filtering, RBAC enforcement,
 * and deny-by-default security patterns.
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
  createStoreWithPersona,
  flushPromises,
  mockImplementations,
  mockResizablePanels,
  mockReactRouter,
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
// RBAC TESTS
// =============================================================================

describe("StudioShellLayout - RBAC", () => {
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

  describe("Persona-based Navigation (Phase 3)", () => {
    it("shows all navigation items for admin persona", async () => {
      renderWithProviders(createStoreWithPersona("admin"));

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      // Admin should see all items including admin-only
      expect(screen.getByTestId("nav-chat")).toBeInTheDocument();
      expect(screen.getByTestId("nav-workflows")).toBeInTheDocument();
      expect(screen.getByTestId("nav-observability")).toBeInTheDocument();
      expect(screen.getByTestId("nav-admin")).toBeInTheDocument();
      expect(screen.getByTestId("nav-settings")).toBeInTheDocument();
    });

    it("shows developer-allowed items for developer persona", async () => {
      renderWithProviders(createStoreWithPersona("developer"));

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      // Developer should see chat, workflows, observability but NOT admin
      expect(screen.getByTestId("nav-chat")).toBeInTheDocument();
      expect(screen.getByTestId("nav-workflows")).toBeInTheDocument();
      expect(screen.getByTestId("nav-observability")).toBeInTheDocument();
      expect(screen.queryByTestId("nav-admin")).not.toBeInTheDocument();
      expect(screen.getByTestId("nav-settings")).toBeInTheDocument();
    });

    it("shows user-allowed items for user persona (deny-by-default)", async () => {
      renderWithProviders(createStoreWithPersona("user"));

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      // User should only see chat and workflows, NOT admin/observability
      expect(screen.getByTestId("nav-chat")).toBeInTheDocument();
      expect(screen.getByTestId("nav-workflows")).toBeInTheDocument();
      // User persona does NOT have access to these
      expect(screen.queryByTestId("nav-observability")).not.toBeInTheDocument();
      expect(screen.queryByTestId("nav-admin")).not.toBeInTheDocument();
      expect(screen.queryByTestId("nav-agents")).not.toBeInTheDocument();
    });

    it("implements deny-by-default - only shows explicitly allowed items", async () => {
      renderWithProviders(createStoreWithPersona("user"));

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      const activityBar = screen.getByTestId("activity-bar");
      const buttons = activityBar.querySelectorAll("button");

      // User persona should have limited navigation items
      // Expect fewer buttons for user than admin (admin has 15+)
      // User has: projects, chat, settings, help, plus some always-visible items
      expect(buttons.length).toBeLessThan(10);
    });
  });

  describe("Persona Transition", () => {
    it("renders correctly when switching from admin to user persona", async () => {
      // First render as admin
      const adminStore = createStoreWithPersona("admin");
      const { unmount: unmountAdmin } = renderWithProviders(adminStore);

      await waitFor(() => {
        expect(screen.getByTestId("nav-admin")).toBeInTheDocument();
      });

      unmountAdmin();

      // Then render as user
      const userStore = createStoreWithPersona("user");
      renderWithProviders(userStore);

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      // User should not see admin nav
      expect(screen.queryByTestId("nav-admin")).not.toBeInTheDocument();
    });

    it("renders correctly when switching from user to developer persona", async () => {
      // First render as user
      const userStore = createStoreWithPersona("user");
      const { unmount: unmountUser } = renderWithProviders(userStore);

      await waitFor(() => {
        expect(
          screen.queryByTestId("nav-observability"),
        ).not.toBeInTheDocument();
      });

      unmountUser();

      // Then render as developer
      const devStore = createStoreWithPersona("developer");
      renderWithProviders(devStore);

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      // Developer should see observability
      expect(screen.getByTestId("nav-observability")).toBeInTheDocument();
    });
  });

  describe("Security Enforcement", () => {
    it("does not render admin panel for non-admin personas", async () => {
      const personas = ["user", "developer"] as const;

      for (const persona of personas) {
        const store = createStoreWithPersona(persona);
        const { unmount } = renderWithProviders(store);

        await waitFor(() => {
          expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
        });

        expect(screen.queryByTestId("nav-admin")).not.toBeInTheDocument();
        unmount();
      }
    });

    it("always shows core navigation items regardless of persona", async () => {
      const personas = ["admin", "developer", "user"] as const;

      for (const persona of personas) {
        const store = createStoreWithPersona(persona);
        const { unmount } = renderWithProviders(store);

        await waitFor(() => {
          expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
        });

        // All personas should see chat and workflows
        expect(screen.getByTestId("nav-chat")).toBeInTheDocument();
        expect(screen.getByTestId("nav-workflows")).toBeInTheDocument();
        unmount();
      }
    });

    it("enforces settings access for admin and developer personas", async () => {
      const personas = ["admin", "developer"] as const;

      for (const persona of personas) {
        const store = createStoreWithPersona(persona);
        const { unmount } = renderWithProviders(store);

        await waitFor(() => {
          expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
        });

        // Settings should be accessible to admin and developer
        expect(screen.getByTestId("nav-settings")).toBeInTheDocument();
        unmount();
      }
    });
  });
});
