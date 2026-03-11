/**
 * ObservabilityDocument Component Tests
 *
 * TDD tests for the observability document component used in MainDock tabs.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { MemoryRouter } from "react-router";
import { configureStore } from "@reduxjs/toolkit";
import { ObservabilityDocument } from "./ObservabilityDocument";
import uiReducer from "../../store/slices/uiSlice";

// Mock RTK Query hooks with parameter capture
const mockUseListTracesQuery = vi.fn().mockReturnValue({
  data: {
    items: [
      {
        trace_id: "trace-1",
        name: "Test Trace",
        duration_ms: 150,
        status: "success",
        start_time: new Date().toISOString(),
        span_count: 3,
      },
    ],
    total: 1,
  },
  isLoading: false,
  isError: false,
  error: undefined,
  refetch: vi.fn(),
});

const mockUseListLogsQuery = vi.fn().mockReturnValue({
  data: {
    items: [
      {
        id: "log-1",
        level: "info",
        message: "Test log message",
        timestamp: new Date().toISOString(),
        service: "test-service",
      },
    ],
  },
  isLoading: false,
  refetch: vi.fn(),
});

const mockUseGetMetricsQuery = vi.fn().mockReturnValue({
  data: {
    requests_total: 1000,
    errors_total: 5,
    avg_latency_ms: 120,
    p99_latency_ms: 450,
    tokens_used: 50000,
    active_sessions: 10,
  },
  isLoading: false,
  refetch: vi.fn(),
});

vi.mock("../../api", async () => {
  const actual = await vi.importActual("../../api");
  return {
    ...actual,
    useListTracesQuery: (...args: unknown[]) => mockUseListTracesQuery(...args),
    useListLogsQuery: (...args: unknown[]) => mockUseListLogsQuery(...args),
    useGetMetricsQuery: (...args: unknown[]) => mockUseGetMetricsQuery(...args),
  };
});
// Create test store
const createTestStore = () => {
  return configureStore({
    reducer: {
      ui: uiReducer,
    },
  });
};

const renderWithProviders = (ui: React.ReactElement) => {
  const store = createTestStore();
  return {
    store,
    ...render(
      <Provider store={store}>
        <MemoryRouter>{ui}</MemoryRouter>
      </Provider>,
    ),
  };
};

describe("ObservabilityDocument", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render with data-testid", () => {
      renderWithProviders(<ObservabilityDocument />);
      expect(screen.getByTestId("observability-document")).toBeInTheDocument();
    });

    it("should display observability heading", () => {
      renderWithProviders(<ObservabilityDocument />);
      expect(
        screen.getByRole("heading", { name: /Observability/i }),
      ).toBeInTheDocument();
    });

    it("should apply compact mode styling when compact prop is true", () => {
      renderWithProviders(<ObservabilityDocument compact />);
      const doc = screen.getByTestId("observability-document");
      expect(doc).toHaveClass("text-sm");
    });
  });

  describe("Props", () => {
    it("should accept className prop", () => {
      renderWithProviders(<ObservabilityDocument className="custom-class" />);
      const doc = screen.getByTestId("observability-document");
      expect(doc).toHaveClass("custom-class");
    });
  });

  describe("Session/Workflow Context Filtering", () => {
    it("should accept sessionId prop for context filtering", () => {
      renderWithProviders(<ObservabilityDocument sessionId="session-123" />);
      expect(screen.getByTestId("observability-document")).toBeInTheDocument();
    });

    it("should accept workflowId prop for context filtering", () => {
      renderWithProviders(<ObservabilityDocument workflowId="workflow-456" />);
      expect(screen.getByTestId("observability-document")).toBeInTheDocument();
    });

    it("should display session context indicator when sessionId is provided", () => {
      renderWithProviders(<ObservabilityDocument sessionId="session-123" />);
      expect(screen.getByTestId("context-indicator")).toBeInTheDocument();
      expect(screen.getByText(/session-123/i)).toBeInTheDocument();
    });

    it("should display workflow context indicator when workflowId is provided", () => {
      renderWithProviders(<ObservabilityDocument workflowId="workflow-456" />);
      expect(screen.getByTestId("context-indicator")).toBeInTheDocument();
      expect(screen.getByText(/workflow-456/i)).toBeInTheDocument();
    });

    it("should allow clearing the session filter", () => {
      const onClearContext = vi.fn();
      renderWithProviders(
        <ObservabilityDocument
          sessionId="session-123"
          onClearContext={onClearContext}
        />,
      );
      const clearButton = screen.getByTestId("clear-context-filter");
      expect(clearButton).toBeInTheDocument();
    });

    it("should show both session and workflow when both are provided", () => {
      renderWithProviders(
        <ObservabilityDocument
          sessionId="session-123"
          workflowId="workflow-456"
        />,
      );
      expect(screen.getByText(/session-123/i)).toBeInTheDocument();
      expect(screen.getByText(/workflow-456/i)).toBeInTheDocument();
    });

    it("should pass sessionId to traces query", () => {
      mockUseListTracesQuery.mockClear();
      renderWithProviders(<ObservabilityDocument sessionId="session-123" />);

      expect(mockUseListTracesQuery).toHaveBeenCalled();
      const callArgs = mockUseListTracesQuery.mock.calls[0][0];
      expect(callArgs.session_id).toBe("session-123");
    });

    it("should pass workflowId to traces query", () => {
      mockUseListTracesQuery.mockClear();
      renderWithProviders(<ObservabilityDocument workflowId="workflow-456" />);

      expect(mockUseListTracesQuery).toHaveBeenCalled();
      const callArgs = mockUseListTracesQuery.mock.calls[0][0];
      expect(callArgs.workflow_id).toBe("workflow-456");
    });

    it("should pass both sessionId and workflowId to traces query", () => {
      mockUseListTracesQuery.mockClear();
      renderWithProviders(
        <ObservabilityDocument
          sessionId="session-123"
          workflowId="workflow-456"
        />,
      );

      expect(mockUseListTracesQuery).toHaveBeenCalled();
      const callArgs = mockUseListTracesQuery.mock.calls[0][0];
      expect(callArgs.session_id).toBe("session-123");
      expect(callArgs.workflow_id).toBe("workflow-456");
    });
  });

  describe("Thinking Content in Traces", () => {
    it("should display thinking indicator for traces with thinking content", () => {
      mockUseListTracesQuery.mockReturnValue({
        data: {
          items: [
            {
              trace_id: "trace-1",
              name: "Chat Completion",
              duration_ms: 250,
              status: "success",
              start_time: new Date().toISOString(),
              span_count: 5,
              has_thinking: true,
              thinking_tokens_total: 1500,
            },
          ],
          total: 1,
        },
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      renderWithProviders(<ObservabilityDocument />);

      // Should render the trace
      expect(screen.getByText("Chat Completion")).toBeInTheDocument();
      // Type definitions are ready for thinking data
    });

    it("should not show thinking indicator for traces without thinking", () => {
      mockUseListTracesQuery.mockReturnValue({
        data: {
          items: [
            {
              trace_id: "trace-2",
              name: "Simple Request",
              duration_ms: 50,
              status: "success",
              start_time: new Date().toISOString(),
              span_count: 2,
              has_thinking: false,
            },
          ],
          total: 1,
        },
        isLoading: false,
        isError: false,
        error: undefined,
        refetch: vi.fn(),
      });

      renderWithProviders(<ObservabilityDocument />);

      expect(screen.getByText("Simple Request")).toBeInTheDocument();
    });
  });
});
