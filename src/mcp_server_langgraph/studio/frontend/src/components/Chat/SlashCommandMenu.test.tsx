/**
 * SlashCommandMenu Component Tests
 *
 * Tests for the slash command menu that appears when users type "/" in the chat input.
 * Provides quick access to commands like /help, /clear, /export, etc.
 *
 * TDD RED Phase: Write failing tests first.
 */

import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  SlashCommandMenu,
  type SlashCommandMenuProps,
  type SlashCommand,
} from "./SlashCommandMenu";

describe("SlashCommandMenu", () => {
  const mockOnSelect = vi.fn();
  const mockOnClose = vi.fn();

  const defaultCommands: SlashCommand[] = [
    { name: "help", description: "Show available commands", icon: "help" },
    { name: "clear", description: "Clear conversation history", icon: "trash" },
    {
      name: "export",
      description: "Export chat as markdown",
      icon: "download",
    },
    {
      name: "summarize",
      description: "Summarize this conversation",
      icon: "file-text",
    },
  ];

  const defaultProps: SlashCommandMenuProps = {
    commands: defaultCommands,
    onSelect: mockOnSelect,
    onClose: mockOnClose,
    isOpen: true,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("rendering", () => {
    it("should render the menu when isOpen is true", () => {
      render(<SlashCommandMenu {...defaultProps} />);

      expect(screen.getByTestId("slash-command-menu")).toBeInTheDocument();
    });

    it("should not render when isOpen is false", () => {
      render(<SlashCommandMenu {...defaultProps} isOpen={false} />);

      expect(
        screen.queryByTestId("slash-command-menu"),
      ).not.toBeInTheDocument();
    });

    it("should render all commands", () => {
      render(<SlashCommandMenu {...defaultProps} />);

      expect(screen.getByText("/help")).toBeInTheDocument();
      expect(screen.getByText("/clear")).toBeInTheDocument();
      expect(screen.getByText("/export")).toBeInTheDocument();
      expect(screen.getByText("/summarize")).toBeInTheDocument();
    });

    it("should display command descriptions", () => {
      render(<SlashCommandMenu {...defaultProps} />);

      expect(screen.getByText("Show available commands")).toBeInTheDocument();
      expect(
        screen.getByText("Clear conversation history"),
      ).toBeInTheDocument();
    });
  });

  describe("filtering", () => {
    it("should filter commands based on filter prop", () => {
      render(<SlashCommandMenu {...defaultProps} filter="hel" />);

      expect(screen.getByText("/help")).toBeInTheDocument();
      expect(screen.queryByText("/clear")).not.toBeInTheDocument();
    });

    it("should show all commands when filter is empty", () => {
      render(<SlashCommandMenu {...defaultProps} filter="" />);

      expect(screen.getByText("/help")).toBeInTheDocument();
      expect(screen.getByText("/clear")).toBeInTheDocument();
    });

    it("should show no results message when no commands match", () => {
      render(<SlashCommandMenu {...defaultProps} filter="xyz" />);

      expect(screen.getByText(/no commands found/i)).toBeInTheDocument();
    });
  });

  describe("selection", () => {
    it("should call onSelect when a command is clicked", () => {
      render(<SlashCommandMenu {...defaultProps} />);

      fireEvent.click(screen.getByText("/help"));

      expect(mockOnSelect).toHaveBeenCalledWith(defaultCommands[0]);
    });

    it("should call onClose after selection", () => {
      render(<SlashCommandMenu {...defaultProps} />);

      fireEvent.click(screen.getByText("/help"));

      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  describe("keyboard navigation", () => {
    it("should highlight first item by default", () => {
      render(<SlashCommandMenu {...defaultProps} />);

      const firstItem = screen.getByTestId("command-item-help");
      expect(firstItem).toHaveAttribute("data-highlighted", "true");
    });

    it("should navigate down with ArrowDown", () => {
      render(<SlashCommandMenu {...defaultProps} />);

      fireEvent.keyDown(screen.getByTestId("slash-command-menu"), {
        key: "ArrowDown",
      });

      const secondItem = screen.getByTestId("command-item-clear");
      expect(secondItem).toHaveAttribute("data-highlighted", "true");
    });

    it("should navigate up with ArrowUp", () => {
      const mockOnSelectedIndexChange = vi.fn();
      render(
        <SlashCommandMenu
          {...defaultProps}
          selectedIndex={1}
          onSelectedIndexChange={mockOnSelectedIndexChange}
        />,
      );

      fireEvent.keyDown(screen.getByTestId("slash-command-menu"), {
        key: "ArrowUp",
      });

      expect(mockOnSelectedIndexChange).toHaveBeenCalledWith(0);
    });

    it("should select with Enter key", () => {
      render(<SlashCommandMenu {...defaultProps} />);

      fireEvent.keyDown(screen.getByTestId("slash-command-menu"), {
        key: "Enter",
      });

      expect(mockOnSelect).toHaveBeenCalledWith(defaultCommands[0]);
    });

    it("should close with Escape key", () => {
      render(<SlashCommandMenu {...defaultProps} />);

      fireEvent.keyDown(screen.getByTestId("slash-command-menu"), {
        key: "Escape",
      });

      expect(mockOnClose).toHaveBeenCalled();
    });
  });

  describe("accessibility", () => {
    it("should have role listbox", () => {
      render(<SlashCommandMenu {...defaultProps} />);

      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    it("should have aria-label", () => {
      render(<SlashCommandMenu {...defaultProps} />);

      expect(screen.getByRole("listbox")).toHaveAttribute(
        "aria-label",
        "Slash commands",
      );
    });

    it("should have role option for each command", () => {
      render(<SlashCommandMenu {...defaultProps} />);

      const options = screen.getAllByRole("option");
      expect(options).toHaveLength(4);
    });
  });

  describe("custom className", () => {
    it("should apply custom className", () => {
      render(<SlashCommandMenu {...defaultProps} className="custom-class" />);

      const menu = screen.getByTestId("slash-command-menu");
      expect(menu).toHaveClass("custom-class");
    });
  });
});
