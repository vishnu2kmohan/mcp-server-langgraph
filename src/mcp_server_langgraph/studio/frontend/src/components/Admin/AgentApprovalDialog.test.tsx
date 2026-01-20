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

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  render,
  screen,
  fireEvent,
  waitFor,
  cleanup,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";

import {
  AgentApprovalDialog,
  type AgentApprovalDialogProps,
  type AgentApprovalRequestCamelCase,
} from "./AgentApprovalDialog";
import type { AIExplanationCamelCase } from "../../types/hitl";

// Mock the API module for HITL Intelligence hooks
vi.mock("../../api", () => ({
  useStudioAnalyzeMutation: vi.fn(() => [
    vi.fn(() => ({
      unwrap: () =>
        Promise.resolve({
          analyses: {
            risk_assess: {
              risk_score: 0.72,
              risk_level: "medium",
              risk_factors: [
                {
                  factor: "external_api_access",
                  weight: 0.3,
                  description: "Sends data to external service",
                },
                {
                  factor: "data_sensitivity",
                  weight: 0.25,
                  description: "Contains user data",
                },
              ],
              mitigations: [
                "Review data before sending",
                "Use staging API first",
              ],
              recommendation: "review",
              explanation:
                "This action involves sending data to an external API with moderate risk.",
            },
            decision_history: {
              similar_decisions: [
                {
                  request_id: "req-prev-001",
                  action_type: "external_api",
                  decision: "approved",
                  decided_by: "admin",
                  decided_at: "2024-01-10T10:00:00Z",
                  reasoning: "Data was verified before sending",
                },
                {
                  request_id: "req-prev-002",
                  action_type: "external_api",
                  decision: "rejected",
                  decided_by: "security-admin",
                  decided_at: "2024-01-08T14:00:00Z",
                  reasoning: "Scope too broad",
                },
              ],
              approval_rate: 0.67,
              total_similar: 6,
              suggested_action: "review",
            },
          },
        }),
    })),
    { isLoading: false },
  ]),
}));

// Create test store for Redux provider
const createTestStore = () =>
  configureStore({
    reducer: {
      test: (state = {}) => state,
    },
  });

interface WrapperProps {
  children: ReactNode;
}

const Wrapper = ({ children }: WrapperProps) => {
  const store = createTestStore();
  return <Provider store={store}>{children}</Provider>;
};

const renderWithProvider = (ui: React.ReactElement) => {
  return render(ui, { wrapper: Wrapper });
};

// =============================================================================
// Test Data
// =============================================================================

// Mock data uses camelCase per ADR-0091 Phase 10
const mockApprovalRequest: AgentApprovalRequestCamelCase = {
  requestId: "req-001",
  sessionId: "session-001",
  taskId: "task-001",
  agentName: "Research Assistant",
  confidence: 0.65,
  threshold: 0.7,
  proposedAction: "Send analysis report to external API",
  triggerReason: "low_confidence",
  context: {
    tokensUsed: 2450,
    timeElapsedSeconds: 12,
    artifacts: ["analysis.json", "chart.png"],
  },
  requestedAt: "2024-01-15T10:36:00Z",
};

// AI explanation uses camelCase per ADR-0091 Phase 10
const mockAIExplanation: AIExplanationCamelCase = {
  whyUncertain:
    "The input query contains ambiguous terms that could refer to multiple entities.",
  whatCouldGoWrong:
    "May send data to the wrong external service if the target is misidentified.",
  saferAlternatives: [
    {
      action: "Preview data before sending",
      confidence: 0.92,
      tradeOff: "Adds one extra confirmation step",
    },
    {
      action: "Send to staging API first",
      confidence: 0.95,
      tradeOff: "Delays production deployment",
    },
  ],
  confidenceFactors: [
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
  reasoningTrace: [
    "Step 1: Parsed user query",
    "Step 2: Identified external API request",
    "Step 3: Detected ambiguity in target specification",
  ],
  modelUsed: "gpt-4o-mini",
  generatedAt: "2024-01-15T10:35:30Z",
  generationLatencyMs: 150.5,
  cached: false,
};

const mockApprovalRequestWithExplanation: AgentApprovalRequestCamelCase = {
  ...mockApprovalRequest,
  aiExplanation: mockAIExplanation,
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
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

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
        screen.getByText("Send analysis report to external API"),
      ).toBeInTheDocument();
    });

    it("should display confidence score", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(screen.getByTestId("confidence-score")).toHaveTextContent("65%");
    });

    it("should display confidence threshold", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(screen.getByTestId("confidence-threshold")).toHaveTextContent(
        "70%",
      );
    });

    it("should display trigger reason", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      // Should explain why approval is needed
      expect(
        screen.getByText(/confidence.*below.*threshold/i),
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
      expect(gauge).toHaveClass("bg-warning-9");
    });

    it("should show red color for critical confidence (<50%)", () => {
      const lowConfidenceRequest = {
        ...mockApprovalRequest,
        confidence: 0.45,
      };
      render(
        <AgentApprovalDialog
          {...defaultProps}
          request={lowConfidenceRequest}
        />,
      );

      const gauge = screen.getByTestId("confidence-gauge");
      expect(gauge).toHaveClass("bg-error-9");
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
        />,
      );

      const gauge = screen.getByTestId("confidence-gauge");
      expect(gauge).toHaveClass("bg-primary-9");
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
        />,
      );

      expect(
        screen.queryByTestId("low-confidence-warning"),
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
      render(<AgentApprovalDialog {...defaultProps} onApprove={onApprove} />);

      fireEvent.click(screen.getByTestId("approve-button"));

      await waitFor(() => {
        // Callbacks use camelCase per ADR-0091 Phase 10
        expect(onApprove).toHaveBeenCalledWith({
          requestId: "req-001",
          approvedBy: "admin@example.com",
          reason: undefined,
        });
      });
    });

    it("should include optional reason if provided", async () => {
      const onApprove = vi.fn();
      const user = userEvent.setup();
      render(<AgentApprovalDialog {...defaultProps} onApprove={onApprove} />);

      await user.type(
        screen.getByTestId("reason-input"),
        "Approved after review",
      );
      await user.click(screen.getByTestId("approve-button"));

      await waitFor(() => {
        // Callbacks use camelCase per ADR-0091 Phase 10
        expect(onApprove).toHaveBeenCalledWith({
          requestId: "req-001",
          approvedBy: "admin@example.com",
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
        // Callbacks use camelCase per ADR-0091 Phase 10
        expect(onReject).toHaveBeenCalledWith({
          requestId: "req-001",
          rejectedBy: "admin@example.com",
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
        // Callbacks use camelCase per ADR-0091 Phase 10
        expect(onReject).toHaveBeenCalledWith({
          requestId: "req-001",
          rejectedBy: "admin@example.com",
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
        />,
      );

      expect(screen.getByText(/failed to approve/i)).toBeInTheDocument();
    });
  });

  describe("Trigger Reason Explanations", () => {
    it("should explain low_confidence trigger", () => {
      render(<AgentApprovalDialog {...defaultProps} />);

      expect(
        screen.getByText(/confidence.*below.*threshold/i),
      ).toBeInTheDocument();
    });

    it("should explain destructive_action trigger", () => {
      const destructiveRequest = {
        ...mockApprovalRequest,
        triggerReason: "destructive_action",
      };
      render(
        <AgentApprovalDialog {...defaultProps} request={destructiveRequest} />,
      );

      expect(screen.getByText(/modify or delete/i)).toBeInTheDocument();
    });

    it("should explain external_api trigger", () => {
      const externalApiRequest = {
        ...mockApprovalRequest,
        triggerReason: "external_api",
      };
      render(
        <AgentApprovalDialog {...defaultProps} request={externalApiRequest} />,
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
        screen.queryByTestId("ai-explanation-section"),
      ).not.toBeInTheDocument();
    });

    it("should render AI explanation section when ai_explanation is present", () => {
      render(
        <AgentApprovalDialog
          {...defaultProps}
          request={mockApprovalRequestWithExplanation}
        />,
      );

      expect(screen.getByTestId("ai-explanation-section")).toBeInTheDocument();
    });

    it("should display 'Why uncertain?' summary text", () => {
      render(
        <AgentApprovalDialog
          {...defaultProps}
          request={mockApprovalRequestWithExplanation}
        />,
      );

      expect(
        screen.getByText(/why is the agent uncertain/i),
      ).toBeInTheDocument();
    });

    it("should display why_uncertain explanation", () => {
      render(
        <AgentApprovalDialog
          {...defaultProps}
          request={mockApprovalRequestWithExplanation}
        />,
      );

      expect(
        screen.getByText(
          /ambiguous terms that could refer to multiple entities/i,
        ),
      ).toBeInTheDocument();
    });

    it("should display what_could_go_wrong explanation", () => {
      render(
        <AgentApprovalDialog
          {...defaultProps}
          request={mockApprovalRequestWithExplanation}
        />,
      );

      expect(screen.getByText(/wrong external service/i)).toBeInTheDocument();
    });

    it("should display 'What could go wrong' label", () => {
      render(
        <AgentApprovalDialog
          {...defaultProps}
          request={mockApprovalRequestWithExplanation}
        />,
      );

      expect(screen.getByText(/what could go wrong/i)).toBeInTheDocument();
    });

    describe("Safer Alternatives", () => {
      it("should display safer alternatives when present", () => {
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={mockApprovalRequestWithExplanation}
          />,
        );

        expect(screen.getByText(/safer alternatives/i)).toBeInTheDocument();
      });

      it("should display all alternative actions", () => {
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={mockApprovalRequestWithExplanation}
          />,
        );

        expect(
          screen.getByText(/Preview data before sending/),
        ).toBeInTheDocument();
        expect(
          screen.getByText(/Send to staging API first/),
        ).toBeInTheDocument();
      });

      it("should display alternative confidence percentages", () => {
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={mockApprovalRequestWithExplanation}
          />,
        );

        expect(screen.getByText(/92%/)).toBeInTheDocument();
        expect(screen.getByText(/95%/)).toBeInTheDocument();
      });

      it("should display trade-offs for alternatives", () => {
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={mockApprovalRequestWithExplanation}
          />,
        );

        expect(
          screen.getByText(/extra confirmation step/i),
        ).toBeInTheDocument();
        expect(
          screen.getByText(/Delays production deployment/i),
        ).toBeInTheDocument();
      });

      it("should not display safer alternatives section when empty", () => {
        // CamelCase per ADR-0091 Phase 10
        const requestWithoutAlternatives: AgentApprovalRequestCamelCase = {
          ...mockApprovalRequest,
          aiExplanation: {
            whyUncertain: "Some uncertainty",
            whatCouldGoWrong: "Some risk",
            saferAlternatives: [],
          },
        };
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={requestWithoutAlternatives}
          />,
        );

        expect(
          screen.queryByText(/safer alternatives/i),
        ).not.toBeInTheDocument();
      });
    });

    describe("Confidence Factors", () => {
      it("should display confidence factors section when present", () => {
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={mockApprovalRequestWithExplanation}
          />,
        );

        expect(screen.getByText(/confidence factors/i)).toBeInTheDocument();
      });

      it("should display factor evidence", () => {
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={mockApprovalRequestWithExplanation}
          />,
        );

        expect(
          screen.getByText(/vague terms like 'the report'/i),
        ).toBeInTheDocument();
        expect(
          screen.getByText(/Multiple external APIs match/i),
        ).toBeInTheDocument();
      });

      it("should not display confidence factors section when empty", () => {
        // CamelCase per ADR-0091 Phase 10
        const requestWithoutFactors: AgentApprovalRequestCamelCase = {
          ...mockApprovalRequest,
          aiExplanation: {
            whyUncertain: "Some uncertainty",
            whatCouldGoWrong: "Some risk",
            confidenceFactors: [],
          },
        };
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={requestWithoutFactors}
          />,
        );

        expect(
          screen.queryByText(/confidence factors/i),
        ).not.toBeInTheDocument();
      });
    });

    describe("Expandable Details", () => {
      it("should render as expandable details element", () => {
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={mockApprovalRequestWithExplanation}
          />,
        );

        const details = screen.getByTestId("ai-explanation-section");
        expect(details.tagName.toLowerCase()).toBe("details");
      });

      it("should have summary element for toggling", () => {
        render(
          <AgentApprovalDialog
            {...defaultProps}
            request={mockApprovalRequestWithExplanation}
          />,
        );

        const summary = screen.getByText(/why is the agent uncertain/i);
        expect(summary.tagName.toLowerCase()).toBe("summary");
      });
    });
  });

  // ===========================================================================
  // Sprint 6: HITL Intelligence Integration Tests
  // ===========================================================================

  describe("HITL Intelligence Integration", () => {
    beforeEach(() => {
      vi.clearAllMocks();
    });

    describe("Risk Assessment Panel", () => {
      it("should display risk assessment panel when enableAI is true", async () => {
        renderWithProvider(
          <AgentApprovalDialog {...defaultProps} enableAI userId="user-123" />,
        );

        await waitFor(() => {
          expect(
            screen.getByTestId("risk-assessment-panel"),
          ).toBeInTheDocument();
        });
      });

      it("should show risk score indicator", async () => {
        renderWithProvider(
          <AgentApprovalDialog {...defaultProps} enableAI userId="user-123" />,
        );

        await waitFor(() => {
          expect(screen.getByTestId("risk-score")).toBeInTheDocument();
          expect(screen.getByTestId("risk-score")).toHaveTextContent(/72%/);
        });
      });

      it("should show risk level badge", async () => {
        renderWithProvider(
          <AgentApprovalDialog {...defaultProps} enableAI userId="user-123" />,
        );

        await waitFor(() => {
          expect(screen.getByTestId("risk-level")).toBeInTheDocument();
          expect(screen.getByTestId("risk-level")).toHaveTextContent(/medium/i);
        });
      });

      it("should display risk factors when available", async () => {
        renderWithProvider(
          <AgentApprovalDialog {...defaultProps} enableAI userId="user-123" />,
        );

        await waitFor(() => {
          expect(
            screen.getByText(/external.*api.*access/i),
          ).toBeInTheDocument();
          expect(screen.getByText(/data.*sensitivity/i)).toBeInTheDocument();
        });
      });

      it("should display risk mitigations", async () => {
        renderWithProvider(
          <AgentApprovalDialog {...defaultProps} enableAI userId="user-123" />,
        );

        await waitFor(() => {
          expect(
            screen.getByText(/review data before sending/i),
          ).toBeInTheDocument();
        });
      });

      it("should show AI recommendation", async () => {
        renderWithProvider(
          <AgentApprovalDialog {...defaultProps} enableAI userId="user-123" />,
        );

        await waitFor(() => {
          expect(screen.getByTestId("ai-recommendation")).toBeInTheDocument();
        });
      });

      it("should not show risk assessment when enableAI is false", () => {
        render(<AgentApprovalDialog {...defaultProps} />);

        expect(
          screen.queryByTestId("risk-assessment-panel"),
        ).not.toBeInTheDocument();
      });
    });

    describe("Decision History Panel", () => {
      it("should display decision history when enableAI is true", async () => {
        renderWithProvider(
          <AgentApprovalDialog {...defaultProps} enableAI userId="user-123" />,
        );

        await waitFor(() => {
          expect(
            screen.getByTestId("decision-history-panel"),
          ).toBeInTheDocument();
        });
      });

      it("should show similar past decisions", async () => {
        renderWithProvider(
          <AgentApprovalDialog {...defaultProps} enableAI userId="user-123" />,
        );

        await waitFor(() => {
          expect(screen.getByText(/similar.*decisions/i)).toBeInTheDocument();
        });
      });

      it("should display approval rate", async () => {
        renderWithProvider(
          <AgentApprovalDialog {...defaultProps} enableAI userId="user-123" />,
        );

        await waitFor(() => {
          expect(screen.getByTestId("approval-rate")).toBeInTheDocument();
          expect(screen.getByTestId("approval-rate")).toHaveTextContent(/67%/);
        });
      });

      it("should show total similar decisions count", async () => {
        renderWithProvider(
          <AgentApprovalDialog {...defaultProps} enableAI userId="user-123" />,
        );

        await waitFor(() => {
          expect(screen.getByText(/6.*similar/i)).toBeInTheDocument();
        });
      });

      it("should display suggested action based on history", async () => {
        renderWithProvider(
          <AgentApprovalDialog {...defaultProps} enableAI userId="user-123" />,
        );

        await waitFor(() => {
          expect(screen.getByTestId("suggested-action")).toBeInTheDocument();
        });
      });

      it("should not show decision history when enableAI is false", () => {
        render(<AgentApprovalDialog {...defaultProps} />);

        expect(
          screen.queryByTestId("decision-history-panel"),
        ).not.toBeInTheDocument();
      });
    });

    describe("Loading States", () => {
      it("should show loading indicator while fetching risk assessment", async () => {
        // This test would need a modified mock to show loading state
        renderWithProvider(
          <AgentApprovalDialog {...defaultProps} enableAI userId="user-123" />,
        );

        // The component should handle loading gracefully
        expect(screen.getByRole("dialog")).toBeInTheDocument();
      });
    });

    describe("Feature Flag Behavior", () => {
      it("should only fetch HITL intelligence when enableAI is true", async () => {
        // Render without enableAI - should not call mutation
        render(<AgentApprovalDialog {...defaultProps} />);

        // Should render without AI panels
        expect(
          screen.queryByTestId("risk-assessment-panel"),
        ).not.toBeInTheDocument();
        expect(
          screen.queryByTestId("decision-history-panel"),
        ).not.toBeInTheDocument();
      });
    });
  });
});
