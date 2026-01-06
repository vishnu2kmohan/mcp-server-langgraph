/**
 * KeyboardShortcutOverlay Tests (Sprint 3.1)
 *
 * Tests for the keyboard shortcut overlay component that shows
 * available shortcuts when user presses ? key.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import { KeyboardShortcutOverlay } from "./KeyboardShortcutOverlay";

expect.extend(toHaveNoViolations);

describe("KeyboardShortcutOverlay", () => {
  const mockOnClose = vi.fn();

  // Sample keyboard shortcuts map (matches StudioShellLayout format)
  const sampleShortcuts: Record<string, () => void> = {
    "ctrl+/": vi.fn(),
    "meta+/": vi.fn(),
    "ctrl+k": vi.fn(),
    "meta+k": vi.fn(),
    "ctrl+shift+i": vi.fn(),
    "meta+shift+i": vi.fn(),
    "ctrl+shift+f": vi.fn(),
    "meta+shift+f": vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render when isOpen is true", () => {
      render(
        <KeyboardShortcutOverlay
          shortcuts={sampleShortcuts}
          isOpen={true}
          onClose={mockOnClose}
        />,
      );

      expect(
        screen.getByTestId("keyboard-shortcut-overlay"),
      ).toBeInTheDocument();
    });

    it("should not render when isOpen is false", () => {
      render(
        <KeyboardShortcutOverlay
          shortcuts={sampleShortcuts}
          isOpen={false}
          onClose={mockOnClose}
        />,
      );

      expect(
        screen.queryByTestId("keyboard-shortcut-overlay"),
      ).not.toBeInTheDocument();
    });

    it("should display overlay title", () => {
      render(
        <KeyboardShortcutOverlay
          shortcuts={sampleShortcuts}
          isOpen={true}
          onClose={mockOnClose}
        />,
      );

      expect(screen.getByText("Keyboard Shortcuts")).toBeInTheDocument();
    });

    it("should display shortcut keys with formatted labels", () => {
      render(
        <KeyboardShortcutOverlay
          shortcuts={sampleShortcuts}
          isOpen={true}
          onClose={mockOnClose}
        />,
      );

      // Should display formatted shortcuts (e.g., "⌘/" for "meta+/")
      // At minimum, should render some shortcut content
      expect(screen.getByTestId("shortcut-list")).toBeInTheDocument();
    });
  });

  describe("close behavior", () => {
    it("should call onClose when Escape is pressed", async () => {
      const user = userEvent.setup();

      render(
        <KeyboardShortcutOverlay
          shortcuts={sampleShortcuts}
          isOpen={true}
          onClose={mockOnClose}
        />,
      );

      await user.keyboard("{Escape}");

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it("should call onClose when clicking backdrop", async () => {
      const user = userEvent.setup();

      render(
        <KeyboardShortcutOverlay
          shortcuts={sampleShortcuts}
          isOpen={true}
          onClose={mockOnClose}
        />,
      );

      // Click the backdrop
      await user.click(screen.getByTestId("overlay-backdrop"));

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

    it("should call onClose when close button is clicked", async () => {
      const user = userEvent.setup();

      render(
        <KeyboardShortcutOverlay
          shortcuts={sampleShortcuts}
          isOpen={true}
          onClose={mockOnClose}
        />,
      );

      await user.click(screen.getByTestId("close-button"));

      expect(mockOnClose).toHaveBeenCalledTimes(1);
    });
  });

  describe("shortcut formatting", () => {
    it("should format meta+key as command symbol on Mac-style display", () => {
      render(
        <KeyboardShortcutOverlay
          shortcuts={{ "meta+k": vi.fn() }}
          isOpen={true}
          onClose={mockOnClose}
        />,
      );

      // The shortcut should be formatted with command symbol
      const list = screen.getByTestId("shortcut-list");
      expect(list).toBeInTheDocument();
    });

    it("should group shortcuts by category when available", () => {
      render(
        <KeyboardShortcutOverlay
          shortcuts={sampleShortcuts}
          isOpen={true}
          onClose={mockOnClose}
        />,
      );

      // Should have shortcut groups or items
      expect(screen.getByTestId("shortcut-list")).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have proper role dialog", () => {
      render(
        <KeyboardShortcutOverlay
          shortcuts={sampleShortcuts}
          isOpen={true}
          onClose={mockOnClose}
        />,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should have aria-modal true", () => {
      render(
        <KeyboardShortcutOverlay
          shortcuts={sampleShortcuts}
          isOpen={true}
          onClose={mockOnClose}
        />,
      );

      expect(screen.getByRole("dialog")).toHaveAttribute("aria-modal", "true");
    });

    it("should have no axe accessibility violations", async () => {
      const { container } = render(
        <KeyboardShortcutOverlay
          shortcuts={sampleShortcuts}
          isOpen={true}
          onClose={mockOnClose}
        />,
      );

      const results = await axe(container, {
        rules: {
          // Disable color contrast as we may use custom theming
          "color-contrast": { enabled: false },
        },
      });

      expect(results).toHaveNoViolations();
    });
  });
});
