/**
 * AlertDetailPanel Component Tests
 *
 * TDD tests for the alert detail view in Admin dashboard.
 *
 * Features:
 * - Alert metadata display
 * - AI recommendation display
 * - Remediation steps with approval buttons
 * - Risk assessment visualization
 * - Regenerate recommendation button
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";

import {
  AlertDetailPanel,
  type AlertDetailPanelProps,
} from "./AlertDetailPanel";
import alertReducer, { type Alert } from "../../store/slices/alertSlice";
import type { AIRecommendation, RemediationRequest } from "../../types/api";

// =============================================================================
// Test Data
// =============================================================================

const mockAlert: Alert = {
  alertId: "alert-001",
  name: "HighCPU",
  severity: "critical",
  state: "firing",
  message: "CPU usage above 90% for 5 minutes",
  labels: { service: "api-server", pod: "api-123", namespace: "production" },
  annotations: {
    summary: "High CPU usage detected",
    runbook_url: "https://runbooks.example.com/high-cpu",
  },
  startedAt: "2024-01-15T10:30:00Z",
  endedAt: null,
  fingerprint: "fp-001",
};

const mockRecommendation: AIRecommendation = {
  recommendationId: "rec-001",
  alertId: "alert-001",
  rootCauseAnalysis:
    "The API server is experiencing memory leak in the request handler, causing increased CPU usage due to garbage collection pressure.",
  remediationSteps: [
    {
      stepNumber: 1,
      action: "scale",
      description: "Scale up replicas to handle current load",
      command: "kubectl scale deployment api-server --replicas=5",
      requiresApproval: true,
      riskLevel: "low",
    },
    {
      stepNumber: 2,
      action: "restart",
      description: "Rolling restart to clear memory",
      command: "kubectl rollout restart deployment api-server",
      requiresApproval: true,
      riskLevel: "medium",
    },
  ],
  riskAssessment: {
    overallRisk: "medium",
    impactAnalysis:
      "Brief service interruption during restart, mitigated by scaling first",
    rollbackPlan: "kubectl rollout undo deployment api-server",
  },
  runbookReference: "https://runbooks.example.com/high-cpu",
  generatedAt: "2024-01-15T10:35:00Z",
  modelUsed: "claude-3-5-sonnet",
};

const mockPendingRemediation: RemediationRequest = {
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

// =============================================================================
// Test Helpers
// =============================================================================

const createTestStore = (selectedAlertId: string | null = null) =>
  configureStore({
    reducer: {
      alerts: alertReducer,
    },
    preloadedState: {
      alerts: {
        alerts: [mockAlert],
        selectedAlertId,
        pendingRemediations: [mockPendingRemediation],
        soundEnabled: true,
        lastCriticalAlertTime: null,
        filters: { severity: ["critical", "warning"], state: ["firing"] },
      },
    },
  });

const defaultProps: AlertDetailPanelProps = {
  alert: mockAlert,
  recommendation: mockRecommendation,
  pendingRemediations: [mockPendingRemediation],
  onApprove: vi.fn(),
  onReject: vi.fn(),
  onRegenerate: vi.fn(),
  onClose: vi.fn(),
};

const renderWithStore = (ui: ReactNode, store = createTestStore("alert-001")) =>
  render(<Provider store={store}>{ui}</Provider>);

// =============================================================================
// Tests
// =============================================================================

describe("AlertDetailPanel", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Alert Metadata", () => {
    it("should render alert name", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(screen.getByText("HighCPU")).toBeInTheDocument();
    });

    it("should render severity badge", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(screen.getByTestId("alert-severity")).toHaveTextContent(
        "critical",
      );
    });

    it("should render state badge", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(screen.getByTestId("alert-state")).toHaveTextContent(/firing/i);
    });

    it("should render alert message", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(
        screen.getByText("CPU usage above 90% for 5 minutes"),
      ).toBeInTheDocument();
    });

    it("should render labels", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(screen.getByText("api-server")).toBeInTheDocument();
      expect(screen.getByText("production")).toBeInTheDocument();
    });

    it("should render started time", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(screen.getByTestId("alert-started")).toBeInTheDocument();
    });

    it("should render close button", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(screen.getByTestId("close-detail-panel")).toBeInTheDocument();
    });

    it("should call onClose when close button clicked", () => {
      const onClose = vi.fn();
      renderWithStore(<AlertDetailPanel {...defaultProps} onClose={onClose} />);

      fireEvent.click(screen.getByTestId("close-detail-panel"));

      expect(onClose).toHaveBeenCalled();
    });
  });

  describe("AI Recommendation", () => {
    it("should render root cause analysis section", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(screen.getByText(/root cause/i)).toBeInTheDocument();
      expect(screen.getByText(/memory leak/i)).toBeInTheDocument();
    });

    it("should render remediation steps", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(
        screen.getByText("Scale up replicas to handle current load"),
      ).toBeInTheDocument();
      expect(
        screen.getByText("Rolling restart to clear memory"),
      ).toBeInTheDocument();
    });

    it("should render step numbers", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(screen.getByTestId("step-number-1")).toBeInTheDocument();
      expect(screen.getByTestId("step-number-2")).toBeInTheDocument();
    });

    it("should render step commands", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(
        screen.getByText(/kubectl scale deployment api-server/),
      ).toBeInTheDocument();
    });

    it("should render risk level for each step", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(screen.getByTestId("step-risk-1")).toHaveTextContent(/low/i);
      expect(screen.getByTestId("step-risk-2")).toHaveTextContent(/medium/i);
    });

    it("should render model info", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(screen.getByText(/claude-3-5-sonnet/i)).toBeInTheDocument();
    });

    it("should show loading state when no recommendation", () => {
      renderWithStore(
        <AlertDetailPanel
          {...defaultProps}
          recommendation={null}
          isLoadingRecommendation
        />,
      );

      expect(screen.getByTestId("recommendation-loading")).toBeInTheDocument();
    });

    it("should show empty state when recommendation failed", () => {
      renderWithStore(
        <AlertDetailPanel
          {...defaultProps}
          recommendation={null}
          recommendationError="Failed to generate recommendation"
        />,
      );

      expect(screen.getByText(/failed to generate/i)).toBeInTheDocument();
    });
  });

  describe("Risk Assessment", () => {
    it("should render overall risk level", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(screen.getByTestId("overall-risk")).toHaveTextContent(/medium/i);
    });

    it("should render impact analysis", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(
        screen.getByText(/brief service interruption/i),
      ).toBeInTheDocument();
    });

    it("should render rollback plan", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(screen.getByText(/kubectl rollout undo/i)).toBeInTheDocument();
    });

    it("should color risk badge based on level", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      const riskBadge = screen.getByTestId("overall-risk");
      expect(riskBadge).toHaveClass("bg-yellow-500");
    });
  });

  describe("Remediation Actions", () => {
    it("should render approve button for pending steps", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(screen.getByTestId("approve-step-1")).toBeInTheDocument();
    });

    it("should render reject button for pending steps", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(screen.getByTestId("reject-step-1")).toBeInTheDocument();
    });

    it("should call onApprove when approve button clicked", () => {
      const onApprove = vi.fn();
      renderWithStore(
        <AlertDetailPanel {...defaultProps} onApprove={onApprove} />,
      );

      fireEvent.click(screen.getByTestId("approve-step-1"));

      expect(onApprove).toHaveBeenCalledWith("rem-001");
    });

    it("should call onReject when reject button clicked", () => {
      const onReject = vi.fn();
      renderWithStore(
        <AlertDetailPanel {...defaultProps} onReject={onReject} />,
      );

      fireEvent.click(screen.getByTestId("reject-step-1"));

      expect(onReject).toHaveBeenCalledWith("rem-001");
    });

    it("should show approved status for approved steps", () => {
      const approvedRemediation: RemediationRequest = {
        ...mockPendingRemediation,
        status: "approved",
        approved_by: "admin@example.com",
        approved_at: "2024-01-15T10:40:00Z",
      };
      renderWithStore(
        <AlertDetailPanel
          {...defaultProps}
          pendingRemediations={[approvedRemediation]}
        />,
      );

      expect(screen.getByTestId("step-status-1")).toHaveTextContent(
        /approved/i,
      );
    });

    it("should show executing status for executing steps", () => {
      const executingRemediation: RemediationRequest = {
        ...mockPendingRemediation,
        status: "executing",
      };
      renderWithStore(
        <AlertDetailPanel
          {...defaultProps}
          pendingRemediations={[executingRemediation]}
        />,
      );

      expect(screen.getByTestId("step-status-1")).toHaveTextContent(
        /executing/i,
      );
    });
  });

  describe("Regenerate Recommendation", () => {
    it("should render regenerate button", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      expect(
        screen.getByTestId("regenerate-recommendation"),
      ).toBeInTheDocument();
    });

    it("should call onRegenerate when clicked", () => {
      const onRegenerate = vi.fn();
      renderWithStore(
        <AlertDetailPanel {...defaultProps} onRegenerate={onRegenerate} />,
      );

      fireEvent.click(screen.getByTestId("regenerate-recommendation"));

      expect(onRegenerate).toHaveBeenCalled();
    });

    it("should disable regenerate button when loading", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} isRegenerating />);

      expect(screen.getByTestId("regenerate-recommendation")).toBeDisabled();
    });
  });

  describe("Runbook Reference", () => {
    it("should render runbook link when available", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} />);

      const runbookLink = screen.getByTestId("runbook-link");
      expect(runbookLink).toHaveAttribute(
        "href",
        "https://runbooks.example.com/high-cpu",
      );
    });

    it("should not render runbook link when not available", () => {
      const noRunbookRecommendation = {
        ...mockRecommendation,
        runbookReference: null,
      };
      renderWithStore(
        <AlertDetailPanel
          {...defaultProps}
          recommendation={noRunbookRecommendation}
        />,
      );

      expect(screen.queryByTestId("runbook-link")).not.toBeInTheDocument();
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no alert selected", () => {
      renderWithStore(<AlertDetailPanel {...defaultProps} alert={null} />);

      expect(screen.getByText(/select an alert/i)).toBeInTheDocument();
    });
  });
});
