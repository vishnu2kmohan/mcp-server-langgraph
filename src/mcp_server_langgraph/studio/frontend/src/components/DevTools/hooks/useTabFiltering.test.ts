/**
 * useTabFiltering Hook Tests
 *
 * TDD: Tests written FIRST, then implementation.
 * Tests filter logic, debouncing, timeline integration, and multi-filter support.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useTabFiltering } from "./useTabFiltering";
import type { TimeWindow } from "./useDevToolsTimeline";

// =============================================================================
// Test Data Types
// =============================================================================

interface TestLogEntry {
  id: string;
  timestamp: string;
  level: "debug" | "info" | "warning" | "error";
  service: string;
  message: string;
  traceId?: string;
}

// =============================================================================
// Mock Data
// =============================================================================

const mockLogs: TestLogEntry[] = [
  {
    id: "log-1",
    timestamp: "2026-01-15T10:00:00Z",
    level: "info",
    service: "api-gateway",
    message: "Request received from user@example.com",
    traceId: "trace-abc",
  },
  {
    id: "log-2",
    timestamp: "2026-01-15T10:00:05Z",
    level: "debug",
    service: "auth-service",
    message: "Token validation started",
    traceId: "trace-abc",
  },
  {
    id: "log-3",
    timestamp: "2026-01-15T10:00:10Z",
    level: "error",
    service: "database",
    message: "Connection timeout to postgres:5432",
    traceId: "trace-def",
  },
  {
    id: "log-4",
    timestamp: "2026-01-15T10:00:15Z",
    level: "warning",
    service: "api-gateway",
    message: "Slow response detected",
  },
  {
    id: "log-5",
    timestamp: "2026-01-15T10:00:20Z",
    level: "info",
    service: "cache",
    message: "Cache miss for key user:123",
    traceId: "trace-ghi",
  },
];

// =============================================================================
// Mock Timeline Context
// =============================================================================

interface MockTimelineOptions {
  timeWindow?: TimeWindow | null;
  currentTime?: number;
  isLiveMode?: boolean;
}

function createMockTimeline(options: MockTimelineOptions = {}) {
  const { timeWindow = null, currentTime = Date.now(), isLiveMode = true } = options;

  return {
    timeWindow,
    currentTime,
    isLiveMode,
    getEventsInWindow: vi.fn(() => []),
    getFilteredEvents: vi.fn(() => []),
    setTimeWindow: vi.fn(),
    clearTimeWindow: vi.fn(),
  };
}

// =============================================================================
// Basic Functionality Tests
// =============================================================================

describe("useTabFiltering", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe("initialization", () => {
    it("should return all data when no filters are applied", () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
        }),
      );

      expect(result.current.filteredData).toHaveLength(mockLogs.length);
      expect(result.current.filteredData).toEqual(mockLogs);
    });

    it("should initialize with empty search term", () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
        }),
      );

      expect(result.current.searchTerm).toBe("");
      expect(result.current.debouncedSearchTerm).toBe("");
    });

    it("should initialize with empty filters", () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
        }),
      );

      expect(result.current.filters).toEqual({});
      expect(result.current.hasActiveFilters).toBe(false);
    });
  });

  // ===========================================================================
  // Search Tests
  // ===========================================================================

  describe("search filtering", () => {
    it("should filter data by search term in default fields", async () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
          searchFields: ["message", "service"],
        }),
      );

      act(() => {
        result.current.setSearchTerm("api-gateway");
      });

      // Advance timers and flush all pending effects
      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.debouncedSearchTerm).toBe("api-gateway");
      expect(result.current.filteredData).toHaveLength(2);
      expect(result.current.filteredData.every((log) => log.service === "api-gateway")).toBe(true);
    });

    it("should be case-insensitive when searching", async () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
          searchFields: ["message"],
        }),
      );

      act(() => {
        result.current.setSearchTerm("TOKEN VALIDATION");
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.filteredData).toHaveLength(1);
      expect(result.current.filteredData[0].id).toBe("log-2");
    });

    it("should search across multiple fields", async () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
          searchFields: ["message", "service", "traceId"],
        }),
      );

      act(() => {
        result.current.setSearchTerm("trace-abc");
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.filteredData).toHaveLength(2);
      expect(result.current.filteredData.every((log) => log.traceId === "trace-abc")).toBe(true);
    });

    it("should debounce search input", async () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
          searchFields: ["message"],
          debounceMs: 150,
        }),
      );

      act(() => {
        result.current.setSearchTerm("api");
      });

      // Before debounce completes
      expect(result.current.searchTerm).toBe("api");
      expect(result.current.debouncedSearchTerm).toBe("");
      expect(result.current.filteredData).toHaveLength(mockLogs.length);

      // After debounce
      await act(async () => {
        await vi.advanceTimersByTimeAsync(150);
      });

      expect(result.current.debouncedSearchTerm).toBe("api");
    });

    it("should respect custom debounce delay", async () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
          searchFields: ["message"],
          debounceMs: 300,
        }),
      );

      act(() => {
        result.current.setSearchTerm("error");
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      // Should still not be debounced (only 200ms of 300ms)
      expect(result.current.debouncedSearchTerm).toBe("");

      await act(async () => {
        await vi.advanceTimersByTimeAsync(150);
      });

      expect(result.current.debouncedSearchTerm).toBe("error");
    });

    it("should return empty array when no matches found", async () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
          searchFields: ["message"],
        }),
      );

      act(() => {
        result.current.setSearchTerm("nonexistent");
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.filteredData).toHaveLength(0);
    });
  });

  // ===========================================================================
  // Filter Tests
  // ===========================================================================

  describe("multi-filter support", () => {
    it("should filter by single key-value pair", () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
        }),
      );

      act(() => {
        result.current.setFilter("level", "error");
      });

      expect(result.current.filters).toEqual({ level: "error" });
      expect(result.current.filteredData).toHaveLength(1);
      expect(result.current.filteredData[0].level).toBe("error");
      expect(result.current.hasActiveFilters).toBe(true);
    });

    it("should filter by multiple key-value pairs (AND logic)", () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
        }),
      );

      act(() => {
        result.current.setFilter("level", "info");
        result.current.setFilter("service", "api-gateway");
      });

      expect(result.current.filters).toEqual({ level: "info", service: "api-gateway" });
      expect(result.current.filteredData).toHaveLength(1);
      expect(result.current.filteredData[0].id).toBe("log-1");
    });

    it("should remove a filter by setting empty value", () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
        }),
      );

      act(() => {
        result.current.setFilter("level", "error");
      });

      expect(result.current.filteredData).toHaveLength(1);

      act(() => {
        result.current.setFilter("level", "");
      });

      expect(result.current.filters).toEqual({});
      expect(result.current.filteredData).toHaveLength(mockLogs.length);
    });

    it("should clear all filters at once", () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
        }),
      );

      act(() => {
        result.current.setFilter("level", "info");
        result.current.setFilter("service", "api-gateway");
      });

      expect(result.current.hasActiveFilters).toBe(true);

      act(() => {
        result.current.clearFilters();
      });

      expect(result.current.filters).toEqual({});
      expect(result.current.hasActiveFilters).toBe(false);
      expect(result.current.filteredData).toHaveLength(mockLogs.length);
    });
  });

  // ===========================================================================
  // Combined Search and Filter Tests
  // ===========================================================================

  describe("combined search and filter", () => {
    it("should apply both search and filters (AND logic)", async () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
          searchFields: ["message"],
        }),
      );

      act(() => {
        result.current.setFilter("service", "api-gateway");
        result.current.setSearchTerm("request");
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.filteredData).toHaveLength(1);
      expect(result.current.filteredData[0].id).toBe("log-1");
    });

    it("should report hasActiveFilters when search is set", async () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
          searchFields: ["message"],
        }),
      );

      expect(result.current.hasActiveFilters).toBe(false);

      act(() => {
        result.current.setSearchTerm("api");
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.hasActiveFilters).toBe(true);
    });
  });

  // ===========================================================================
  // Timeline Integration Tests
  // ===========================================================================

  describe("timeline integration", () => {
    it("should filter by timeline time window when provided", () => {
      const startTime = new Date("2026-01-15T10:00:00Z").getTime();
      const endTime = new Date("2026-01-15T10:00:10Z").getTime();

      const mockTimeline = createMockTimeline({
        timeWindow: { start: startTime, end: endTime },
      });

      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: mockTimeline as unknown as null, // Type workaround for test
          timestampKey: "timestamp",
        }),
      );

      // Should only include logs within the time window
      const filteredIds = result.current.filteredData.map((l) => l.id);
      expect(filteredIds).toContain("log-1");
      expect(filteredIds).toContain("log-2");
      expect(filteredIds).toContain("log-3");
      expect(filteredIds).not.toContain("log-4");
      expect(filteredIds).not.toContain("log-5");
    });

    it("should use custom timestamp key when specified", () => {
      interface CustomTimestampEntry {
        id: string;
        createdAt: string;
        value: number;
      }

      const customData: CustomTimestampEntry[] = [
        { id: "1", createdAt: "2026-01-15T10:00:00Z", value: 100 },
        { id: "2", createdAt: "2026-01-15T10:00:30Z", value: 200 },
      ];

      const startTime = new Date("2026-01-15T10:00:00Z").getTime();
      const endTime = new Date("2026-01-15T10:00:15Z").getTime();

      const mockTimeline = createMockTimeline({
        timeWindow: { start: startTime, end: endTime },
      });

      const { result } = renderHook(() =>
        useTabFiltering({
          data: customData,
          timeline: mockTimeline as unknown as null,
          timestampKey: "createdAt",
        }),
      );

      expect(result.current.filteredData).toHaveLength(1);
      expect(result.current.filteredData[0].id).toBe("1");
    });

    it("should ignore timeline filter when timeline is null", () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
          timestampKey: "timestamp",
        }),
      );

      expect(result.current.filteredData).toHaveLength(mockLogs.length);
    });
  });

  // ===========================================================================
  // Performance Tests
  // ===========================================================================

  describe("performance", () => {
    it("should memoize filtered results when inputs don't change", () => {
      const { result, rerender } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
        }),
      );

      const firstResult = result.current.filteredData;

      rerender();

      expect(result.current.filteredData).toBe(firstResult);
    });

    it("should update filtered results when data changes", () => {
      const { result, rerender } = renderHook(
        ({ data }) =>
          useTabFiltering({
            data,
            timeline: null,
          }),
        { initialProps: { data: mockLogs } },
      );

      const firstResult = result.current.filteredData;
      const newLogs = [...mockLogs, { ...mockLogs[0], id: "log-new" }];

      rerender({ data: newLogs });

      expect(result.current.filteredData).not.toBe(firstResult);
      expect(result.current.filteredData).toHaveLength(newLogs.length);
    });

    it("should handle large datasets efficiently", () => {
      // Generate 10,000 entries
      const largeDataset = Array.from({ length: 10000 }, (_, i) => ({
        id: `log-${i}`,
        timestamp: new Date(Date.now() + i * 1000).toISOString(),
        level: (["debug", "info", "warning", "error"] as const)[i % 4],
        service: `service-${i % 10}`,
        message: `Log message ${i}`,
      }));

      const startTime = performance.now();

      const { result } = renderHook(() =>
        useTabFiltering({
          data: largeDataset,
          timeline: null,
          searchFields: ["message", "service"],
        }),
      );

      const initTime = performance.now() - startTime;

      // Initial render should be fast (< 100ms)
      expect(initTime).toBeLessThan(100);

      // Apply search
      const searchStartTime = performance.now();

      act(() => {
        result.current.setFilter("level", "error");
      });

      const filterTime = performance.now() - searchStartTime;

      // Filter should be fast (< 50ms)
      expect(filterTime).toBeLessThan(50);
      expect(result.current.filteredData).toHaveLength(2500); // 1/4 of 10,000
    });
  });

  // ===========================================================================
  // Edge Cases
  // ===========================================================================

  describe("edge cases", () => {
    it("should handle empty data array", () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: [],
          timeline: null,
        }),
      );

      expect(result.current.filteredData).toEqual([]);
      expect(result.current.hasActiveFilters).toBe(false);
    });

    it("should handle undefined searchFields by searching all string fields", async () => {
      const { result } = renderHook(() =>
        useTabFiltering({
          data: mockLogs,
          timeline: null,
          // No searchFields specified
        }),
      );

      act(() => {
        result.current.setSearchTerm("api-gateway");
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      // Should still find matches in string fields
      expect(result.current.filteredData.length).toBeGreaterThan(0);
    });

    it("should handle null/undefined values in data gracefully", async () => {
      const dataWithNulls = [
        ...mockLogs,
        {
          id: "log-null",
          timestamp: "2026-01-15T10:00:25Z",
          level: "info" as const,
          service: "test",
          message: undefined as unknown as string,
        },
      ];

      const { result } = renderHook(() =>
        useTabFiltering({
          data: dataWithNulls,
          timeline: null,
          searchFields: ["message"],
        }),
      );

      act(() => {
        result.current.setSearchTerm("request");
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      // Should not throw, should filter correctly
      expect(result.current.filteredData).toHaveLength(1);
    });

    it("should handle special regex characters in search term", async () => {
      const dataWithSpecialChars = [
        {
          id: "log-special",
          timestamp: "2026-01-15T10:00:00Z",
          level: "info" as const,
          service: "test",
          message: "Error: [object Object] at line 42",
        },
      ];

      const { result } = renderHook(() =>
        useTabFiltering({
          data: dataWithSpecialChars,
          timeline: null,
          searchFields: ["message"],
        }),
      );

      act(() => {
        result.current.setSearchTerm("[object Object]");
      });

      await act(async () => {
        await vi.advanceTimersByTimeAsync(200);
      });

      expect(result.current.filteredData).toHaveLength(1);
    });
  });
});
