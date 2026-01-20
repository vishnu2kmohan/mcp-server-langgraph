/**
 * ThemeSettings Component Tests
 *
 * Tests for the theme and appearance settings panel.
 */

import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, Mock } from "vitest";
import { ThemeSettings } from "./ThemeSettings";
import { useTheme, usePreferences } from "../../contexts/PreferencesContext";
import type { ThemeMode, ColorTheme, CodeFontTheme } from "../../types/preferences";

// Mock the hooks
vi.mock("../../contexts/PreferencesContext", () => ({
  useTheme: vi.fn(),
  usePreferences: vi.fn(),
}));

describe("ThemeSettings", () => {
  const mockSetTheme = vi.fn();
  const mockUpdateGeneralPreferences = vi.fn();
  const mockResetToDefaults = vi.fn();

  const defaultPreferences = {
    general: {
      theme: "system" as ThemeMode,
      colorTheme: "violet-sage" as ColorTheme,
      codeFontTheme: "jetbrains" as CodeFontTheme,
      language: "en",
      autoScroll: true,
      notificationsEnabled: true,
      showShortcutHints: true,
    },
  };

  beforeEach(() => {
    vi.clearAllMocks();
    (useTheme as Mock).mockReturnValue({
      theme: "system" as ThemeMode,
      effectiveTheme: "light",
      setTheme: mockSetTheme,
    });
    (usePreferences as Mock).mockReturnValue({
      preferences: defaultPreferences,
      updateGeneralPreferences: mockUpdateGeneralPreferences,
      resetToDefaults: mockResetToDefaults,
    });
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("renders the component with header", () => {
      render(<ThemeSettings />);

      expect(screen.getByTestId("theme-settings")).toBeInTheDocument();
      expect(screen.getByText("Theme & Appearance")).toBeInTheDocument();
      expect(
        screen.getByText("Customize the look and feel of Agent Studio")
      ).toBeInTheDocument();
    });

    it("renders all theme mode options", () => {
      render(<ThemeSettings />);

      expect(screen.getByTestId("theme-mode-light")).toBeInTheDocument();
      expect(screen.getByTestId("theme-mode-dark")).toBeInTheDocument();
      expect(screen.getByTestId("theme-mode-system")).toBeInTheDocument();
    });

    it("renders all color theme options", () => {
      render(<ThemeSettings />);

      expect(screen.getByTestId("color-theme-violet-sage")).toBeInTheDocument();
      expect(screen.getByTestId("color-theme-teal-sage")).toBeInTheDocument();
      expect(screen.getByTestId("color-theme-violet-olive")).toBeInTheDocument();
      expect(screen.getByTestId("color-theme-teal-olive")).toBeInTheDocument();
    });

    it("renders all code font options", () => {
      render(<ThemeSettings />);

      expect(screen.getByTestId("code-font-jetbrains")).toBeInTheDocument();
      expect(screen.getByTestId("code-font-firacode")).toBeInTheDocument();
      expect(screen.getByTestId("code-font-monaspace")).toBeInTheDocument();
    });

    it("renders reset to defaults button", () => {
      render(<ThemeSettings />);

      expect(screen.getByTestId("reset-theme-defaults")).toBeInTheDocument();
      expect(screen.getByText("Reset to Defaults")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Theme Mode Selection Tests
  // ===========================================================================

  describe("theme mode selection", () => {
    it("shows system theme as selected by default", () => {
      render(<ThemeSettings />);

      const systemButton = screen.getByTestId("theme-mode-system");
      expect(systemButton).toHaveAttribute("aria-checked", "true");
    });

    it("calls setTheme when light mode is clicked", () => {
      render(<ThemeSettings />);

      fireEvent.click(screen.getByTestId("theme-mode-light"));

      expect(mockSetTheme).toHaveBeenCalledWith("light");
    });

    it("calls setTheme when dark mode is clicked", () => {
      render(<ThemeSettings />);

      fireEvent.click(screen.getByTestId("theme-mode-dark"));

      expect(mockSetTheme).toHaveBeenCalledWith("dark");
    });

    it("shows correct selection when theme prop changes", () => {
      (useTheme as Mock).mockReturnValue({
        theme: "dark" as ThemeMode,
        effectiveTheme: "dark",
        setTheme: mockSetTheme,
      });

      render(<ThemeSettings />);

      const darkButton = screen.getByTestId("theme-mode-dark");
      expect(darkButton).toHaveAttribute("aria-checked", "true");
    });
  });

  // ===========================================================================
  // Color Theme Selection Tests
  // ===========================================================================

  describe("color theme selection", () => {
    it("shows violet-sage as selected by default", () => {
      render(<ThemeSettings />);

      const violetSageButton = screen.getByTestId("color-theme-violet-sage");
      expect(violetSageButton).toHaveAttribute("aria-checked", "true");
    });

    it("calls updateGeneralPreferences when teal-sage is clicked", () => {
      render(<ThemeSettings />);

      fireEvent.click(screen.getByTestId("color-theme-teal-sage"));

      expect(mockUpdateGeneralPreferences).toHaveBeenCalledWith({
        colorTheme: "teal-sage",
      });
    });

    it("calls updateGeneralPreferences when violet-olive is clicked", () => {
      render(<ThemeSettings />);

      fireEvent.click(screen.getByTestId("color-theme-violet-olive"));

      expect(mockUpdateGeneralPreferences).toHaveBeenCalledWith({
        colorTheme: "violet-olive",
      });
    });

    it("displays color swatches for each theme", () => {
      render(<ThemeSettings />);

      // Each theme button should contain a color swatch
      const violetSageButton = screen.getByTestId("color-theme-violet-sage");
      expect(violetSageButton.querySelector("div > div")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Code Font Selection Tests
  // ===========================================================================

  describe("code font selection", () => {
    it("shows jetbrains as selected by default", () => {
      render(<ThemeSettings />);

      const jetbrainsButton = screen.getByTestId("code-font-jetbrains");
      expect(jetbrainsButton).toHaveAttribute("aria-checked", "true");
    });

    it("calls updateGeneralPreferences when firacode is clicked", () => {
      render(<ThemeSettings />);

      fireEvent.click(screen.getByTestId("code-font-firacode"));

      expect(mockUpdateGeneralPreferences).toHaveBeenCalledWith({
        codeFontTheme: "firacode",
      });
    });

    it("calls updateGeneralPreferences when monaspace is clicked", () => {
      render(<ThemeSettings />);

      fireEvent.click(screen.getByTestId("code-font-monaspace"));

      expect(mockUpdateGeneralPreferences).toHaveBeenCalledWith({
        codeFontTheme: "monaspace",
      });
    });

    it("displays font preview for each option", () => {
      render(<ThemeSettings />);

      // Each code font should display the character preview "0O1l"
      expect(screen.getAllByText("0O1l")).toHaveLength(3);
    });
  });

  // ===========================================================================
  // Reset to Defaults Tests
  // ===========================================================================

  describe("reset to defaults", () => {
    it("calls resetToDefaults when button is clicked", () => {
      render(<ThemeSettings />);

      fireEvent.click(screen.getByTestId("reset-theme-defaults"));

      expect(mockResetToDefaults).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Accessibility Tests
  // ===========================================================================

  describe("accessibility", () => {
    it("uses radiogroup role for theme mode selector", () => {
      render(<ThemeSettings />);

      const radiogroup = screen.getByRole("radiogroup", { name: "Theme mode" });
      expect(radiogroup).toBeInTheDocument();
    });

    it("uses radiogroup role for color theme selector", () => {
      render(<ThemeSettings />);

      const radiogroup = screen.getByRole("radiogroup", { name: "Color theme" });
      expect(radiogroup).toBeInTheDocument();
    });

    it("uses radiogroup role for code font selector", () => {
      render(<ThemeSettings />);

      const radiogroup = screen.getByRole("radiogroup", { name: "Code font" });
      expect(radiogroup).toBeInTheDocument();
    });

    it("has correct aria-checked states for theme modes", () => {
      render(<ThemeSettings />);

      expect(screen.getByTestId("theme-mode-light")).toHaveAttribute(
        "aria-checked",
        "false"
      );
      expect(screen.getByTestId("theme-mode-dark")).toHaveAttribute(
        "aria-checked",
        "false"
      );
      expect(screen.getByTestId("theme-mode-system")).toHaveAttribute(
        "aria-checked",
        "true"
      );
    });
  });

  // ===========================================================================
  // CSS Class Tests
  // ===========================================================================

  describe("custom className", () => {
    it("applies custom className to root element", () => {
      render(<ThemeSettings className="custom-class" />);

      expect(screen.getByTestId("theme-settings")).toHaveClass("custom-class");
    });
  });
});
