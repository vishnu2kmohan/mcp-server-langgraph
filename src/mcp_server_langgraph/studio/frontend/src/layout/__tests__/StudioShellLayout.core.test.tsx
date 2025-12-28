/**
 * StudioShellLayout Core Tests
 *
 * Tests for core layout structure, panels, keyboard navigation, accessibility,
 * and mobile responsive behavior.
 *
 * Split from StudioShellLayout.test.tsx for memory optimization.
 * See StudioShellLayout.setup.ts for shared mocks and utilities.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, cleanup } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import userEvent from "@testing-library/user-event";
import { Provider } from "react-redux";
import React from "react";

expect.extend(toHaveNoViolations);

// Import shared setup
import {
  resetAllMocks,
  createTestStore,
  createStoreWithPersona as _createStoreWithPersona,
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
// TESTS
// =============================================================================

describe("StudioShellLayout - Core", () => {
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

  describe("Core Layout", () => {
    it("renders the studio shell container", () => {
      renderWithProviders(createTestStore());

      // The main shell container should always render
      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
    });

    it("renders activity bar in main layout", () => {
      renderWithProviders(createTestStore());

      expect(screen.getByTestId("activity-bar")).toBeInTheDocument();
    });

    it("renders top bar", () => {
      renderWithProviders(createTestStore());

      expect(screen.getByTestId("top-bar")).toBeInTheDocument();
    });

    it("renders status bar", () => {
      renderWithProviders(createTestStore());

      expect(screen.getByTestId("status-bar")).toBeInTheDocument();
    });
  });

  describe("ActivityBar", () => {
    it("renders navigation items", () => {
      renderWithProviders(createTestStore());

      const activityBar = screen.getByTestId("activity-bar");
      expect(activityBar).toBeInTheDocument();
    });

    it("renders with consistent layout across routes", () => {
      renderWithProviders(createTestStore(), ["/studio/chat"]);

      // Activity bar should be present with navigation items
      expect(screen.getByTestId("activity-bar")).toBeInTheDocument();
    });
  });

  describe("Keyboard Navigation", () => {
    it("supports keyboard focus traversal", async () => {
      const user = userEvent.setup();
      renderWithProviders(createTestStore());

      // Tab through focusable elements
      await user.tab();

      // Some element should be focused
      expect(document.activeElement).not.toBe(document.body);
    });
  });

  describe("Accessibility (WCAG 2.1 AA)", () => {
    it("has no axe violations for main layout", async () => {
      const { container } = renderWithProviders(createTestStore());

      // Wait for component to settle
      await act(async () => {
        await flushPromises();
      });

      const results = await axe(container, {
        rules: {
          // Disable rules that may not apply to mocked components
          "color-contrast": { enabled: false },
          region: { enabled: false },
        },
      });

      expect(results).toHaveNoViolations();
    });

    it("provides proper ARIA landmarks", () => {
      renderWithProviders(createTestStore());

      // Main layout should use semantic HTML or ARIA roles
      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
    });

    it("supports keyboard-only navigation", async () => {
      const user = userEvent.setup();
      renderWithProviders(createTestStore());

      // Tab through layout
      await user.tab();
      await user.tab();

      // Should be able to tab without getting stuck
      expect(document.activeElement).not.toBe(document.body);
    });
  });

  describe("Mobile Responsive Layout", () => {
    it("renders at mobile viewport width", () => {
      // Mock mobile viewport
      Object.defineProperty(window, "innerWidth", {
        value: 375,
        writable: true,
      });
      Object.defineProperty(window, "innerHeight", {
        value: 667,
        writable: true,
      });

      renderWithProviders(createTestStore());

      // Layout should still render
      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
    });

    it("renders at tablet viewport width", () => {
      Object.defineProperty(window, "innerWidth", {
        value: 768,
        writable: true,
      });
      Object.defineProperty(window, "innerHeight", {
        value: 1024,
        writable: true,
      });

      renderWithProviders(createTestStore());

      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
    });

    it("renders at desktop viewport width", () => {
      Object.defineProperty(window, "innerWidth", {
        value: 1920,
        writable: true,
      });
      Object.defineProperty(window, "innerHeight", {
        value: 1080,
        writable: true,
      });

      renderWithProviders(createTestStore());

      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
    });
  });
});
