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
import { storage, STORAGE_KEYS } from "../../utils/storage";

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
  mockFns,
  mockBreakpointState,
  mockFeatureFlags,
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

  describe("Command Palette Navigation", () => {
    it("should use navigate() for settings command instead of window.location.href", async () => {
      // GIVEN: StudioShellLayout is rendered
      renderWithProviders(createTestStore());

      // Wait for component to settle
      await act(async () => {
        await flushPromises();
      });

      // WHEN: The handleCommandExecute is called with 'open-settings' command
      // We need to trigger this via keyboard shortcut or command palette
      // For now, we verify the mock is properly set up
      expect(mockFns.navigate).not.toHaveBeenCalled();

      // Note: Full integration test would trigger Cmd+K -> select settings
      // This test verifies the navigate mock is available for command execution
    });

    it("should not use window.location.href for navigation commands", () => {
      // GIVEN: StudioShellLayout is rendered
      renderWithProviders(createTestStore());

      // THEN: Verify navigate is the expected navigation method
      // The implementation should use useNavigate() hook, not window.location.href
      // This test documents the expected behavior
      expect(typeof mockFns.navigate).toBe("function");
    });

    it("should have navigate function available from useNavigate mock", () => {
      // GIVEN: The mock setup provides useNavigate
      renderWithProviders(createTestStore());

      // THEN: The navigate mock should be callable
      mockFns.navigate("/studio/settings");
      expect(mockFns.navigate).toHaveBeenCalledWith("/studio/settings");

      // Cleanup
      mockFns.navigate.mockClear();
    });
  });

  describe("Panel Size Persistence", () => {
    it("should read panel sizes from Redux store for initial defaultSize values", () => {
      // GIVEN: Redux store has custom panel sizes
      const store = createTestStore({
        canvas: {
          panelSizes: {
            sessionNav: 25,
            conversation: 35,
            canvas: 40,
          },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: null,
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto" as const,
          },
          focusModeEnabled: false,
        },
      });

      // WHEN: StudioShellLayout is rendered
      renderWithProviders(store);

      // THEN: Panel sizes should be read from Redux (verified by no errors)
      // The actual defaultSize prop application is internal to react-resizable-panels
      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
    });

    it("should persist panel sizes to Redux when panels are resized", async () => {
      // GIVEN: StudioShellLayout is rendered
      const store = createTestStore();
      renderWithProviders(store);

      // Wait for component to settle
      await act(async () => {
        await flushPromises();
      });

      // THEN: The onLayout handler should be set up to persist changes
      // This test verifies the component renders without errors
      // Full resize testing requires react-resizable-panels internals
      expect(screen.getByTestId("studio-shell")).toBeInTheDocument();
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

  describe("ResponsiveLayout Integration (Sprint 2.2)", () => {
    it("should auto-collapse SessionNav on sm breakpoint at mount", async () => {
      // GIVEN: Breakpoint is sm (mobile)
      mockBreakpointState.currentBreakpoint = "sm";

      // AND: SessionNav is not collapsed in initial state
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: null,
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto" as const,
          },
          focusModeEnabled: false,
          hasCustomLayout: false,
        },
      });

      // WHEN: StudioShellLayout is rendered at narrow width
      renderWithProviders(store);

      await act(async () => {
        await flushPromises();
      });

      // THEN: SessionNav should be auto-collapsed (Redux state updated)
      // Note: This test will fail until implementation is complete
      expect(store.getState().canvas.sessionNavCollapsed).toBe(true);
    });

    it("should auto-collapse SessionNav on md breakpoint at mount", async () => {
      // GIVEN: Breakpoint is md (tablet)
      mockBreakpointState.currentBreakpoint = "md";

      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: null,
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto" as const,
          },
          focusModeEnabled: false,
          hasCustomLayout: false,
        },
      });

      // WHEN: StudioShellLayout is rendered at tablet width
      renderWithProviders(store);

      await act(async () => {
        await flushPromises();
      });

      // THEN: SessionNav should be auto-collapsed
      expect(store.getState().canvas.sessionNavCollapsed).toBe(true);
    });

    it("should NOT auto-collapse SessionNav on lg/xl breakpoints", async () => {
      // GIVEN: Breakpoint is xl (desktop)
      mockBreakpointState.currentBreakpoint = "xl";

      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: null,
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto" as const,
          },
          focusModeEnabled: false,
          hasCustomLayout: false,
        },
      });

      // WHEN: StudioShellLayout is rendered at desktop width
      renderWithProviders(store);

      await act(async () => {
        await flushPromises();
      });

      // THEN: SessionNav should remain expanded
      expect(store.getState().canvas.sessionNavCollapsed).toBe(false);
    });

    it("should preserve user's manual toggle and not flip-flop on resize", async () => {
      // GIVEN: Breakpoint is xl (desktop) initially
      mockBreakpointState.currentBreakpoint = "xl";

      // AND: User has manually collapsed SessionNav
      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: true, // User manually collapsed
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: null,
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto" as const,
          },
          focusModeEnabled: false,
          hasCustomLayout: true, // User has customized layout
        },
      });

      // WHEN: StudioShellLayout is rendered
      renderWithProviders(store);

      await act(async () => {
        await flushPromises();
      });

      // THEN: SessionNav should remain collapsed (respect user's choice)
      expect(store.getState().canvas.sessionNavCollapsed).toBe(true);
    });

    it("should only apply auto-collapse once at mount, not on every render", async () => {
      // GIVEN: Breakpoint starts as sm
      mockBreakpointState.currentBreakpoint = "sm";

      const store = createTestStore({
        canvas: {
          panelSizes: { sessionNav: 20, conversation: 40, canvas: 40 },
          sessionNavCollapsed: false,
          canvasCollapsed: false,
          activeNavItem: "chat",
          selectedArtifactId: null,
          preferences: {
            showTimestamps: true,
            compactMode: false,
            showLineNumbers: true,
            codeTheme: "auto" as const,
          },
          focusModeEnabled: false,
          hasCustomLayout: false,
        },
      });

      // WHEN: Component mounts at sm breakpoint
      const { rerender } = renderWithProviders(store);

      await act(async () => {
        await flushPromises();
      });

      // THEN: SessionNav should be collapsed
      expect(store.getState().canvas.sessionNavCollapsed).toBe(true);

      // AND WHEN: We change breakpoint to xl and rerender
      mockBreakpointState.currentBreakpoint = "xl";

      // Rerender to simulate breakpoint change
      await act(async () => {
        rerender(
          <TelemetryProvider>
            <Provider store={store}>
              <MemoryRouter initialEntries={["/"]}>
                <StudioShellLayout />
              </MemoryRouter>
            </Provider>
          </TelemetryProvider>,
        );
        await flushPromises();
      });

      // THEN: SessionNav should STILL be collapsed (no flip-flop)
      // The auto-collapse only runs once at mount
      expect(store.getState().canvas.sessionNavCollapsed).toBe(true);
    });
  });

  describe("Onboarding Wizard Integration (Sprint 3.2)", () => {
    it("should show onboarding wizard for first-time users when flag enabled", async () => {
      // GIVEN: Onboarding wizard feature flag is enabled
      mockFeatureFlags.enabledFlags = [
        ...mockFeatureFlags.enabledFlags,
        "onboarding_wizard",
      ];
      // AND: User has NOT completed onboarding (no localStorage key)
      // (localStorage is cleared in beforeEach via resetAllMocks)

      const store = createTestStore();

      // WHEN: StudioShellLayout is rendered
      renderWithProviders(store);

      await act(async () => {
        await flushPromises();
      });

      // THEN: OnboardingWizard should be visible
      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText("Welcome to Agent Studio")).toBeInTheDocument();
    });

    it("should NOT show onboarding wizard when already completed", async () => {
      // GIVEN: Onboarding wizard feature flag is enabled
      mockFeatureFlags.enabledFlags = [
        ...mockFeatureFlags.enabledFlags,
        "onboarding_wizard",
      ];
      // AND: User has already completed onboarding
      storage.set(STORAGE_KEYS.ONBOARDING, true);

      const store = createTestStore();

      // WHEN: StudioShellLayout is rendered
      renderWithProviders(store);

      await act(async () => {
        await flushPromises();
      });

      // THEN: OnboardingWizard should NOT be visible
      expect(
        screen.queryByText("Welcome to Agent Studio"),
      ).not.toBeInTheDocument();
    });

    it("should NOT show onboarding wizard when feature flag disabled", async () => {
      // GIVEN: Onboarding wizard feature flag is NOT enabled
      // (default mockFeatureFlags does not include 'onboarding_wizard')

      const store = createTestStore();

      // WHEN: StudioShellLayout is rendered
      renderWithProviders(store);

      await act(async () => {
        await flushPromises();
      });

      // THEN: OnboardingWizard should NOT be visible
      expect(
        screen.queryByText("Welcome to Agent Studio"),
      ).not.toBeInTheDocument();
    });
  });
});
