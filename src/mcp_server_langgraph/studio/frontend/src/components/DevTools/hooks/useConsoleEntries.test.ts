/**
 * useConsoleEntries Hook Tests
 *
 * TDD tests for the console entries management hook.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useConsoleEntries } from "./useConsoleEntries";
import type { ConsoleEntry } from "../types";

// =============================================================================
// Test Data
// =============================================================================

const mockEntry: ConsoleEntry = {
  id: "entry-1",
  level: "info",
  source: "system",
  message: "Test message",
  timestamp: Date.now(),
};

// =============================================================================
// Tests
// =============================================================================

describe("useConsoleEntries", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("initial state", () => {
    it("should return empty entries initially", () => {
      const { result } = renderHook(() => useConsoleEntries());

      expect(result.current.entries).toEqual([]);
    });

    it("should return isLoading as false initially", () => {
      const { result } = renderHook(() => useConsoleEntries());

      expect(result.current.isLoading).toBe(false);
    });

    it("should return clearConsole function", () => {
      const { result } = renderHook(() => useConsoleEntries());

      expect(typeof result.current.clearConsole).toBe("function");
    });

    it("should return addEntry function", () => {
      const { result } = renderHook(() => useConsoleEntries());

      expect(typeof result.current.addEntry).toBe("function");
    });
  });

  describe("addEntry", () => {
    it("should add entry to entries list", () => {
      const { result } = renderHook(() => useConsoleEntries());

      act(() => {
        result.current.addEntry(mockEntry);
      });

      expect(result.current.entries).toHaveLength(1);
      expect(result.current.entries[0]).toEqual(mockEntry);
    });

    it("should add multiple entries", () => {
      const { result } = renderHook(() => useConsoleEntries());

      act(() => {
        result.current.addEntry({ ...mockEntry, id: "entry-1" });
        result.current.addEntry({ ...mockEntry, id: "entry-2" });
        result.current.addEntry({ ...mockEntry, id: "entry-3" });
      });

      expect(result.current.entries).toHaveLength(3);
    });

    it("should maintain chronological order (newest last)", () => {
      const { result } = renderHook(() => useConsoleEntries());

      act(() => {
        result.current.addEntry({
          ...mockEntry,
          id: "entry-1",
          timestamp: 1000,
        });
        result.current.addEntry({
          ...mockEntry,
          id: "entry-2",
          timestamp: 2000,
        });
      });

      expect(result.current.entries[0].id).toBe("entry-1");
      expect(result.current.entries[1].id).toBe("entry-2");
    });
  });

  describe("clearConsole", () => {
    it("should clear all entries", () => {
      const { result } = renderHook(() => useConsoleEntries());

      act(() => {
        result.current.addEntry({ ...mockEntry, id: "entry-1" });
        result.current.addEntry({ ...mockEntry, id: "entry-2" });
      });

      expect(result.current.entries).toHaveLength(2);

      act(() => {
        result.current.clearConsole();
      });

      expect(result.current.entries).toHaveLength(0);
    });
  });

  describe("filtering by level", () => {
    it("should filter entries by level when filter provided", () => {
      const { result } = renderHook(() =>
        useConsoleEntries({ filter: "error" })
      );

      act(() => {
        result.current.addEntry({ ...mockEntry, id: "entry-1", level: "info" });
        result.current.addEntry({
          ...mockEntry,
          id: "entry-2",
          level: "error",
        });
        result.current.addEntry({
          ...mockEntry,
          id: "entry-3",
          level: "warning",
        });
      });

      // Filtered entries should only include errors
      expect(result.current.filteredEntries).toHaveLength(1);
      expect(result.current.filteredEntries[0].level).toBe("error");
    });

    it("should return all entries when filter is 'all'", () => {
      const { result } = renderHook(() => useConsoleEntries({ filter: "all" }));

      act(() => {
        result.current.addEntry({ ...mockEntry, id: "entry-1", level: "info" });
        result.current.addEntry({
          ...mockEntry,
          id: "entry-2",
          level: "error",
        });
      });

      expect(result.current.filteredEntries).toHaveLength(2);
    });
  });

  describe("filtering by contextEntityId", () => {
    it("should filter entries by contextEntityId when provided", () => {
      const { result } = renderHook(() =>
        useConsoleEntries({ contextEntityId: "session-123" })
      );

      act(() => {
        result.current.addEntry({
          ...mockEntry,
          id: "entry-1",
          data: { sessionId: "session-123" },
        });
        result.current.addEntry({
          ...mockEntry,
          id: "entry-2",
          data: { sessionId: "session-456" },
        });
        result.current.addEntry({
          ...mockEntry,
          id: "entry-3",
          // No session ID - should be included (global)
        });
      });

      // Should include matching session and global entries
      expect(result.current.filteredEntries.length).toBeGreaterThanOrEqual(1);
    });
  });

  describe("max entries limit", () => {
    it("should limit entries to maxEntries", () => {
      const { result } = renderHook(() =>
        useConsoleEntries({ maxEntries: 3 })
      );

      act(() => {
        for (let i = 0; i < 10; i++) {
          result.current.addEntry({ ...mockEntry, id: `entry-${i}` });
        }
      });

      expect(result.current.entries).toHaveLength(3);
    });

    it("should keep newest entries when limit exceeded", () => {
      const { result } = renderHook(() =>
        useConsoleEntries({ maxEntries: 2 })
      );

      act(() => {
        result.current.addEntry({ ...mockEntry, id: "entry-1", timestamp: 1000 });
        result.current.addEntry({ ...mockEntry, id: "entry-2", timestamp: 2000 });
        result.current.addEntry({ ...mockEntry, id: "entry-3", timestamp: 3000 });
      });

      expect(result.current.entries).toHaveLength(2);
      expect(result.current.entries[0].id).toBe("entry-2");
      expect(result.current.entries[1].id).toBe("entry-3");
    });
  });

  describe("entry counts", () => {
    it("should provide counts by level", () => {
      const { result } = renderHook(() => useConsoleEntries());

      act(() => {
        result.current.addEntry({ ...mockEntry, id: "1", level: "info" });
        result.current.addEntry({ ...mockEntry, id: "2", level: "info" });
        result.current.addEntry({ ...mockEntry, id: "3", level: "error" });
        result.current.addEntry({ ...mockEntry, id: "4", level: "warning" });
      });

      expect(result.current.counts.info).toBe(2);
      expect(result.current.counts.error).toBe(1);
      expect(result.current.counts.warning).toBe(1);
      expect(result.current.counts.debug).toBe(0);
      expect(result.current.counts.total).toBe(4);
    });
  });
});
