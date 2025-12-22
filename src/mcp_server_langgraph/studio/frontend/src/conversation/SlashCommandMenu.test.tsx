/**
 * SlashCommandMenu Tests - Phase 2
 *
 * Tests for the slash command menu component.
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";
import { SlashCommandMenu, type SlashCommand } from "./SlashCommandMenu";

expect.extend(toHaveNoViolations);

// =============================================================================
// Test Data
// =============================================================================

const mockCommands: SlashCommand[] = [
  {
    id: "help",
    name: "help",
    description: "Show available commands",
    icon: "help-circle",
  },
  {
    id: "clear",
    name: "clear",
    description: "Clear conversation",
    icon: "trash",
  },
  {
    id: "export",
    name: "export",
    description: "Export conversation",
    icon: "download",
  },
  {
    id: "settings",
    name: "settings",
    description: "Open settings",
    icon: "settings",
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("SlashCommandMenu", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render menu container", () => {
      render(
        <SlashCommandMenu
          commands={mockCommands}
          isOpen
          onSelect={() => {}}
          onClose={() => {}}
        />,
      );
      expect(screen.getByTestId("slash-command-menu")).toBeInTheDocument();
    });

    it("should not render when isOpen is false", () => {
      render(
        <SlashCommandMenu
          commands={mockCommands}
          isOpen={false}
          onSelect={() => {}}
          onClose={() => {}}
        />,
      );
      expect(
        screen.queryByTestId("slash-command-menu"),
      ).not.toBeInTheDocument();
    });

    it("should render all commands", () => {
      render(
        <SlashCommandMenu
          commands={mockCommands}
          isOpen
          onSelect={() => {}}
          onClose={() => {}}
        />,
      );
      expect(screen.getByText("/help")).toBeInTheDocument();
      expect(screen.getByText("/clear")).toBeInTheDocument();
      expect(screen.getByText("/export")).toBeInTheDocument();
      expect(screen.getByText("/settings")).toBeInTheDocument();
    });

    it("should display command descriptions", () => {
      render(
        <SlashCommandMenu
          commands={mockCommands}
          isOpen
          onSelect={() => {}}
          onClose={() => {}}
        />,
      );
      expect(screen.getByText("Show available commands")).toBeInTheDocument();
      expect(screen.getByText("Clear conversation")).toBeInTheDocument();
    });
  });

  describe("Filtering", () => {
    it("should filter commands based on query", () => {
      render(
        <SlashCommandMenu
          commands={mockCommands}
          isOpen
          query="he"
          onSelect={() => {}}
          onClose={() => {}}
        />,
      );
      expect(screen.getByText("/help")).toBeInTheDocument();
      expect(screen.queryByText("/clear")).not.toBeInTheDocument();
    });

    it("should show no results message when no matches", () => {
      render(
        <SlashCommandMenu
          commands={mockCommands}
          isOpen
          query="xyz"
          onSelect={() => {}}
          onClose={() => {}}
        />,
      );
      expect(screen.getByText(/no commands found/i)).toBeInTheDocument();
    });
  });

  describe("Selection", () => {
    it("should highlight selected command", () => {
      render(
        <SlashCommandMenu
          commands={mockCommands}
          isOpen
          selectedIndex={1}
          onSelect={() => {}}
          onClose={() => {}}
        />,
      );
      const items = screen.getAllByTestId("command-item");
      expect(items[1]).toHaveClass("selected");
    });

    it("should call onSelect when command clicked", () => {
      const onSelect = vi.fn();
      render(
        <SlashCommandMenu
          commands={mockCommands}
          isOpen
          onSelect={onSelect}
          onClose={() => {}}
        />,
      );

      fireEvent.click(screen.getByText("/help"));
      expect(onSelect).toHaveBeenCalledWith(mockCommands[0]);
    });
  });

  describe("Keyboard Navigation", () => {
    it("should call onKeyDown when key pressed", () => {
      const onKeyDown = vi.fn();
      render(
        <SlashCommandMenu
          commands={mockCommands}
          isOpen
          onSelect={() => {}}
          onClose={() => {}}
          onKeyDown={onKeyDown}
        />,
      );

      const menu = screen.getByTestId("slash-command-menu");
      fireEvent.keyDown(menu, { key: "ArrowDown" });
      expect(onKeyDown).toHaveBeenCalled();
    });
  });

  describe("Close Behavior", () => {
    it("should call onClose when Escape pressed", () => {
      const onClose = vi.fn();
      render(
        <SlashCommandMenu
          commands={mockCommands}
          isOpen
          onSelect={() => {}}
          onClose={onClose}
        />,
      );

      const menu = screen.getByTestId("slash-command-menu");
      fireEvent.keyDown(menu, { key: "Escape" });
      expect(onClose).toHaveBeenCalled();
    });

    it("should call onClose when clicking outside", () => {
      const onClose = vi.fn();
      render(
        <div>
          <div data-testid="outside">Outside</div>
          <SlashCommandMenu
            commands={mockCommands}
            isOpen
            onSelect={() => {}}
            onClose={onClose}
          />
        </div>,
      );

      fireEvent.mouseDown(screen.getByTestId("outside"));
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("Accessibility", () => {
    it("should have no accessibility violations", async () => {
      const { container } = render(
        <SlashCommandMenu
          commands={mockCommands}
          isOpen
          onSelect={() => {}}
          onClose={() => {}}
        />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have no accessibility violations with selected item", async () => {
      const { container } = render(
        <SlashCommandMenu
          commands={mockCommands}
          isOpen
          selectedIndex={1}
          onSelect={() => {}}
          onClose={() => {}}
        />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it("should have aria-label on listbox", () => {
      render(
        <SlashCommandMenu
          commands={mockCommands}
          isOpen
          onSelect={() => {}}
          onClose={() => {}}
        />,
      );
      expect(screen.getByRole("listbox")).toHaveAttribute(
        "aria-label",
        "Slash commands",
      );
    });

    it("should have listbox role", () => {
      render(
        <SlashCommandMenu
          commands={mockCommands}
          isOpen
          onSelect={() => {}}
          onClose={() => {}}
        />,
      );
      expect(screen.getByRole("listbox")).toBeInTheDocument();
    });

    it("should have option role for items", () => {
      render(
        <SlashCommandMenu
          commands={mockCommands}
          isOpen
          onSelect={() => {}}
          onClose={() => {}}
        />,
      );
      expect(screen.getAllByRole("option")).toHaveLength(4);
    });
  });
});
