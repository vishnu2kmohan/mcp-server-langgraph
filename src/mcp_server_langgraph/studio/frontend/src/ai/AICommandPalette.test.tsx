/**
 * AICommandPalette Tests - Phase 2
 *
 * Tests for AI-enhanced command palette with natural language interpretation.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);
import userEvent from "@testing-library/user-event";
import { AICommandPalette, type Command } from "./AICommandPalette";

// =============================================================================
// Test Data
// =============================================================================

const mockCommands: Command[] = [
  {
    id: "new-chat",
    name: "New Chat",
    description: "Start a new conversation",
    shortcut: "Cmd+N",
    category: "chat",
  },
  {
    id: "clear-chat",
    name: "Clear Chat",
    description: "Clear current conversation",
    shortcut: "Cmd+K",
    category: "chat",
  },
  {
    id: "settings",
    name: "Open Settings",
    description: "Open application settings",
    shortcut: "Cmd+,",
    category: "app",
  },
  {
    id: "export",
    name: "Export Conversation",
    description: "Export to file",
    shortcut: "Cmd+E",
    category: "app",
  },
];

// =============================================================================
// Tests
// =============================================================================

describe("AICommandPalette", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render when open", () => {
      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={() => {}}
          onExecute={() => {}}
        />,
      );
      expect(screen.getByTestId("ai-command-palette")).toBeInTheDocument();
    });

    it("should not render when closed", () => {
      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen={false}
          onClose={() => {}}
          onExecute={() => {}}
        />,
      );
      expect(
        screen.queryByTestId("ai-command-palette"),
      ).not.toBeInTheDocument();
    });

    it("should render search input", () => {
      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={() => {}}
          onExecute={() => {}}
        />,
      );
      expect(screen.getByTestId("command-search")).toBeInTheDocument();
    });

    it("should render all commands", () => {
      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={() => {}}
          onExecute={() => {}}
        />,
      );
      expect(screen.getByText("New Chat")).toBeInTheDocument();
      expect(screen.getByText("Clear Chat")).toBeInTheDocument();
      expect(screen.getByText("Open Settings")).toBeInTheDocument();
    });
  });

  describe("Search", () => {
    it("should filter commands based on search", async () => {
      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={() => {}}
          onExecute={() => {}}
        />,
      );
      const input = screen.getByTestId("command-search");
      await userEvent.type(input, "new");
      expect(screen.getByText("New Chat")).toBeInTheDocument();
      expect(screen.queryByText("Open Settings")).not.toBeInTheDocument();
    });

    it("should show no results message when no matches", async () => {
      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={() => {}}
          onExecute={() => {}}
        />,
      );
      const input = screen.getByTestId("command-search");
      await userEvent.type(input, "nonexistent");
      expect(screen.getByTestId("no-results")).toBeInTheDocument();
    });
  });

  describe("AI Interpretation", () => {
    it("should show AI suggestion when no static matches", async () => {
      const onAIInterpret = vi.fn().mockResolvedValue({
        action: "create_workflow",
        params: { name: "data processing" },
        confidence: 0.85,
      });

      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={() => {}}
          onExecute={() => {}}
          onAIInterpret={onAIInterpret}
        />,
      );

      const input = screen.getByTestId("command-search");
      await userEvent.type(input, "create a workflow for data processing");

      await waitFor(() => {
        expect(screen.getByTestId("ai-suggestion")).toBeInTheDocument();
      });
    });

    it("should show AI indicator on suggestions", async () => {
      const onAIInterpret = vi.fn().mockResolvedValue({
        action: "navigate",
        params: { to: "/traces" },
        confidence: 0.9,
      });

      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={() => {}}
          onExecute={() => {}}
          onAIInterpret={onAIInterpret}
        />,
      );

      const input = screen.getByTestId("command-search");
      await userEvent.type(input, "show me yesterday's traces");

      await waitFor(() => {
        expect(screen.getByTestId("ai-badge")).toBeInTheDocument();
      });
    });
  });

  describe("Execution", () => {
    it("should call onExecute when command clicked", () => {
      const onExecute = vi.fn();
      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={() => {}}
          onExecute={onExecute}
        />,
      );
      fireEvent.click(screen.getByText("New Chat"));
      expect(onExecute).toHaveBeenCalledWith(mockCommands[0]);
    });

    it("should close palette after execution", () => {
      const onClose = vi.fn();
      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={onClose}
          onExecute={() => {}}
        />,
      );
      fireEvent.click(screen.getByText("New Chat"));
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("Keyboard Navigation", () => {
    it("should navigate with arrow keys", async () => {
      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={() => {}}
          onExecute={() => {}}
        />,
      );
      // First item is already selected (index 0), ArrowDown moves to second item (index 1)
      const input = screen.getByTestId("command-search");
      const items = screen.getAllByTestId("command-item");
      expect(items[0]).toHaveClass("selected"); // Initially first is selected
      fireEvent.keyDown(input, { key: "ArrowDown" });
      expect(items[1]).toHaveClass("selected"); // After ArrowDown, second is selected
    });

    it("should execute on Enter key", async () => {
      const onExecute = vi.fn();
      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={() => {}}
          onExecute={onExecute}
        />,
      );
      const input = screen.getByTestId("command-search");
      fireEvent.keyDown(input, { key: "ArrowDown" });
      fireEvent.keyDown(input, { key: "Enter" });
      expect(onExecute).toHaveBeenCalled();
    });

    it("should close on Escape", () => {
      const onClose = vi.fn();
      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={onClose}
          onExecute={() => {}}
        />,
      );
      const input = screen.getByTestId("command-search");
      fireEvent.keyDown(input, { key: "Escape" });
      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("Categories", () => {
    it("should group commands by category", () => {
      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={() => {}}
          onExecute={() => {}}
          groupByCategory
        />,
      );
      expect(screen.getByTestId("category-chat")).toBeInTheDocument();
      expect(screen.getByTestId("category-app")).toBeInTheDocument();
    });
  });

  describe("Shortcuts", () => {
    it("should display command shortcuts", () => {
      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={() => {}}
          onExecute={() => {}}
        />,
      );
      expect(screen.getByText("Cmd+N")).toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("should have dialog role", () => {
      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={() => {}}
          onExecute={() => {}}
        />,
      );
      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should have combobox role on search", () => {
      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={() => {}}
          onExecute={() => {}}
        />,
      );
      expect(screen.getByRole("combobox")).toBeInTheDocument();
    });

    it("should focus search input when opened", () => {
      render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={() => {}}
          onExecute={() => {}}
        />,
      );
      expect(screen.getByTestId("command-search")).toHaveFocus();
    });

    it("should have no accessibility violations when open", async () => {
      const { container } = render(
        <AICommandPalette
          commands={mockCommands}
          isOpen
          onClose={() => {}}
          onExecute={() => {}}
        />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
