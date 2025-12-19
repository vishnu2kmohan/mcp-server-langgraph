/**
 * ThemeToggle Tests
 *
 * TDD tests for the Theme Toggle component.
 * Tests cover:
 * - Toggle rendering
 * - Theme switching (light/dark/system)
 * - Visual state indicators
 * - WCAG 2.1 AA accessibility
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import { ThemeToggle } from "./ThemeToggle";

expect.extend(toHaveNoViolations);

// Mock matchMedia for system preference detection
const mockMatchMedia = (matches: boolean) => {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: vi.fn().mockImplementation((query) => ({
      matches,
      media: query,
      onchange: null,
      addListener: vi.fn(),
      removeListener: vi.fn(),
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      dispatchEvent: vi.fn(),
    })),
  });
};

describe("ThemeToggle", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockMatchMedia(false); // Default to light mode system preference
    document.documentElement.classList.remove("dark");
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("should render the toggle button", () => {
      render(<ThemeToggle />);

      expect(
        screen.getByRole("button", { name: /theme/i }),
      ).toBeInTheDocument();
    });

    it("should render with custom className", () => {
      render(<ThemeToggle className="custom-class" />);

      expect(screen.getByRole("button", { name: /theme/i })).toHaveClass(
        "custom-class",
      );
    });
  });

  // ===========================================================================
  // Theme State Tests
  // ===========================================================================

  describe("theme state", () => {
    it("should show light theme icon when in light mode", () => {
      render(<ThemeToggle theme="light" />);

      expect(screen.getByTestId("sun-icon")).toBeInTheDocument();
    });

    it("should show dark theme icon when in dark mode", () => {
      render(<ThemeToggle theme="dark" />);

      expect(screen.getByTestId("moon-icon")).toBeInTheDocument();
    });

    it("should show system theme icon when using system preference", () => {
      render(<ThemeToggle theme="system" />);

      expect(screen.getByTestId("monitor-icon")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Theme Switching Tests
  // ===========================================================================

  describe("theme switching", () => {
    it("should call onThemeChange when clicked", async () => {
      const onThemeChange = vi.fn();
      const user = userEvent.setup();
      render(<ThemeToggle theme="light" onThemeChange={onThemeChange} />);

      await user.click(screen.getByRole("button", { name: /theme/i }));

      expect(onThemeChange).toHaveBeenCalled();
    });

    it("should cycle from light to dark to system", async () => {
      const onThemeChange = vi.fn();
      const user = userEvent.setup();
      const { rerender } = render(
        <ThemeToggle theme="light" onThemeChange={onThemeChange} />,
      );

      // Click to go to dark
      await user.click(screen.getByRole("button", { name: /theme/i }));
      expect(onThemeChange).toHaveBeenCalledWith("dark");

      // Rerender as dark and click to go to system
      rerender(<ThemeToggle theme="dark" onThemeChange={onThemeChange} />);
      await user.click(screen.getByRole("button", { name: /theme/i }));
      expect(onThemeChange).toHaveBeenCalledWith("system");

      // Rerender as system and click to go to light
      rerender(<ThemeToggle theme="system" onThemeChange={onThemeChange} />);
      await user.click(screen.getByRole("button", { name: /theme/i }));
      expect(onThemeChange).toHaveBeenCalledWith("light");
    });
  });

  // ===========================================================================
  // Dropdown Mode Tests
  // ===========================================================================

  describe("dropdown mode", () => {
    it("should show dropdown when variant is dropdown", async () => {
      const user = userEvent.setup();
      render(
        <ThemeToggle
          variant="dropdown"
          theme="light"
          onThemeChange={() => {}}
        />,
      );

      await user.click(screen.getByRole("button", { name: /theme/i }));

      await waitFor(() => {
        expect(screen.getByRole("menu")).toBeInTheDocument();
      });
    });

    it("should show all theme options in dropdown", async () => {
      const user = userEvent.setup();
      render(
        <ThemeToggle
          variant="dropdown"
          theme="light"
          onThemeChange={() => {}}
        />,
      );

      await user.click(screen.getByRole("button", { name: /theme/i }));

      await waitFor(() => {
        expect(
          screen.getByRole("menuitem", { name: /light/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("menuitem", { name: /dark/i }),
        ).toBeInTheDocument();
        expect(
          screen.getByRole("menuitem", { name: /system/i }),
        ).toBeInTheDocument();
      });
    });

    it("should call onThemeChange when dropdown option is selected", async () => {
      const onThemeChange = vi.fn();
      const user = userEvent.setup();
      render(
        <ThemeToggle
          variant="dropdown"
          theme="light"
          onThemeChange={onThemeChange}
        />,
      );

      await user.click(screen.getByRole("button", { name: /theme/i }));
      await user.click(screen.getByRole("menuitem", { name: /dark/i }));

      expect(onThemeChange).toHaveBeenCalledWith("dark");
    });
  });

  // ===========================================================================
  // Compact Mode Tests
  // ===========================================================================

  describe("compact mode", () => {
    it("should hide label text in compact mode", () => {
      render(<ThemeToggle compact theme="light" />);

      expect(screen.queryByText(/light mode/i)).not.toBeInTheDocument();
    });

    it("should show tooltip on hover in compact mode", async () => {
      const user = userEvent.setup();
      render(<ThemeToggle compact theme="light" />);

      await user.hover(screen.getByRole("button", { name: /theme/i }));

      await waitFor(() => {
        expect(screen.getByRole("tooltip")).toBeInTheDocument();
      });
    });
  });

  // ===========================================================================
  // Accessibility Tests (WCAG 2.1 AA)
  // ===========================================================================

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(<ThemeToggle theme="light" />);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have proper aria-label", () => {
      render(<ThemeToggle theme="light" />);

      expect(screen.getByRole("button", { name: /theme/i })).toHaveAttribute(
        "aria-label",
      );
    });

    it("should indicate current theme state", () => {
      render(<ThemeToggle theme="dark" />);

      const button = screen.getByRole("button", { name: /theme/i });
      expect(button).toHaveAttribute("aria-pressed", "true");
    });
  });
});
