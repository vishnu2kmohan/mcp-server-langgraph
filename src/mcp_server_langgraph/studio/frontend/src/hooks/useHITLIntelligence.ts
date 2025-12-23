/**
 * HITL Intelligence Hooks
 *
 * Sprint 6: HITL Intelligence
 * - Risk assessment provides AI-generated risk scores for pending actions
 * - Decision history shows how user decided similar requests before
 *
 * These hooks use the unified StudioOrchestrator via RTK Query.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useStudioAnalyzeMutation } from "../api";

// =============================================================================
// Types
// =============================================================================

export interface RiskFactor {
  factor: string;
  weight: number;
  description: string;
}

export type RiskLevel = "low" | "medium" | "high" | "critical";
export type RiskRecommendation =
  | "approve"
  | "approve_with_caution"
  | "require_review"
  | "reject";

export interface RiskAssessmentOptions {
  userId: string;
  requestId: string;
  actionType: string;
  parameters: Record<string, unknown>;
  enabled?: boolean;
}

export interface RiskAssessmentResult {
  riskScore: number | null;
  riskLevel: RiskLevel | null;
  riskFactors: RiskFactor[];
  mitigations: string[];
  recommendation: RiskRecommendation | null;
  explanation: string | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export interface SimilarDecision {
  request_id: string;
  action_type: string;
  decision: "approved" | "rejected";
  decided_by: string;
  decided_at: string;
  reasoning: string;
}

export interface DecisionHistoryOptions {
  userId: string;
  actionType: string;
  persona?: string;
  timeRangeDays?: number;
  enabled?: boolean;
}

export interface DecisionHistoryResult {
  similarDecisions: SimilarDecision[];
  approvalRate: number | null;
  totalSimilar: number | null;
  averageDecisionTimeMs: number | null;
  suggestedAction: "approve" | "reject" | "review" | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

// =============================================================================
// useRiskAssessment
// =============================================================================

/**
 * Hook for assessing risk of pending HITL actions.
 *
 * Uses the StudioOrchestrator's risk_assess task type to provide
 * AI-generated risk scores and recommendations for approval decisions.
 *
 * @param options - Configuration options
 * @returns Risk assessment with score, factors, and recommendation
 */
export function useRiskAssessment(
  options: RiskAssessmentOptions,
): RiskAssessmentResult {
  const { userId, requestId, actionType, parameters, enabled = true } = options;

  const [analyzeMutation, { isLoading }] = useStudioAnalyzeMutation();

  const [result, setResult] = useState<{
    riskScore: number | null;
    riskLevel: RiskLevel | null;
    riskFactors: RiskFactor[];
    mitigations: string[];
    recommendation: RiskRecommendation | null;
    explanation: string | null;
    error: Error | null;
  }>({
    riskScore: null,
    riskLevel: null,
    riskFactors: [],
    mitigations: [],
    recommendation: null,
    explanation: null,
    error: null,
  });

  const fetchRiskAssessment = useCallback(async () => {
    if (!enabled || !requestId) {
      setResult({
        riskScore: null,
        riskLevel: null,
        riskFactors: [],
        mitigations: [],
        recommendation: null,
        explanation: null,
        error: null,
      });
      return;
    }

    try {
      const response = await analyzeMutation({
        user_id: userId,
        session_id: "",
        tasks: [
          {
            category: "hitl",
            type: "risk_assess",
            data: {
              request_id: requestId,
              action_type: actionType,
              parameters,
            },
          },
        ],
      }).unwrap();

      const riskResult = response.analyses?.risk_assess as
        | {
            risk_score?: number;
            risk_level?: RiskLevel;
            risk_factors?: RiskFactor[];
            mitigations?: string[];
            recommendation?: RiskRecommendation;
            explanation?: string;
          }
        | undefined;

      if (riskResult) {
        setResult({
          riskScore: riskResult.risk_score ?? null,
          riskLevel: riskResult.risk_level ?? null,
          riskFactors: riskResult.risk_factors || [],
          mitigations: riskResult.mitigations || [],
          recommendation: riskResult.recommendation ?? null,
          explanation: riskResult.explanation || null,
          error: null,
        });
      }
    } catch (err) {
      setResult((prev) => ({
        ...prev,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [analyzeMutation, userId, requestId, actionType, parameters, enabled]);

  useEffect(() => {
    fetchRiskAssessment();
  }, [fetchRiskAssessment]);

  return useMemo(
    () => ({
      riskScore: result.riskScore,
      riskLevel: result.riskLevel,
      riskFactors: result.riskFactors,
      mitigations: result.mitigations,
      recommendation: result.recommendation,
      explanation: result.explanation,
      isLoading,
      error: result.error,
      refetch: fetchRiskAssessment,
    }),
    [result, isLoading, fetchRiskAssessment],
  );
}

// =============================================================================
// useDecisionHistory
// =============================================================================

/**
 * Hook for retrieving similar past decisions.
 *
 * Uses the StudioOrchestrator's decision_history task type to show
 * how users decided similar requests in the past.
 *
 * @param options - Configuration options
 * @returns Decision history with similar decisions and statistics
 */
export function useDecisionHistory(
  options: DecisionHistoryOptions,
): DecisionHistoryResult {
  const {
    userId,
    actionType,
    persona,
    timeRangeDays,
    enabled = true,
  } = options;

  const [analyzeMutation, { isLoading }] = useStudioAnalyzeMutation();

  const [result, setResult] = useState<{
    similarDecisions: SimilarDecision[];
    approvalRate: number | null;
    totalSimilar: number | null;
    averageDecisionTimeMs: number | null;
    suggestedAction: "approve" | "reject" | "review" | null;
    error: Error | null;
  }>({
    similarDecisions: [],
    approvalRate: null,
    totalSimilar: null,
    averageDecisionTimeMs: null,
    suggestedAction: null,
    error: null,
  });

  const fetchDecisionHistory = useCallback(async () => {
    if (!enabled || !actionType) {
      setResult({
        similarDecisions: [],
        approvalRate: null,
        totalSimilar: null,
        averageDecisionTimeMs: null,
        suggestedAction: null,
        error: null,
      });
      return;
    }

    try {
      const response = await analyzeMutation({
        user_id: userId,
        session_id: "",
        tasks: [
          {
            category: "hitl",
            type: "decision_history",
            data: {
              action_type: actionType,
              persona,
              time_range_days: timeRangeDays,
            },
          },
        ],
      }).unwrap();

      const historyResult = response.analyses?.decision_history as
        | {
            similar_decisions?: SimilarDecision[];
            approval_rate?: number;
            total_similar?: number;
            average_decision_time_ms?: number;
            suggested_action?: "approve" | "reject" | "review";
          }
        | undefined;

      if (historyResult) {
        setResult({
          similarDecisions: historyResult.similar_decisions || [],
          approvalRate: historyResult.approval_rate ?? null,
          totalSimilar: historyResult.total_similar ?? null,
          averageDecisionTimeMs: historyResult.average_decision_time_ms ?? null,
          suggestedAction: historyResult.suggested_action ?? null,
          error: null,
        });
      }
    } catch (err) {
      setResult((prev) => ({
        ...prev,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [analyzeMutation, userId, actionType, persona, timeRangeDays, enabled]);

  useEffect(() => {
    fetchDecisionHistory();
  }, [fetchDecisionHistory]);

  return useMemo(
    () => ({
      similarDecisions: result.similarDecisions,
      approvalRate: result.approvalRate,
      totalSimilar: result.totalSimilar,
      averageDecisionTimeMs: result.averageDecisionTimeMs,
      suggestedAction: result.suggestedAction,
      isLoading,
      error: result.error,
      refetch: fetchDecisionHistory,
    }),
    [result, isLoading, fetchDecisionHistory],
  );
}
