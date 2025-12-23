/**
 * useCommandPalette Tests
 *
 * TDD tests for the Command Palette hook.
 * Tests cover:
 * - Command registration
 * - Fuzzy search
 * - Recent commands
 * - Command execution
 * - Category filtering
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act, cleanup } from "@testing-library/react";
import { useCommandPalette, Command } from "./useCommandPalette";

describe("useCommandPalette", () => {
  const mockCommands: Command[] = [
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
    {
      id: "export-chat",
      label: "Export Conversation",
      category: "Session",
      action: vi.fn(),
    },
    {
      id: "clear-history",
      label: "Clear Chat History",
      category: "Session",
      action: vi.fn(),
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
    // Clear localStorage
    localStorage.clear();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  // ===========================================================================
  // Open/Close State Tests
  // ===========================================================================

  describe("open/close state", () => {
    it("should start closed", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      expect(result.current.isOpen).toBe(false);
    });

    it("should open the palette", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      act(() => {
        result.current.open();
      });

      expect(result.current.isOpen).toBe(true);
    });

    it("should close the palette", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      act(() => {
        result.current.open();
      });

      act(() => {
        result.current.close();
      });

      expect(result.current.isOpen).toBe(false);
    });

    it("should toggle the palette", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      act(() => {
        result.current.toggle();
      });
      expect(result.current.isOpen).toBe(true);

      act(() => {
        result.current.toggle();
      });
      expect(result.current.isOpen).toBe(false);
    });
  });

  // ===========================================================================
  // Search Tests
  // ===========================================================================

  describe("search", () => {
    it("should return all commands when query is empty", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      expect(result.current.filteredCommands).toHaveLength(mockCommands.length);
    });

    it("should filter commands by search query", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      act(() => {
        result.current.setQuery("session");
      });

      expect(result.current.filteredCommands.length).toBeGreaterThan(0);
      result.current.filteredCommands.forEach((cmd) => {
        expect(
          cmd.label.toLowerCase().includes("session") ||
            cmd.category.toLowerCase().includes("session"),
        ).toBe(true);
      });
    });

    it("should perform fuzzy search", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      act(() => {
        result.current.setQuery("newsess");
      });

      expect(
        result.current.filteredCommands.some((c) => c.id === "new-session"),
      ).toBe(true);
    });

    it("should be case insensitive", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      act(() => {
        result.current.setQuery("SETTINGS");
      });

      expect(
        result.current.filteredCommands.some((c) => c.id === "open-settings"),
      ).toBe(true);
    });

    it("should clear query", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      act(() => {
        result.current.setQuery("test");
      });

      act(() => {
        result.current.clearQuery();
      });

      expect(result.current.query).toBe("");
    });
  });

  // ===========================================================================
  // Command Execution Tests
  // ===========================================================================

  describe("command execution", () => {
    it("should execute a command", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      act(() => {
        result.current.executeCommand("new-session");
      });

      expect(mockCommands[0].action).toHaveBeenCalled();
    });

    it("should close palette after executing command", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      act(() => {
        result.current.open();
      });

      act(() => {
        result.current.executeCommand("new-session");
      });

      expect(result.current.isOpen).toBe(false);
    });

    it("should add executed command to recent list", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      act(() => {
        result.current.executeCommand("open-settings");
      });

      expect(result.current.recentCommands).toContain("open-settings");
    });
  });

  // ===========================================================================
  // Recent Commands Tests
  // ===========================================================================

  describe("recent commands", () => {
    it("should maintain order of recent commands", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      act(() => {
        result.current.executeCommand("new-session");
      });
      act(() => {
        result.current.executeCommand("open-settings");
      });
      act(() => {
        result.current.executeCommand("toggle-theme");
      });

      expect(result.current.recentCommands[0]).toBe("toggle-theme");
      expect(result.current.recentCommands[1]).toBe("open-settings");
      expect(result.current.recentCommands[2]).toBe("new-session");
    });

    it("should limit recent commands to 5", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      for (let i = 0; i < 10; i++) {
        act(() => {
          result.current.executeCommand(
            mockCommands[i % mockCommands.length].id,
          );
        });
      }

      expect(result.current.recentCommands.length).toBeLessThanOrEqual(5);
    });

    it("should not duplicate commands in recent list", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      act(() => {
        result.current.executeCommand("new-session");
      });
      act(() => {
        result.current.executeCommand("new-session");
      });

      const newSessionCount = result.current.recentCommands.filter(
        (id) => id === "new-session",
      ).length;
      expect(newSessionCount).toBe(1);
    });
  });

  // ===========================================================================
  // Category Tests
  // ===========================================================================

  describe("categories", () => {
    it("should return grouped commands by category", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      const categories = result.current.commandsByCategory;

      expect(categories["Session"]).toBeDefined();
      expect(categories["Application"]).toBeDefined();
      expect(categories["Session"].length).toBe(3);
      expect(categories["Application"].length).toBe(2);
    });
  });

  // ===========================================================================
  // Selection Tests
  // ===========================================================================

  describe("selection", () => {
    it("should track selected index", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      expect(result.current.selectedIndex).toBe(0);
    });

    it("should move selection down", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      act(() => {
        result.current.selectNext();
      });

      expect(result.current.selectedIndex).toBe(1);
    });

    it("should move selection up", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      act(() => {
        result.current.selectNext();
        result.current.selectNext();
      });

      act(() => {
        result.current.selectPrevious();
      });

      expect(result.current.selectedIndex).toBe(1);
    });

    it("should wrap selection at bottom", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      for (let i = 0; i < mockCommands.length; i++) {
        act(() => {
          result.current.selectNext();
        });
      }

      expect(result.current.selectedIndex).toBe(0);
    });

    it("should wrap selection at top", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      act(() => {
        result.current.selectPrevious();
      });

      expect(result.current.selectedIndex).toBe(mockCommands.length - 1);
    });

    it("should reset selection when query changes", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      act(() => {
        result.current.selectNext();
        result.current.selectNext();
      });

      act(() => {
        result.current.setQuery("test");
      });

      expect(result.current.selectedIndex).toBe(0);
    });

    it("should execute selected command", () => {
      const { result } = renderHook(() => useCommandPalette(mockCommands));

      act(() => {
        result.current.selectNext();
      });

      act(() => {
        result.current.executeSelected();
      });

      expect(mockCommands[1].action).toHaveBeenCalled();
    });
  });
});
