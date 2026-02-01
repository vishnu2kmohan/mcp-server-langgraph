/**
 * useWorkflowExecution Hook Tests
 *
 * TDD tests for the workflow execution data fetching hook.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";

import {
  useWorkflowExecution,
  type ExecutionStep,
} from "./useWorkflowExecution";

// =============================================================================
// Test Data
// =============================================================================

/**
 * Create a mock step in FRONTEND format (camelCase).
 * Used for expected values after transformation.
 */
const createMockStep = (
  overrides: Partial<ExecutionStep> = {},
): ExecutionStep => ({
  id: `step-${Date.now()}-${Math.random()}`,
  nodeId: "node-1",
  nodeName: "Process Data",
  status: "completed",
  duration: 1000,
  startTime: Date.now() - 1000,
  endTime: Date.now(),
  ...overrides,
});

/**
 * Create a mock step in API format (snake_case).
 * This matches what the backend actually returns.
 */
const createMockApiStep = (overrides: Record<string, unknown> = {}) => ({
  id: `step-${Date.now()}-${Math.random()}`,
  node_id: "node-1",
  node_name: "Process Data",
  status: "completed",
  duration: 1000,
  start_time: Date.now() - 1000,
  end_time: Date.now(),
  ...overrides,
});

/**
 * Mock API response in snake_case format (matches backend WorkflowExecutionResponse).
 * This ensures tests verify the transformation from API to frontend format.
 */
const mockApiResponse = {
  steps: [
    createMockApiStep({ id: "step-1", node_id: "node-1", node_name: "Start" }),
    createMockApiStep({
      id: "step-2",
      node_id: "node-2",
      node_name: "Process",
    }),
    createMockApiStep({ id: "step-3", node_id: "node-3", node_name: "End" }),
  ],
  current_step_id: "step-2",
};

// Legacy mock for backward compatibility with some tests
const mockExecutionResponse = {
  steps: [
    createMockStep({ id: "step-1", nodeId: "node-1", nodeName: "Start" }),
    createMockStep({ id: "step-2", nodeId: "node-2", nodeName: "Process" }),
    createMockStep({ id: "step-3", nodeId: "node-3", nodeName: "End" }),
  ],
  currentStepId: "step-2",
};

// =============================================================================
// Mocks
// =============================================================================

const mockFetch = vi.fn();

// =============================================================================
// Tests
// =============================================================================

describe("useWorkflowExecution", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetch;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("initial state", () => {
    it("should return empty steps initially", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockExecutionResponse),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      // Initially empty before fetch completes
      expect(result.current.steps).toEqual([]);
    });

    it("should set isLoading to true during fetch", async () => {
      mockFetch.mockImplementation(
        () =>
          new Promise((resolve) =>
            setTimeout(
              () =>
                resolve({
                  ok: true,
                  json: () => Promise.resolve(mockExecutionResponse),
                }),
              100,
            ),
          ),
      );

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      // Should be loading initially
      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });
    });

    it("should return null error initially", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockExecutionResponse),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      expect(result.current.error).toBeNull();
    });

    it("should return null currentStepId initially", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockExecutionResponse),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      expect(result.current.currentStepId).toBeNull();
    });

    it("should return refetch function", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockExecutionResponse),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      expect(typeof result.current.refetch).toBe("function");
    });
  });

  describe("successful fetch", () => {
    it("should fetch execution on mount", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockExecutionResponse),
      });

      renderHook(() => useWorkflowExecution({ workflowId: "workflow-123" }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/workflows/workflow-123/execution",
          expect.anything(),
        );
      });
    });

    it("should set steps after successful fetch", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockExecutionResponse),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.steps).toHaveLength(3);
      });
    });

    it("should set currentStepId after successful fetch", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockExecutionResponse),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.currentStepId).toBe("step-2");
      });
    });

    it("should set isLoading to false after fetch completes", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockExecutionResponse),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
        expect(result.current.steps).toHaveLength(3);
      });
    });

    it("should handle response without currentStepId", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ steps: mockExecutionResponse.steps }),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.currentStepId).toBeNull();
      });
    });

    it("should handle response without steps", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({}),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.steps).toEqual([]);
      });
    });
  });

  describe("failed fetch", () => {
    it("should set error on non-ok response", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        statusText: "Not Found",
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-404" }),
      );

      await waitFor(() => {
        expect(result.current.error).not.toBeNull();
        expect(result.current.error?.message).toContain("Not Found");
      });
    });

    it("should set steps to empty array on error", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        statusText: "Internal Server Error",
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-500" }),
      );

      await waitFor(() => {
        expect(result.current.steps).toEqual([]);
        expect(result.current.error).not.toBeNull();
      });
    });

    it("should set currentStepId to null on error", async () => {
      mockFetch.mockResolvedValue({
        ok: false,
        statusText: "Internal Server Error",
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-500" }),
      );

      await waitFor(() => {
        expect(result.current.currentStepId).toBeNull();
        expect(result.current.error).not.toBeNull();
      });
    });

    it("should handle network errors", async () => {
      mockFetch.mockRejectedValue(new Error("Network error"));

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.error?.message).toBe("Network error");
      });
    });

    it("should handle non-Error thrown values", async () => {
      mockFetch.mockRejectedValue("String error");

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.error?.message).toBe("Unknown error");
      });
    });
  });

  describe("refetch", () => {
    it("should refetch execution when refetch is called", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockExecutionResponse),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.steps).toHaveLength(3);
      });

      expect(mockFetch).toHaveBeenCalledTimes(1);

      act(() => {
        result.current.refetch();
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(2);
      });
    });
  });

  describe("workflowId changes", () => {
    it("should refetch when workflowId changes", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockExecutionResponse),
      });

      const { result, rerender } = renderHook(
        ({ workflowId }) => useWorkflowExecution({ workflowId }),
        { initialProps: { workflowId: "workflow-123" } },
      );

      await waitFor(() => {
        expect(result.current.steps).toHaveLength(3);
      });

      rerender({ workflowId: "workflow-456" });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/workflows/workflow-456/execution",
          expect.anything(),
        );
      });
    });

    it("should not fetch if workflowId is empty", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockExecutionResponse),
      });

      renderHook(() => useWorkflowExecution({ workflowId: "" }));

      // Give time for potential fetch
      await new Promise((r) => setTimeout(r, 50));

      expect(mockFetch).not.toHaveBeenCalled();
    });
  });

  describe("auto-refresh", () => {
    beforeEach(() => {
      vi.useFakeTimers();
    });

    afterEach(() => {
      vi.useRealTimers();
    });

    it("should not auto-refresh by default", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockExecutionResponse),
      });

      renderHook(() => useWorkflowExecution({ workflowId: "workflow-123" }));

      // Flush initial fetch
      await vi.advanceTimersByTimeAsync(0);

      // Only initial fetch
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Advance time - should not cause more fetches without autoRefresh
      await vi.advanceTimersByTimeAsync(10000);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it("should auto-refresh when enabled", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockExecutionResponse),
      });

      renderHook(() =>
        useWorkflowExecution({
          workflowId: "workflow-123",
          autoRefresh: true,
          refreshInterval: 1000,
        }),
      );

      // Flush initial fetch
      await vi.advanceTimersByTimeAsync(0);
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Advance time for first refresh
      await vi.advanceTimersByTimeAsync(1000);
      expect(mockFetch).toHaveBeenCalledTimes(2);

      // Another refresh
      await vi.advanceTimersByTimeAsync(1000);
      expect(mockFetch).toHaveBeenCalledTimes(3);
    });

    it("should use default refresh interval of 2000ms", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockExecutionResponse),
      });

      renderHook(() =>
        useWorkflowExecution({
          workflowId: "workflow-123",
          autoRefresh: true,
        }),
      );

      // Flush initial fetch
      await vi.advanceTimersByTimeAsync(0);
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Not enough time for refresh with default 2000ms
      await vi.advanceTimersByTimeAsync(1500);
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Now should refresh
      await vi.advanceTimersByTimeAsync(500);
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    it("should stop auto-refresh on unmount", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockExecutionResponse),
      });

      const { unmount } = renderHook(() =>
        useWorkflowExecution({
          workflowId: "workflow-123",
          autoRefresh: true,
          refreshInterval: 1000,
        }),
      );

      // Flush initial fetch
      await vi.advanceTimersByTimeAsync(0);
      expect(mockFetch).toHaveBeenCalledTimes(1);

      unmount();

      // Advance time - should not trigger more fetches
      await vi.advanceTimersByTimeAsync(5000);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe("step statuses", () => {
    it("should handle pending steps", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            steps: [createMockStep({ id: "step-1", status: "pending" })],
          }),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.steps[0].status).toBe("pending");
      });
    });

    it("should handle running steps", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            steps: [
              createMockStep({
                id: "step-1",
                status: "running",
                endTime: undefined,
              }),
            ],
            currentStepId: "step-1",
          }),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.steps[0].status).toBe("running");
        expect(result.current.currentStepId).toBe("step-1");
      });
    });

    it("should handle error steps", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            steps: [
              createMockStep({
                id: "step-1",
                status: "error",
                error: "Step failed",
              }),
            ],
          }),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.steps[0].status).toBe("error");
        expect(result.current.steps[0].error).toBe("Step failed");
      });
    });

    it("should handle skipped steps", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            steps: [createMockStep({ id: "step-1", status: "skipped" })],
          }),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.steps[0].status).toBe("skipped");
      });
    });
  });

  describe("step data", () => {
    it("should include input/output data", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            steps: [
              createMockStep({
                id: "step-1",
                input: { data: "input value" },
                output: { result: "output value" },
              }),
            ],
          }),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.steps[0].input).toEqual({ data: "input value" });
        expect(result.current.steps[0].output).toEqual({
          result: "output value",
        });
      });
    });

    it("should include duration and timing", async () => {
      const startTime = Date.now() - 1000;
      const endTime = Date.now();

      mockFetch.mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            steps: [
              createMockStep({
                id: "step-1",
                startTime,
                endTime,
                duration: 1000,
              }),
            ],
          }),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.steps[0].startTime).toBe(startTime);
        expect(result.current.steps[0].endTime).toBe(endTime);
        expect(result.current.steps[0].duration).toBe(1000);
      });
    });
  });

  describe("API response transformation", () => {
    it("should transform snake_case API response to camelCase", async () => {
      // API returns snake_case fields (WorkflowExecutionResponse format)
      const apiResponse = {
        steps: [
          {
            id: "step-1",
            node_id: "node-1",
            node_name: "Start",
            status: "completed",
            duration: 100,
            start_time: 1700000000000,
            end_time: 1700000000100,
          },
        ],
        current_step_id: "step-1",
      };

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(apiResponse),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.steps).toHaveLength(1);
      });

      // Should have camelCase fields
      const step = result.current.steps[0];
      expect(step.nodeId).toBe("node-1");
      expect(step.nodeName).toBe("Start");
      expect(step.startTime).toBe(1700000000000);
      expect(step.endTime).toBe(1700000000100);
      expect(result.current.currentStepId).toBe("step-1");
    });

    it("should transform nested step input/output from snake_case", async () => {
      const apiResponse = {
        steps: [
          {
            id: "step-1",
            node_id: "node-1",
            node_name: "Process",
            status: "completed",
            duration: 100,
            start_time: 1700000000000,
            input: { user_id: "123", request_data: { foo_bar: "baz" } },
            output: { response_body: { nested_key: "value" } },
          },
        ],
        current_step_id: null,
      };

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(apiResponse),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.steps).toHaveLength(1);
      });

      // Nested objects should be transformed to camelCase
      const step = result.current.steps[0];
      expect(step.input).toEqual({
        userId: "123",
        requestData: { fooBar: "baz" },
      });
      expect(step.output).toEqual({
        responseBody: { nestedKey: "value" },
      });
    });

    it("should handle null current_step_id from API", async () => {
      const apiResponse = {
        steps: [],
        current_step_id: null,
      };

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(apiResponse),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.currentStepId).toBeNull();
    });

    it("should handle step error field from snake_case API", async () => {
      const apiResponse = {
        steps: [
          {
            id: "step-1",
            node_id: "node-1",
            node_name: "Failed Step",
            status: "error",
            duration: 50,
            start_time: 1700000000000,
            end_time: 1700000000050,
            error: "Connection timeout",
          },
        ],
        current_step_id: null,
      };

      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(apiResponse),
      });

      const { result } = renderHook(() =>
        useWorkflowExecution({ workflowId: "workflow-123" }),
      );

      await waitFor(() => {
        expect(result.current.steps).toHaveLength(1);
      });

      expect(result.current.steps[0].error).toBe("Connection timeout");
      expect(result.current.steps[0].status).toBe("error");
    });

    it("should correctly fetch with authenticatedFetch", async () => {
      mockFetch.mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiResponse),
      });

      renderHook(() => useWorkflowExecution({ workflowId: "workflow-123" }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/workflows/workflow-123/execution",
          expect.anything(),
        );
      });
    });
  });
});
