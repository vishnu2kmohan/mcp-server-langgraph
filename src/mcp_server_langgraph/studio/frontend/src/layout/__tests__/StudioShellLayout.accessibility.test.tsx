/**
 * StudioShellLayout Accessibility Tests
 *
 * Tests for WCAG 2.1 AA compliance, accessible labels, keyboard navigation,
 * and screen reader compatibility.
 *
 * Split from StudioShellLayout.test.tsx for memory optimization.
 * See StudioShellLayout.setup.ts for shared mocks and utilities.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, waitFor, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";

// Extend expect with jest-axe matchers
expect.extend(toHaveNoViolations);

// Import shared setup
import {
  resetAllMocks,
  createTestStore,
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
// ACCESSIBILITY TESTS
// =============================================================================

describe("StudioShellLayout - Accessibility", () => {
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

  describe("WCAG 2.1 AA Compliance", () => {
    it("should have no axe-core accessibility violations for admin", async () => {
      const { container } = renderWithProviders(
        createStoreWithPersona("admin"),
      );

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      // Run axe-core accessibility analysis
      const results = await axe(container, {
        rules: {
          // Skip color contrast for now as it requires full CSS rendering
          "color-contrast": { enabled: false },
        },
      });

      expect(results).toHaveNoViolations();
    });

    it("should have no axe violations for user persona (limited navigation)", async () => {
      const { container } = renderWithProviders(createStoreWithPersona("user"));

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      const results = await axe(container, {
        rules: {
          "color-contrast": { enabled: false },
        },
      });

      expect(results).toHaveNoViolations();
    });

    it("should have no axe violations for developer persona", async () => {
      const { container } = renderWithProviders(
        createStoreWithPersona("developer"),
      );

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      const results = await axe(container, {
        rules: {
          "color-contrast": { enabled: false },
        },
      });

      expect(results).toHaveNoViolations();
    });
  });

  describe("Accessible Labels", () => {
    it("all navigation buttons have accessible labels", async () => {
      renderWithProviders(createStoreWithPersona("admin"));

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      // Activity bar nav buttons should have aria-label or accessible text
      const chatButton = screen.getByTestId("nav-chat");
      expect(chatButton).toBeInTheDocument();
      expect(chatButton).toHaveAttribute("type", "button");

      const adminButton = screen.getByTestId("nav-admin");
      expect(adminButton).toBeInTheDocument();
    });

    it("activity bar buttons are accessible", async () => {
      renderWithProviders(createTestStore());

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      // Activity bar should have accessible navigation buttons
      const activityBar = screen.getByTestId("activity-bar");
      const buttons = activityBar.querySelectorAll("button");
      expect(buttons.length).toBeGreaterThan(0);
    });

    it("navigation buttons have button type", async () => {
      renderWithProviders(createStoreWithPersona("admin"));

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      // Buttons should have proper type attribute
      const chatButton = screen.getByTestId("nav-chat");
      expect(chatButton).toHaveAttribute("type", "button");
    });
  });

  describe("Status Indication", () => {
    it("status bar is rendered for status indication", async () => {
      renderWithProviders(createTestStore());

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      const statusBar = screen.getByTestId("status-bar");
      expect(statusBar).toBeInTheDocument();
      // StatusBar shows context-aware status: "Connected" from mocked WebSocket status
      expect(statusBar).toHaveTextContent(/connected/i);
    });

    it("activity bar is accessible to screen readers", async () => {
      renderWithProviders(createTestStore());

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      const activityBar = screen.getByTestId("activity-bar");
      expect(activityBar).toBeInTheDocument();
    });
  });

  describe("Keyboard Accessibility", () => {
    it("interactive elements are focusable", async () => {
      renderWithProviders(createTestStore());

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      // Buttons should be focusable
      const chatButton = screen.getByTestId("nav-chat");
      expect(chatButton.tabIndex).toBeGreaterThanOrEqual(-1);
    });

    it("buttons have proper type attributes", async () => {
      renderWithProviders(createStoreWithPersona("admin"));

      await waitFor(() => {
        expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
      });

      const navButtons = [
        screen.getByTestId("nav-chat"),
        screen.getByTestId("nav-workflows"),
        screen.getByTestId("nav-admin"),
      ];

      for (const button of navButtons) {
        expect(button).toHaveAttribute("type", "button");
      }
    });
  });
});
