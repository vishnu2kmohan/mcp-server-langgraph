/**
 * RemediationApprovalDialog Component Tests
 *
 * TDD tests for the remediation approval/rejection modal dialog.
 *
 * Features:
 * - Display remediation details
 * - Approve/reject confirmation
 * - Optional reason input
 * - Risk level warning
 * - Loading states
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  RemediationApprovalDialog,
  type RemediationApprovalDialogProps,
} from "./RemediationApprovalDialog";
import type { RemediationRequest, AIRecommendation } from "../../types/api";

// =============================================================================
// Test Data
// =============================================================================

const mockRemediation: RemediationRequest = {
  remediationId: "rem-001",
  alertId: "alert-001",
  alertName: "HighCPU",
  severity: "critical",
  stepNumber: 1,
  action: "scale",
  description: "Scale up replicas to handle current load",
  command: "kubectl scale deployment api-server --replicas=5",
  riskLevel: "low",
  status: "pending",
  requestedAt: "2024-01-15T10:36:00Z",
  approvedBy: null,
  approvedAt: null,
  reason: null,
  recommendationId: "rec-001",
};

const mockRecommendation: AIRecommendation = {
  recommendationId: "rec-001",
  alertId: "alert-001",
  rootCauseAnalysis: "Memory leak causing CPU pressure",
  remediationSteps: [
    {
      stepNumber: 1,
      action: "scale",
      description: "Scale up replicas to handle current load",
      command: "kubectl scale deployment api-server --replicas=5",
      requiresApproval: true,
      riskLevel: "low",
    },
  ],
  riskAssessment: {
    overallRisk: "low",
    impactAnalysis: "Minimal impact, additional pods added",
    rollbackPlan: "kubectl scale deployment api-server --replicas=3",
  },
  runbookReference: "https://runbooks.example.com/scale",
  generatedAt: "2024-01-15T10:35:00Z",
  modelUsed: "claude-3-5-sonnet",
};

const defaultProps: RemediationApprovalDialogProps = {
  remediation: mockRemediation,
  recommendation: mockRecommendation,
  isOpen: true,
  onClose: vi.fn(),
  onApprove: vi.fn(),
  onReject: vi.fn(),
};

// =============================================================================
// Tests
// =============================================================================

describe("RemediationApprovalDialog", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Basic Rendering", () => {
    it("should render when isOpen is true", () => {
      render(<RemediationApprovalDialog {...defaultProps} />);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should not render when isOpen is false", () => {
      render(<RemediationApprovalDialog {...defaultProps} isOpen={false} />);

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("should render dialog title", () => {
      render(<RemediationApprovalDialog {...defaultProps} />);

      expect(screen.getByText(/approve remediation/i)).toBeInTheDocument();
    });

    it("should render close button", () => {
      render(<RemediationApprovalDialog {...defaultProps} />);

      expect(screen.getByTestId("close-dialog")).toBeInTheDocument();
    });

    it("should call onClose when close button clicked", () => {
      const onClose = vi.fn();
      render(<RemediationApprovalDialog {...defaultProps} onClose={onClose} />);

      fireEvent.click(screen.getByTestId("close-dialog"));

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("Remediation Details", () => {
    it("should display alert name", () => {
      render(<RemediationApprovalDialog {...defaultProps} />);

      expect(screen.getByText("HighCPU")).toBeInTheDocument();
    });

    it("should display action description", () => {
      render(<RemediationApprovalDialog {...defaultProps} />);

      expect(
        screen.getByText("Scale up replicas to handle current load"),
      ).toBeInTheDocument();
    });

    it("should display command", () => {
      render(<RemediationApprovalDialog {...defaultProps} />);

      // Use getAllByText since both remediation command and rollback plan contain similar text
      const commands = screen.getAllByText(
        /kubectl scale deployment api-server/,
      );
      expect(commands.length).toBeGreaterThanOrEqual(1);
      // Check that the specific remediation command is present
      expect(screen.getByText(/--replicas=5/)).toBeInTheDocument();
    });

    it("should display step number", () => {
      render(<RemediationApprovalDialog {...defaultProps} />);

      expect(screen.getByTestId("step-number")).toHaveTextContent("1");
    });

    it("should display risk level", () => {
      render(<RemediationApprovalDialog {...defaultProps} />);

      expect(screen.getByTestId("risk-level")).toHaveTextContent(/low/i);
    });

    it("should display severity badge", () => {
      render(<RemediationApprovalDialog {...defaultProps} />);

      expect(screen.getByTestId("severity-badge")).toHaveTextContent(
        /critical/i,
      );
    });
  });

  describe("Risk Warning", () => {
    it("should show warning for high risk remediations", () => {
      const highRiskRemediation = {
        ...mockRemediation,
        riskLevel: "high" as const,
      };
      render(
        <RemediationApprovalDialog
          {...defaultProps}
          remediation={highRiskRemediation}
        />,
      );

      expect(screen.getByTestId("high-risk-warning")).toBeInTheDocument();
    });

    it("should not show warning for low risk remediations", () => {
      render(<RemediationApprovalDialog {...defaultProps} />);

      expect(screen.queryByTestId("high-risk-warning")).not.toBeInTheDocument();
    });

    it("should show impact analysis", () => {
      render(<RemediationApprovalDialog {...defaultProps} />);

      expect(
        screen.getByText(/minimal impact, additional pods added/i),
      ).toBeInTheDocument();
    });

    it("should show rollback plan", () => {
      render(<RemediationApprovalDialog {...defaultProps} />);

      expect(
        screen.getByText(/kubectl scale deployment api-server --replicas=3/i),
      ).toBeInTheDocument();
    });
  });

  describe("Approve Action", () => {
    it("should render approve button", () => {
      render(<RemediationApprovalDialog {...defaultProps} />);

      expect(screen.getByTestId("approve-button")).toBeInTheDocument();
    });

    it("should call onApprove with remediation id when clicked", async () => {
      const onApprove = vi.fn();
      render(
        <RemediationApprovalDialog {...defaultProps} onApprove={onApprove} />,
      );

      fireEvent.click(screen.getByTestId("approve-button"));

      await waitFor(() => {
        expect(onApprove).toHaveBeenCalledWith({
          remediationId: "rem-001",
          approvedBy: expect.any(String),
          reason: undefined,
        });
      });
    });

    it("should include optional reason if provided", async () => {
      const onApprove = vi.fn();
      const user = userEvent.setup();
      render(
        <RemediationApprovalDialog {...defaultProps} onApprove={onApprove} />,
      );

      await user.type(
        screen.getByTestId("reason-input"),
        "Approved after review",
      );
      await user.click(screen.getByTestId("approve-button"));

      await waitFor(() => {
        expect(onApprove).toHaveBeenCalledWith({
          remediationId: "rem-001",
          approvedBy: expect.any(String),
          reason: "Approved after review",
        });
      });
    });

    it("should disable approve button when loading", () => {
      render(<RemediationApprovalDialog {...defaultProps} isApproving />);

      expect(screen.getByTestId("approve-button")).toBeDisabled();
    });

    it("should show loading spinner when approving", () => {
      render(<RemediationApprovalDialog {...defaultProps} isApproving />);

      expect(screen.getByTestId("approve-loading")).toBeInTheDocument();
    });
  });

  describe("Reject Action", () => {
    it("should render reject button", () => {
      render(<RemediationApprovalDialog {...defaultProps} />);

      expect(screen.getByTestId("reject-button")).toBeInTheDocument();
    });

    it("should require reason for rejection", async () => {
      const onReject = vi.fn();
      render(
        <RemediationApprovalDialog {...defaultProps} onReject={onReject} />,
      );

      // Click reject without selecting a structured rejection reason
      fireEvent.click(screen.getByTestId("reject-button"));

      // Should show validation error (component now requires structured rejection reason)
      await waitFor(() => {
        expect(
          screen.getByText(/select a rejection reason/i),
        ).toBeInTheDocument();
      });

      // onReject should not be called
      expect(onReject).not.toHaveBeenCalled();
    });

    it("should call onReject with reason when provided", async () => {
      const onReject = vi.fn();
      const user = userEvent.setup();
      render(
        <RemediationApprovalDialog {...defaultProps} onReject={onReject} />,
      );

      // First select a structured rejection reason (now required)
      await user.click(screen.getByTestId("rejection-reason-too_risky"));
      // Then click reject
      await user.click(screen.getByTestId("reject-button"));

      await waitFor(() => {
        expect(onReject).toHaveBeenCalledWith({
          remediationId: "rem-001",
          rejectedBy: expect.any(String),
          reason: "too_risky",
          reasonDetail: undefined,
        });
      });
    });

    it("should disable reject button when loading", () => {
      render(<RemediationApprovalDialog {...defaultProps} isRejecting />);

      expect(screen.getByTestId("reject-button")).toBeDisabled();
    });

    it("should show loading spinner when rejecting", () => {
      render(<RemediationApprovalDialog {...defaultProps} isRejecting />);

      expect(screen.getByTestId("reject-loading")).toBeInTheDocument();
    });
  });

  describe("Keyboard Accessibility", () => {
    it("should close on Escape key", async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();
      render(<RemediationApprovalDialog {...defaultProps} onClose={onClose} />);

      await user.keyboard("{Escape}");

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("Error Handling", () => {
    it("should display error message when provided", () => {
      render(
        <RemediationApprovalDialog
          {...defaultProps}
          error="Failed to approve remediation"
        />,
      );

      expect(screen.getByText(/failed to approve/i)).toBeInTheDocument();
    });
  });

  describe("Structured Rejection Reasons", () => {
    it("should render rejection reason options", () => {
      render(<RemediationApprovalDialog {...defaultProps} />);

      expect(screen.getByTestId("rejection-reason-select")).toBeInTheDocument();
    });

    it("should have all rejection reason options", () => {
      render(<RemediationApprovalDialog {...defaultProps} />);

      const select = screen.getByTestId("rejection-reason-select");
      expect(select).toBeInTheDocument();

      // Check for key options
      expect(screen.getByText(/too risky/i)).toBeInTheDocument();
      expect(screen.getByText(/incorrect diagnosis/i)).toBeInTheDocument();
      expect(screen.getByText(/wrong command/i)).toBeInTheDocument();
    });

    it("should require structured reason for rejection", async () => {
      const onReject = vi.fn();
      const user = userEvent.setup();
      render(
        <RemediationApprovalDialog {...defaultProps} onReject={onReject} />,
      );

      // Type text reason but don't select structured reason
      await user.type(screen.getByTestId("reason-input"), "Some reason");
      await user.click(screen.getByTestId("reject-button"));

      // Should show validation error for structured reason
      await waitFor(() => {
        expect(
          screen.getByText(/select a rejection reason/i),
        ).toBeInTheDocument();
      });

      expect(onReject).not.toHaveBeenCalled();
    });

    it("should include structured reason in rejection callback", async () => {
      const onReject = vi.fn();
      const user = userEvent.setup();
      render(
        <RemediationApprovalDialog {...defaultProps} onReject={onReject} />,
      );

      // Select structured reason
      await user.click(screen.getByTestId("rejection-reason-too_risky"));

      // Click reject
      await user.click(screen.getByTestId("reject-button"));

      await waitFor(() => {
        expect(onReject).toHaveBeenCalledWith(
          expect.objectContaining({
            remediationId: "rem-001",
            reason: "too_risky",
          }),
        );
      });
    });

    it("should show detail input when 'other' is selected", async () => {
      const user = userEvent.setup();
      render(<RemediationApprovalDialog {...defaultProps} />);

      // Select 'other' reason
      await user.click(screen.getByTestId("rejection-reason-other"));

      // Should show detail input
      expect(screen.getByTestId("rejection-detail-input")).toBeInTheDocument();
    });

    it("should require detail when 'other' is selected", async () => {
      const onReject = vi.fn();
      const user = userEvent.setup();
      render(
        <RemediationApprovalDialog {...defaultProps} onReject={onReject} />,
      );

      // Select 'other' reason without providing detail
      await user.click(screen.getByTestId("rejection-reason-other"));
      await user.click(screen.getByTestId("reject-button"));

      // Should show validation error (use more specific match to avoid matching label)
      await waitFor(() => {
        expect(
          screen.getByText(/please provide details for your reason/i),
        ).toBeInTheDocument();
      });

      expect(onReject).not.toHaveBeenCalled();
    });

    it("should include detail in rejection when 'other' is selected", async () => {
      const onReject = vi.fn();
      const user = userEvent.setup();
      render(
        <RemediationApprovalDialog {...defaultProps} onReject={onReject} />,
      );

      // Select 'other' and provide detail
      await user.click(screen.getByTestId("rejection-reason-other"));
      await user.type(
        screen.getByTestId("rejection-detail-input"),
        "Custom reason here",
      );
      await user.click(screen.getByTestId("reject-button"));

      await waitFor(() => {
        expect(onReject).toHaveBeenCalledWith(
          expect.objectContaining({
            reason: "other",
            reasonDetail: "Custom reason here",
          }),
        );
      });
    });
  });
});
