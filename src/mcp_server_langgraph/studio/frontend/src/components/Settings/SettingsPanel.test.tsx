/**
 * SettingsPanel Tests
 *
 * TDD tests for the Settings Panel component.
 * Tests cover:
 * - Panel rendering with tabs
 * - General settings tab
 * - Accessibility settings tab
 * - Model defaults tab
 * - Keyboard shortcuts tab
 * - Privacy settings tab
 * - Settings persistence
 * - WCAG 2.1 AA accessibility requirements
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { MemoryRouter } from "react-router";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { SettingsPanel } from "./SettingsPanel";
import { PreferencesProvider } from "../../contexts/PreferencesContext";
import { STORAGE_KEYS } from "../../utils/storage";
import { fullCleanup } from "../../test/testIsolation";
import uiReducer from "../../store/slices/uiSlice";

// Helper to flush pending promises (prevents act() warnings)
const flushPromises = () => new Promise((resolve) => setTimeout(resolve, 0));

expect.extend(toHaveNoViolations);

// Storage key used by the context - use centralized key
const STORAGE_KEY = STORAGE_KEYS.PREFERENCES;

// Create a test store with ui slice
const createTestStore = () =>
  configureStore({
    reducer: {
      ui: uiReducer,
    },
  });

// Helper to create wrapper with preferences provider, router, and Redux store
const renderWithProvider = (ui: React.ReactElement) => {
  const store = createTestStore();
  return render(
    <Provider store={store}>
      <MemoryRouter>
        <PreferencesProvider>{ui}</PreferencesProvider>
      </MemoryRouter>
    </Provider>,
  );
};

describe("SettingsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(async () => {
    // Flush pending promises to prevent state leakage
    await flushPromises();
    // Comprehensive cleanup for test isolation
    cleanup();
    fullCleanup();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("should render the settings panel", async () => {
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.getByRole("tabpanel")).toBeInTheDocument();
      });
    });

    it("should render all settings tabs", async () => {
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(
          screen.getByRole("tab", { name: /general/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("tab", { name: /accessibility/i }),
        ).toBeInTheDocument();
        expect(screen.getByRole("tab", { name: /model/i })).toBeInTheDocument();
        expect(
          screen.getByRole("tab", { name: /shortcuts/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("tab", { name: /privacy/i }),
        ).toBeInTheDocument();
      });
    });

    it("should show General tab content by default", async () => {
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.getByRole("tab", { name: /general/i })).toHaveAttribute(
          "aria-selected",
          "true",
        );
      });
    });

    it("should render with custom className", async () => {
      renderWithProvider(<SettingsPanel className="custom-class" />);

      await waitFor(() => {
        const panel = screen.getByTestId("settings-panel");
        expect(panel).toHaveClass("custom-class");
      });
    });
  });

  // ===========================================================================
  // Tab Navigation Tests
  // ===========================================================================

  describe("tab navigation", () => {
    it("should switch to Accessibility tab when clicked", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(
          screen.getByRole("tab", { name: /accessibility/i }),
        ).toBeInTheDocument();
      });

      await user.click(screen.getByRole("tab", { name: /accessibility/i }));

      expect(
        screen.getByRole("tab", { name: /accessibility/i }),
      ).toHaveAttribute("aria-selected", "true");
    });

    it("should switch to Model Defaults tab when clicked", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.getByRole("tab", { name: /model/i })).toBeInTheDocument();
      });

      await user.click(screen.getByRole("tab", { name: /model/i }));

      expect(screen.getByRole("tab", { name: /model/i })).toHaveAttribute(
        "aria-selected",
        "true",
      );
    });

    it("should support keyboard navigation between tabs", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(
          screen.getByRole("tab", { name: /general/i }),
        ).toBeInTheDocument();
      });

      // Focus the first tab
      screen.getByRole("tab", { name: /general/i }).focus();

      // Arrow right should move to next tab
      await user.keyboard("{ArrowRight}");

      expect(screen.getByRole("tab", { name: /accessibility/i })).toHaveFocus();
    });
  });

  // ===========================================================================
  // General Settings Tab Tests
  // ===========================================================================

  describe("General settings tab", () => {
    it("should render theme selector", async () => {
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.getByLabelText(/theme/i)).toBeInTheDocument();
      });
    });

    it("should change theme when selected", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.getByLabelText(/theme/i)).toBeInTheDocument();
      });

      const themeSelect = screen.getByLabelText(/theme/i);
      await user.selectOptions(themeSelect, "dark");

      expect(themeSelect).toHaveValue("dark");
    });

    it("should render language selector", async () => {
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.getByLabelText(/language/i)).toBeInTheDocument();
      });
    });

    it("should render auto-scroll toggle", async () => {
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.getByLabelText(/auto-scroll/i)).toBeInTheDocument();
      });
    });

    it("should toggle auto-scroll when clicked", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.getByLabelText(/auto-scroll/i)).toBeInTheDocument();
      });

      const toggle = screen.getByLabelText(/auto-scroll/i);
      // Initial state should be true (autoScroll default is true)
      expect(toggle.getAttribute("aria-checked")).toBe("true");

      await user.click(toggle);

      await waitFor(() => {
        expect(toggle.getAttribute("aria-checked")).toBe("false");
      });
    });
  });

  // ===========================================================================
  // Accessibility Settings Tab Tests
  // ===========================================================================

  describe("Accessibility settings tab", () => {
    it("should render reduced motion toggle", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(
          screen.getByRole("tab", { name: /accessibility/i }),
        ).toBeInTheDocument();
      });

      await user.click(screen.getByRole("tab", { name: /accessibility/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/reduce motion/i)).toBeInTheDocument();
      });
    });

    it("should render high contrast toggle", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /accessibility/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/high contrast/i)).toBeInTheDocument();
      });
    });

    it("should render screen reader mode toggle", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /accessibility/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/screen reader/i)).toBeInTheDocument();
      });
    });

    it("should render font size selector", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /accessibility/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/font size/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Model Defaults Tab Tests
  // ===========================================================================

  describe("Model Defaults tab", () => {
    it("should render temperature slider", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /model/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/temperature/i)).toBeInTheDocument();
      });
    });

    it("should render max tokens input", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /model/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/max tokens/i)).toBeInTheDocument();
      });
    });

    it("should render reasoning effort selector", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /model/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/reasoning effort/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Keyboard Shortcuts Tab Tests
  // ===========================================================================

  describe("Keyboard Shortcuts tab", () => {
    it("should render shortcuts list", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /shortcuts/i }));

      await waitFor(() => {
        expect(screen.getByText(/new session/i)).toBeInTheDocument();
      });
    });

    it("should show default shortcuts", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /shortcuts/i }));

      await waitFor(() => {
        expect(screen.getByText(/cmd\+n/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Privacy Tab Tests
  // ===========================================================================

  describe("Privacy tab", () => {
    it("should render analytics toggle", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /privacy/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/analytics/i)).toBeInTheDocument();
      });
    });

    it("should render error reporting toggle", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /privacy/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/error reporting/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Reset to Defaults Tests
  // ===========================================================================

  describe("reset to defaults", () => {
    it("should render reset button", async () => {
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /reset/i }),
        ).toBeInTheDocument();
      });
    });

    it("should show confirmation before reset", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /reset/i }),
        ).toBeInTheDocument();
      });

      await user.click(screen.getByRole("button", { name: /reset/i }));

      await waitFor(() => {
        expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Persistence Tests
  // ===========================================================================

  describe("persistence", () => {
    it("should persist settings to localStorage", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.getByLabelText(/theme/i)).toBeInTheDocument();
      });

      const themeSelect = screen.getByLabelText(/theme/i);
      await user.selectOptions(themeSelect, "dark");

      // Wait for debounced save
      await waitFor(
        () => {
          const stored = localStorage.getItem(STORAGE_KEY);
          expect(stored).toBeTruthy();
          const parsed = JSON.parse(stored!);
          expect(parsed.general.theme).toBe("dark");
        },
        { timeout: 2000 },
      );
    });
  });

  // ===========================================================================
  // Accessibility Tests (WCAG 2.1 AA)
  // ===========================================================================

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(screen.getByRole("tabpanel")).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have proper heading structure", async () => {
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        const headings = screen.getAllByRole("heading");
        expect(headings.length).toBeGreaterThan(0);
      });
    });

    it("should have proper form labels", async () => {
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        const themeInput = screen.getByLabelText(/theme/i);
        expect(themeInput).toBeInTheDocument();
      });
    });

    it("should support focus management", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(
          screen.getByRole("tab", { name: /general/i }),
        ).toBeInTheDocument();
      });

      // Tab navigation should work
      await user.tab();
      expect(document.activeElement).toBeTruthy();
    });
  });

  // ===========================================================================
  // HITL Agent Approval Tab Tests
  // ===========================================================================

  describe("HITL Agent Approval tab", () => {
    it("should render Agent Approval tab in tab list", async () => {
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(
          screen.getByRole("tab", { name: /agent approval/i }),
        ).toBeInTheDocument();
      });
    });

    it("should switch to Agent Approval tab when clicked", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await waitFor(() => {
        expect(
          screen.getByRole("tab", { name: /agent approval/i }),
        ).toBeInTheDocument();
      });

      await user.click(screen.getByRole("tab", { name: /agent approval/i }));

      expect(
        screen.getByRole("tab", { name: /agent approval/i }),
      ).toHaveAttribute("aria-selected", "true");
    });

    it("should render HITL enabled toggle", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /agent approval/i }));

      await waitFor(() => {
        expect(
          screen.getByLabelText(/enable agent approval/i),
        ).toBeInTheDocument();
      });
    });

    it("should toggle HITL enabled when clicked", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /agent approval/i }));

      await waitFor(() => {
        expect(
          screen.getByLabelText(/enable agent approval/i),
        ).toBeInTheDocument();
      });

      const toggle = screen.getByLabelText(/enable agent approval/i);
      const initialState = toggle.getAttribute("aria-checked");

      await user.click(toggle);

      await waitFor(() => {
        expect(toggle.getAttribute("aria-checked")).toBe(
          initialState === "true" ? "false" : "true",
        );
      });
    });

    it("should render confidence threshold slider", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /agent approval/i }));

      await waitFor(() => {
        expect(
          screen.getByLabelText(/confidence threshold/i),
        ).toBeInTheDocument();
      });
    });

    it("should display current confidence threshold value", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /agent approval/i }));

      await waitFor(() => {
        // Default threshold is 70%
        expect(screen.getByText(/70%/i)).toBeInTheDocument();
      });
    });

    it("should render auto-approve threshold slider", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /agent approval/i }));

      await waitFor(() => {
        expect(
          screen.getByLabelText(/auto-approve threshold/i),
        ).toBeInTheDocument();
      });
    });

    it("should display current auto-approve threshold value", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /agent approval/i }));

      await waitFor(() => {
        // Default auto-approve threshold is 90%
        expect(screen.getByText(/90%/i)).toBeInTheDocument();
      });
    });

    it("should render push notifications toggle", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /agent approval/i }));

      await waitFor(() => {
        expect(
          screen.getByLabelText(/push notifications/i),
        ).toBeInTheDocument();
      });
    });

    it("should render sound alerts toggle", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /agent approval/i }));

      await waitFor(() => {
        expect(screen.getByLabelText(/sound alerts/i)).toBeInTheDocument();
      });
    });

    it("should disable settings when HITL is disabled", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /agent approval/i }));

      await waitFor(() => {
        expect(
          screen.getByLabelText(/enable agent approval/i),
        ).toBeInTheDocument();
      });

      // Turn off HITL
      const hitlToggle = screen.getByLabelText(/enable agent approval/i);
      if (hitlToggle.getAttribute("aria-checked") === "true") {
        await user.click(hitlToggle);
      }

      await waitFor(() => {
        expect(hitlToggle.getAttribute("aria-checked")).toBe("false");
      });

      // Verify other controls are disabled
      const confidenceSlider = screen.getByLabelText(/confidence threshold/i);
      expect(confidenceSlider).toBeDisabled();

      const autoApproveSlider = screen.getByLabelText(
        /auto-approve threshold/i,
      );
      expect(autoApproveSlider).toBeDisabled();

      const pushToggle = screen.getByLabelText(/push notifications/i);
      expect(pushToggle).toBeDisabled();

      const soundToggle = screen.getByLabelText(/sound alerts/i);
      expect(soundToggle).toBeDisabled();
    });

    it("should enable settings when HITL is enabled", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /agent approval/i }));

      await waitFor(() => {
        expect(
          screen.getByLabelText(/enable agent approval/i),
        ).toBeInTheDocument();
      });

      // Ensure HITL is on
      const hitlToggle = screen.getByLabelText(/enable agent approval/i);
      if (hitlToggle.getAttribute("aria-checked") === "false") {
        await user.click(hitlToggle);
      }

      await waitFor(() => {
        expect(hitlToggle.getAttribute("aria-checked")).toBe("true");
      });

      // Verify other controls are enabled
      const confidenceSlider = screen.getByLabelText(/confidence threshold/i);
      expect(confidenceSlider).not.toBeDisabled();

      const autoApproveSlider = screen.getByLabelText(
        /auto-approve threshold/i,
      );
      expect(autoApproveSlider).not.toBeDisabled();

      const pushToggle = screen.getByLabelText(/push notifications/i);
      expect(pushToggle).not.toBeDisabled();

      const soundToggle = screen.getByLabelText(/sound alerts/i);
      expect(soundToggle).not.toBeDisabled();
    });

    it("should persist HITL settings to localStorage", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /agent approval/i }));

      await waitFor(() => {
        expect(
          screen.getByLabelText(/enable agent approval/i),
        ).toBeInTheDocument();
      });

      // Toggle HITL off
      const hitlToggle = screen.getByLabelText(/enable agent approval/i);
      if (hitlToggle.getAttribute("aria-checked") === "true") {
        await user.click(hitlToggle);
      }

      // Wait for debounced save
      await waitFor(
        () => {
          const stored = localStorage.getItem(STORAGE_KEY);
          expect(stored).toBeTruthy();
          const parsed = JSON.parse(stored!);
          expect(parsed.hitl).toBeDefined();
          expect(parsed.hitl.enabled).toBe(false);
        },
        { timeout: 2000 },
      );
    });

    it("should have no accessibility violations for HITL tab", async () => {
      const user = userEvent.setup();
      const { container } = renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /agent approval/i }));

      await waitFor(() => {
        expect(
          screen.getByLabelText(/enable agent approval/i),
        ).toBeInTheDocument();
      });

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    // Threshold Recommendation Tests
    it("should render threshold recommendation section", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /agent approval/i }));

      await waitFor(() => {
        expect(
          screen.getByText(/threshold recommendation/i),
        ).toBeInTheDocument();
      });
    });

    it("should show loading state when fetching recommendation", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /agent approval/i }));

      await waitFor(() => {
        // Should show fetch recommendation button
        expect(
          screen.getByRole("button", { name: /get recommendation/i }),
        ).toBeInTheDocument();
      });
    });

    it("should have apply recommendation button", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /agent approval/i }));

      await waitFor(() => {
        // Apply button should be present but disabled until recommendation is fetched
        const applyButton = screen.getByRole("button", {
          name: /apply recommendation/i,
        });
        expect(applyButton).toBeInTheDocument();
        expect(applyButton).toBeDisabled();
      });
    });

    it("should show auto-adjust toggle", async () => {
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel />);

      await user.click(screen.getByRole("tab", { name: /agent approval/i }));

      await waitFor(() => {
        expect(
          screen.getByLabelText(/auto-adjust thresholds/i),
        ).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Callback Tests
  // ===========================================================================

  describe("callbacks", () => {
    it("should call onClose when close button is clicked", async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();
      renderWithProvider(<SettingsPanel onClose={onClose} />);

      await waitFor(() => {
        expect(
          screen.getByRole("button", { name: /close/i }),
        ).toBeInTheDocument();
      });

      await user.click(screen.getByRole("button", { name: /close/i }));

      expect(onClose).toHaveBeenCalled();
    });
  });
});
