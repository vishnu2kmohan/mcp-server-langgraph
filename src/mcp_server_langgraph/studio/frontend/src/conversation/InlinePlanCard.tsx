/**
 * InlinePlanCard Component
 *
 * Displays execution plans inline in the chat stream with approval/rejection actions.
 * Part of the Claude Code-style Ctrl/Cmd+Shift+M mode toggle feature.
 *
 * Design System Compliance:
 * - Uses CVA for variant styling (risk, complexity, status)
 * - Uses Motion.dev for card hover and expand animations
 * - Implements useReducedMotion() for accessibility
 * - Uses semantic colors per STYLE.md
 *
 * @see Plan: Research-Plan-Implement UX with Ctrl/Cmd+Shift+M Mode Toggle
 */

import { useState, useCallback } from "react";
import { motion, AnimatePresence, useReducedMotion } from "motion/react";
import { useSessionTelemetry } from "../contexts/TelemetryContext";
import { cva, type VariantProps } from "class-variance-authority";
import {
  ClipboardList,
  CheckCircle2,
  XCircle,
  Settings2,
  Zap,
  AlertTriangle,
  Shield,
  ChevronDown,
  ChevronUp,
  Cpu,
  DollarSign,
  Brain,
  Gauge,
  MessageSquareText,
} from "lucide-react";
import { cn } from "@/utils/cn";
import { Button } from "@/components/UI";
import { PlanEditor, type ExecutionPlanView } from "@/components/PlanEditor";
import type {
  ExecutionPlan,
  RoutingDecision,
} from "@/store/slices/executionModeSlice";

// =============================================================================
// CVA Variants
// =============================================================================

/**
 * Card container variants based on risk level
 */
const planCardVariants = cva(
  ["rounded-lg border p-4 shadow-sm", "transition-colors duration-150"],
  {
    variants: {
      riskLevel: {
        low: "border-success-6 bg-success-2",
        medium: "border-warning-6 bg-warning-2",
        high: "border-error-6 bg-error-2",
      },
      status: {
        awaiting_approval: "",
        approved: "opacity-75",
        rejected: "opacity-50",
        executed: "opacity-75",
        expired: "opacity-50",
      },
    },
    defaultVariants: {
      riskLevel: "medium",
      status: "awaiting_approval",
    },
  },
);

/**
 * Badge variants for complexity and risk
 */
const badgeVariants = cva(
  "inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium",
  {
    variants: {
      type: {
        complexity: "",
        risk: "",
        status: "",
      },
      level: {
        simple: "bg-success-3 text-success-11",
        complicated: "bg-warning-3 text-warning-11",
        complex: "bg-error-3 text-error-11",
        low: "bg-success-3 text-success-11",
        medium: "bg-warning-3 text-warning-11",
        high: "bg-error-3 text-error-11",
        approved: "bg-success-3 text-success-11",
        rejected: "bg-error-3 text-error-11",
        awaiting_approval: "bg-primary-3 text-primary-11",
        executed: "bg-success-3 text-success-11",
        expired: "bg-neutral-3 text-neutral-11",
      },
    },
    defaultVariants: {
      type: "complexity",
      level: "medium",
    },
  },
);

// =============================================================================
// Motion Variants
// =============================================================================

const cardHoverVariants = {
  rest: { scale: 1, boxShadow: "0 1px 3px rgba(0,0,0,0.1)" },
  hover: { scale: 1.01, boxShadow: "0 4px 12px rgba(0,0,0,0.1)" },
};

const accordionVariants = {
  collapsed: { height: 0, opacity: 0 },
  expanded: {
    height: "auto",
    opacity: 1,
    transition: { type: "spring" as const, stiffness: 400, damping: 30 },
  },
};

// =============================================================================
// Types
// =============================================================================

export interface InlinePlanCardProps extends VariantProps<
  typeof planCardVariants
> {
  /** Execution plan data */
  plan: ExecutionPlan;
  /** Routing decision data (for debugging/observability) */
  routingDecision?: RoutingDecision | null;
  /** Callback when user approves the plan */
  onApprove: (planId: string) => void;
  /** Callback when user rejects the plan */
  onReject: (planId: string) => void;
  /** Callback when user edits the plan */
  onEdit?: (planId: string, updates: Partial<ExecutionPlan>) => void;
  /** Whether the card is in loading state */
  isLoading?: boolean;
  /** Override status (for displaying approved/rejected state) */
  status?: "awaiting_approval" | "approved" | "rejected";
  /** Additional class names */
  className?: string;
}

// =============================================================================
// Helper Functions
// =============================================================================

function capitalizeFirst(str: string): string {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

function getComplexityIcon(complexity: string) {
  switch (complexity) {
    case "simple":
      return Zap;
    case "complicated":
      return Settings2;
    case "complex":
      return Brain;
    default:
      return Settings2;
  }
}

function getRiskIcon(risk: string) {
  switch (risk) {
    case "low":
      return Shield;
    case "medium":
      return AlertTriangle;
    case "high":
      return AlertTriangle;
    default:
      return AlertTriangle;
  }
}

// =============================================================================
// Component
// =============================================================================

/**
 * InlinePlanCard - Displays execution plan inline in chat stream
 *
 * Features:
 * - Shows plan summary (complexity, risk, model, cost, tools)
 * - Expandable "Edit Plan" section
 * - Action buttons (Edit, Approve, Reject)
 * - Status display for approved/rejected plans
 */
export function InlinePlanCard({
  plan,
  routingDecision,
  onApprove,
  onReject,
  onEdit,
  isLoading = false,
  status: statusOverride,
  className,
}: InlinePlanCardProps) {
  const prefersReducedMotion = useReducedMotion();
  const [isExpanded, setIsExpanded] = useState(false);
  const telemetry = useSessionTelemetry();

  // Transform ExecutionPlan to ExecutionPlanView for PlanEditor
  const planView: ExecutionPlanView = {
    planId: plan.planId,
    sessionId: plan.sessionId,
    status:
      plan.status === "executed" || plan.status === "expired"
        ? "awaiting_approval"
        : plan.status,
    complexity: plan.complexity,
    riskLevel: plan.riskLevel,
    taskType: plan.taskType,
    executorModel: plan.executorModel,
    criticModel: plan.criticModel ?? "",
    estimatedCost: plan.estimatedCost.toString(),
    message: plan.message,
    toolsNeeded: plan.toolsNeeded,
    thinkingBudget: plan.thinkingBudget,
    critiqueRounds: plan.critiqueRounds,
    orchestrator: plan.suggestedOrchestrator,
  };

  // Handle plan configuration changes from PlanEditor
  const handlePlanSave = useCallback(
    (updates: Partial<ExecutionPlanView>) => {
      if (onEdit) {
        // Map PlanEditor fields back to ExecutionPlan fields
        const planUpdates: Partial<ExecutionPlan> = {};
        if (updates.orchestrator !== undefined) {
          planUpdates.suggestedOrchestrator =
            updates.orchestrator as ExecutionPlan["suggestedOrchestrator"];
        }
        if (updates.thinkingBudget !== undefined) {
          planUpdates.thinkingBudget =
            updates.thinkingBudget as ExecutionPlan["thinkingBudget"];
        }
        if (updates.critiqueRounds !== undefined) {
          planUpdates.critiqueRounds = updates.critiqueRounds;
        }
        onEdit(plan.planId, planUpdates);
      }
    },
    [onEdit, plan.planId],
  );

  // Use override status if provided, otherwise use plan status
  const displayStatus = statusOverride ?? plan.status;
  const isActionable = displayStatus === "awaiting_approval" && !isLoading;

  const handleApprove = useCallback(() => {
    // Track bypass approval telemetry
    telemetry.trackBypassApproval({
      planId: plan.planId,
      sessionId: plan.sessionId,
      approvalType: "user",
      riskLevel: plan.riskLevel,
      complexity: plan.complexity,
      toolsNeeded: plan.toolsNeeded,
    });

    onApprove(plan.planId);
  }, [onApprove, plan, telemetry]);

  const handleReject = useCallback(() => {
    // Track bypass rejection telemetry
    telemetry.trackBypassApproval({
      planId: plan.planId,
      sessionId: plan.sessionId,
      approvalType: "rejected",
      riskLevel: plan.riskLevel,
      complexity: plan.complexity,
      toolsNeeded: plan.toolsNeeded,
    });

    onReject(plan.planId);
  }, [onReject, plan, telemetry]);

  const handleToggleExpand = useCallback(() => {
    setIsExpanded((prev) => !prev);
  }, []);

  const ComplexityIcon = getComplexityIcon(plan.complexity);
  const RiskIcon = getRiskIcon(plan.riskLevel);

  return (
    <motion.div
      data-testid="inline-plan-card"
      className={cn(
        planCardVariants({
          riskLevel: plan.riskLevel,
          status: displayStatus,
        }),
        className,
      )}
      variants={prefersReducedMotion ? undefined : cardHoverVariants}
      initial="rest"
      whileHover={isLoading ? undefined : "hover"}
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3">
        <ClipboardList className="w-5 h-5 text-neutral-11" aria-hidden="true" />
        <h3 className="text-sm font-semibold text-neutral-12">
          Execution Plan
        </h3>
        {displayStatus !== "awaiting_approval" && (
          <span
            className={badgeVariants({
              type: "status",
              level: displayStatus,
            })}
          >
            {displayStatus === "approved" && (
              <CheckCircle2 className="w-3 h-3" aria-hidden="true" />
            )}
            {displayStatus === "rejected" && (
              <XCircle className="w-3 h-3" aria-hidden="true" />
            )}
            {capitalizeFirst(displayStatus.replace("_", " "))}
          </span>
        )}
      </div>

      {/* Badges Row */}
      <div className="flex flex-wrap gap-2 mb-3">
        <span
          className={badgeVariants({
            type: "complexity",
            level: plan.complexity,
          })}
          aria-label={`Complexity: ${plan.complexity}`}
        >
          <ComplexityIcon className="w-3 h-3" aria-hidden="true" />
          {capitalizeFirst(plan.complexity)}
        </span>
        <span
          className={badgeVariants({
            type: "risk",
            level: plan.riskLevel,
          })}
          aria-label={`Risk: ${plan.riskLevel}`}
        >
          <RiskIcon className="w-3 h-3" aria-hidden="true" />
          {capitalizeFirst(plan.riskLevel)} Risk
        </span>
      </div>

      {/* Plan Details Grid */}
      <div className="grid grid-cols-2 gap-2 text-xs mb-4">
        <div className="flex items-center gap-1.5 text-neutral-11">
          <Cpu className="w-3.5 h-3.5" aria-hidden="true" />
          <span className="font-medium">Model:</span>
          <span className="text-neutral-12">{plan.executorModel}</span>
        </div>
        <div className="flex items-center gap-1.5 text-neutral-11">
          <DollarSign className="w-3.5 h-3.5" aria-hidden="true" />
          <span className="font-medium">Est. Cost:</span>
          <span className="text-neutral-12">{plan.estimatedCost}</span>
        </div>
        <div className="flex items-center gap-1.5 text-neutral-11">
          <ClipboardList className="w-3.5 h-3.5" aria-hidden="true" />
          <span className="font-medium">Task:</span>
          <span className="text-neutral-12">{plan.taskType}</span>
        </div>
        <div className="flex items-center gap-1.5 text-neutral-11">
          <Brain className="w-3.5 h-3.5" aria-hidden="true" />
          <span className="font-medium">Thinking:</span>
          <span className="text-neutral-12">{plan.thinkingBudget}</span>
        </div>
      </div>

      {/* Tools List */}
      <div className="mb-4">
        <span className="text-xs font-medium text-neutral-11">Tools: </span>
        <span className="text-xs text-neutral-12">
          {plan.toolsNeeded.length > 0 ? plan.toolsNeeded.join(", ") : "None"}
        </span>
      </div>

      {/* Routing Decision (debugging/observability) */}
      {routingDecision && (
        <div className="mb-4 border-t border-neutral-6 pt-3">
          <div className="flex items-center gap-2 mb-2">
            <Gauge className="w-4 h-4 text-neutral-11" aria-hidden="true" />
            <span className="text-xs font-semibold text-neutral-11">
              Router Classification
            </span>
          </div>

          {/* Confidence Score */}
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xs text-neutral-11 w-20">Confidence:</span>
            <div className="flex-1 h-2 bg-neutral-4 rounded-full overflow-hidden">
              <div
                className={cn(
                  "h-full rounded-full transition-all",
                  routingDecision.confidence >= 0.8
                    ? "bg-success-9"
                    : routingDecision.confidence >= 0.5
                      ? "bg-warning-9"
                      : "bg-error-9",
                )}
                style={{ width: `${routingDecision.confidence * 100}%` }}
                aria-label={`Confidence: ${Math.round(routingDecision.confidence * 100)}%`}
              />
            </div>
            <span className="text-xs font-medium text-neutral-12 w-12 text-right">
              {Math.round(routingDecision.confidence * 100)}%
            </span>
          </div>

          {/* Orchestrator */}
          <div className="flex items-center gap-1.5 text-xs text-neutral-11 mb-2">
            <span className="font-medium">Orchestrator:</span>
            <span className="text-neutral-12 capitalize">
              {routingDecision.suggestedOrchestrator}
            </span>
          </div>

          {/* Routing Rationale */}
          {routingDecision.routingRationale && (
            <div className="mt-2">
              <div className="flex items-center gap-1.5 mb-1">
                <MessageSquareText
                  className="w-3.5 h-3.5 text-neutral-11"
                  aria-hidden="true"
                />
                <span className="text-xs font-medium text-neutral-11">
                  Rationale:
                </span>
              </div>
              <p className="text-xs text-neutral-12 bg-neutral-3 rounded px-2 py-1.5 italic">
                {routingDecision.routingRationale}
              </p>
            </div>
          )}
        </div>
      )}

      {/* Expandable Edit Section */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            data-testid="plan-editor-section"
            className="overflow-hidden mb-4"
            variants={prefersReducedMotion ? undefined : accordionVariants}
            initial="collapsed"
            animate="expanded"
            exit="collapsed"
          >
            <div className="border-t border-neutral-6 pt-4 mt-2">
              <PlanEditor
                plan={planView}
                onApprove={handleApprove}
                onReject={handleReject}
                onSave={handlePlanSave}
                readOnly={!isActionable}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Action Buttons */}
      {isActionable && (
        <div className="flex gap-2 pt-2 border-t border-neutral-6">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleToggleExpand}
            disabled={isLoading}
            aria-expanded={isExpanded}
            aria-label={isExpanded ? "Collapse edit section" : "Edit plan"}
          >
            {isExpanded ? (
              <ChevronUp className="w-4 h-4" aria-hidden="true" />
            ) : (
              <ChevronDown className="w-4 h-4" aria-hidden="true" />
            )}
            Edit Plan
          </Button>
          <Button
            variant="success"
            size="sm"
            onClick={handleApprove}
            disabled={isLoading}
            aria-label="Approve plan"
          >
            <CheckCircle2 className="w-4 h-4" aria-hidden="true" />
            Approve
          </Button>
          <Button
            variant="danger"
            size="sm"
            onClick={handleReject}
            disabled={isLoading}
            aria-label="Reject plan"
          >
            <XCircle className="w-4 h-4" aria-hidden="true" />
            Reject
          </Button>
        </div>
      )}
    </motion.div>
  );
}

InlinePlanCard.displayName = "InlinePlanCard";
