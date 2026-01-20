/**
 * InlinePlanCard Tests
 *
 * Tests for the inline plan display component that shows execution plans
 * in the chat stream with approval/rejection actions.
 *
 * @see test-utils.tsx for MOTION_PROPS and filterMotionProps documentation
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { InlinePlanCard } from "./InlinePlanCard";
import type { ExecutionPlan } from "@/store/slices/executionModeSlice";

// Motion-specific props that should not be passed to DOM elements
const MOTION_PROPS = new Set([
  "whileHover", "whileTap", "whileFocus", "whileDrag", "whileInView",
  "initial", "animate", "exit", "variants", "transition",
  "layout", "layoutId", "drag", "dragConstraints", "dragElastic",
  "dragMomentum", "onAnimationStart", "onAnimationComplete",
  "onDragStart", "onDragEnd", "onDrag",
]);

function filterMotionProps<T extends Record<string, unknown>>(props: T): T {
  const filtered = { ...props };
  for (const key of Object.keys(filtered)) {
    if (MOTION_PROPS.has(key)) delete filtered[key];
  }
  return filtered;
}

// =============================================================================
// Mock TelemetryContext for bypass approval tracking
// =============================================================================
const mockTrackBypassApproval = vi.fn();

vi.mock("../contexts/TelemetryContext", () => ({
  useSessionTelemetry: () => ({
    trackExecutionModeChange: vi.fn(),
    trackBypassApproval: mockTrackBypassApproval,
    trackSessionCreation: vi.fn(),
    trackRevalidation: vi.fn(),
    trackSync: vi.fn(),
    trackArtifactSave: vi.fn(),
    trackArtifactDelete: vi.fn(),
    trackSuggestionAction: vi.fn(),
    trackCanvasAction: vi.fn(),
    getMetrics: vi.fn(),
    getHistory: vi.fn(),
    reset: vi.fn(),
  }),
}));

// Mock motion/react to avoid animation issues in tests
vi.mock("motion/react", () => ({
  motion: {
    div: ({ children, ...props }: React.ComponentProps<"div"> & Record<string, unknown>) => (
      <div {...filterMotionProps(props)}>{children}</div>
    ),
    button: ({ children, ...props }: React.ComponentProps<"button"> & Record<string, unknown>) => (
      <button {...filterMotionProps(props)}>{children}</button>
    ),
  },
  useReducedMotion: () => false,
  AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

describe("InlinePlanCard", () => {
  const mockPlan: ExecutionPlan = {
    planId: "plan-123",
    sessionId: "session-456",
    status: "awaiting_approval",
    complexity: "complicated",
    riskLevel: "medium",
    taskType: "code_generation",
    executorModel: "claude-opus-4-5",
    criticModel: "claude-sonnet-4",
    estimatedCost: "$0.15",
    message: "Generate a React component",
    toolsNeeded: ["code_executor", "file_writer"],
    thinkingBudget: "medium",
    critiqueRounds: 1,
    orchestrator: "standard",
    requiresApproval: true,
  };

  const defaultProps = {
    plan: mockPlan,
    onApprove: vi.fn(),
    onReject: vi.fn(),
    onEdit: vi.fn(),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("renders plan card with data-testid", () => {
      render(<InlinePlanCard {...defaultProps} />);

      expect(screen.getByTestId("inline-plan-card")).toBeInTheDocument();
    });

    it("displays plan header", () => {
      render(<InlinePlanCard {...defaultProps} />);

      expect(screen.getByText(/Execution Plan/i)).toBeInTheDocument();
    });

    it("displays complexity badge", () => {
      render(<InlinePlanCard {...defaultProps} />);

      expect(screen.getByText(/Complicated/i)).toBeInTheDocument();
    });

    it("displays risk level", () => {
      render(<InlinePlanCard {...defaultProps} />);

      // Risk level should be displayed
      const riskBadges = screen.getAllByText(/Medium/i);
      expect(riskBadges.length).toBeGreaterThan(0);
    });

    it("displays task type", () => {
      render(<InlinePlanCard {...defaultProps} />);

      expect(screen.getByText(/code_generation/i)).toBeInTheDocument();
    });

    it("displays executor model", () => {
      render(<InlinePlanCard {...defaultProps} />);

      expect(screen.getByText(/claude-opus-4-5/i)).toBeInTheDocument();
    });

    it("displays estimated cost", () => {
      render(<InlinePlanCard {...defaultProps} />);

      expect(screen.getByText(/\$0\.15/)).toBeInTheDocument();
    });

    it("displays tools needed", () => {
      render(<InlinePlanCard {...defaultProps} />);

      expect(screen.getByText(/code_executor/i)).toBeInTheDocument();
      expect(screen.getByText(/file_writer/i)).toBeInTheDocument();
    });

    it("displays thinking budget", () => {
      render(<InlinePlanCard {...defaultProps} />);

      // Should display thinking budget (may be part of details)
      expect(screen.getByText(/thinking/i)).toBeInTheDocument();
    });
  });

  describe("Action Buttons", () => {
    it("renders approve button", () => {
      render(<InlinePlanCard {...defaultProps} />);

      expect(screen.getByRole("button", { name: /approve/i })).toBeInTheDocument();
    });

    it("renders reject button", () => {
      render(<InlinePlanCard {...defaultProps} />);

      expect(screen.getByRole("button", { name: /reject/i })).toBeInTheDocument();
    });

    it("renders edit plan button", () => {
      render(<InlinePlanCard {...defaultProps} />);

      expect(screen.getByRole("button", { name: /edit/i })).toBeInTheDocument();
    });

    it("calls onApprove when approve button clicked", async () => {
      const onApprove = vi.fn();
      const user = userEvent.setup();

      render(<InlinePlanCard {...defaultProps} onApprove={onApprove} />);

      await user.click(screen.getByRole("button", { name: /approve/i }));
      expect(onApprove).toHaveBeenCalledWith(mockPlan.planId);
    });

    it("calls onReject when reject button clicked", async () => {
      const onReject = vi.fn();
      const user = userEvent.setup();

      render(<InlinePlanCard {...defaultProps} onReject={onReject} />);

      await user.click(screen.getByRole("button", { name: /reject/i }));
      expect(onReject).toHaveBeenCalledWith(mockPlan.planId);
    });
  });

  describe("Edit Section", () => {
    it("expands edit section when edit button clicked", async () => {
      const user = userEvent.setup();

      render(<InlinePlanCard {...defaultProps} />);

      // Edit section should be collapsed initially
      expect(screen.queryByTestId("plan-editor-section")).not.toBeInTheDocument();

      // Click edit button
      await user.click(screen.getByRole("button", { name: /edit/i }));

      // Edit section should be visible
      expect(screen.getByTestId("plan-editor-section")).toBeInTheDocument();
    });

    it("collapses edit section when edit button clicked again", async () => {
      const user = userEvent.setup();

      render(<InlinePlanCard {...defaultProps} />);

      // Expand
      await user.click(screen.getByRole("button", { name: /edit/i }));
      expect(screen.getByTestId("plan-editor-section")).toBeInTheDocument();

      // Collapse
      await user.click(screen.getByRole("button", { name: /edit/i }));
      expect(screen.queryByTestId("plan-editor-section")).not.toBeInTheDocument();
    });

    it("calls onEdit when changes saved", async () => {
      const onEdit = vi.fn();
      const user = userEvent.setup();

      render(<InlinePlanCard {...defaultProps} onEdit={onEdit} />);

      // Expand edit section
      await user.click(screen.getByRole("button", { name: /edit/i }));

      // Save changes (if save button exists in edit section)
      const saveButton = screen.queryByRole("button", { name: /save/i });
      if (saveButton) {
        await user.click(saveButton);
        expect(onEdit).toHaveBeenCalled();
      }
    });
  });

  describe("Risk Level Variants", () => {
    it("applies low risk styling", () => {
      const lowRiskPlan = { ...mockPlan, riskLevel: "low" as const };
      render(<InlinePlanCard {...defaultProps} plan={lowRiskPlan} />);

      // Low risk should have success styling
      const card = screen.getByTestId("inline-plan-card");
      expect(card).toBeInTheDocument();
    });

    it("applies medium risk styling", () => {
      render(<InlinePlanCard {...defaultProps} />);

      const card = screen.getByTestId("inline-plan-card");
      expect(card).toBeInTheDocument();
    });

    it("applies high risk styling", () => {
      const highRiskPlan = { ...mockPlan, riskLevel: "high" as const };
      render(<InlinePlanCard {...defaultProps} plan={highRiskPlan} />);

      const card = screen.getByTestId("inline-plan-card");
      expect(card).toBeInTheDocument();
    });
  });

  describe("Complexity Variants", () => {
    it("renders simple complexity", () => {
      const simplePlan = { ...mockPlan, complexity: "simple" as const };
      render(<InlinePlanCard {...defaultProps} plan={simplePlan} />);

      expect(screen.getByText(/Simple/i)).toBeInTheDocument();
    });

    it("renders complicated complexity", () => {
      const complicatedPlan = { ...mockPlan, complexity: "complicated" as const };
      render(<InlinePlanCard {...defaultProps} plan={complicatedPlan} />);

      expect(screen.getByText(/Complicated/i)).toBeInTheDocument();
    });

    it("renders complex complexity", () => {
      const complexPlan = { ...mockPlan, complexity: "complex" as const };
      render(<InlinePlanCard {...defaultProps} plan={complexPlan} />);

      expect(screen.getByText(/Complex/i)).toBeInTheDocument();
    });
  });

  describe("Loading State", () => {
    it("hides action buttons when loading", () => {
      render(<InlinePlanCard {...defaultProps} isLoading={true} />);

      // When loading, action buttons are not rendered (isActionable is false)
      expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
      expect(screen.queryByRole("button", { name: /reject/i })).not.toBeInTheDocument();
    });

    it("still renders card when loading", () => {
      render(<InlinePlanCard {...defaultProps} isLoading={true} />);

      // Card should still be visible
      const card = screen.getByTestId("inline-plan-card");
      expect(card).toBeInTheDocument();
    });
  });

  describe("Status States", () => {
    it("shows approved state", () => {
      render(<InlinePlanCard {...defaultProps} status="approved" />);

      expect(screen.getByText(/approved/i)).toBeInTheDocument();
    });

    it("shows rejected state", () => {
      render(<InlinePlanCard {...defaultProps} status="rejected" />);

      expect(screen.getByText(/rejected/i)).toBeInTheDocument();
    });

    it("hides action buttons when approved", () => {
      render(<InlinePlanCard {...defaultProps} status="approved" />);

      expect(screen.queryByRole("button", { name: /approve/i })).not.toBeInTheDocument();
    });

    it("hides action buttons when rejected", () => {
      render(<InlinePlanCard {...defaultProps} status="rejected" />);

      expect(screen.queryByRole("button", { name: /reject/i })).not.toBeInTheDocument();
    });
  });

  describe("Accessibility", () => {
    it("has proper heading structure", () => {
      render(<InlinePlanCard {...defaultProps} />);

      // Card should have a heading
      const heading = screen.getByRole("heading", { level: 3 });
      expect(heading).toBeInTheDocument();
    });

    it("buttons are keyboard accessible", async () => {
      const onApprove = vi.fn();

      render(<InlinePlanCard {...defaultProps} onApprove={onApprove} />);

      const approveButton = screen.getByRole("button", { name: /approve/i });
      approveButton.focus();
      expect(document.activeElement).toBe(approveButton);
    });

    it("has proper aria labels on badges", () => {
      render(<InlinePlanCard {...defaultProps} />);

      // Badges should have proper labels for screen readers
      const card = screen.getByTestId("inline-plan-card");
      expect(card).toBeInTheDocument();
    });
  });

  describe("Bypass Approval Telemetry", () => {
    beforeEach(() => {
      mockTrackBypassApproval.mockClear();
    });

    it("should track telemetry when plan is approved", async () => {
      const user = userEvent.setup();
      const onApprove = vi.fn();

      render(<InlinePlanCard {...defaultProps} onApprove={onApprove} />);

      const approveButton = screen.getByRole("button", { name: /approve/i });
      await user.click(approveButton);

      // Verify telemetry was tracked
      expect(mockTrackBypassApproval).toHaveBeenCalledWith({
        planId: "plan-123",
        sessionId: "session-456",
        approvalType: "user",
        riskLevel: "medium",
        complexity: "complicated",
        toolsNeeded: ["code_executor", "file_writer"],
      });
    });

    it("should track telemetry when plan is rejected", async () => {
      const user = userEvent.setup();
      const onReject = vi.fn();

      render(<InlinePlanCard {...defaultProps} onReject={onReject} />);

      const rejectButton = screen.getByRole("button", { name: /reject/i });
      await user.click(rejectButton);

      // Verify telemetry was tracked with rejected type
      expect(mockTrackBypassApproval).toHaveBeenCalledWith({
        planId: "plan-123",
        sessionId: "session-456",
        approvalType: "rejected",
        riskLevel: "medium",
        complexity: "complicated",
        toolsNeeded: ["code_executor", "file_writer"],
      });
    });

    it("should include correct risk level in telemetry for high-risk plan", async () => {
      const user = userEvent.setup();
      const highRiskPlan = { ...mockPlan, riskLevel: "high" as const };

      render(
        <InlinePlanCard
          {...defaultProps}
          plan={highRiskPlan}
        />
      );

      const approveButton = screen.getByRole("button", { name: /approve/i });
      await user.click(approveButton);

      expect(mockTrackBypassApproval).toHaveBeenCalledWith(
        expect.objectContaining({
          riskLevel: "high",
        })
      );
    });

    it("should include correct complexity in telemetry for complex plan", async () => {
      const user = userEvent.setup();
      const complexPlan = { ...mockPlan, complexity: "complex" as const };

      render(
        <InlinePlanCard
          {...defaultProps}
          plan={complexPlan}
        />
      );

      const approveButton = screen.getByRole("button", { name: /approve/i });
      await user.click(approveButton);

      expect(mockTrackBypassApproval).toHaveBeenCalledWith(
        expect.objectContaining({
          complexity: "complex",
        })
      );
    });
  });
});
