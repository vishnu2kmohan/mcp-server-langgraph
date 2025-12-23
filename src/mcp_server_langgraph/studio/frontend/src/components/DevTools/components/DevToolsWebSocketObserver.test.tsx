/**
 * DevToolsWebSocketObserver Tests
 *
 * TDD tests for the WebSocket observer component that bridges
 * WebSocket events to the unified timeline.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, waitFor, cleanup } from "@testing-library/react";

import { DevToolsWebSocketObserver } from "./DevToolsWebSocketObserver";

// =============================================================================
// Mocks
// =============================================================================

// Mock the timeline context
const mockRegisterEvent = vi.fn();
vi.mock("../context/DevToolsTimelineProvider", () => ({
  useTimelineContext: () => ({
    registerEvent: mockRegisterEvent,
    events: [],
    currentTime: 0,
    timeWindow: null,
  }),
}));

// Mock the WebSocket bridge
const mockHandleTraceSpan = vi.fn();
const mockHandleAlert = vi.fn();
const mockHandleLangGraphNode = vi.fn();
vi.mock("../hooks/useDevToolsWebSocketBridge", () => ({
  useDevToolsWebSocketBridge: () => ({
    handleTraceSpan: mockHandleTraceSpan,
    handleAlert: mockHandleAlert,
    handleMetric: vi.fn(),
    handleLog: vi.fn(),
    handleLangGraphNode: mockHandleLangGraphNode,
  }),
}));

// Mock trace WebSocket with controllable spans state
let mockSpans: Array<{
  traceId: string;
  spanId: string;
  name: string;
  startTime: string;
  status: string;
  attributes: Record<string, unknown>;
}> = [];
const mockTraceConnect = vi.fn();
vi.mock("../../../hooks/useTraceWebSocket", () => ({
  useTraceWebSocket: () => ({
    spans: mockSpans,
    events: [],
    isConnected: true,
    connect: mockTraceConnect,
    disconnect: vi.fn(),
    clearTraces: vi.fn(),
  }),
}));

// Mock alert slice selector
let mockAlerts: Array<{
  alert_id: string;
  name: string;
  state: string;
  severity: string;
  service: string;
  message: string;
  started_at: string;
}> = [];
vi.mock("../../../store/hooks", () => ({
  useAppSelector: (selector: unknown) => {
    // Return mock alerts when selector is for alerts
    if (typeof selector === "function") {
      return mockAlerts;
    }
    return [];
  },
}));
vi.mock("../../../store/slices/alertSlice", () => ({
  selectAlerts: (_state: unknown) => mockAlerts,
}));

// =============================================================================
// Tests
// =============================================================================

describe("DevToolsWebSocketObserver", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSpans = [];
    mockAlerts = [];
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("rendering", () => {
    it("should render without crashing", () => {
      const { container } = render(<DevToolsWebSocketObserver />);
      // Should render nothing (observer component)
      expect(container.firstChild).toBeNull();
    });

    it("should render children if provided", () => {
      const { getByText } = render(
        <DevToolsWebSocketObserver>
          <div>Child content</div>
        </DevToolsWebSocketObserver>,
      );
      expect(getByText("Child content")).toBeInTheDocument();
    });
  });

  describe("trace span observation", () => {
    it("should call handleTraceSpan when new spans appear", async () => {
      render(<DevToolsWebSocketObserver />);

      // Simulate new span appearing
      mockSpans = [
        {
          traceId: "trace-1",
          spanId: "span-1",
          name: "api.request",
          startTime: "2024-01-01T12:00:00Z",
          status: "OK",
          attributes: {},
        },
      ];

      // Re-render to trigger effect
      const { rerender } = render(<DevToolsWebSocketObserver />);
      rerender(<DevToolsWebSocketObserver />);

      await waitFor(() => {
        expect(mockHandleTraceSpan).toHaveBeenCalled();
      });
    });

    it("should not call handleTraceSpan for already processed spans", async () => {
      mockSpans = [
        {
          traceId: "trace-1",
          spanId: "span-1",
          name: "api.request",
          startTime: "2024-01-01T12:00:00Z",
          status: "OK",
          attributes: {},
        },
      ];

      const { rerender } = render(<DevToolsWebSocketObserver />);

      // First render should process the span
      await waitFor(() => {
        expect(mockHandleTraceSpan).toHaveBeenCalledTimes(1);
      });

      // Re-render with same spans
      mockHandleTraceSpan.mockClear();
      rerender(<DevToolsWebSocketObserver />);

      // Should not call again for same span
      expect(mockHandleTraceSpan).not.toHaveBeenCalled();
    });
  });

  describe("alert observation", () => {
    it("should call handleAlert when new alerts appear in Redux", async () => {
      render(<DevToolsWebSocketObserver />);

      // Simulate new alert in Redux
      mockAlerts = [
        {
          alert_id: "alert-1",
          name: "HighErrorRate",
          state: "firing",
          severity: "critical",
          service: "api",
          message: "Error rate exceeded threshold",
          started_at: "2024-01-01T12:00:00Z",
        },
      ];

      const { rerender } = render(<DevToolsWebSocketObserver />);
      rerender(<DevToolsWebSocketObserver />);

      await waitFor(() => {
        expect(mockHandleAlert).toHaveBeenCalled();
      });
    });
  });

  describe("disabled state", () => {
    it("should not process events when disabled", () => {
      mockSpans = [
        {
          traceId: "trace-1",
          spanId: "span-1",
          name: "api.request",
          startTime: "2024-01-01T12:00:00Z",
          status: "OK",
          attributes: {},
        },
      ];

      render(<DevToolsWebSocketObserver enabled={false} />);

      expect(mockHandleTraceSpan).not.toHaveBeenCalled();
    });
  });
});
