/**
 * Context Graph Types (ADR-0101)
 *
 * TypeScript types for decision traces and context graph API.
 * All field names use camelCase per ADR-0091.
 */

/**
 * Decision type classification
 */
export type DecisionType =
  | "routing"
  | "tool_selection"
  | "skill_selection"
  | "model_selection"
  | "response"
  | "approval"
  | "exception";

/**
 * Decision stage in the pipeline
 */
export type DecisionStage =
  | "context_gathering"
  | "policy_check"
  | "action"
  | "write";

/**
 * Decision outcome status
 */
export type DecisionOutcome = "success" | "failure" | "partial" | "pending";

/**
 * Summary of a decision trace for list views
 */
export interface DecisionTraceSummary {
  traceId: string;
  timestamp: string;
  decisionType: DecisionType;
  chosenAction: string;
  confidence: number;
  outcome: DecisionOutcome | null;
}

/**
 * Full decision trace with all details
 */
export interface DecisionTrace extends DecisionTraceSummary {
  runId: string;
  sessionId: string;
  workflowId?: string;
  projectId?: string;
  rationale: string;
  requiresApproval: boolean;
  approvalStatus?: string;
}

/**
 * Precedent search request
 */
export interface PrecedentSearchRequest {
  query: string;
  decisionType?: DecisionType;
  outcome?: DecisionOutcome;
  limit?: number;
}

/**
 * Precedent search result
 */
export interface PrecedentSearchResult {
  trace: DecisionTrace;
  similarityScore: number;
}
