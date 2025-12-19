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
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { SettingsPanel } from "./SettingsPanel";
import { PreferencesProvider } from "../../contexts/PreferencesContext";

expect.extend(toHaveNoViolations);

// Storage key used by the context
const STORAGE_KEY = "mcp_studio_preferences";

// Helper to create wrapper with preferences provider
const renderWithProvider = (ui: React.ReactElement) => {
  return render(<PreferencesProvider>{ui}</PreferencesProvider>);
};

describe("SettingsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    localStorage.clear();
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
