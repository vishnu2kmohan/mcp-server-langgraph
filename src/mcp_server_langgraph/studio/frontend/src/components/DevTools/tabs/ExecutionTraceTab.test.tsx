/**
 * ExecutionTraceTab Tests
 *
 * TDD tests for the Execution Trace tab in DevTools.
 * Displays workflow node execution traces.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { axe, toHaveNoViolations } from "jest-axe";

expect.extend(toHaveNoViolations);

import { ExecutionTraceTab } from "./ExecutionTraceTab";

// =============================================================================
// Mock Data
// =============================================================================

const mockExecutionSteps = [
  {
    id: "step-1",
    nodeId: "node-start",
    nodeName: "Start",
    status: "completed" as const,
    duration: 10,
    startTime: 1703000000000,
    endTime: 1703000000010,
    input: { query: "test" },
    output: { result: "initialized" },
  },
  {
    id: "step-2",
    nodeId: "node-process",
    nodeName: "Process Data",
    status: "completed" as const,
    duration: 150,
    startTime: 1703000000010,
    endTime: 1703000000160,
    input: { data: "raw" },
    output: { processed: true },
  },
  {
    id: "step-3",
    nodeId: "node-output",
    nodeName: "Generate Output",
    status: "running" as const,
    duration: 0,
    startTime: 1703000000160,
    input: { processed: true },
  },
];

// =============================================================================
// Mock Hook
// =============================================================================

const mockUseWorkflowExecution = vi.fn().mockReturnValue({
  steps: mockExecutionSteps,
  isLoading: false,
  error: null,
  refetch: vi.fn(),
  currentStepId: "step-3",
});

vi.mock("../hooks/useWorkflowExecution", () => ({
  useWorkflowExecution: () => mockUseWorkflowExecution(),
}));

// Mock timeline context to avoid provider requirement
vi.mock("../context/DevToolsTimelineProvider", () => ({
  useTimelineContext: () => ({
    timeWindow: null,
    isLiveMode: true,
    currentTime: Date.now(),
    events: [],
    bookmarks: [],
  }),
}));

// =============================================================================
// Tests
// =============================================================================

describe("ExecutionTraceTab", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUseWorkflowExecution.mockReturnValue({
      steps: mockExecutionSteps,
      isLoading: false,
      error: null,
      refetch: vi.fn(),
      currentStepId: "step-3",
    });
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("rendering", () => {
    it("should render with data-testid", () => {
      render(<ExecutionTraceTab workflowId="workflow-123" />);

      expect(screen.getByTestId("execution-trace-tab")).toBeInTheDocument();
    });

    it("should display workflow ID", () => {
      render(<ExecutionTraceTab workflowId="workflow-123" />);

      expect(screen.getByText("workflow-123")).toBeInTheDocument();
    });

    it("should show loading state", () => {
      mockUseWorkflowExecution.mockReturnValue({
        steps: [],
        isLoading: true,
        error: null,
        refetch: vi.fn(),
        currentStepId: null,
      });

      render(<ExecutionTraceTab workflowId="workflow-123" />);

      expect(screen.getByTestId("execution-trace-loading")).toBeInTheDocument();
    });

    it("should show empty state when no execution data", () => {
      mockUseWorkflowExecution.mockReturnValue({
        steps: [],
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        currentStepId: null,
      });

      render(<ExecutionTraceTab workflowId="workflow-123" />);

      expect(screen.getByTestId("execution-trace-empty")).toBeInTheDocument();
    });
  });

  describe("step display", () => {
    it("should display all execution steps", () => {
      render(<ExecutionTraceTab workflowId="workflow-123" />);

      expect(screen.getByText("Start")).toBeInTheDocument();
      expect(screen.getByText("Process Data")).toBeInTheDocument();
      expect(screen.getByText("Generate Output")).toBeInTheDocument();
    });

    it("should show step status indicators", () => {
      render(<ExecutionTraceTab workflowId="workflow-123" />);

      expect(screen.getByTestId("step-status-step-1")).toBeInTheDocument();
      expect(screen.getByTestId("step-status-step-2")).toBeInTheDocument();
      expect(screen.getByTestId("step-status-step-3")).toBeInTheDocument();
    });

    it("should show step duration for completed steps", () => {
      render(<ExecutionTraceTab workflowId="workflow-123" />);

      expect(screen.getByText("10ms")).toBeInTheDocument();
      expect(screen.getByText("150ms")).toBeInTheDocument();
    });

    it("should highlight current step", () => {
      render(<ExecutionTraceTab workflowId="workflow-123" />);

      const currentStep = screen.getByTestId("execution-step-step-3");
      expect(currentStep).toHaveAttribute("data-current", "true");
    });
  });

  describe("node highlighting", () => {
    it("should call onNodeHighlight when step clicked", () => {
      const handleNodeHighlight = vi.fn();

      render(
        <ExecutionTraceTab
          workflowId="workflow-123"
          onNodeHighlight={handleNodeHighlight}
        />,
      );

      const step = screen.getByTestId("execution-step-step-1");
      fireEvent.click(step);

      expect(handleNodeHighlight).toHaveBeenCalledWith("node-start");
    });

    it("should clear highlight when clicking same step", () => {
      const handleNodeHighlight = vi.fn();

      render(
        <ExecutionTraceTab
          workflowId="workflow-123"
          onNodeHighlight={handleNodeHighlight}
        />,
      );

      const step = screen.getByTestId("execution-step-step-1");

      fireEvent.click(step);
      expect(handleNodeHighlight).toHaveBeenCalledWith("node-start");

      fireEvent.click(step);
      expect(handleNodeHighlight).toHaveBeenCalledWith(null);
    });
  });

  describe("step details", () => {
    it("should expand step details on click", async () => {
      const user = userEvent.setup();

      render(<ExecutionTraceTab workflowId="workflow-123" />);

      const expandButton = screen.getByTestId("expand-step-step-1");
      await user.click(expandButton);

      expect(screen.getByTestId("step-details-step-1")).toBeInTheDocument();
    });

    it("should show input/output data when expanded", async () => {
      const user = userEvent.setup();

      render(<ExecutionTraceTab workflowId="workflow-123" />);

      const expandButton = screen.getByTestId("expand-step-step-1");
      await user.click(expandButton);

      expect(screen.getByTestId("step-input-step-1")).toBeInTheDocument();
      expect(screen.getByTestId("step-output-step-1")).toBeInTheDocument();
    });
  });

  describe("refresh", () => {
    it("should have refresh button", () => {
      render(<ExecutionTraceTab workflowId="workflow-123" />);

      expect(
        screen.getByTestId("refresh-execution-button"),
      ).toBeInTheDocument();
    });

    it("should call refetch when refresh clicked", async () => {
      const user = userEvent.setup();
      const mockRefetch = vi.fn();

      mockUseWorkflowExecution.mockReturnValue({
        steps: mockExecutionSteps,
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        currentStepId: "step-3",
      });

      render(<ExecutionTraceTab workflowId="workflow-123" />);

      await user.click(screen.getByTestId("refresh-execution-button"));

      expect(mockRefetch).toHaveBeenCalled();
    });
  });

  describe("error handling", () => {
    it("should display error message when fetch fails", () => {
      mockUseWorkflowExecution.mockReturnValue({
        steps: [],
        isLoading: false,
        error: new Error("Workflow execution failed"),
        refetch: vi.fn(),
        currentStepId: null,
      });

      render(<ExecutionTraceTab workflowId="workflow-123" />);

      expect(screen.getByTestId("execution-trace-error")).toBeInTheDocument();
      expect(
        screen.getByText(/workflow execution failed/i),
      ).toBeInTheDocument();
    });
  });

  describe("accessibility", () => {
    it("should have accessible heading", () => {
      render(<ExecutionTraceTab workflowId="workflow-123" />);

      expect(
        screen.getByRole("heading", { name: /execution/i }),
      ).toBeInTheDocument();
    });

    it("should have no accessibility violations", async () => {
      const { container } = render(
        <ExecutionTraceTab workflowId="workflow-123" />,
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
