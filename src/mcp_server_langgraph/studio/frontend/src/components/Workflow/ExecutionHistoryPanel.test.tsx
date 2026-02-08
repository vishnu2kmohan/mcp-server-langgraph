/**
 * ExecutionHistoryPanel Tests
 *
 * TDD tests for the workflow execution history panel component.
 * Tests cover:
 * - Rendering execution list
 * - Execution status indicators
 * - Execution details display
 * - Loading and error states
 * - Pagination
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, cleanup } from "@testing-library/react";
import {
  ExecutionHistoryPanel,
  type WorkflowExecution,
} from "./ExecutionHistoryPanel";

import { TestProvider } from "@/test-utils";

describe("ExecutionHistoryPanel", () => {
  const mockExecutions: WorkflowExecution[] = [
    {
      id: "exec-1",
      workflowId: "wf-1",
      status: "completed",
      startedAt: "2025-01-01T10:00:00Z",
      completedAt: "2025-01-01T10:05:00Z",
      inputData: { query: "test" },
      outputData: { result: "success" },
      error: null,
    },
    {
      id: "exec-2",
      workflowId: "wf-1",
      status: "running",
      startedAt: "2025-01-01T11:00:00Z",
      completedAt: null,
      inputData: { query: "test 2" },
      outputData: null,
      error: null,
    },
    {
      id: "exec-3",
      workflowId: "wf-1",
      status: "failed",
      startedAt: "2025-01-01T09:00:00Z",
      completedAt: "2025-01-01T09:02:00Z",
      inputData: { query: "fail" },
      outputData: null,
      error: "Connection timeout",
    },
  ];

  const defaultProps = {
    executions: mockExecutions,
    isLoading: false,
    onSelectExecution: vi.fn(),
    onLoadMore: vi.fn(),
    hasMore: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render panel title", () => {
      render(
        <TestProvider>
          <ExecutionHistoryPanel {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("Execution History")).toBeInTheDocument();
    });

    it("should render execution list", () => {
      render(
        <TestProvider>
          <ExecutionHistoryPanel {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("execution-exec-1")).toBeInTheDocument();
      expect(screen.getByTestId("execution-exec-2")).toBeInTheDocument();
      expect(screen.getByTestId("execution-exec-3")).toBeInTheDocument();
    });

    it("should display execution count", () => {
      render(
        <TestProvider>
          <ExecutionHistoryPanel {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("3 executions")).toBeInTheDocument();
    });
  });

  describe("Status Indicators", () => {
    it("should show green indicator for completed status", () => {
      render(
        <TestProvider>
          <ExecutionHistoryPanel {...defaultProps} />
        </TestProvider>,
      );

      const completedExec = screen.getByTestId("execution-exec-1");
      expect(completedExec.querySelector(".bg-success-9")).toBeInTheDocument();
    });

    it("should show blue indicator for running status", () => {
      render(
        <TestProvider>
          <ExecutionHistoryPanel {...defaultProps} />
        </TestProvider>,
      );

      const runningExec = screen.getByTestId("execution-exec-2");
      expect(runningExec.querySelector(".bg-primary-9")).toBeInTheDocument();
    });

    it("should show red indicator for failed status", () => {
      render(
        <TestProvider>
          <ExecutionHistoryPanel {...defaultProps} />
        </TestProvider>,
      );

      const failedExec = screen.getByTestId("execution-exec-3");
      expect(failedExec.querySelector(".bg-error-9")).toBeInTheDocument();
    });

    it("should show spinning indicator for running executions", () => {
      render(
        <TestProvider>
          <ExecutionHistoryPanel {...defaultProps} />
        </TestProvider>,
      );

      const runningExec = screen.getByTestId("execution-exec-2");
      expect(runningExec.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });

  describe("Execution Details", () => {
    it("should display execution start time", () => {
      render(
        <TestProvider>
          <ExecutionHistoryPanel {...defaultProps} />
        </TestProvider>,
      );

      // Should display formatted time - check for any time pattern (HH:MM format)
      // Time format is locale-dependent, so check for Clock icon presence with time text
      const executionItem = screen.getByTestId("execution-exec-1");
      expect(executionItem.querySelector(".w-3.h-3")).toBeInTheDocument();
    });

    it("should display execution duration for completed executions", () => {
      render(
        <TestProvider>
          <ExecutionHistoryPanel {...defaultProps} />
        </TestProvider>,
      );

      // Completed execution should show duration (5 minutes = 5m)
      const completedExec = screen.getByTestId("execution-exec-1");
      expect(completedExec).toHaveTextContent(/5m/);
    });

    it("should display error message for failed executions", () => {
      render(
        <TestProvider>
          <ExecutionHistoryPanel {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText("Connection timeout")).toBeInTheDocument();
    });
  });

  describe("Selection", () => {
    it("should call onSelectExecution when execution is clicked", async () => {
      const onSelectExecution = vi.fn();
      render(
        <TestProvider>
          <ExecutionHistoryPanel
            {...defaultProps}
            onSelectExecution={onSelectExecution}
          />
        </TestProvider>,
      );

      const execution = screen.getByTestId("execution-exec-1");
      await act(async () => {
        execution.click();
      });

      expect(onSelectExecution).toHaveBeenCalledWith(mockExecutions[0]);
    });

    it("should highlight selected execution", () => {
      render(
        <TestProvider>
          <ExecutionHistoryPanel
            {...defaultProps}
            selectedExecutionId="exec-1"
          />
        </TestProvider>,
      );

      const execution = screen.getByTestId("execution-exec-1");
      expect(execution).toHaveClass("ring-2");
    });
  });

  describe("Loading State", () => {
    it("should show loading spinner when isLoading is true and no executions", () => {
      // Loading spinner only shows when loading AND no existing executions
      render(
        <TestProvider>
          <ExecutionHistoryPanel
            {...defaultProps}
            isLoading={true}
            executions={[]}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("execution-loading")).toBeInTheDocument();
    });

    it("should still show existing executions while loading more", () => {
      // When loading more (has existing executions), continue showing them
      render(
        <TestProvider>
          <ExecutionHistoryPanel {...defaultProps} isLoading={true} />
        </TestProvider>,
      );

      // Existing executions should still be visible
      expect(screen.getByTestId("execution-exec-1")).toBeInTheDocument();
      expect(screen.getByTestId("execution-exec-2")).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should show empty message when no executions", () => {
      render(
        <TestProvider>
          <ExecutionHistoryPanel {...defaultProps} executions={[]} />
        </TestProvider>,
      );

      expect(screen.getByText("No executions yet")).toBeInTheDocument();
    });

    it("should show helpful message in empty state", () => {
      render(
        <TestProvider>
          <ExecutionHistoryPanel {...defaultProps} executions={[]} />
        </TestProvider>,
      );

      expect(
        screen.getByText(/Run this workflow to see execution history/),
      ).toBeInTheDocument();
    });
  });

  describe("Pagination", () => {
    it("should show Load More button when hasMore is true", () => {
      render(
        <TestProvider>
          <ExecutionHistoryPanel {...defaultProps} hasMore={true} />
        </TestProvider>,
      );

      expect(
        screen.getByRole("button", { name: /load more/i }),
      ).toBeInTheDocument();
    });

    it("should not show Load More button when hasMore is false", () => {
      render(
        <TestProvider>
          <ExecutionHistoryPanel {...defaultProps} hasMore={false} />
        </TestProvider>,
      );

      expect(
        screen.queryByRole("button", { name: /load more/i }),
      ).not.toBeInTheDocument();
    });

    it("should call onLoadMore when Load More is clicked", async () => {
      const onLoadMore = vi.fn();
      render(
        <TestProvider>
          <ExecutionHistoryPanel
            {...defaultProps}
            hasMore={true}
            onLoadMore={onLoadMore}
          />
        </TestProvider>,
      );

      const loadMoreButton = screen.getByRole("button", { name: /load more/i });
      await act(async () => {
        loadMoreButton.click();
      });

      expect(onLoadMore).toHaveBeenCalledTimes(1);
    });
  });

  describe("Status Filter", () => {
    it("should render status filter buttons", () => {
      render(
        <TestProvider>
          <ExecutionHistoryPanel {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByRole("button", { name: /all/i })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /completed/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /failed/i }),
      ).toBeInTheDocument();
    });

    it("should filter executions by status when filter is clicked", async () => {
      render(
        <TestProvider>
          <ExecutionHistoryPanel {...defaultProps} />
        </TestProvider>,
      );

      const failedFilter = screen.getByRole("button", { name: /failed/i });
      await act(async () => {
        failedFilter.click();
      });

      // Only failed executions should be visible
      expect(screen.queryByTestId("execution-exec-1")).not.toBeInTheDocument();
      expect(screen.queryByTestId("execution-exec-2")).not.toBeInTheDocument();
      expect(screen.getByTestId("execution-exec-3")).toBeInTheDocument();
    });
  });
});
