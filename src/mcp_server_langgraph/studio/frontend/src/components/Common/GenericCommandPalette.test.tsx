/**
 * GenericCommandPalette Tests
 *
 * TDD tests for the Generic Command Palette component.
 * Tests cover:
 * - Modal rendering
 * - Search input
 * - Command list display
 * - Keyboard navigation
 * - Command execution
 * - WCAG 2.1 AA accessibility compliance
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";
import React from "react";
import {
  GenericCommandPalette,
  GenericCommandPaletteProps,
} from "./GenericCommandPalette";

expect.extend(toHaveNoViolations);

const mockCommands = [
  {
    id: "new-session",
    label: "New Session",
    category: "Session",
    action: vi.fn(),
    shortcut: "Cmd+N",
  },
  {
    id: "open-settings",
    label: "Open Settings",
    category: "Application",
    action: vi.fn(),
    shortcut: "Cmd+,",
  },
  {
    id: "toggle-theme",
    label: "Toggle Dark Mode",
    category: "Application",
    action: vi.fn(),
  },
];

const defaultProps: GenericCommandPaletteProps = {
  isOpen: true,
  onClose: vi.fn(),
  commands: mockCommands,
  onExecute: vi.fn(),
};

describe("GenericCommandPalette", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Rendering Tests
  // ===========================================================================

  describe("rendering", () => {
    it("should render when open", () => {
      render(<GenericCommandPalette {...defaultProps} />);

      expect(screen.getByTestId("command-palette")).toBeInTheDocument();
    });

    it("should not render when closed", () => {
      render(<GenericCommandPalette {...defaultProps} isOpen={false} />);

      expect(screen.queryByTestId("command-palette")).not.toBeInTheDocument();
    });

    it("should render search input", () => {
      render(<GenericCommandPalette {...defaultProps} />);

      expect(
        screen.getByPlaceholderText(/type a command/i),
      ).toBeInTheDocument();
    });

    it("should render command list", () => {
      render(<GenericCommandPalette {...defaultProps} />);

      expect(screen.getByText("New Session")).toBeInTheDocument();
      expect(screen.getByText("Open Settings")).toBeInTheDocument();
      expect(screen.getByText("Toggle Dark Mode")).toBeInTheDocument();
    });

    it("should display shortcuts when available", () => {
      render(<GenericCommandPalette {...defaultProps} />);

      expect(screen.getByText("Cmd+N")).toBeInTheDocument();
      expect(screen.getByText("Cmd+,")).toBeInTheDocument();
    });

    it("should group commands by category", () => {
      render(<GenericCommandPalette {...defaultProps} />);

      expect(screen.getByText("Session")).toBeInTheDocument();
      expect(screen.getByText("Application")).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Search Tests
  // ===========================================================================

  describe("search", () => {
    it("should filter commands when typing", async () => {
      const user = userEvent.setup();
      render(<GenericCommandPalette {...defaultProps} />);

      await user.type(screen.getByPlaceholderText(/type a command/i), "new");

      expect(screen.getByText("New Session")).toBeInTheDocument();
      expect(screen.queryByText("Toggle Dark Mode")).not.toBeInTheDocument();
    });

    it("should show no results message when no matches", async () => {
      const user = userEvent.setup();
      render(<GenericCommandPalette {...defaultProps} />);

      await user.type(
        screen.getByPlaceholderText(/type a command/i),
        "zzzzzzz",
      );

      expect(screen.getByText(/no commands found/i)).toBeInTheDocument();
    });

    it("should focus search input on open", async () => {
      render(<GenericCommandPalette {...defaultProps} />);

      await waitFor(() => {
        expect(screen.getByPlaceholderText(/type a command/i)).toHaveFocus();
      });
    });
  });

  // ===========================================================================
  // Keyboard Navigation Tests
  // ===========================================================================

  describe("keyboard navigation", () => {
    it("should navigate down with arrow down", async () => {
      const user = userEvent.setup();
      render(<GenericCommandPalette {...defaultProps} />);

      await user.keyboard("{ArrowDown}");

      const items = screen.getAllByRole("option");
      expect(items[1]).toHaveAttribute("aria-selected", "true");
    });

    it("should navigate up with arrow up", async () => {
      const user = userEvent.setup();
      render(<GenericCommandPalette {...defaultProps} />);

      await user.keyboard("{ArrowDown}{ArrowDown}{ArrowUp}");

      const items = screen.getAllByRole("option");
      expect(items[1]).toHaveAttribute("aria-selected", "true");
    });

    it("should execute command on Enter", async () => {
      const user = userEvent.setup();
      render(<GenericCommandPalette {...defaultProps} />);

      await user.keyboard("{Enter}");

      expect(defaultProps.onExecute).toHaveBeenCalledWith("new-session");
    });

    it("should close on Escape", async () => {
      const user = userEvent.setup();
      render(<GenericCommandPalette {...defaultProps} />);

      await user.keyboard("{Escape}");

      expect(defaultProps.onClose).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Click Interaction Tests
  // ===========================================================================

  describe("click interactions", () => {
    it("should execute command on click", async () => {
      const user = userEvent.setup();
      render(<GenericCommandPalette {...defaultProps} />);

      await user.click(screen.getByText("Open Settings"));

      expect(defaultProps.onExecute).toHaveBeenCalledWith("open-settings");
    });

    it("should close when clicking backdrop", async () => {
      const user = userEvent.setup();
      render(<GenericCommandPalette {...defaultProps} />);

      await user.click(screen.getByTestId("command-palette-backdrop"));

      expect(defaultProps.onClose).toHaveBeenCalled();
    });
  });

  // ===========================================================================
  // Recent Commands Tests
  // ===========================================================================

  describe("recent commands", () => {
    it("should display recent commands section", () => {
      render(
        <GenericCommandPalette
          {...defaultProps}
          recentCommandIds={["new-session"]}
        />,
      );

      expect(screen.getByText(/recent/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // Accessibility Tests (WCAG 2.1 AA)
  // ===========================================================================

  describe("accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(<GenericCommandPalette {...defaultProps} />);

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have proper ARIA attributes", () => {
      render(<GenericCommandPalette {...defaultProps} />);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
      expect(screen.getByRole("combobox")).toBeInTheDocument();
      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    it("should have aria-label on search input", () => {
      render(<GenericCommandPalette {...defaultProps} />);

      expect(screen.getByRole("combobox")).toHaveAttribute("aria-label");
    });

    it("should have focused search input", async () => {
      render(<GenericCommandPalette {...defaultProps} />);

      // Search input should be focused on open
      await waitFor(() => {
        expect(screen.getByPlaceholderText(/type a command/i)).toHaveFocus();
      });
    });
  });

  // ===========================================================================
  // Custom ClassName Tests
  // ===========================================================================

  describe("custom className", () => {
    it("should apply custom className", () => {
      render(
        <GenericCommandPalette {...defaultProps} className="custom-class" />,
      );

      expect(screen.getByTestId("command-palette")).toHaveClass("custom-class");
    });
  });
});
