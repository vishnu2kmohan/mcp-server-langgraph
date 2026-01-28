/**
 * executionModeSlice
 *
 * Redux slice for managing execution mode toggling and plan approval workflow.
 * Implements Claude Code-style Ctrl/Cmd+Shift+M mode cycling with OpenFGA permission.
 *
 * Execution Modes:
 * - default: Plans generated; approval for medium/high-risk tasks
 * - plan: Plans generated; ALL require user approval
 * - auto_accept: Plans generated but auto-approved (no modal)
 * - bypass: Plans generated but skip approvals (admin only, audited)
 *
 * Plan Approval Flow:
 * - Plans are always generated and persisted for audit trail
 * - Display inline in chat stream (not modal) for plan review
 * - User can approve, reject, or edit plan configuration
 */

import { createSlice, PayloadAction } from "@reduxjs/toolkit";

// =============================================================================
// Types
// =============================================================================

/**
 * Execution mode options
 */
export type ExecutionMode = "default" | "plan" | "auto_accept" | "bypass";

/**
 * Plan status during approval workflow
 */
export type PlanStatus = "idle" | "awaiting_approval" | "approved" | "rejected";

/**
 * Routing decision from SSE stream
 * Contains router agent classification factors for debugging/observability
 */
export interface RoutingDecision {
  /** Task complexity assessment */
  complexity: "simple" | "complicated" | "complex";
  /** Risk level assessment */
  risk: "low" | "medium" | "high";
  /** Type of task detected */
  taskType: string;
  /** Tools identified as needed */
  toolsNeeded: string[];
  /** Recommended orchestrator pattern */
  suggestedOrchestrator: string;
  /** Recommended critique rounds */
  critiqueRounds: number;
  /** Recommended thinking budget */
  thinkingBudget: string;
  /** Router confidence score (0-1) */
  confidence: number;
  /** Skills identified as needed */
  skillsNeeded: string[];
  /** Execution mode from router */
  executionMode: string;
  /** Explanation of routing decision */
  routingRationale: string;
}

/**
 * Execution plan data from SSE stream (27 fields)
 * Matches the plan_generated SSE event structure from plan_to_dict()
 */
export interface ExecutionPlan {
  // Core identification
  /** Unique plan identifier */
  planId: string;
  /** Session this plan belongs to */
  sessionId: string;
  /** Current plan status */
  status: "awaiting_approval" | "approved" | "rejected" | "executed" | "expired";

  // Classification
  /** Task complexity level */
  complexity: "simple" | "complicated" | "complex";
  /** Risk level assessment */
  riskLevel: "low" | "medium" | "high";
  /** Type of task */
  taskType: string;

  // Model configuration
  /** Model for execution */
  executorModel: string;
  /** Model for critique (nullable) */
  criticModel: string | null;

  // Cost tracking
  /** Estimated cost in USD */
  estimatedCost: string;
  /** Actual cost after execution (nullable) */
  actualCost: string | null;

  // Content
  /** Original user message */
  message: string;
  /** Tools required for execution */
  toolsNeeded: string[];

  // Approval configuration
  /** Whether approval is forced regardless of risk */
  forceApproval: boolean;
  /** Router confidence score (0-1) */
  confidence: number;

  // Orchestrator
  /** Suggested orchestrator pattern from router */
  suggestedOrchestrator: string;
  /** Orchestrator pattern (alias for suggestedOrchestrator) */
  orchestrator: string;

  // Computed property
  /** Whether this plan requires user approval */
  requiresApproval: boolean;

  // Thinking configuration
  /** Thinking budget level */
  thinkingBudget: string;
  /** Number of critique rounds */
  critiqueRounds: number;

  // Timestamps (ISO strings or null)
  /** When the plan was created */
  createdAt: string | null;
  /** When the plan expires */
  expiresAt: string | null;
  /** When the plan was executed */
  executedAt: string | null;

  // Approval/rejection tracking
  /** User who approved the plan */
  approvedBy: string | null;
  /** When the plan was approved */
  approvedAt: string | null;
  /** User who rejected the plan */
  rejectedBy: string | null;
  /** When the plan was rejected */
  rejectedAt: string | null;
  /** Reason for rejection */
  rejectionReason: string | null;
}

/**
 * Execution mode slice state
 */
export interface ExecutionModeState {
  /** Current execution mode */
  executionMode: ExecutionMode;
  /** Current plan awaiting action (if any) */
  currentPlan: ExecutionPlan | null;
  /** Current routing decision (for debugging/observability) */
  currentRoutingDecision: RoutingDecision | null;
  /** Current plan approval status */
  planStatus: PlanStatus;
  /** Whether current user has admin role (for bypass mode) - legacy, use hasBypassPermission */
  userIsAdmin: boolean;
  /** Whether current user has bypass_executor permission via OpenFGA (for bypass mode) */
  hasBypassPermission: boolean;
}

// =============================================================================
// Initial State
// =============================================================================

const initialState: ExecutionModeState = {
  executionMode: "default",
  currentPlan: null,
  currentRoutingDecision: null,
  planStatus: "idle",
  userIsAdmin: false,
  hasBypassPermission: false,
};

// =============================================================================
// Slice Definition
// =============================================================================

export const executionModeSlice = createSlice({
  name: "executionMode",
  initialState,
  reducers: {
    /**
     * Set execution mode directly
     * Bypass mode requires bypass permission (from OpenFGA) or admin role
     */
    setExecutionMode: (state, action: PayloadAction<ExecutionMode>) => {
      const newMode = action.payload;

      // Bypass mode requires bypass permission (OpenFGA) or admin role
      const canBypass = state.hasBypassPermission || state.userIsAdmin;
      if (newMode === "bypass" && !canBypass) {
        // Silently ignore - can't set bypass without permission
        return;
      }

      state.executionMode = newMode;
    },

    /**
     * Cycle through execution modes (Ctrl/Cmd+Shift+M)
     * Order: default → plan → auto_accept → [bypass if permitted] → default
     */
    cycleExecutionMode: (state) => {
      // Bypass mode available if user has OpenFGA permission or admin role
      const canBypass = state.hasBypassPermission || state.userIsAdmin;
      const modeOrder: ExecutionMode[] = canBypass
        ? ["default", "plan", "auto_accept", "bypass"]
        : ["default", "plan", "auto_accept"];

      const currentIndex = modeOrder.indexOf(state.executionMode);
      const nextIndex = (currentIndex + 1) % modeOrder.length;
      state.executionMode = modeOrder[nextIndex];
    },

    /**
     * Set current user's admin status (legacy - prefer setHasBypassPermission)
     * If admin is revoked while in bypass mode, reset to default
     */
    setUserIsAdmin: (state, action: PayloadAction<boolean>) => {
      state.userIsAdmin = action.payload;

      // Reset bypass mode if admin is revoked and no OpenFGA permission
      if (
        !action.payload &&
        !state.hasBypassPermission &&
        state.executionMode === "bypass"
      ) {
        state.executionMode = "default";
      }
    },

    /**
     * Set bypass permission from OpenFGA check (bypass_executor on system:global)
     * If permission is revoked while in bypass mode, reset to default
     */
    setHasBypassPermission: (state, action: PayloadAction<boolean>) => {
      state.hasBypassPermission = action.payload;

      // Reset bypass mode if permission is revoked and no admin role
      if (
        !action.payload &&
        !state.userIsAdmin &&
        state.executionMode === "bypass"
      ) {
        state.executionMode = "default";
      }
    },

    /**
     * Set current plan from SSE stream
     * Automatically sets planStatus to awaiting_approval
     */
    setPlan: (state, action: PayloadAction<ExecutionPlan>) => {
      state.currentPlan = action.payload;
      state.planStatus = "awaiting_approval";
    },

    /**
     * Set current routing decision from SSE stream
     * Used for debugging/observability of router classification
     */
    setRoutingDecision: (state, action: PayloadAction<RoutingDecision>) => {
      state.currentRoutingDecision = action.payload;
    },

    /**
     * Clear current plan, routing decision, and reset status
     */
    clearPlan: (state) => {
      state.currentPlan = null;
      state.currentRoutingDecision = null;
      state.planStatus = "idle";
    },

    /**
     * Update plan status (approved/rejected)
     * Also updates currentPlan.status if plan exists
     */
    setPlanStatus: (state, action: PayloadAction<PlanStatus>) => {
      state.planStatus = action.payload;

      // Sync currentPlan.status if it exists
      if (state.currentPlan && action.payload !== "idle") {
        state.currentPlan.status = action.payload as
          | "awaiting_approval"
          | "approved"
          | "rejected";
      }
    },
  },
});

// =============================================================================
// Actions
// =============================================================================

export const {
  setExecutionMode,
  cycleExecutionMode,
  setUserIsAdmin,
  setHasBypassPermission,
  setPlan,
  setRoutingDecision,
  clearPlan,
  setPlanStatus,
} = executionModeSlice.actions;

// =============================================================================
// Selectors
// =============================================================================

/**
 * Select current execution mode
 */
export const selectExecutionMode = (state: {
  executionMode: ExecutionModeState;
}) => state.executionMode.executionMode;

/**
 * Select current plan (if any)
 */
export const selectCurrentPlan = (state: {
  executionMode: ExecutionModeState;
}) => state.executionMode.currentPlan;

/**
 * Select current routing decision (for debugging/observability)
 */
export const selectRoutingDecision = (state: {
  executionMode: ExecutionModeState;
}) => state.executionMode.currentRoutingDecision;

/**
 * Select current plan status
 */
export const selectPlanStatus = (state: {
  executionMode: ExecutionModeState;
}) => state.executionMode.planStatus;

/**
 * Select whether user is admin (legacy - can use bypass mode)
 */
export const selectUserIsAdmin = (state: {
  executionMode: ExecutionModeState;
}) => state.executionMode.userIsAdmin;

/**
 * Select whether user has bypass permission from OpenFGA
 */
export const selectHasBypassPermission = (state: {
  executionMode: ExecutionModeState;
}) => state.executionMode.hasBypassPermission;

/**
 * Select whether user can use bypass mode (has OpenFGA permission or admin role)
 */
export const selectCanBypass = (state: {
  executionMode: ExecutionModeState;
}): boolean =>
  state.executionMode.hasBypassPermission || state.executionMode.userIsAdmin;

/**
 * Select whether to show plan approval UI
 * True when there's a plan that requires approval
 */
export const selectShowPlanApproval = (state: {
  executionMode: ExecutionModeState;
}): boolean => {
  const plan = state.executionMode.currentPlan;
  const status = state.executionMode.planStatus;

  if (!plan) return false;
  if (!plan.requiresApproval) return false;
  if (status !== "awaiting_approval") return false;

  return true;
};

// =============================================================================
// Default Export
// =============================================================================

export default executionModeSlice.reducer;
