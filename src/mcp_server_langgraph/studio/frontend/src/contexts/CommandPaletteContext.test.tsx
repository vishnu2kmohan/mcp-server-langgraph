/**
 * CommandPaletteContext Tests
 *
 * Tests for the command palette context that provides
 * dynamic command registration and deduplication.
 *
 * Sprint 4: CommandPalette Enhancement
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, act, cleanup } from "@testing-library/react";
import { ReactNode } from "react";
import {
  CommandPaletteProvider,
  useCommandPalette,
} from "./CommandPaletteContext";
import type { Command } from "../ai/AICommandPalette";

// ==============================================================================
// Test Setup
// ==============================================================================

const STATIC_COMMANDS: Command[] = [
  {
    id: "new-chat",
    name: "New Chat",
    description: "Start a new conversation",
    category: "chat",
    shortcut: "⌘N",
  },
  {
    id: "toggle-sidebar",
    name: "Toggle Sidebar",
    description: "Show or hide the sidebar",
    category: "layout",
  },
];

function TestConsumer({
  onRender,
}: {
  onRender?: (commands: Command[]) => void;
}) {
  const { commands, registerCommands, unregisterCommands } =
    useCommandPalette();

  // Call onRender callback for assertions
  onRender?.(commands);

  return (
    <div data-testid="consumer">
      <span data-testid="command-count">{commands.length}</span>
      <button
        data-testid="register-btn"
        onClick={() =>
          registerCommands([
            {
              id: "route-new-workflow",
              name: "New Workflow",
              description: "Create a new workflow",
              category: "Workflow",
            },
          ])
        }
      >
        Register
      </button>
      <button
        data-testid="unregister-btn"
        onClick={() => unregisterCommands(["route-new-workflow"])}
      >
        Unregister
      </button>
      <button
        data-testid="override-btn"
        onClick={() =>
          registerCommands([
            {
              id: "new-chat",
              name: "New Chat (Modified)",
              description: "Modified description",
              category: "chat",
            },
          ])
        }
      >
        Override
      </button>
    </div>
  );
}

function TestWrapper({
  children,
  staticCommands = STATIC_COMMANDS,
}: {
  children: ReactNode;
  staticCommands?: Command[];
}) {
  return (
    <CommandPaletteProvider staticCommands={staticCommands}>
      {children}
    </CommandPaletteProvider>
  );
}

// ==============================================================================
// Tests
// ==============================================================================

describe("CommandPaletteContext", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("initialization", () => {
    it("should provide static commands on initial render", () => {
      let capturedCommands: Command[] = [];

      render(
        <TestWrapper>
          <TestConsumer onRender={(cmds) => (capturedCommands = cmds)} />
        </TestWrapper>,
      );

      expect(capturedCommands).toHaveLength(2);
      expect(capturedCommands.map((c) => c.id)).toContain("new-chat");
      expect(capturedCommands.map((c) => c.id)).toContain("toggle-sidebar");
    });

    it("should throw error when useCommandPalette is used outside provider", () => {
      const consoleError = vi
        .spyOn(console, "error")
        .mockImplementation(() => {});

      expect(() => {
        render(<TestConsumer />);
      }).toThrow(
        "useCommandPalette must be used within CommandPaletteProvider",
      );

      consoleError.mockRestore();
    });
  });

  describe("registerCommands", () => {
    it("should add new commands to the list", async () => {
      let capturedCommands: Command[] = [];

      render(
        <TestWrapper>
          <TestConsumer onRender={(cmds) => (capturedCommands = cmds)} />
        </TestWrapper>,
      );

      expect(capturedCommands).toHaveLength(2);

      const registerBtn = screen.getByTestId("register-btn");
      await act(async () => {
        registerBtn.click();
      });

      // Re-render should show updated count
      expect(screen.getByTestId("command-count").textContent).toBe("3");
    });

    it("should dedupe by id with dynamic overriding static", async () => {
      let capturedCommands: Command[] = [];

      render(
        <TestWrapper>
          <TestConsumer onRender={(cmds) => (capturedCommands = cmds)} />
        </TestWrapper>,
      );

      expect(capturedCommands).toHaveLength(2);
      const originalNewChat = capturedCommands.find((c) => c.id === "new-chat");
      expect(originalNewChat?.name).toBe("New Chat");

      const overrideBtn = screen.getByTestId("override-btn");
      await act(async () => {
        overrideBtn.click();
      });

      // Still 2 commands (override, not add)
      expect(screen.getByTestId("command-count").textContent).toBe("2");
    });
  });

  describe("unregisterCommands", () => {
    it("should remove commands by id", async () => {
      render(
        <TestWrapper>
          <TestConsumer />
        </TestWrapper>,
      );

      // First register
      const registerBtn = screen.getByTestId("register-btn");
      await act(async () => {
        registerBtn.click();
      });
      expect(screen.getByTestId("command-count").textContent).toBe("3");

      // Then unregister
      const unregisterBtn = screen.getByTestId("unregister-btn");
      await act(async () => {
        unregisterBtn.click();
      });
      expect(screen.getByTestId("command-count").textContent).toBe("2");
    });

    it("should not affect static commands when unregistering dynamic", async () => {
      let capturedCommands: Command[] = [];

      render(
        <TestWrapper>
          <TestConsumer onRender={(cmds) => (capturedCommands = cmds)} />
        </TestWrapper>,
      );

      // Register and then unregister
      const registerBtn = screen.getByTestId("register-btn");
      const unregisterBtn = screen.getByTestId("unregister-btn");

      await act(async () => {
        registerBtn.click();
      });
      await act(async () => {
        unregisterBtn.click();
      });

      // Original static commands should still be present
      expect(capturedCommands.map((c) => c.id)).toContain("new-chat");
      expect(capturedCommands.map((c) => c.id)).toContain("toggle-sidebar");
    });
  });

  describe("concurrent operations", () => {
    it("should handle multiple register calls correctly", async () => {
      const RegisterMultiple = () => {
        const { registerCommands, commands } = useCommandPalette();

        return (
          <div>
            <span data-testid="count">{commands.length}</span>
            <button
              data-testid="register-many"
              onClick={() => {
                registerCommands([
                  {
                    id: "cmd-1",
                    name: "Cmd 1",
                    description: "Desc 1",
                    category: "test",
                  },
                  {
                    id: "cmd-2",
                    name: "Cmd 2",
                    description: "Desc 2",
                    category: "test",
                  },
                ]);
              }}
            >
              Register Many
            </button>
          </div>
        );
      };

      render(
        <TestWrapper>
          <RegisterMultiple />
        </TestWrapper>,
      );

      expect(screen.getByTestId("count").textContent).toBe("2");

      const btn = screen.getByTestId("register-many");
      await act(async () => {
        btn.click();
      });

      expect(screen.getByTestId("count").textContent).toBe("4");
    });
  });
});
