/**
 * AccessibilitySettings Tests
 *
 * TDD tests for the Accessibility Settings component.
 * Tests cover:
 * - Screen reader mode toggle
 * - Reduced motion toggle
 * - High contrast mode toggle
 * - Font size selector
 * - Enhanced focus indicators toggle
 * - WCAG 2.1 AA accessibility compliance
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { AccessibilitySettings } from "./AccessibilitySettings";

expect.extend(toHaveNoViolations);

// Mock useAccessibility hook
const mockSetScreenReaderMode = vi.fn();
const mockSetReducedMotion = vi.fn();
const mockSetHighContrast = vi.fn();
const mockSetFontSize = vi.fn();
const mockSetEnhancedFocus = vi.fn();
const mockResetToDefaults = vi.fn();

vi.mock("../../hooks/useAccessibility", () => ({
  useAccessibility: () => ({
    screenReaderMode: false,
    reducedMotion: false,
    highContrast: false,
    fontSize: "medium" as const,
    enhancedFocus: false,
    setScreenReaderMode: mockSetScreenReaderMode,
    setReducedMotion: mockSetReducedMotion,
    setHighContrast: mockSetHighContrast,
    setFontSize: mockSetFontSize,
    setEnhancedFocus: mockSetEnhancedFocus,
    resetToDefaults: mockResetToDefaults,
    announce: vi.fn(),
  }),
}));

describe("AccessibilitySettings", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("should render all accessibility settings sections", () => {
      render(<AccessibilitySettings />);

      // Use getAllByText and check at least one exists (there may be sr-only duplicates)
      expect(screen.getAllByText("Screen Reader Mode").length).toBeGreaterThan(
        0,
      );
      expect(screen.getAllByText("Reduced Motion").length).toBeGreaterThan(0);
      expect(screen.getAllByText("High Contrast").length).toBeGreaterThan(0);
      expect(screen.getByText("Font Size")).toBeInTheDocument();
      expect(
        screen.getAllByText("Enhanced Focus Indicators").length,
      ).toBeGreaterThan(0);
    });

    it("should render section descriptions", () => {
      render(<AccessibilitySettings />);

      expect(
        screen.getByText(/optimize the interface for screen reader/i),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/reduce animations and motion/i),
      ).toBeInTheDocument();
      expect(
        screen.getByText(/increase color contrast for better/i),
      ).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Screen Reader Mode Tests
  // ===========================================================================

  describe("screen reader mode", () => {
    it("should toggle screen reader mode when clicked", async () => {
      const user = userEvent.setup();
      render(<AccessibilitySettings />);

      const toggle = screen.getByTestId("screen-reader-toggle");
      await user.click(toggle);

      expect(mockSetScreenReaderMode).toHaveBeenCalledWith(true);
    });
  });

  // ===========================================================================
  // Reduced Motion Tests
  // ===========================================================================

  describe("reduced motion", () => {
    it("should toggle reduced motion when clicked", async () => {
      const user = userEvent.setup();
      render(<AccessibilitySettings />);

      const toggle = screen.getByTestId("reduced-motion-toggle");
      await user.click(toggle);

      expect(mockSetReducedMotion).toHaveBeenCalledWith(true);
    });
  });

  // ===========================================================================
  // High Contrast Tests
  // ===========================================================================

  describe("high contrast", () => {
    it("should toggle high contrast when clicked", async () => {
      const user = userEvent.setup();
      render(<AccessibilitySettings />);

      const toggle = screen.getByTestId("high-contrast-toggle");
      await user.click(toggle);

      expect(mockSetHighContrast).toHaveBeenCalledWith(true);
    });
  });

  // ===========================================================================
  // Font Size Tests
  // ===========================================================================

  describe("font size", () => {
    it("should render font size options", () => {
      render(<AccessibilitySettings />);

      expect(screen.getByTestId("font-size-small")).toBeInTheDocument();
      expect(screen.getByTestId("font-size-medium")).toBeInTheDocument();
      expect(screen.getByTestId("font-size-large")).toBeInTheDocument();
    });

    it("should call setFontSize when size option is clicked", async () => {
      const user = userEvent.setup();
      render(<AccessibilitySettings />);

      await user.click(screen.getByTestId("font-size-large"));

      expect(mockSetFontSize).toHaveBeenCalledWith("large");
    });
  });

  // ===========================================================================
  // Enhanced Focus Tests
  // ===========================================================================

  describe("enhanced focus", () => {
    it("should toggle enhanced focus when clicked", async () => {
      const user = userEvent.setup();
      render(<AccessibilitySettings />);

      const toggle = screen.getByTestId("enhanced-focus-toggle");
      await user.click(toggle);

      expect(mockSetEnhancedFocus).toHaveBeenCalledWith(true);
    });
  });

  // ===========================================================================
  // Reset Tests
  // ===========================================================================

  describe("reset", () => {
    it("should render reset button", () => {
      render(<AccessibilitySettings />);

      expect(
        screen.getByRole("button", { name: /reset to defaults/i }),
      ).toBeInTheDocument();
    });

    it("should call resetToDefaults when reset is clicked", async () => {
      const user = userEvent.setup();
      render(<AccessibilitySettings />);

      await user.click(
        screen.getByRole("button", { name: /reset to defaults/i }),
      );

      expect(mockResetToDefaults).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Accessibility Tests (WCAG 2.1 AA)
  // ===========================================================================

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(<AccessibilitySettings />);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have proper heading structure", () => {
      render(<AccessibilitySettings />);

      expect(
        screen.getByRole("heading", { name: /accessibility/i }),
      ).toBeInTheDocument();
    });

    it("should have proper labels for all controls", () => {
      render(<AccessibilitySettings />);

      // All toggles should be accessible
      const toggles = screen.getAllByRole("switch");
      toggles.forEach((toggle) => {
        expect(toggle).toHaveAccessibleName();
      });
    });

    it("should be keyboard navigable", async () => {
      const user = userEvent.setup();
      render(<AccessibilitySettings />);

      // Tab through the controls
      await user.tab();
      expect(screen.getByTestId("screen-reader-toggle")).toHaveFocus();

      await user.tab();
      expect(screen.getByTestId("reduced-motion-toggle")).toHaveFocus();

      await user.tab();
      expect(screen.getByTestId("high-contrast-toggle")).toHaveFocus();
    });

    it("should support keyboard activation of toggles", async () => {
      const user = userEvent.setup();
      render(<AccessibilitySettings />);

      // Tab to the first toggle and activate with Enter
      await user.tab();
      await user.keyboard("{Enter}");

      expect(mockSetScreenReaderMode).toHaveBeenCalledWith(true);
    });
  });

  // ===========================================================================
  // Custom ClassName Tests
  // ===========================================================================

  describe("custom className", () => {
    it("should apply custom className", () => {
      render(<AccessibilitySettings className="custom-class" />);

      expect(screen.getByTestId("accessibility-settings")).toHaveClass(
        "custom-class",
      );
    });
  });
});
