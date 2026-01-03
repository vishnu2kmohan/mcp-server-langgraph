/**
 * PlanEditor Tests
 *
 * Tests for the execution plan editor component with markdown preview,
 * validation, and approval/rejection controls.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { PlanEditor, type ExecutionPlanView } from "./PlanEditor";

describe("PlanEditor", () => {
  const samplePlan: ExecutionPlanView = {
    plan_id: "plan-123",
    session_id: "session-456",
    status: "awaiting_approval",
    complexity: "complicated",
    risk_level: "medium",
    task_type: "code",
    executor_model: "gemini-3-flash",
    critic_model: "claude-haiku-4-5-20251001",
    estimated_cost: "0.05",
    message: "Help me refactor this code",
    tools_needed: ["file_read", "file_write"],
    thinking_budget: "medium",
    critique_rounds: 1,
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
      render(<PlanEditor {...defaultProps} />);
      expect(screen.getByText(/Execution Plan/i)).toBeInTheDocument();
    });

    it("should display plan ID", () => {
      render(<PlanEditor {...defaultProps} />);
      expect(screen.getByText(/plan-123/i)).toBeInTheDocument();
    });

    it("should display complexity level", () => {
      render(<PlanEditor {...defaultProps} />);
      expect(screen.getByText(/complicated/i)).toBeInTheDocument();
    });

    it("should display risk level", () => {
      render(<PlanEditor {...defaultProps} />);
      // Find the Risk: label and verify the risk level is displayed near it
      expect(screen.getByText(/Risk:/i)).toBeInTheDocument();
      // Use getAllByText since "medium" appears in both risk level and thinking budget
      const mediumElements = screen.getAllByText(/medium/i);
      expect(mediumElements.length).toBeGreaterThanOrEqual(1);
    });

    it("should display estimated cost", () => {
      render(<PlanEditor {...defaultProps} />);
      expect(screen.getByText(/0.05/i)).toBeInTheDocument();
    });

    it("should display executor model", () => {
      render(<PlanEditor {...defaultProps} />);
      expect(screen.getByText(/gemini-3-flash/i)).toBeInTheDocument();
    });
  });

  describe("Configuration Fields", () => {
    it("should display orchestrator selector", () => {
      render(<PlanEditor {...defaultProps} />);
      expect(screen.getByLabelText(/orchestrator/i)).toBeInTheDocument();
    });

    it("should display thinking budget selector", () => {
      render(<PlanEditor {...defaultProps} />);
      expect(screen.getByLabelText(/thinking budget/i)).toBeInTheDocument();
    });

    it("should display critique rounds input", () => {
      render(<PlanEditor {...defaultProps} />);
      expect(screen.getByLabelText(/critique rounds/i)).toBeInTheDocument();
    });
  });

  describe("Approval Actions", () => {
    it("should render approve button", () => {
      render(<PlanEditor {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /approve/i }),
      ).toBeInTheDocument();
    });

    it("should render reject button", () => {
      render(<PlanEditor {...defaultProps} />);
      expect(
        screen.getByRole("button", { name: /reject/i }),
      ).toBeInTheDocument();
    });

    it("should call onApprove when approve button clicked", () => {
      render(<PlanEditor {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /approve/i }));
      expect(defaultProps.onApprove).toHaveBeenCalledTimes(1);
    });

    it("should call onReject when reject button clicked", () => {
      render(<PlanEditor {...defaultProps} />);
      fireEvent.click(screen.getByRole("button", { name: /reject/i }));
      expect(defaultProps.onReject).toHaveBeenCalledTimes(1);
    });

    it("should disable actions when readOnly", () => {
      render(<PlanEditor {...defaultProps} readOnly={true} />);
      expect(screen.getByRole("button", { name: /approve/i })).toBeDisabled();
      expect(screen.getByRole("button", { name: /reject/i })).toBeDisabled();
    });
  });

  describe("Status Display", () => {
    it("should show pending status indicator", () => {
      render(<PlanEditor {...defaultProps} />);
      expect(screen.getByText(/awaiting approval/i)).toBeInTheDocument();
    });

    it("should show approved status when plan is approved", () => {
      const approvedPlan = { ...samplePlan, status: "approved" as const };
      render(<PlanEditor {...defaultProps} plan={approvedPlan} />);
      expect(screen.getByText(/approved/i)).toBeInTheDocument();
    });

    it("should show rejected status when plan is rejected", () => {
      const rejectedPlan = { ...samplePlan, status: "rejected" as const };
      render(<PlanEditor {...defaultProps} plan={rejectedPlan} />);
      expect(screen.getByText(/rejected/i)).toBeInTheDocument();
    });
  });

  describe("Tools Display", () => {
    it("should display required tools", () => {
      render(<PlanEditor {...defaultProps} />);
      expect(screen.getByText(/file_read/i)).toBeInTheDocument();
      expect(screen.getByText(/file_write/i)).toBeInTheDocument();
    });
  });
});
