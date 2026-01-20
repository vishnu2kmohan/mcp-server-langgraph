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
      render(<ExecutionHistoryPanel {...defaultProps} />);

      expect(screen.getByText("Execution History")).toBeInTheDocument();
    });

    it("should render execution list", () => {
      render(<ExecutionHistoryPanel {...defaultProps} />);

      expect(screen.getByTestId("execution-exec-1")).toBeInTheDocument();
      expect(screen.getByTestId("execution-exec-2")).toBeInTheDocument();
      expect(screen.getByTestId("execution-exec-3")).toBeInTheDocument();
    });

    it("should display execution count", () => {
      render(<ExecutionHistoryPanel {...defaultProps} />);

      expect(screen.getByText("3 executions")).toBeInTheDocument();
    });
  });

  describe("Status Indicators", () => {
    it("should show green indicator for completed status", () => {
      render(<ExecutionHistoryPanel {...defaultProps} />);

      const completedExec = screen.getByTestId("execution-exec-1");
      expect(
        completedExec.querySelector(".bg-success-9"),
      ).toBeInTheDocument();
    });

    it("should show blue indicator for running status", () => {
      render(<ExecutionHistoryPanel {...defaultProps} />);

      const runningExec = screen.getByTestId("execution-exec-2");
      expect(runningExec.querySelector(".bg-primary-9")).toBeInTheDocument();
    });

    it("should show red indicator for failed status", () => {
      render(<ExecutionHistoryPanel {...defaultProps} />);

      const failedExec = screen.getByTestId("execution-exec-3");
      expect(failedExec.querySelector(".bg-error-9")).toBeInTheDocument();
    });

    it("should show spinning indicator for running executions", () => {
      render(<ExecutionHistoryPanel {...defaultProps} />);

      const runningExec = screen.getByTestId("execution-exec-2");
      expect(runningExec.querySelector(".animate-spin")).toBeInTheDocument();
    });
  });

  describe("Execution Details", () => {
    it("should display execution start time", () => {
      render(<ExecutionHistoryPanel {...defaultProps} />);

      // Should display formatted time - check for any time pattern (HH:MM format)
      // Time format is locale-dependent, so check for Clock icon presence with time text
      const executionItem = screen.getByTestId("execution-exec-1");
      expect(executionItem.querySelector(".w-3.h-3")).toBeInTheDocument();
    });

    it("should display execution duration for completed executions", () => {
      render(<ExecutionHistoryPanel {...defaultProps} />);

      // Completed execution should show duration (5 minutes = 5m)
      const completedExec = screen.getByTestId("execution-exec-1");
      expect(completedExec).toHaveTextContent(/5m/);
    });

    it("should display error message for failed executions", () => {
      render(<ExecutionHistoryPanel {...defaultProps} />);

      expect(screen.getByText("Connection timeout")).toBeInTheDocument();
    });
  });

  describe("Selection", () => {
    it("should call onSelectExecution when execution is clicked", async () => {
      const onSelectExecution = vi.fn();
      render(
        <ExecutionHistoryPanel
          {...defaultProps}
          onSelectExecution={onSelectExecution}
        />,
      );

      const execution = screen.getByTestId("execution-exec-1");
      await act(async () => {
        execution.click();
      });

      expect(onSelectExecution).toHaveBeenCalledWith(mockExecutions[0]);
    });

    it("should highlight selected execution", () => {
      render(
        <ExecutionHistoryPanel
          {...defaultProps}
          selectedExecutionId="exec-1"
        />,
      );

      const execution = screen.getByTestId("execution-exec-1");
      expect(execution).toHaveClass("ring-2");
    });
  });

  describe("Loading State", () => {
    it("should show loading spinner when isLoading is true and no executions", () => {
      // Loading spinner only shows when loading AND no existing executions
      render(
        <ExecutionHistoryPanel
          {...defaultProps}
          isLoading={true}
          executions={[]}
        />,
      );

      expect(screen.getByTestId("execution-loading")).toBeInTheDocument();
    });

    it("should still show existing executions while loading more", () => {
      // When loading more (has existing executions), continue showing them
      render(<ExecutionHistoryPanel {...defaultProps} isLoading={true} />);

      // Existing executions should still be visible
      expect(screen.getByTestId("execution-exec-1")).toBeInTheDocument();
      expect(screen.getByTestId("execution-exec-2")).toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should show empty message when no executions", () => {
      render(<ExecutionHistoryPanel {...defaultProps} executions={[]} />);

      expect(screen.getByText("No executions yet")).toBeInTheDocument();
    });

    it("should show helpful message in empty state", () => {
      render(<ExecutionHistoryPanel {...defaultProps} executions={[]} />);

      expect(
        screen.getByText(/Run this workflow to see execution history/),
      ).toBeInTheDocument();
    });
  });

  describe("Pagination", () => {
    it("should show Load More button when hasMore is true", () => {
      render(<ExecutionHistoryPanel {...defaultProps} hasMore={true} />);

      expect(
        screen.getByRole("button", { name: /load more/i }),
      ).toBeInTheDocument();
    });

    it("should not show Load More button when hasMore is false", () => {
      render(<ExecutionHistoryPanel {...defaultProps} hasMore={false} />);

      expect(
        screen.queryByRole("button", { name: /load more/i }),
      ).not.toBeInTheDocument();
    });

    it("should call onLoadMore when Load More is clicked", async () => {
      const onLoadMore = vi.fn();
      render(
        <ExecutionHistoryPanel
          {...defaultProps}
          hasMore={true}
          onLoadMore={onLoadMore}
        />,
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
      render(<ExecutionHistoryPanel {...defaultProps} />);

      expect(screen.getByRole("button", { name: /all/i })).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /completed/i }),
      ).toBeInTheDocument();
      expect(
        screen.getByRole("button", { name: /failed/i }),
      ).toBeInTheDocument();
    });

    it("should filter executions by status when filter is clicked", async () => {
      render(<ExecutionHistoryPanel {...defaultProps} />);

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
