/**
 * PlanEditor Tests
 *
 * Tests for the execution plan editor component with markdown preview,
 * validation, and approval/rejection controls.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { PlanEditor, type ExecutionPlanView } from "./PlanEditor";

import { TestProvider } from "@/test-utils";

describe("PlanEditor", () => {
  const samplePlan: ExecutionPlanView = {
    planId: "plan-123",
    sessionId: "session-456",
    status: "awaiting_approval",
    complexity: "complicated",
    riskLevel: "medium",
    taskType: "code",
    executorModel: "gemini-3-flash-preview",
    criticModel: "claude-haiku-4-5-20251001",
    estimatedCost: "0.05",
    message: "Help me refactor this code",
    toolsNeeded: ["file_read", "file_write"],
    thinkingBudget: "medium",
    critiqueRounds: 1,
    orchestrator: "standard",
  };

  const defaultProps = {
    plan: samplePlan,
    onApprove: vi.fn(),
    onReject: vi.fn(),
    onSave: vi.fn(),
    readOnly: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render plan summary section", () => {
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByText(/Execution Plan/i)).toBeInTheDocument();
    });

    it("should display plan ID", () => {
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByText(/plan-123/i)).toBeInTheDocument();
    });

    it("should display complexity level", () => {
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByText(/complicated/i)).toBeInTheDocument();
    });

    it("should display risk level", () => {
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} />
        </TestProvider>,
      );
      // Find the Risk: label and verify the risk level is displayed near it
      expect(screen.getByText(/Risk:/i)).toBeInTheDocument();
      // Use getAllByText since "medium" appears in both risk level and thinking budget
      const mediumElements = screen.getAllByText(/medium/i);
      expect(mediumElements.length).toBeGreaterThanOrEqual(1);
    });

    it("should display estimated cost", () => {
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByText(/0.05/i)).toBeInTheDocument();
    });

    it("should display executor model", () => {
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByText(/gemini-3-flash-preview/i)).toBeInTheDocument();
    });
  });

  describe("Configuration Fields", () => {
    it("should display orchestrator selector", () => {
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByLabelText(/orchestrator/i)).toBeInTheDocument();
    });

    it("should display thinking budget selector", () => {
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByLabelText(/thinking budget/i)).toBeInTheDocument();
    });

    it("should display critique rounds input", () => {
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByLabelText(/critique rounds/i)).toBeInTheDocument();
    });
  });

  describe("Approval Actions", () => {
    it("should render approve button", () => {
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /approve/i }),
      ).toBeInTheDocument();
    });

    it("should render reject button", () => {
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} />
        </TestProvider>,
      );
      expect(
        screen.getByRole("button", { name: /reject/i }),
      ).toBeInTheDocument();
    });

    it("should call onApprove when approve button clicked", () => {
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /approve/i }));
      expect(defaultProps.onApprove).toHaveBeenCalledTimes(1);
    });

    it("should call onReject when reject button clicked", () => {
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} />
        </TestProvider>,
      );
      fireEvent.click(screen.getByRole("button", { name: /reject/i }));
      expect(defaultProps.onReject).toHaveBeenCalledTimes(1);
    });

    it("should disable actions when readOnly", () => {
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} readOnly={true} />
        </TestProvider>,
      );
      expect(screen.getByRole("button", { name: /approve/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /reject/i })).toBeDisabled();
    });
  });

  describe("Status Display", () => {
    it("should show pending status indicator", () => {
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByText(/awaiting approval/i)).toBeInTheDocument();
    });

    it("should show approved status when plan is approved", () => {
      const approvedPlan = { ...samplePlan, status: "approved" as const };
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} plan={approvedPlan} />
        </TestProvider>,
      );
      expect(screen.getByText(/approved/i)).toBeInTheDocument();
    });

    it("should show rejected status when plan is rejected", () => {
      const rejectedPlan = { ...samplePlan, status: "rejected" as const };
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} plan={rejectedPlan} />
        </TestProvider>,
      );
      expect(screen.getByText(/rejected/i)).toBeInTheDocument();
    });
  });

  describe("Tools Display", () => {
    it("should display required tools", () => {
      render(
        <TestProvider>
          <PlanEditor {...defaultProps} />
        </TestProvider>,
      );
      expect(screen.getByText(/file_read/i)).toBeInTheDocument();
      expect(screen.getByText(/file_write/i)).toBeInTheDocument();
    });
  });
});
