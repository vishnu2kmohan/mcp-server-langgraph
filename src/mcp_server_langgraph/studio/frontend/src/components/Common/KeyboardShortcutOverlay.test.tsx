/**
 * KeyboardShortcutOverlay Component Tests
 *
 * TDD tests for the keyboard shortcut help overlay.
 * Toggled with the ? key or from Help menu.
 *
 * Reference: Plan - StudioShell UX Audit - Sprint 3.2
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import React from "react";

// Mock shortcuts that would come from StudioShellLayout
const mockShortcuts = {
  "meta+k": vi.fn(),
  "ctrl+k": vi.fn(),
  "meta+/": vi.fn(),
  "ctrl+/": vi.fn(),
  "meta+shift+i": vi.fn(),
  "ctrl+shift+i": vi.fn(),
  "meta+shift+f": vi.fn(),
  "ctrl+shift+f": vi.fn(),
  "shift+?": vi.fn(),
  escape: vi.fn(),
};

describe("KeyboardShortcutOverlay", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("Export", () => {
    it("should export KeyboardShortcutOverlay component", async () => {
      const module = await import("./KeyboardShortcutOverlay");
      expect(module.KeyboardShortcutOverlay).toBeDefined();
    });
  });

  describe("Rendering", () => {
    it("should render overlay when isOpen is true", async () => {
      const { KeyboardShortcutOverlay } =
        await import("./KeyboardShortcutOverlay");

      render(
        <KeyboardShortcutOverlay
          shortcuts={mockShortcuts}
          isOpen={true}
          onClose={() => {}}
        />,
      );

      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByText(/Keyboard Shortcuts/i)).toBeInTheDocument();
    });

    it("should not render when isOpen is false", async () => {
      const { KeyboardShortcutOverlay } =
        await import("./KeyboardShortcutOverlay");

      render(
        <KeyboardShortcutOverlay
          shortcuts={mockShortcuts}
          isOpen={false}
          onClose={() => {}}
        />,
      );

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("should display shortcut list", async () => {
      const { KeyboardShortcutOverlay } =
        await import("./KeyboardShortcutOverlay");

      render(
        <KeyboardShortcutOverlay
          shortcuts={mockShortcuts}
          isOpen={true}
          onClose={() => {}}
        />,
      );

      // Should show common shortcuts
      expect(screen.getByText(/Open Command Palette/i)).toBeInTheDocument();
      expect(screen.getByText(/Toggle Canvas/i)).toBeInTheDocument();
    });
  });

  describe("Interactions", () => {
    it("should call onClose when close button clicked", async () => {
      const { KeyboardShortcutOverlay } =
        await import("./KeyboardShortcutOverlay");

      const onClose = vi.fn();
      render(
        <KeyboardShortcutOverlay
          shortcuts={mockShortcuts}
          isOpen={true}
          onClose={onClose}
        />,
      );

      const closeButton = screen.getByRole("button", {
        name: /close shortcuts/i,
      });
      fireEvent.click(closeButton);

      expect(onClose).toHaveBeenCalled();
    });

    it("should call onClose when Escape key pressed", async () => {
      const { KeyboardShortcutOverlay } =
        await import("./KeyboardShortcutOverlay");

      const onClose = vi.fn();
      render(
        <KeyboardShortcutOverlay
          shortcuts={mockShortcuts}
          isOpen={true}
          onClose={onClose}
        />,
      );

      fireEvent.keyDown(document, { key: "Escape" });

      expect(onClose).toHaveBeenCalled();
    });

    it("should call onClose when backdrop clicked", async () => {
      const { KeyboardShortcutOverlay } =
        await import("./KeyboardShortcutOverlay");

      const onClose = vi.fn();
      render(
        <KeyboardShortcutOverlay
          shortcuts={mockShortcuts}
          isOpen={true}
          onClose={onClose}
        />,
      );

      const backdrop = screen.getByTestId("overlay-backdrop");
      fireEvent.click(backdrop);

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("should have proper dialog role", async () => {
      const { KeyboardShortcutOverlay } =
        await import("./KeyboardShortcutOverlay");

      render(
        <KeyboardShortcutOverlay
          shortcuts={mockShortcuts}
          isOpen={true}
          onClose={() => {}}
        />,
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-modal", "true");
    });

    it("should have accessible name", async () => {
      const { KeyboardShortcutOverlay } =
        await import("./KeyboardShortcutOverlay");

      render(
        <KeyboardShortcutOverlay
          shortcuts={mockShortcuts}
          isOpen={true}
          onClose={() => {}}
        />,
      );

      const dialog = screen.getByRole("dialog");
      expect(dialog).toHaveAttribute("aria-labelledby");
    });
  });

  describe("Shortcut Categories", () => {
    it("should group shortcuts by category", async () => {
      const { KeyboardShortcutOverlay } =
        await import("./KeyboardShortcutOverlay");

      render(
        <KeyboardShortcutOverlay
          shortcuts={mockShortcuts}
          isOpen={true}
          onClose={() => {}}
        />,
      );

      // Should have category headers (from the component's category logic)
      expect(screen.getByText(/General/i)).toBeInTheDocument();
      expect(screen.getByText(/Navigation/i)).toBeInTheDocument();
    });
  });

  describe("Shortcut Display", () => {
    it("should deduplicate meta/ctrl variants", async () => {
      const { KeyboardShortcutOverlay } =
        await import("./KeyboardShortcutOverlay");

      render(
        <KeyboardShortcutOverlay
          shortcuts={mockShortcuts}
          isOpen={true}
          onClose={() => {}}
        />,
      );

      // Should only show one version of command palette shortcut
      const commandPaletteItems = screen.getAllByText(/Open Command Palette/i);
      expect(commandPaletteItems).toHaveLength(1);
    });

    it("should format shortcuts for Mac display", async () => {
      const { KeyboardShortcutOverlay } =
        await import("./KeyboardShortcutOverlay");

      render(
        <KeyboardShortcutOverlay
          shortcuts={mockShortcuts}
          isOpen={true}
          onClose={() => {}}
        />,
      );

      // Should display ⌘ for meta key
      expect(screen.getByText("⌘K")).toBeInTheDocument();
    });
  });
});
