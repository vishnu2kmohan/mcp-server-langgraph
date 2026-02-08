/**
 * AIRecommendationCard Component Tests
 *
 * TDD tests for the AI recommendation display card.
 *
 * Features:
 * - Root cause analysis display
 * - Remediation steps list
 * - Risk assessment badge
 * - Regenerate button
 * - Cache freshness indicator
 * - Runbook link
 *
 * Reference: ADR-0026 - Comprehensive Client Resilience Patterns
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, fireEvent, cleanup } from "@testing-library/react";

import {
  AIRecommendationCard,
  type AIRecommendationCardProps,
} from "./AIRecommendationCard";
import type { AIRecommendation } from "../../types/api";

import { TestProvider } from "@/test-utils";

// =============================================================================
// Test Data
// =============================================================================

const mockRecommendation: AIRecommendation = {
  recommendationId: "rec-001",
  alertId: "alert-001",
  rootCauseAnalysis:
    "The API server is experiencing a memory leak in the request handler, causing increased CPU usage due to garbage collection pressure.",
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
    {
      stepNumber: 3,
      action: "investigate",
      description: "Profile memory usage for root cause",
      command: null,
      requiresApproval: false,
      riskLevel: "low",
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

const defaultProps: AIRecommendationCardProps = {
  recommendation: mockRecommendation,
  onRegenerate: vi.fn(),
};

// =============================================================================
// Tests
// =============================================================================

describe("AIRecommendationCard", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Basic Rendering", () => {
    it("should render the card", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("ai-recommendation-card")).toBeInTheDocument();
    });

    it("should render recommendation title", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/ai recommendation/i)).toBeInTheDocument();
    });

    it("should render model info", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/claude-3-5-sonnet/i)).toBeInTheDocument();
    });
  });

  describe("Root Cause Analysis", () => {
    it("should render root cause section header", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      // Use getByRole for the header to avoid matching step description
      expect(screen.getByText("Root Cause Analysis")).toBeInTheDocument();
    });

    it("should display root cause analysis text", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/memory leak/i)).toBeInTheDocument();
    });
  });

  describe("Remediation Steps", () => {
    it("should render remediation steps section", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/remediation steps/i)).toBeInTheDocument();
    });

    it("should render all steps", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("step-1")).toBeInTheDocument();
      expect(screen.getByTestId("step-2")).toBeInTheDocument();
      expect(screen.getByTestId("step-3")).toBeInTheDocument();
    });

    it("should display step descriptions", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByText("Scale up replicas to handle current load"),
      ).toBeInTheDocument();
      expect(
        screen.getByText("Rolling restart to clear memory"),
      ).toBeInTheDocument();
    });

    it("should display step commands", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByText(/kubectl scale deployment api-server/),
      ).toBeInTheDocument();
    });

    it("should show 'No command' for steps without commands", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/manual step/i)).toBeInTheDocument();
    });

    it("should show requires approval indicator", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      // Steps 1 and 2 require approval
      const approvalIndicators = screen.getAllByTestId(/requires-approval/);
      expect(approvalIndicators.length).toBe(2);
    });

    it("should display risk level for each step", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("step-1-risk")).toHaveTextContent(/low/i);
      expect(screen.getByTestId("step-2-risk")).toHaveTextContent(/medium/i);
    });
  });

  describe("Risk Assessment", () => {
    it("should render risk assessment section", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/risk assessment/i)).toBeInTheDocument();
    });

    it("should display overall risk level", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("overall-risk-badge")).toHaveTextContent(
        /medium/i,
      );
    });

    it("should style risk badge based on level", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("overall-risk-badge")).toHaveClass(
        "bg-warning-9",
      );
    });

    it("should display impact analysis", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(
        screen.getByText(/brief service interruption/i),
      ).toBeInTheDocument();
    });

    it("should display rollback plan", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByText(/kubectl rollout undo/i)).toBeInTheDocument();
    });

    it("should style high risk badge red", () => {
      const highRiskRecommendation = {
        ...mockRecommendation,
        riskAssessment: {
          ...mockRecommendation.riskAssessment,
          overallRisk: "high" as const,
        },
      };
      render(
        <TestProvider>
          <AIRecommendationCard
            {...defaultProps}
            recommendation={highRiskRecommendation}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("overall-risk-badge")).toHaveClass(
        "bg-error-9",
      );
    });

    it("should style low risk badge green", () => {
      const lowRiskRecommendation = {
        ...mockRecommendation,
        riskAssessment: {
          ...mockRecommendation.riskAssessment,
          overallRisk: "low" as const,
        },
      };
      render(
        <TestProvider>
          <AIRecommendationCard
            {...defaultProps}
            recommendation={lowRiskRecommendation}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("overall-risk-badge")).toHaveClass(
        "bg-success-9",
      );
    });
  });

  describe("Regenerate Button", () => {
    it("should render regenerate button", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("regenerate-button")).toBeInTheDocument();
    });

    it("should call onRegenerate when clicked", () => {
      const onRegenerate = vi.fn();
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} onRegenerate={onRegenerate} />
        </TestProvider>,
      );

      fireEvent.click(screen.getByTestId("regenerate-button"));

      expect(onRegenerate).toHaveBeenCalled();
    });

    it("should disable button when regenerating", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} isRegenerating />
        </TestProvider>,
      );

      expect(screen.getByTestId("regenerate-button")).toBeDisabled();
    });

    it("should show loading state when regenerating", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} isRegenerating />
        </TestProvider>,
      );

      expect(screen.getByTestId("regenerate-loading")).toBeInTheDocument();
    });
  });

  describe("Cache Freshness", () => {
    it("should display generation time", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("generated-at")).toBeInTheDocument();
    });

    it("should show stale indicator for old recommendations", () => {
      // Create a recommendation that's more than 1 hour old
      const oldRecommendation = {
        ...mockRecommendation,
        generatedAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
      };
      render(
        <TestProvider>
          <AIRecommendationCard
            {...defaultProps}
            recommendation={oldRecommendation}
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("stale-indicator")).toBeInTheDocument();
    });

    it("should not show stale indicator for fresh recommendations", () => {
      const freshRecommendation = {
        ...mockRecommendation,
        generatedAt: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 minutes ago
      };
      render(
        <TestProvider>
          <AIRecommendationCard
            {...defaultProps}
            recommendation={freshRecommendation}
          />
        </TestProvider>,
      );

      expect(screen.queryByTestId("stale-indicator")).not.toBeInTheDocument();
    });
  });

  describe("Runbook Link", () => {
    it("should render runbook link when available", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("runbook-link")).toBeInTheDocument();
    });

    it("should have correct href", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("runbook-link")).toHaveAttribute(
        "href",
        "https://runbooks.example.com/high-cpu",
      );
    });

    it("should open in new tab", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} />
        </TestProvider>,
      );

      expect(screen.getByTestId("runbook-link")).toHaveAttribute(
        "target",
        "_blank",
      );
    });

    it("should not render runbook link when not available", () => {
      const noRunbookRecommendation = {
        ...mockRecommendation,
        runbookReference: null,
      };
      render(
        <TestProvider>
          <AIRecommendationCard
            {...defaultProps}
            recommendation={noRunbookRecommendation}
          />
        </TestProvider>,
      );

      expect(screen.queryByTestId("runbook-link")).not.toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading skeleton when loading", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} isLoading />
        </TestProvider>,
      );

      expect(screen.getByTestId("recommendation-skeleton")).toBeInTheDocument();
    });

    it("should not show content when loading", () => {
      render(
        <TestProvider>
          <AIRecommendationCard {...defaultProps} isLoading />
        </TestProvider>,
      );

      expect(screen.queryByText(/root cause/i)).not.toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("should show error message when error provided", () => {
      render(
        <TestProvider>
          <AIRecommendationCard
            {...defaultProps}
            recommendation={null}
            error="Failed to generate recommendation"
          />
        </TestProvider>,
      );

      expect(screen.getByText(/failed to generate/i)).toBeInTheDocument();
    });

    it("should show retry button on error", () => {
      render(
        <TestProvider>
          <AIRecommendationCard
            {...defaultProps}
            recommendation={null}
            error="Failed to generate recommendation"
          />
        </TestProvider>,
      );

      expect(screen.getByTestId("retry-button")).toBeInTheDocument();
    });

    it("should call onRegenerate when retry clicked", () => {
      const onRegenerate = vi.fn();
      render(
        <TestProvider>
          <AIRecommendationCard
            {...defaultProps}
            recommendation={null}
            error="Failed to generate recommendation"
            onRegenerate={onRegenerate}
          />
        </TestProvider>,
      );

      fireEvent.click(screen.getByTestId("retry-button"));

      expect(onRegenerate).toHaveBeenCalled();
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no recommendation and no error", () => {
      render(
        <TestProvider>
          <AIRecommendationCard
            {...defaultProps}
            recommendation={null}
            isLoading={false}
          />
        </TestProvider>,
      );

      expect(screen.getByText(/no recommendation/i)).toBeInTheDocument();
    });
  });
});
