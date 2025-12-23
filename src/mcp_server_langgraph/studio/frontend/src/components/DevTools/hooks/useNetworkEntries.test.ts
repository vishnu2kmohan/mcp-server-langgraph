/**
 * useNetworkEntries Hook Tests
 *
 * TDD tests for the network entries management hook.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useNetworkEntries } from "./useNetworkEntries";
import type { NetworkEntry } from "../types";

// =============================================================================
// Test Data
// =============================================================================

const createMockEntry = (
  overrides: Partial<NetworkEntry> = {},
): NetworkEntry => ({
  id: `entry-${Date.now()}-${Math.random()}`,
  method: "GET",
  url: "/api/v1/test",
  status: "completed",
  statusCode: 200,
  statusText: "OK",
  startTime: Date.now(),
  endTime: Date.now() + 100,
  duration: 100,
  ...overrides,
});

// =============================================================================
// Tests
// =============================================================================

describe("useNetworkEntries", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("initial state", () => {
    it("should return empty entries initially", () => {
      const { result } = renderHook(() => useNetworkEntries());

      expect(result.current.entries).toEqual([]);
    });

    it("should have recording enabled by default", () => {
      const { result } = renderHook(() => useNetworkEntries());

      expect(result.current.isRecording).toBe(true);
    });

    it("should return toggleRecording function", () => {
      const { result } = renderHook(() => useNetworkEntries());

      expect(typeof result.current.toggleRecording).toBe("function");
    });

    it("should return clearEntries function", () => {
      const { result } = renderHook(() => useNetworkEntries());

      expect(typeof result.current.clearEntries).toBe("function");
    });

    it("should return addEntry function", () => {
      const { result } = renderHook(() => useNetworkEntries());

      expect(typeof result.current.addEntry).toBe("function");
    });

    it("should return updateEntry function", () => {
      const { result } = renderHook(() => useNetworkEntries());

      expect(typeof result.current.updateEntry).toBe("function");
    });
  });

  describe("addEntry", () => {
    it("should add entry to entries list", () => {
      const { result } = renderHook(() => useNetworkEntries());
      const entry = createMockEntry({ id: "entry-1" });

      act(() => {
        result.current.addEntry(entry);
      });

      expect(result.current.entries).toHaveLength(1);
      expect(result.current.entries[0]).toEqual(entry);
    });

    it("should add multiple entries", () => {
      const { result } = renderHook(() => useNetworkEntries());

      act(() => {
        result.current.addEntry(createMockEntry({ id: "entry-1" }));
        result.current.addEntry(createMockEntry({ id: "entry-2" }));
        result.current.addEntry(createMockEntry({ id: "entry-3" }));
      });

      expect(result.current.entries).toHaveLength(3);
    });

    it("should not add entry when recording is disabled", () => {
      const { result } = renderHook(() => useNetworkEntries());

      act(() => {
        result.current.toggleRecording(); // Disable recording
      });

      act(() => {
        result.current.addEntry(createMockEntry({ id: "entry-1" }));
      });

      expect(result.current.entries).toHaveLength(0);
    });

    it("should maintain chronological order (newest last)", () => {
      const { result } = renderHook(() => useNetworkEntries());

      act(() => {
        result.current.addEntry(
          createMockEntry({ id: "entry-1", startTime: 1000 }),
        );
        result.current.addEntry(
          createMockEntry({ id: "entry-2", startTime: 2000 }),
        );
      });

      expect(result.current.entries[0].id).toBe("entry-1");
      expect(result.current.entries[1].id).toBe("entry-2");
    });
  });

  describe("updateEntry", () => {
    it("should update an existing entry", () => {
      const { result } = renderHook(() => useNetworkEntries());
      const entry = createMockEntry({ id: "entry-1", status: "pending" });

      act(() => {
        result.current.addEntry(entry);
      });

      act(() => {
        result.current.updateEntry("entry-1", {
          status: "completed",
          statusCode: 200,
          duration: 150,
        });
      });

      expect(result.current.entries[0].status).toBe("completed");
      expect(result.current.entries[0].statusCode).toBe(200);
      expect(result.current.entries[0].duration).toBe(150);
    });

    it("should not affect other entries when updating", () => {
      const { result } = renderHook(() => useNetworkEntries());

      act(() => {
        result.current.addEntry(
          createMockEntry({ id: "entry-1", status: "pending" }),
        );
        result.current.addEntry(
          createMockEntry({ id: "entry-2", status: "pending" }),
        );
      });

      act(() => {
        result.current.updateEntry("entry-1", { status: "completed" });
      });

      expect(result.current.entries[0].status).toBe("completed");
      expect(result.current.entries[1].status).toBe("pending");
    });

    it("should do nothing if entry ID not found", () => {
      const { result } = renderHook(() => useNetworkEntries());
      const entry = createMockEntry({ id: "entry-1" });

      act(() => {
        result.current.addEntry(entry);
      });

      act(() => {
        result.current.updateEntry("non-existent", { status: "error" });
      });

      expect(result.current.entries).toHaveLength(1);
      expect(result.current.entries[0].status).toBe("completed");
    });

    it("should work even when recording is disabled", () => {
      const { result } = renderHook(() => useNetworkEntries());

      act(() => {
        result.current.addEntry(
          createMockEntry({ id: "entry-1", status: "pending" }),
        );
      });

      act(() => {
        result.current.toggleRecording(); // Disable recording
      });

      act(() => {
        result.current.updateEntry("entry-1", { status: "completed" });
      });

      expect(result.current.entries[0].status).toBe("completed");
    });
  });

  describe("toggleRecording", () => {
    it("should toggle recording state", () => {
      const { result } = renderHook(() => useNetworkEntries());

      expect(result.current.isRecording).toBe(true);

      act(() => {
        result.current.toggleRecording();
      });

      expect(result.current.isRecording).toBe(false);

      act(() => {
        result.current.toggleRecording();
      });

      expect(result.current.isRecording).toBe(true);
    });
  });

  describe("clearEntries", () => {
    it("should clear all entries", () => {
      const { result } = renderHook(() => useNetworkEntries());

      act(() => {
        result.current.addEntry(createMockEntry({ id: "entry-1" }));
        result.current.addEntry(createMockEntry({ id: "entry-2" }));
      });

      expect(result.current.entries).toHaveLength(2);

      act(() => {
        result.current.clearEntries();
      });

      expect(result.current.entries).toHaveLength(0);
    });

    it("should work when entries are empty", () => {
      const { result } = renderHook(() => useNetworkEntries());

      act(() => {
        result.current.clearEntries();
      });

      expect(result.current.entries).toHaveLength(0);
    });
  });

  describe("maxEntries limit", () => {
    it("should use default maxEntries of 500", () => {
      const { result } = renderHook(() => useNetworkEntries());

      act(() => {
        for (let i = 0; i < 600; i++) {
          result.current.addEntry(createMockEntry({ id: `entry-${i}` }));
        }
      });

      expect(result.current.entries).toHaveLength(500);
    });

    it("should respect custom maxEntries option", () => {
      const { result } = renderHook(() =>
        useNetworkEntries({ maxEntries: 10 }),
      );

      act(() => {
        for (let i = 0; i < 20; i++) {
          result.current.addEntry(createMockEntry({ id: `entry-${i}` }));
        }
      });

      expect(result.current.entries).toHaveLength(10);
    });

    it("should keep newest entries when limit exceeded", () => {
      const { result } = renderHook(() => useNetworkEntries({ maxEntries: 3 }));

      act(() => {
        result.current.addEntry(createMockEntry({ id: "entry-1" }));
        result.current.addEntry(createMockEntry({ id: "entry-2" }));
        result.current.addEntry(createMockEntry({ id: "entry-3" }));
        result.current.addEntry(createMockEntry({ id: "entry-4" }));
        result.current.addEntry(createMockEntry({ id: "entry-5" }));
      });

      expect(result.current.entries).toHaveLength(3);
      expect(result.current.entries[0].id).toBe("entry-3");
      expect(result.current.entries[1].id).toBe("entry-4");
      expect(result.current.entries[2].id).toBe("entry-5");
    });
  });

  describe("entry types", () => {
    it("should handle GET requests", () => {
      const { result } = renderHook(() => useNetworkEntries());

      act(() => {
        result.current.addEntry(
          createMockEntry({
            id: "get-1",
            method: "GET",
            url: "/api/v1/users",
          }),
        );
      });

      expect(result.current.entries[0].method).toBe("GET");
    });

    it("should handle POST requests with body", () => {
      const { result } = renderHook(() => useNetworkEntries());

      act(() => {
        result.current.addEntry(
          createMockEntry({
            id: "post-1",
            method: "POST",
            url: "/api/v1/users",
            requestBody: { name: "Test User" },
          }),
        );
      });

      expect(result.current.entries[0].method).toBe("POST");
      expect(result.current.entries[0].requestBody).toEqual({
        name: "Test User",
      });
    });

    it("should handle error responses", () => {
      const { result } = renderHook(() => useNetworkEntries());

      act(() => {
        result.current.addEntry(
          createMockEntry({
            id: "error-1",
            status: "error",
            statusCode: 500,
            statusText: "Internal Server Error",
          }),
        );
      });

      expect(result.current.entries[0].status).toBe("error");
      expect(result.current.entries[0].statusCode).toBe(500);
    });

    it("should handle pending requests", () => {
      const { result } = renderHook(() => useNetworkEntries());

      act(() => {
        result.current.addEntry(
          createMockEntry({
            id: "pending-1",
            status: "pending",
            statusCode: undefined,
            endTime: undefined,
            duration: undefined,
          }),
        );
      });

      expect(result.current.entries[0].status).toBe("pending");
      expect(result.current.entries[0].endTime).toBeUndefined();
    });

    it("should handle MCP tool calls with source", () => {
      const { result } = renderHook(() => useNetworkEntries());

      act(() => {
        result.current.addEntry(
          createMockEntry({
            id: "mcp-1",
            method: "POST",
            url: "/mcp/tools/search",
            source: "mcp-server-search",
          }),
        );
      });

      expect(result.current.entries[0].source).toBe("mcp-server-search");
    });
  });

  describe("callback stability", () => {
    it("should have stable addEntry reference", () => {
      const { result, rerender } = renderHook(() => useNetworkEntries());

      const firstAddEntry = result.current.addEntry;

      rerender();

      // Callbacks should remain stable
      expect(result.current.addEntry).toBe(firstAddEntry);
    });

    it("should have stable toggleRecording reference", () => {
      const { result, rerender } = renderHook(() => useNetworkEntries());

      const firstToggle = result.current.toggleRecording;

      rerender();

      expect(result.current.toggleRecording).toBe(firstToggle);
    });

    it("should have stable clearEntries reference", () => {
      const { result, rerender } = renderHook(() => useNetworkEntries());

      const firstClear = result.current.clearEntries;

      rerender();

      expect(result.current.clearEntries).toBe(firstClear);
    });

    it("should have stable updateEntry reference", () => {
      const { result, rerender } = renderHook(() => useNetworkEntries());

      const firstUpdate = result.current.updateEntry;

      rerender();

      expect(result.current.updateEntry).toBe(firstUpdate);
    });
  });
});
