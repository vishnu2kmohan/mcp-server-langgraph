/**
 * useTraceToReactFlow Hook Tests
 *
 * TDD tests for converting trace spans to React Flow nodes and edges.
 * Tests cover:
 * - Node generation
 * - Edge generation
 * - Layout calculation
 * - Status colors
 * - Duration formatting
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, cleanup } from "@testing-library/react";
import { useTraceToReactFlow } from "./useTraceToReactFlow";
import type { TraceSpan } from "./useTraceWebSocket";

describe("useTraceToReactFlow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });
  describe("Empty State", () => {
    it("should return empty arrays for empty spans", () => {
      const { result } = renderHook(() => useTraceToReactFlow({ spans: [] }));

      expect(result.current.nodes).toEqual([]);
      expect(result.current.edges).toEqual([]);
    });
  });

  describe("Node Generation", () => {
    it("should create a node for each span", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "span-1",
          name: "First Span",
          startTime: "2024-01-15T10:00:00Z",
          status: "OK",
          attributes: {},
        },
        {
          traceId: "trace-1",
          spanId: "span-2",
          name: "Second Span",
          startTime: "2024-01-15T10:00:01Z",
          status: "OK",
          attributes: {},
        },
      ];

      const { result } = renderHook(() => useTraceToReactFlow({ spans }));

      expect(result.current.nodes).toHaveLength(2);
    });

    it("should use span ID as node ID", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "unique-span-id",
          name: "Test Span",
          startTime: "2024-01-15T10:00:00Z",
          status: "OK",
          attributes: {},
        },
      ];

      const { result } = renderHook(() => useTraceToReactFlow({ spans }));

      expect(result.current.nodes[0].id).toBe("unique-span-id");
    });

    it("should set node type to traceNode", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "span-1",
          name: "Test Span",
          startTime: "2024-01-15T10:00:00Z",
          status: "OK",
          attributes: {},
        },
      ];

      const { result } = renderHook(() => useTraceToReactFlow({ spans }));

      expect(result.current.nodes[0].type).toBe("traceNode");
    });

    it("should include span name in node data", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "span-1",
          name: "My Span Name",
          startTime: "2024-01-15T10:00:00Z",
          status: "OK",
          attributes: {},
        },
      ];

      const { result } = renderHook(() => useTraceToReactFlow({ spans }));

      expect(result.current.nodes[0].data.label).toBe("My Span Name");
    });

    it("should include status in node data", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "span-1",
          name: "Test",
          startTime: "2024-01-15T10:00:00Z",
          status: "ERROR",
          attributes: {},
        },
      ];

      const { result } = renderHook(() => useTraceToReactFlow({ spans }));

      expect(result.current.nodes[0].data.status).toBe("ERROR");
    });
  });

  describe("Status Colors", () => {
    it("should set green color for OK status", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "span-1",
          name: "Test",
          startTime: "2024-01-15T10:00:00Z",
          status: "OK",
          attributes: {},
        },
      ];

      const { result } = renderHook(() => useTraceToReactFlow({ spans }));

      expect(result.current.nodes[0].data.statusColor).toBe("#22c55e");
    });

    it("should set red color for ERROR status", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "span-1",
          name: "Test",
          startTime: "2024-01-15T10:00:00Z",
          status: "ERROR",
          attributes: {},
        },
      ];

      const { result } = renderHook(() => useTraceToReactFlow({ spans }));

      expect(result.current.nodes[0].data.statusColor).toBe("#ef4444");
    });

    it("should set indigo color for UNSET status", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "span-1",
          name: "Test",
          startTime: "2024-01-15T10:00:00Z",
          status: "UNSET",
          attributes: {},
        },
      ];

      const { result } = renderHook(() => useTraceToReactFlow({ spans }));

      expect(result.current.nodes[0].data.statusColor).toBe("#6366f1");
    });
  });

  describe("Duration Formatting", () => {
    it("should format duration in milliseconds for short spans", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "span-1",
          name: "Test",
          startTime: "2024-01-15T10:00:00.000Z",
          endTime: "2024-01-15T10:00:00.500Z",
          status: "OK",
          attributes: {},
        },
      ];

      const { result } = renderHook(() => useTraceToReactFlow({ spans }));

      expect(result.current.nodes[0].data.duration).toBe("500ms");
    });

    it("should format duration in seconds for long spans", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "span-1",
          name: "Test",
          startTime: "2024-01-15T10:00:00.000Z",
          endTime: "2024-01-15T10:00:02.500Z",
          status: "OK",
          attributes: {},
        },
      ];

      const { result } = renderHook(() => useTraceToReactFlow({ spans }));

      expect(result.current.nodes[0].data.duration).toBe("2.50s");
    });

    it("should have empty duration when endTime is not set", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "span-1",
          name: "Test",
          startTime: "2024-01-15T10:00:00.000Z",
          status: "UNSET",
          attributes: {},
        },
      ];

      const { result } = renderHook(() => useTraceToReactFlow({ spans }));

      expect(result.current.nodes[0].data.duration).toBe("");
    });
  });

  describe("Edge Generation", () => {
    it("should create edges for parent-child relationships", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "parent",
          name: "Parent",
          startTime: "2024-01-15T10:00:00Z",
          status: "OK",
          attributes: {},
        },
        {
          traceId: "trace-1",
          spanId: "child",
          parentSpanId: "parent",
          name: "Child",
          startTime: "2024-01-15T10:00:01Z",
          status: "OK",
          attributes: {},
        },
      ];

      const { result } = renderHook(() => useTraceToReactFlow({ spans }));

      expect(result.current.edges).toHaveLength(1);
      expect(result.current.edges[0].source).toBe("parent");
      expect(result.current.edges[0].target).toBe("child");
    });

    it("should not create edges for root spans", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "root-1",
          name: "Root 1",
          startTime: "2024-01-15T10:00:00Z",
          status: "OK",
          attributes: {},
        },
        {
          traceId: "trace-2",
          spanId: "root-2",
          name: "Root 2",
          startTime: "2024-01-15T10:00:01Z",
          status: "OK",
          attributes: {},
        },
      ];

      const { result } = renderHook(() => useTraceToReactFlow({ spans }));

      expect(result.current.edges).toHaveLength(0);
    });

    it("should animate edges for running spans", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "parent",
          name: "Parent",
          startTime: "2024-01-15T10:00:00Z",
          status: "UNSET",
          attributes: {},
        },
        {
          traceId: "trace-1",
          spanId: "child",
          parentSpanId: "parent",
          name: "Child",
          startTime: "2024-01-15T10:00:01Z",
          status: "UNSET",
          attributes: {},
        },
      ];

      const { result } = renderHook(() => useTraceToReactFlow({ spans }));

      expect(result.current.edges[0].animated).toBe(true);
    });

    it("should use red stroke for ERROR spans", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "parent",
          name: "Parent",
          startTime: "2024-01-15T10:00:00Z",
          status: "OK",
          attributes: {},
        },
        {
          traceId: "trace-1",
          spanId: "child",
          parentSpanId: "parent",
          name: "Child",
          startTime: "2024-01-15T10:00:01Z",
          status: "ERROR",
          attributes: {},
        },
      ];

      const { result } = renderHook(() => useTraceToReactFlow({ spans }));

      expect(result.current.edges[0].style?.stroke).toBe("#ef4444");
    });
  });

  describe("Layout", () => {
    it("should use horizontal layout by default", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "span-1",
          name: "Test",
          startTime: "2024-01-15T10:00:00Z",
          status: "OK",
          attributes: {},
        },
        {
          traceId: "trace-1",
          spanId: "span-2",
          parentSpanId: "span-1",
          name: "Test 2",
          startTime: "2024-01-15T10:00:01Z",
          status: "OK",
          attributes: {},
        },
      ];

      const { result } = renderHook(() =>
        useTraceToReactFlow({ spans, layout: "horizontal" }),
      );

      // In horizontal layout, child should be to the right (higher x)
      const parentNode = result.current.nodes.find((n) => n.id === "span-1");
      const childNode = result.current.nodes.find((n) => n.id === "span-2");

      expect(childNode!.position.x).toBeGreaterThan(parentNode!.position.x);
    });

    it("should support vertical layout", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "span-1",
          name: "Test",
          startTime: "2024-01-15T10:00:00Z",
          status: "OK",
          attributes: {},
        },
        {
          traceId: "trace-1",
          spanId: "span-2",
          parentSpanId: "span-1",
          name: "Test 2",
          startTime: "2024-01-15T10:00:01Z",
          status: "OK",
          attributes: {},
        },
      ];

      const { result } = renderHook(() =>
        useTraceToReactFlow({ spans, layout: "vertical" }),
      );

      // In vertical layout, child should be below (higher y)
      const parentNode = result.current.nodes.find((n) => n.id === "span-1");
      const childNode = result.current.nodes.find((n) => n.id === "span-2");

      expect(childNode!.position.y).toBeGreaterThan(parentNode!.position.y);
    });

    it("should respect custom node spacing", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "span-1",
          name: "Test",
          startTime: "2024-01-15T10:00:00Z",
          status: "OK",
          attributes: {},
        },
        {
          traceId: "trace-1",
          spanId: "span-2",
          parentSpanId: "span-1",
          name: "Test 2",
          startTime: "2024-01-15T10:00:01Z",
          status: "OK",
          attributes: {},
        },
      ];

      const customSpacing = 200;
      const { result } = renderHook(() =>
        useTraceToReactFlow({ spans, nodeSpacing: customSpacing }),
      );

      const parentNode = result.current.nodes.find((n) => n.id === "span-1");
      const childNode = result.current.nodes.find((n) => n.id === "span-2");

      // The spacing between nodes should include the custom spacing
      const xDiff = Math.abs(childNode!.position.x - parentNode!.position.x);
      expect(xDiff).toBeGreaterThanOrEqual(customSpacing);
    });
  });

  describe("Complex Hierarchies", () => {
    it("should handle multi-level hierarchies", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "root",
          name: "Root",
          startTime: "2024-01-15T10:00:00Z",
          status: "OK",
          attributes: {},
        },
        {
          traceId: "trace-1",
          spanId: "level-1",
          parentSpanId: "root",
          name: "Level 1",
          startTime: "2024-01-15T10:00:01Z",
          status: "OK",
          attributes: {},
        },
        {
          traceId: "trace-1",
          spanId: "level-2",
          parentSpanId: "level-1",
          name: "Level 2",
          startTime: "2024-01-15T10:00:02Z",
          status: "OK",
          attributes: {},
        },
      ];

      const { result } = renderHook(() => useTraceToReactFlow({ spans }));

      expect(result.current.nodes).toHaveLength(3);
      expect(result.current.edges).toHaveLength(2);
    });

    it("should handle sibling spans", () => {
      const spans: TraceSpan[] = [
        {
          traceId: "trace-1",
          spanId: "parent",
          name: "Parent",
          startTime: "2024-01-15T10:00:00Z",
          status: "OK",
          attributes: {},
        },
        {
          traceId: "trace-1",
          spanId: "sibling-1",
          parentSpanId: "parent",
          name: "Sibling 1",
          startTime: "2024-01-15T10:00:01Z",
          status: "OK",
          attributes: {},
        },
        {
          traceId: "trace-1",
          spanId: "sibling-2",
          parentSpanId: "parent",
          name: "Sibling 2",
          startTime: "2024-01-15T10:00:01Z",
          status: "OK",
          attributes: {},
        },
      ];

      const { result } = renderHook(() => useTraceToReactFlow({ spans }));

      expect(result.current.nodes).toHaveLength(3);
      expect(result.current.edges).toHaveLength(2);

      // Both edges should have the parent as source
      result.current.edges.forEach((edge) => {
        expect(edge.source).toBe("parent");
      });
    });
  });
});
