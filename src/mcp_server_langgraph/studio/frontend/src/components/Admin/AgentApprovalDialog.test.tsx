/**
 * AgentApprovalDialog Component Tests
 *
 * TDD tests for the agent HITL approval/rejection modal dialog.
 *
 * Features:
 * - Display agent request details (confidence, proposed action)
 * - Approve/reject with optional reason
 * - Confidence gauge visualization
 * - Low confidence warning
 * - Loading states
 * - Keyboard accessibility
 *
 * Reference: Plan - Confidence-Based Human-in-the-Loop (HITL) for Multi-Agent Orchestrator
 */

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import {
  AgentApprovalDialog,
  type AgentApprovalDialogProps,
  type AgentApprovalRequest,
} from "./AgentApprovalDialog";
import type { AIExplanation } from "../../types/hitl";

// =============================================================================
// Test Data
// =============================================================================

const mockApprovalRequest: AgentApprovalRequest = {
  request_id: "req-001",
  session_id: "session-001",
  task_id: "task-001",
  agent_name: "Research Assistant",
  confidence: 0.65,
  threshold: 0.7,
  proposed_action: "Send analysis report to external API",
  trigger_reason: "low_confidence",
  context: {
    tokens_used: 2450,
    time_elapsed_seconds: 12,
    artifacts: ["analysis.json", "chart.png"],
  },
  requested_at: "2024-01-15T10:36:00Z",
};

const mockAIExplanation: AIExplanation = {
  why_uncertain: "The input query contains ambiguous terms that could refer to multiple entities.",
  what_could_go_wrong: "May send data to the wrong external service if the target is misidentified.",
  safer_alternatives: [
    {
      action: "Preview data before sending",
      confidence: 0.92,
      trade_off: "Adds one extra confirmation step",
    },
    {
      action: "Send to staging API first",
      confidence: 0.95,
      trade_off: "Delays production deployment",
    },
  ],
  confidence_factors: [
    {
      factor: "ambiguous_input",
      weight: -0.2,
      evidence: "Query uses vague terms like 'the report'",
    },
    {
      factor: "multiple_targets",
      weight: -0.15,
      evidence: "Multiple external APIs match the request",
    },
  ],
  reasoning_trace: [
    "Step 1: Parsed user query",
    "Step 2: Identified external API request",
    "Step 3: Detected ambiguity in target specification",
  ],
  model_used: "gpt-4o-mini",
  generated_at: "2024-01-15T10:35:30Z",
  generation_latency_ms: 150.5,
  cached: false,
};

const mockApprovalRequestWithExplanation: AgentApprovalRequest = {
  ...mockApprovalRequest,
  ai_explanation: mockAIExplanation,
};

const defaultProps: AgentApprovalDialogProps = {
  request: mockApprovalRequest,
  isOpen: true,
  onClose: vi.fn(),
  onApprove: vi.fn(),
  onReject: vi.fn(),
  currentUser: "admin@example.com",
};

// =============================================================================
// Tests
// =============================================================================

describe("AgentApprovalDialog", () => {
  describe("Basic Rendering", () => {
    it("should render when isOpen is true", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(screen.getByRole("dialog")).toBeInTheDocument();
    });

    it("should not render when isOpen is false", () => {
      render(<AgentApprovalDialog {...defaultProps} isOpen={false} />);

      expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    });

    it("should render dialog title", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(screen.getByText(/agent.*requires approval/i)).toBeInTheDocument();
    });

    it("should render close button", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(screen.getByTestId("close-dialog")).toBeInTheDocument();
    });

    it("should call onClose when close button clicked", () => {
      const onClose = vi.fn();
      render(<AgentApprovalDialog {...defaultProps} onClose={onClose} />);

      fireEvent.click(screen.getByTestId("close-dialog"));

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("Request Details", () => {
    it("should display agent name", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(screen.getByText(/Research Assistant/)).toBeInTheDocument();
    });

    it("should display proposed action", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(
        screen.getByText("Send analysis report to external API")
      ).toBeInTheDocument();
    });

    it("should display confidence score", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(screen.getByTestId("confidence-score")).toHaveTextContent("65%");
    });

    it("should display confidence threshold", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(screen.getByTestId("confidence-threshold")).toHaveTextContent(
        "70%"
      );
    });

    it("should display trigger reason", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      // Should explain why approval is needed
      expect(
        screen.getByText(/confidence.*below.*threshold/i)
      ).toBeInTheDocument();
    });
  });

  describe("Confidence Gauge", () => {
    it("should render confidence gauge", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(screen.getByTestId("confidence-gauge")).toBeInTheDocument();
    });

    it("should show amber color for low confidence (50-69%)", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      const gauge = screen.getByTestId("confidence-gauge");
      // Gauge should have amber styling for 65% confidence
      expect(gauge).toHaveClass("bg-amber-500");
    });

    it("should show red color for critical confidence (<50%)", () => {
      const lowConfidenceRequest = {
        ...mockApprovalRequest,
        confidence: 0.45,
      };
      render(
        <AgentApprovalDialog {...defaultProps} request={lowConfidenceRequest} />
      );

      const gauge = screen.getByTestId("confidence-gauge");
      expect(gauge).toHaveClass("bg-red-500");
    });

    it("should show blue color for medium confidence (70-89%)", () => {
      const mediumConfidenceRequest = {
        ...mockApprovalRequest,
        confidence: 0.75,
      };
      render(
        <AgentApprovalDialog
          {...defaultProps}
          request={mediumConfidenceRequest}
        />
      );

      const gauge = screen.getByTestId("confidence-gauge");
      expect(gauge).toHaveClass("bg-blue-500");
    });
  });

  describe("Low Confidence Warning", () => {
    it("should show warning for low confidence", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(screen.getByTestId("low-confidence-warning")).toBeInTheDocument();
    });

    it("should not show warning for high confidence", () => {
      const highConfidenceRequest = {
        ...mockApprovalRequest,
        confidence: 0.95,
        threshold: 0.7,
      };
      render(
        <AgentApprovalDialog
          {...defaultProps}
          request={highConfidenceRequest}
        />
      );

      expect(
        screen.queryByTestId("low-confidence-warning")
      ).not.toBeInTheDocument();
    });
  });

  describe("Context Display", () => {
    it("should display tokens used", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(screen.getByText(/2,?450/)).toBeInTheDocument();
    });

    it("should display time elapsed", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(screen.getByText(/12s/)).toBeInTheDocument();
    });

    it("should display artifacts", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(screen.getByText(/analysis\.json/)).toBeInTheDocument();
      expect(screen.getByText(/chart\.png/)).toBeInTheDocument();
    });
  });

  describe("Approve Action", () => {
    it("should render approve button", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(screen.getByTestId("approve-button")).toBeInTheDocument();
    });

    it("should call onApprove with request id when clicked", async () => {
      const onApprove = vi.fn();
      render(
        <AgentApprovalDialog {...defaultProps} onApprove={onApprove} />
      );

      fireEvent.click(screen.getByTestId("approve-button"));

      await waitFor(() => {
        expect(onApprove).toHaveBeenCalledWith({
          request_id: "req-001",
          approved_by: "admin@example.com",
          reason: undefined,
        });
      });
    });

    it("should include optional reason if provided", async () => {
      const onApprove = vi.fn();
      const user = userEvent.setup();
      render(
        <AgentApprovalDialog {...defaultProps} onApprove={onApprove} />
      );

      await user.type(
        screen.getByTestId("reason-input"),
        "Approved after review"
      );
      await user.click(screen.getByTestId("approve-button"));

      await waitFor(() => {
        expect(onApprove).toHaveBeenCalledWith({
          request_id: "req-001",
          approved_by: "admin@example.com",
          reason: "Approved after review",
        });
      });
    });

    it("should disable approve button when loading", () => {
      render(<AgentApprovalDialog {...defaultProps} isApproving />);

      expect(screen.getByTestId("approve-button")).toBeDisabled();
    });

    it("should show loading spinner when approving", () => {
      render(<AgentApprovalDialog {...defaultProps} isApproving />);

      expect(screen.getByTestId("approve-loading")).toBeInTheDocument();
    });
  });

  describe("Reject Action", () => {
    it("should render reject button", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(screen.getByTestId("reject-button")).toBeInTheDocument();
    });

    it("should call onReject with request id when clicked", async () => {
      const onReject = vi.fn();
      render(<AgentApprovalDialog {...defaultProps} onReject={onReject} />);

      fireEvent.click(screen.getByTestId("reject-button"));

      await waitFor(() => {
        expect(onReject).toHaveBeenCalledWith({
          request_id: "req-001",
          rejected_by: "admin@example.com",
          reason: undefined,
        });
      });
    });

    it("should include optional reason if provided", async () => {
      const onReject = vi.fn();
      const user = userEvent.setup();
      render(<AgentApprovalDialog {...defaultProps} onReject={onReject} />);

      await user.type(screen.getByTestId("reason-input"), "Too risky");
      await user.click(screen.getByTestId("reject-button"));

      await waitFor(() => {
        expect(onReject).toHaveBeenCalledWith({
          request_id: "req-001",
          rejected_by: "admin@example.com",
          reason: "Too risky",
        });
      });
    });

    it("should disable reject button when loading", () => {
      render(<AgentApprovalDialog {...defaultProps} isRejecting />);

      expect(screen.getByTestId("reject-button")).toBeDisabled();
    });

    it("should show loading spinner when rejecting", () => {
      render(<AgentApprovalDialog {...defaultProps} isRejecting />);

      expect(screen.getByTestId("reject-loading")).toBeInTheDocument();
    });
  });

  describe("Keyboard Accessibility", () => {
    it("should close on Escape key", async () => {
      const onClose = vi.fn();
      const user = userEvent.setup();
      render(<AgentApprovalDialog {...defaultProps} onClose={onClose} />);

      await user.keyboard("{Escape}");

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("Error Handling", () => {
    it("should display error message when provided", () => {
      render(
        <AgentApprovalDialog
          {...defaultProps}
          error="Failed to approve request"
        />
      );

      expect(screen.getByText(/failed to approve/i)).toBeInTheDocument();
    });
  });

  describe("Trigger Reason Explanations", () => {
    it("should explain low_confidence trigger", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(
        screen.getByText(/confidence.*below.*threshold/i)
      ).toBeInTheDocument();
    });

    it("should explain destructive_action trigger", () => {
      const destructiveRequest = {
        ...mockApprovalRequest,
        trigger_reason: "destructive_action",
      };
      render(
        <AgentApprovalDialog {...defaultProps} request={destructiveRequest} />
      );

      expect(screen.getByText(/modify or delete/i)).toBeInTheDocument();
    });

    it("should explain external_api trigger", () => {
      const externalApiRequest = {
        ...mockApprovalRequest,
        trigger_reason: "external_api",
      };
      render(
        <AgentApprovalDialog {...defaultProps} request={externalApiRequest} />
      );

      expect(screen.getByText(/external service/i)).toBeInTheDocument();
    });
  });

  // ===========================================================================
  // AI Explanation Section Tests (AI-Native HITL Enhancements Phase 1)
  // ===========================================================================

  describe("AI Explanation Section", () => {
    it("should not render AI explanation section when ai_explanation is undefined", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(
        screen.queryByTestId("ai-explanation-section")
      ).not.toBeInTheDocument();
    });

    it("should render AI explanation section when ai_explanation is present", () => {
      render(
        <AgentApprovalDialog
          {...defaultProps}
          request={mockApprovalRequestWithExplanation}
        />
      );

      expect(screen.getByTestId("ai-explanation-section")).toBeInTheDocument();
    });

    it("should display 'Why uncertain?' summary text", () => {
      render(
        <AgentApprovalDialog
          {...defaultProps}
          request={mockApprovalRequestWithExplanation}
        />
      );

      expect(screen.getByText(/why is the agent uncertain/i)).toBeInTheDocument();
    });

    it("should display why_uncertain explanation", () => {
      render(
        <AgentApprovalDialog
          {...defaultProps}
          request={mockApprovalRequestWithExplanation}
        />
      );

      expect(
        screen.getByText(/ambiguous terms that could refer to multiple entities/i)
      ).toBeInTheDocument();
    });

    it("should display what_could_go_wrong explanation", () => {
      render(
        <AgentApprovalDialog
          {...defaultProps}
          request={mockApprovalRequestWithExplanation}
        />
      );

      expect(
        screen.getByText(/wrong external service/i)
      ).toBeInTheDocument();
    });

    it("should display 'What could go wrong' label", () => {
      render(
        <AgentApprovalDialog
          {...defaultProps}
          request={mockApprovalRequestWithExplanation}
        />
      );

      expect(screen.getByText(/what could go wrong/i)).toBeInTheDocument();
    });

    describe("Safer Alternatives", () => {
      it("should display safer alternatives when present", () => {
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={mockApprovalRequestWithExplanation}
          />
        );

        expect(screen.getByText(/safer alternatives/i)).toBeInTheDocument();
      });

      it("should display all alternative actions", () => {
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={mockApprovalRequestWithExplanation}
          />
        );

        expect(screen.getByText(/Preview data before sending/)).toBeInTheDocument();
        expect(screen.getByText(/Send to staging API first/)).toBeInTheDocument();
      });

      it("should display alternative confidence percentages", () => {
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={mockApprovalRequestWithExplanation}
          />
        );

        expect(screen.getByText(/92%/)).toBeInTheDocument();
        expect(screen.getByText(/95%/)).toBeInTheDocument();
      });

      it("should display trade-offs for alternatives", () => {
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={mockApprovalRequestWithExplanation}
          />
        );

        expect(screen.getByText(/extra confirmation step/i)).toBeInTheDocument();
        expect(screen.getByText(/Delays production deployment/i)).toBeInTheDocument();
      });

      it("should not display safer alternatives section when empty", () => {
        const requestWithoutAlternatives: AgentApprovalRequest = {
          ...mockApprovalRequest,
          ai_explanation: {
            why_uncertain: "Some uncertainty",
            what_could_go_wrong: "Some risk",
            safer_alternatives: [],
          },
        };
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={requestWithoutAlternatives}
          />
        );

        expect(
          screen.queryByText(/safer alternatives/i)
        ).not.toBeInTheDocument();
      });
    });

    describe("Confidence Factors", () => {
      it("should display confidence factors section when present", () => {
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={mockApprovalRequestWithExplanation}
          />
        );

        expect(screen.getByText(/confidence factors/i)).toBeInTheDocument();
      });

      it("should display factor evidence", () => {
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={mockApprovalRequestWithExplanation}
          />
        );

        expect(screen.getByText(/vague terms like 'the report'/i)).toBeInTheDocument();
        expect(screen.getByText(/Multiple external APIs match/i)).toBeInTheDocument();
      });

      it("should not display confidence factors section when empty", () => {
        const requestWithoutFactors: AgentApprovalRequest = {
          ...mockApprovalRequest,
          ai_explanation: {
            why_uncertain: "Some uncertainty",
            what_could_go_wrong: "Some risk",
            confidence_factors: [],
          },
        };
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={requestWithoutFactors}
          />
        );

        expect(
          screen.queryByText(/confidence factors/i)
        ).not.toBeInTheDocument();
      });
    });

    describe("Expandable Details", () => {
      it("should render as expandable details element", () => {
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={mockApprovalRequestWithExplanation}
          />
        );

        const details = screen.getByTestId("ai-explanation-section");
        expect(details.tagName.toLowerCase()).toBe("details");
      });

      it("should have summary element for toggling", () => {
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={mockApprovalRequestWithExplanation}
          />
        );

        const summary = screen.getByText(/why is the agent uncertain/i);
        expect(summary.tagName.toLowerCase()).toBe("summary");
      });
    });
  });
});
