/**
 * useDevToolsTimeline Filtering Tests
 *
 * Tests for event filtering and correlation:
 * - Event filtering (by type, by time range, visible events)
 * - Event correlation (by timestamp, by correlation ID, by event type)
 * - OTEL distributed traces (spans, hierarchy, statistics)
 * - LangGraph execution traces (node events, state transitions)
 * - Time window and span selection
 *
 * @see useDevToolsTimeline.fixtures.ts for shared utilities
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useDevToolsTimeline } from "../useDevToolsTimeline";
import {
  generateTraceId,
  generateSpanId,
} from "./useDevToolsTimeline.fixtures";

describe("useDevToolsTimeline - Filtering", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  // ===========================================================================
  // EVENT FILTERING
  // ===========================================================================

  describe("event filtering", () => {
    it("should get events at current time", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: { id: 1 },
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 200,
          data: { id: 2 },
        });
        result.current.registerEvent({
          type: "state",
          timestamp: 300,
          data: { id: 3 },
        });
        result.current.setCurrentTime(200);
      });

      const eventsAtTime = result.current.getEventsAtCurrentTime();

      // Should return events up to and including current time
      expect(eventsAtTime).toHaveLength(2);
      expect(eventsAtTime[0].data).toEqual({ id: 1 });
      expect(eventsAtTime[1].data).toEqual({ id: 2 });
    });

    it("should filter events by type", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 200,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 300,
          data: {},
        });
        result.current.registerEvent({
          type: "state",
          timestamp: 400,
          data: {},
        });
      });

      const consoleEvents = result.current.getEventsByType("console");

      expect(consoleEvents).toHaveLength(2);
      expect(consoleEvents.every((e) => e.type === "console")).toBe(true);
    });

    it("should filter events by time range", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: { id: 1 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 200,
          data: { id: 2 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 300,
          data: { id: 3 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 400,
          data: { id: 4 },
        });
      });

      const rangeEvents = result.current.getEventsInRange(150, 350);

      expect(rangeEvents).toHaveLength(2);
      expect(rangeEvents[0].data).toEqual({ id: 2 });
      expect(rangeEvents[1].data).toEqual({ id: 3 });
    });

    it("should get visible events based on current time and filter", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 150,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 200,
          data: {},
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 250,
          data: {},
        });
        result.current.setCurrentTime(200);
        result.current.setTypeFilter(["console"]);
      });

      const visible = result.current.getVisibleEvents();

      expect(visible).toHaveLength(2);
      expect(visible.every((e) => e.type === "console")).toBe(true);
    });
  });

  // ===========================================================================
  // EVENT CORRELATION
  // ===========================================================================

  describe("event correlation", () => {
    it("should find events near a timestamp", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: { id: 1 },
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 105,
          data: { id: 2 },
        });
        result.current.registerEvent({
          type: "state",
          timestamp: 110,
          data: { id: 3 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 500,
          data: { id: 4 },
        });
      });

      const nearEvents = result.current.getEventsNear(105, 20);

      expect(nearEvents).toHaveLength(3);
    });

    it("should find correlated events by ID", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      const correlationId = "request-123";

      act(() => {
        result.current.registerEvent({
          type: "network",
          timestamp: 100,
          data: { correlationId, status: "pending" },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 150,
          data: { correlationId, message: "Processing request" },
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 200,
          data: { correlationId, status: "completed" },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 300,
          data: { message: "Unrelated log" },
        });
      });

      const correlated = result.current.getCorrelatedEvents(correlationId);

      expect(correlated).toHaveLength(3);
    });

    it("should get previous event of same type", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "state",
          timestamp: 100,
          data: { value: 1 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 150,
          data: {},
        });
        result.current.registerEvent({
          type: "state",
          timestamp: 200,
          data: { value: 2 },
        });
        result.current.registerEvent({
          type: "state",
          timestamp: 300,
          data: { value: 3 },
        });
      });

      const event = result.current.events.find((e) => e.timestamp === 300);
      const previous = result.current.getPreviousEventOfType(
        event!.id,
        "state",
      );

      expect(previous?.data).toEqual({ value: 2 });
    });
  });

  // ===========================================================================
  // OTEL DISTRIBUTED TRACES
  // ===========================================================================

  describe("OTEL distributed traces", () => {
    it("should register an OTEL span event", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();
      const spanId = generateSpanId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: {
            traceId,
            spanId,
            operationName: "HTTP GET /api/users",
            serviceName: "mcp-server",
            duration: 150,
            status: "OK",
          },
        });
      });

      expect(result.current.events).toHaveLength(1);
      expect(result.current.events[0].type).toBe("otel_span");
      expect(result.current.events[0].data.traceId).toBe(traceId);
    });

    it("should register nested OTEL spans with parent-child relationship", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();
      const parentSpanId = generateSpanId();
      const childSpanId = generateSpanId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: {
            traceId,
            spanId: parentSpanId,
            operationName: "agent.execute",
            serviceName: "mcp-server",
            duration: 500,
          },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1050,
          data: {
            traceId,
            spanId: childSpanId,
            parentSpanId,
            operationName: "llm.invoke",
            serviceName: "mcp-server",
            duration: 300,
          },
        });
      });

      expect(result.current.events).toHaveLength(2);

      // Verify parent-child relationship
      const childSpan = result.current.events.find(
        (e) => e.data.spanId === childSpanId,
      );
      expect(childSpan?.data.parentSpanId).toBe(parentSpanId);
    });

    it("should get all spans for a distributed trace by traceId", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId1 = generateTraceId();
      const traceId2 = generateTraceId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: {
            traceId: traceId1,
            spanId: generateSpanId(),
            operationName: "op1",
          },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1100,
          data: {
            traceId: traceId1,
            spanId: generateSpanId(),
            operationName: "op2",
          },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1200,
          data: {
            traceId: traceId2,
            spanId: generateSpanId(),
            operationName: "op3",
          },
        });
      });

      const trace1Spans = result.current.getSpansByTraceId(traceId1);

      expect(trace1Spans).toHaveLength(2);
      expect(trace1Spans.every((s) => s.data.traceId === traceId1)).toBe(true);
    });

    it("should get span hierarchy for a trace", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();
      const rootSpanId = generateSpanId();
      const childSpanId1 = generateSpanId();
      const childSpanId2 = generateSpanId();
      const grandchildSpanId = generateSpanId();

      act(() => {
        // Root span
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: { traceId, spanId: rootSpanId, operationName: "root" },
        });
        // Child spans
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1010,
          data: {
            traceId,
            spanId: childSpanId1,
            parentSpanId: rootSpanId,
            operationName: "child1",
          },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1020,
          data: {
            traceId,
            spanId: childSpanId2,
            parentSpanId: rootSpanId,
            operationName: "child2",
          },
        });
        // Grandchild span
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1030,
          data: {
            traceId,
            spanId: grandchildSpanId,
            parentSpanId: childSpanId1,
            operationName: "grandchild",
          },
        });
      });

      const hierarchy = result.current.getSpanHierarchy(traceId);

      expect(hierarchy.root?.data.spanId).toBe(rootSpanId);
      expect(hierarchy.children).toHaveLength(2);
      expect(hierarchy.depth).toBe(3);
    });

    it("should correlate OTEL spans with console logs by traceId", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: { traceId, spanId: generateSpanId(), operationName: "process" },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 1050,
          data: { traceId, message: "Processing request" },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 1100,
          data: { message: "Unrelated log" },
        });
      });

      const correlated = result.current.getEventsByTraceId(traceId);

      expect(correlated).toHaveLength(2);
      expect(correlated.some((e) => e.type === "otel_span")).toBe(true);
      expect(correlated.some((e) => e.type === "console")).toBe(true);
    });

    it("should correlate OTEL spans with network requests", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "HTTP POST",
          },
        });
        result.current.registerEvent({
          type: "network",
          timestamp: 1000,
          data: { traceId, url: "/api/submit", method: "POST" },
        });
      });

      const correlated = result.current.getEventsByTraceId(traceId);

      expect(correlated).toHaveLength(2);
    });

    it("should get span duration statistics", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "op1",
            duration: 100,
          },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1100,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "op2",
            duration: 200,
          },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1300,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "op3",
            duration: 300,
          },
        });
      });

      const stats = result.current.getSpanStats(traceId);

      expect(stats.totalSpans).toBe(3);
      expect(stats.totalDuration).toBe(600);
      expect(stats.averageDuration).toBe(200);
    });

    it("should identify slow spans", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "fast",
            duration: 50,
          },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1050,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "slow",
            duration: 5000,
          },
        });
      });

      const slowSpans = result.current.getSlowSpans(1000); // threshold 1000ms

      expect(slowSpans).toHaveLength(1);
      expect(slowSpans[0].data.operationName).toBe("slow");
    });

    it("should identify error spans", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "success",
            status: "OK",
          },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1100,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "failed",
            status: "ERROR",
            errorMessage: "Connection refused",
          },
        });
      });

      const errorSpans = result.current.getErrorSpans();

      expect(errorSpans).toHaveLength(1);
      expect(errorSpans[0].data.status).toBe("ERROR");
    });
  });

  // ===========================================================================
  // LANGGRAPH EXECUTION TRACE
  // ===========================================================================

  describe("LangGraph execution trace", () => {
    it("should register a LangGraph node execution event", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 1000,
          data: {
            nodeId: "agent",
            nodeName: "Agent",
            nodeType: "agent",
            status: "running",
            input: { query: "Hello" },
          },
        });
      });

      expect(result.current.events).toHaveLength(1);
      expect(result.current.events[0].type).toBe("langgraph_node");
    });

    it("should track LangGraph node state transitions", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const nodeId = "agent-1";

      act(() => {
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 1000,
          data: { nodeId, status: "pending" },
        });
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 1100,
          data: { nodeId, status: "running" },
        });
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 1500,
          data: { nodeId, status: "completed", output: { response: "Hi" } },
        });
      });

      const nodeEvents = result.current.getLangGraphNodeEvents(nodeId);

      expect(nodeEvents).toHaveLength(3);
      expect(nodeEvents[0].data.status).toBe("pending");
      expect(nodeEvents[2].data.status).toBe("completed");
    });

    it("should correlate LangGraph nodes with OTEL spans", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();
      const nodeId = "agent-1";

      act(() => {
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 1000,
          data: { nodeId, traceId, status: "running" },
        });
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 1000,
          data: {
            traceId,
            spanId: generateSpanId(),
            operationName: "langgraph.node.agent",
          },
        });
      });

      const correlated = result.current.getEventsByTraceId(traceId);

      expect(correlated).toHaveLength(2);
      expect(correlated.some((e) => e.type === "langgraph_node")).toBe(true);
      expect(correlated.some((e) => e.type === "otel_span")).toBe(true);
    });

    it("should get LangGraph execution graph at current time", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 100,
          data: { nodeId: "start", status: "completed" },
        });
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 200,
          data: { nodeId: "agent", status: "running" },
        });
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 300,
          data: { nodeId: "agent", status: "completed" },
        });
        result.current.registerEvent({
          type: "langgraph_node",
          timestamp: 400,
          data: { nodeId: "tool", status: "running" },
        });
        result.current.setCurrentTime(250);
      });

      const graphState = result.current.getLangGraphStateAtCurrentTime();

      // At time 250: start=completed, agent=running, tool=not started
      expect(graphState.start).toBe("completed");
      expect(graphState.agent).toBe("running");
      expect(graphState.tool).toBeUndefined();
    });
  });

  // ===========================================================================
  // TIME WINDOW AND SPAN SELECTION
  // ===========================================================================

  describe("time window and span selection", () => {
    it("should set and get time window selection", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 500,
          data: {},
        });
      });

      act(() => {
        result.current.setTimeWindow(150, 400);
      });

      expect(result.current.timeWindow).toEqual({ start: 150, end: 400 });
    });

    it("should filter events within time window", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: { id: 1 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 200,
          data: { id: 2 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 300,
          data: { id: 3 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 400,
          data: { id: 4 },
        });
      });

      act(() => {
        result.current.setTimeWindow(150, 350);
      });

      const windowedEvents = result.current.getEventsInWindow();

      expect(windowedEvents).toHaveLength(2);
      expect(windowedEvents[0].data).toEqual({ id: 2 });
      expect(windowedEvents[1].data).toEqual({ id: 3 });
    });

    it("should clear time window selection", () => {
      const { result } = renderHook(() => useDevToolsTimeline());

      act(() => {
        result.current.registerEvent({
          type: "console",
          timestamp: 100,
          data: {},
        });
        result.current.setTimeWindow(100, 200);
      });

      act(() => {
        result.current.clearTimeWindow();
      });

      expect(result.current.timeWindow).toBeNull();
    });

    it("should select a span for filtering", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();
      const spanId = generateSpanId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 100,
          data: { traceId, spanId, operationName: "root", duration: 500 },
        });
      });

      act(() => {
        result.current.selectSpan(spanId);
      });

      expect(result.current.selectedSpanId).toBe(spanId);
    });

    it("should filter events that occurred during selected span", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const traceId = generateTraceId();
      const spanId = generateSpanId();

      act(() => {
        // Span runs from 100 to 600 (duration 500ms)
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 100,
          data: { traceId, spanId, operationName: "root", duration: 500 },
        });
        // Events during the span
        result.current.registerEvent({
          type: "console",
          timestamp: 150,
          data: { message: "During span 1" },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 400,
          data: { message: "During span 2" },
        });
        // Event after the span
        result.current.registerEvent({
          type: "console",
          timestamp: 700,
          data: { message: "After span" },
        });
      });

      act(() => {
        result.current.selectSpan(spanId);
      });

      const spanEvents = result.current.getEventsInSelectedSpan();

      expect(spanEvents).toHaveLength(2);
      expect(spanEvents[0].data.message).toBe("During span 1");
      expect(spanEvents[1].data.message).toBe("During span 2");
    });

    it("should clear span selection", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const spanId = generateSpanId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 100,
          data: { spanId, duration: 100 },
        });
        result.current.selectSpan(spanId);
      });

      act(() => {
        result.current.clearSpanSelection();
      });

      expect(result.current.selectedSpanId).toBeNull();
    });

    it("should get active filters summary", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const spanId = generateSpanId();

      act(() => {
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 100,
          data: { spanId, duration: 100 },
        });
      });

      act(() => {
        result.current.setTimeWindow(50, 250);
        result.current.selectSpan(spanId);
        result.current.setTypeFilter(["console", "network"]);
      });

      const filters = result.current.getActiveFilters();

      expect(filters.hasTimeWindow).toBe(true);
      expect(filters.hasSpanSelection).toBe(true);
      expect(filters.hasTypeFilter).toBe(true);
      expect(filters.typeFilter).toEqual(["console", "network"]);
    });

    it("should combine time window and span selection", () => {
      const { result } = renderHook(() => useDevToolsTimeline());
      const spanId = generateSpanId();

      act(() => {
        // Span from 100-600
        result.current.registerEvent({
          type: "otel_span",
          timestamp: 100,
          data: { spanId, duration: 500 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 150,
          data: { id: 1 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 300,
          data: { id: 2 },
        });
        result.current.registerEvent({
          type: "console",
          timestamp: 500,
          data: { id: 3 },
        });
      });

      act(() => {
        result.current.selectSpan(spanId);
        // Further constrain to 200-400
        result.current.setTimeWindow(200, 400);
      });

      // Should only include console event at 300 (within span AND within time window)
      const filtered = result.current.getFilteredEvents();

      // The span itself is at 100, so excluded. Console at 300 is within both.
      expect(filtered.filter((e) => e.type === "console")).toHaveLength(1);
      expect(filtered.find((e) => e.type === "console")?.data).toEqual({
        id: 2,
      });
    });
  });
});
