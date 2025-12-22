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

import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";

import {
  AIRecommendationCard,
  type AIRecommendationCardProps,
} from "./AIRecommendationCard";
import type { AIRecommendation } from "../../types/api";

// =============================================================================
// Test Data
// =============================================================================

const mockRecommendation: AIRecommendation = {
  recommendation_id: "rec-001",
  alert_id: "alert-001",
  root_cause_analysis:
    "The API server is experiencing a memory leak in the request handler, causing increased CPU usage due to garbage collection pressure.",
  remediation_steps: [
    {
      step_number: 1,
      action: "scale",
      description: "Scale up replicas to handle current load",
      command: "kubectl scale deployment api-server --replicas=5",
      requires_approval: true,
      risk_level: "low",
    },
    {
      step_number: 2,
      action: "restart",
      description: "Rolling restart to clear memory",
      command: "kubectl rollout restart deployment api-server",
      requires_approval: true,
      risk_level: "medium",
    },
    {
      step_number: 3,
      action: "investigate",
      description: "Profile memory usage for root cause",
      command: null,
      requires_approval: false,
      risk_level: "low",
    },
  ],
  risk_assessment: {
    overall_risk: "medium",
    impact_analysis:
      "Brief service interruption during restart, mitigated by scaling first",
    rollback_plan: "kubectl rollout undo deployment api-server",
  },
  runbook_reference: "https://runbooks.example.com/high-cpu",
  generated_at: "2024-01-15T10:35:00Z",
  model_used: "claude-3-5-sonnet",
};

const defaultProps: AIRecommendationCardProps = {
  recommendation: mockRecommendation,
  onRegenerate: vi.fn(),
};

// =============================================================================
// Tests
// =============================================================================

describe("AIRecommendationCard", () => {
  describe("Basic Rendering", () => {
    it("should render the card", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(screen.getByTestId("ai-recommendation-card")).toBeInTheDocument();
    });

    it("should render recommendation title", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(screen.getByText(/ai recommendation/i)).toBeInTheDocument();
    });

    it("should render model info", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(screen.getByText(/claude-3-5-sonnet/i)).toBeInTheDocument();
    });
  });

  describe("Root Cause Analysis", () => {
    it("should render root cause section header", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      // Use getByRole for the header to avoid matching step description
      expect(screen.getByText("Root Cause Analysis")).toBeInTheDocument();
    });

    it("should display root cause analysis text", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(screen.getByText(/memory leak/i)).toBeInTheDocument();
    });
  });

  describe("Remediation Steps", () => {
    it("should render remediation steps section", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(screen.getByText(/remediation steps/i)).toBeInTheDocument();
    });

    it("should render all steps", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(screen.getByTestId("step-1")).toBeInTheDocument();
      expect(screen.getByTestId("step-2")).toBeInTheDocument();
      expect(screen.getByTestId("step-3")).toBeInTheDocument();
    });

    it("should display step descriptions", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(
        screen.getByText("Scale up replicas to handle current load")
      ).toBeInTheDocument();
      expect(
        screen.getByText("Rolling restart to clear memory")
      ).toBeInTheDocument();
    });

    it("should display step commands", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(
        screen.getByText(/kubectl scale deployment api-server/)
      ).toBeInTheDocument();
    });

    it("should show 'No command' for steps without commands", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(screen.getByText(/manual step/i)).toBeInTheDocument();
    });

    it("should show requires approval indicator", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      // Steps 1 and 2 require approval
      const approvalIndicators = screen.getAllByTestId(/requires-approval/);
      expect(approvalIndicators.length).toBe(2);
    });

    it("should display risk level for each step", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(screen.getByTestId("step-1-risk")).toHaveTextContent(/low/i);
      expect(screen.getByTestId("step-2-risk")).toHaveTextContent(/medium/i);
    });
  });

  describe("Risk Assessment", () => {
    it("should render risk assessment section", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(screen.getByText(/risk assessment/i)).toBeInTheDocument();
    });

    it("should display overall risk level", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(screen.getByTestId("overall-risk-badge")).toHaveTextContent(
        /medium/i
      );
    });

    it("should style risk badge based on level", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(screen.getByTestId("overall-risk-badge")).toHaveClass(
        "bg-yellow-500"
      );
    });

    it("should display impact analysis", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(
        screen.getByText(/brief service interruption/i)
      ).toBeInTheDocument();
    });

    it("should display rollback plan", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(screen.getByText(/kubectl rollout undo/i)).toBeInTheDocument();
    });

    it("should style high risk badge red", () => {
      const highRiskRecommendation = {
        ...mockRecommendation,
        risk_assessment: {
          ...mockRecommendation.risk_assessment,
          overall_risk: "high" as const,
        },
      };
      render(
        <AIRecommendationCard
          {...defaultProps}
          recommendation={highRiskRecommendation}
        />
      );

      expect(screen.getByTestId("overall-risk-badge")).toHaveClass(
        "bg-red-500"
      );
    });

    it("should style low risk badge green", () => {
      const lowRiskRecommendation = {
        ...mockRecommendation,
        risk_assessment: {
          ...mockRecommendation.risk_assessment,
          overall_risk: "low" as const,
        },
      };
      render(
        <AIRecommendationCard
          {...defaultProps}
          recommendation={lowRiskRecommendation}
        />
      );

      expect(screen.getByTestId("overall-risk-badge")).toHaveClass(
        "bg-green-500"
      );
    });
  });

  describe("Regenerate Button", () => {
    it("should render regenerate button", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(screen.getByTestId("regenerate-button")).toBeInTheDocument();
    });

    it("should call onRegenerate when clicked", () => {
      const onRegenerate = vi.fn();
      render(
        <AIRecommendationCard {...defaultProps} onRegenerate={onRegenerate} />
      );

      fireEvent.click(screen.getByTestId("regenerate-button"));

      expect(onRegenerate).toHaveBeenCalled();
    });

    it("should disable button when regenerating", () => {
      render(<AIRecommendationCard {...defaultProps} isRegenerating />);

      expect(screen.getByTestId("regenerate-button")).toBeDisabled();
    });

    it("should show loading state when regenerating", () => {
      render(<AIRecommendationCard {...defaultProps} isRegenerating />);

      expect(screen.getByTestId("regenerate-loading")).toBeInTheDocument();
    });
  });

  describe("Cache Freshness", () => {
    it("should display generation time", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(screen.getByTestId("generated-at")).toBeInTheDocument();
    });

    it("should show stale indicator for old recommendations", () => {
      // Create a recommendation that's more than 1 hour old
      const oldRecommendation = {
        ...mockRecommendation,
        generated_at: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
      };
      render(
        <AIRecommendationCard
          {...defaultProps}
          recommendation={oldRecommendation}
        />
      );

      expect(screen.getByTestId("stale-indicator")).toBeInTheDocument();
    });

    it("should not show stale indicator for fresh recommendations", () => {
      const freshRecommendation = {
        ...mockRecommendation,
        generated_at: new Date(Date.now() - 5 * 60 * 1000).toISOString(), // 5 minutes ago
      };
      render(
        <AIRecommendationCard
          {...defaultProps}
          recommendation={freshRecommendation}
        />
      );

      expect(screen.queryByTestId("stale-indicator")).not.toBeInTheDocument();
    });
  });

  describe("Runbook Link", () => {
    it("should render runbook link when available", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(screen.getByTestId("runbook-link")).toBeInTheDocument();
    });

    it("should have correct href", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(screen.getByTestId("runbook-link")).toHaveAttribute(
        "href",
        "https://runbooks.example.com/high-cpu"
      );
    });

    it("should open in new tab", () => {
      render(<AIRecommendationCard {...defaultProps} />);

      expect(screen.getByTestId("runbook-link")).toHaveAttribute(
        "target",
        "_blank"
      );
    });

    it("should not render runbook link when not available", () => {
      const noRunbookRecommendation = {
        ...mockRecommendation,
        runbook_reference: null,
      };
      render(
        <AIRecommendationCard
          {...defaultProps}
          recommendation={noRunbookRecommendation}
        />
      );

      expect(screen.queryByTestId("runbook-link")).not.toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("should show loading skeleton when loading", () => {
      render(<AIRecommendationCard {...defaultProps} isLoading />);

      expect(screen.getByTestId("recommendation-skeleton")).toBeInTheDocument();
    });

    it("should not show content when loading", () => {
      render(<AIRecommendationCard {...defaultProps} isLoading />);

      expect(screen.queryByText(/root cause/i)).not.toBeInTheDocument();
    });
  });

  describe("Error State", () => {
    it("should show error message when error provided", () => {
      render(
        <AIRecommendationCard
          {...defaultProps}
          recommendation={null}
          error="Failed to generate recommendation"
        />
      );

      expect(screen.getByText(/failed to generate/i)).toBeInTheDocument();
    });

    it("should show retry button on error", () => {
      render(
        <AIRecommendationCard
          {...defaultProps}
          recommendation={null}
          error="Failed to generate recommendation"
        />
      );

      expect(screen.getByTestId("retry-button")).toBeInTheDocument();
    });

    it("should call onRegenerate when retry clicked", () => {
      const onRegenerate = vi.fn();
      render(
        <AIRecommendationCard
          {...defaultProps}
          recommendation={null}
          error="Failed to generate recommendation"
          onRegenerate={onRegenerate}
        />
      );

      fireEvent.click(screen.getByTestId("retry-button"));

      expect(onRegenerate).toHaveBeenCalled();
    });
  });

  describe("Empty State", () => {
    it("should show empty state when no recommendation and no error", () => {
      render(
        <AIRecommendationCard
          {...defaultProps}
          recommendation={null}
          isLoading={false}
        />
      );

      expect(screen.getByText(/no recommendation/i)).toBeInTheDocument();
    });
  });
});
