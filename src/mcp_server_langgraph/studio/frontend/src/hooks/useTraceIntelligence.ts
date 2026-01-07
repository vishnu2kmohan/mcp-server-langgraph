/**
 * Trace Intelligence Hooks
 *
 * Sprint 5: Trace Intelligence + Cost Projection
 * - Trace summary provides one-sentence summary of agent execution
 * - Trace anomaly detection identifies bottlenecks and issues
 * - Cost projection estimates real-time session costs
 * - Token prediction forecasts token usage
 *
 * These hooks use the unified StudioOrchestrator via RTK Query.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useStudioAnalyzeMutation } from "../api";

// =============================================================================
// Types
// =============================================================================

export interface TraceSummaryOptions {
  userId: string;
  sessionId: string;
  traceId: string;
  enabled?: boolean;
}

export interface TraceSummaryResult {
  summary: string | null;
  totalDurationMs: number | null;
  stepCount: number | null;
  toolCallCount: number | null;
  success: boolean | null;
  keyActions: string[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export interface TraceAnomalyOptions {
  userId: string;
  sessionId: string;
  traceId: string;
  enabled?: boolean;
}

export interface TraceAnomaly {
  type: string;
  stepName: string;
  severity: "error" | "warning" | "info";
  message: string;
  suggestedFix?: string;
}

export interface TraceBottleneck {
  stepName: string;
  durationMs: number;
  percentageOfTotal: number;
}

export interface TraceAnomalyResult {
  anomalies: TraceAnomaly[];
  bottlenecks: TraceBottleneck[];
  healthScore: number | null;
  optimizationSuggestions: string[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export interface CostProjectionOptions {
  userId: string;
  sessionId: string;
  enabled?: boolean;
}

/**
 * Token breakdown for trace cost calculations.
 * Note: Different from session.ts TraceTokenBreakdown which tracks USD estimates.
 */
export interface TraceTokenBreakdown {
  input_tokens: number;
  output_tokens: number;
}

export interface CostProjectionResult {
  currentCost: number | null;
  projectedCost: number | null;
  costBreakdown: TraceTokenBreakdown | null;
  budgetRemaining: number | null;
  budgetPercentageUsed: number | null;
  estimatedRemainingMessages: number | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export interface TokenPredictionOptions {
  userId: string;
  sessionId: string;
  enabled?: boolean;
}

export interface TokenPredictionResult {
  currentTokens: number | null;
  projectedTokens: number | null;
  contextUtilization: number | null;
  optimizationAvailable: boolean | null;
  optimizationSavings: number | null;
  recommendedAction: string | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

// =============================================================================
// useTraceSummary
// =============================================================================

/**
 * Hook for generating a summary of agent execution traces.
 *
 * Uses the StudioOrchestrator's trace_summarize task type to provide
 * a one-sentence summary of what the agent did, along with key metrics.
 *
 * @param options - Configuration options
 * @returns Trace summary with key metrics
 */
export function useTraceSummary(
  options: TraceSummaryOptions,
): TraceSummaryResult {
  const { userId, sessionId, traceId, enabled = true } = options;

  const [analyzeMutation, { isLoading }] = useStudioAnalyzeMutation();

  const [result, setResult] = useState<{
    summary: string | null;
    totalDurationMs: number | null;
    stepCount: number | null;
    toolCallCount: number | null;
    success: boolean | null;
    keyActions: string[];
    error: Error | null;
  }>({
    summary: null,
    totalDurationMs: null,
    stepCount: null,
    toolCallCount: null,
    success: null,
    keyActions: [],
    error: null,
  });

  const fetchSummary = useCallback(async () => {
    if (!enabled || !traceId.trim()) {
      setResult({
        summary: null,
        totalDurationMs: null,
        stepCount: null,
        toolCallCount: null,
        success: null,
        keyActions: [],
        error: null,
      });
      return;
    }

    try {
      const response = await analyzeMutation({
        user_id: userId,
        session_id: sessionId,
        tasks: [
          {
            category: "trace",
            type: "trace_summarize",
            data: { trace_id: traceId },
          },
        ],
      }).unwrap();

      const summaryResult = response.analyses?.trace_summarize as
        | {
            summary?: string;
            total_duration_ms?: number;
            step_count?: number;
            tool_call_count?: number;
            success?: boolean;
            key_actions?: string[];
          }
        | undefined;

      if (summaryResult) {
        setResult({
          summary: summaryResult.summary || null,
          totalDurationMs: summaryResult.total_duration_ms ?? null,
          stepCount: summaryResult.step_count ?? null,
          toolCallCount: summaryResult.tool_call_count ?? null,
          success: summaryResult.success ?? null,
          keyActions: summaryResult.key_actions || [],
          error: null,
        });
      }
    } catch (err) {
      setResult((prev) => ({
        ...prev,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [analyzeMutation, userId, sessionId, traceId, enabled]);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  return useMemo(
    () => ({
      summary: result.summary,
      totalDurationMs: result.totalDurationMs,
      stepCount: result.stepCount,
      toolCallCount: result.toolCallCount,
      success: result.success,
      keyActions: result.keyActions,
      isLoading,
      error: result.error,
      refetch: fetchSummary,
    }),
    [result, isLoading, fetchSummary],
  );
}

// =============================================================================
// useTraceAnomaly
// =============================================================================

/**
 * Hook for detecting anomalies in agent execution traces.
 *
 * Uses the StudioOrchestrator's trace_anomaly task type to identify
 * bottlenecks, slow steps, and potential issues in agent execution.
 *
 * @param options - Configuration options
 * @returns Anomaly detection results with suggestions
 */
export function useTraceAnomaly(
  options: TraceAnomalyOptions,
): TraceAnomalyResult {
  const { userId, sessionId, traceId, enabled = true } = options;

  const [analyzeMutation, { isLoading }] = useStudioAnalyzeMutation();

  const [result, setResult] = useState<{
    anomalies: TraceAnomaly[];
    bottlenecks: TraceBottleneck[];
    healthScore: number | null;
    optimizationSuggestions: string[];
    error: Error | null;
  }>({
    anomalies: [],
    bottlenecks: [],
    healthScore: null,
    optimizationSuggestions: [],
    error: null,
  });

  const fetchAnomalies = useCallback(async () => {
    if (!enabled || !traceId.trim()) {
      setResult({
        anomalies: [],
        bottlenecks: [],
        healthScore: null,
        optimizationSuggestions: [],
        error: null,
      });
      return;
    }

    try {
      const response = await analyzeMutation({
        user_id: userId,
        session_id: sessionId,
        tasks: [
          {
            category: "trace",
            type: "trace_anomaly",
            data: { trace_id: traceId },
          },
        ],
      }).unwrap();

      const anomalyResult = response.analyses?.trace_anomaly as
        | {
            anomalies?: TraceAnomaly[];
            bottlenecks?: TraceBottleneck[];
            health_score?: number;
            optimization_suggestions?: string[];
          }
        | undefined;

      if (anomalyResult) {
        setResult({
          anomalies: anomalyResult.anomalies || [],
          bottlenecks: anomalyResult.bottlenecks || [],
          healthScore: anomalyResult.health_score ?? null,
          optimizationSuggestions: anomalyResult.optimization_suggestions || [],
          error: null,
        });
      }
    } catch (err) {
      setResult((prev) => ({
        ...prev,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [analyzeMutation, userId, sessionId, traceId, enabled]);

  useEffect(() => {
    fetchAnomalies();
  }, [fetchAnomalies]);

  return useMemo(
    () => ({
      anomalies: result.anomalies,
      bottlenecks: result.bottlenecks,
      healthScore: result.healthScore,
      optimizationSuggestions: result.optimizationSuggestions,
      isLoading,
      error: result.error,
      refetch: fetchAnomalies,
    }),
    [result, isLoading, fetchAnomalies],
  );
}

// =============================================================================
// useCostProjection
// =============================================================================

/**
 * Hook for projecting session costs.
 *
 * Uses the StudioOrchestrator's cost_project task type to estimate
 * real-time session costs and provide budget tracking.
 *
 * @param options - Configuration options
 * @returns Cost projection with budget information
 */
export function useCostProjection(
  options: CostProjectionOptions,
): CostProjectionResult {
  const { userId, sessionId, enabled = true } = options;

  const [analyzeMutation, { isLoading }] = useStudioAnalyzeMutation();

  const [result, setResult] = useState<{
    currentCost: number | null;
    projectedCost: number | null;
    costBreakdown: TraceTokenBreakdown | null;
    budgetRemaining: number | null;
    budgetPercentageUsed: number | null;
    estimatedRemainingMessages: number | null;
    error: Error | null;
  }>({
    currentCost: null,
    projectedCost: null,
    costBreakdown: null,
    budgetRemaining: null,
    budgetPercentageUsed: null,
    estimatedRemainingMessages: null,
    error: null,
  });

  const fetchProjection = useCallback(async () => {
    if (!enabled) {
      setResult({
        currentCost: null,
        projectedCost: null,
        costBreakdown: null,
        budgetRemaining: null,
        budgetPercentageUsed: null,
        estimatedRemainingMessages: null,
        error: null,
      });
      return;
    }

    try {
      const response = await analyzeMutation({
        user_id: userId,
        session_id: sessionId,
        tasks: [
          {
            category: "trace",
            type: "cost_project",
            data: { session_id: sessionId },
          },
        ],
      }).unwrap();

      const costResult = response.analyses?.cost_project as
        | {
            current_cost?: number;
            projected_cost?: number;
            cost_breakdown?: TraceTokenBreakdown;
            budget_remaining?: number;
            budget_percentage_used?: number;
            estimated_remaining_messages?: number;
          }
        | undefined;

      if (costResult) {
        setResult({
          currentCost: costResult.current_cost ?? null,
          projectedCost: costResult.projected_cost ?? null,
          costBreakdown: costResult.cost_breakdown || null,
          budgetRemaining: costResult.budget_remaining ?? null,
          budgetPercentageUsed: costResult.budget_percentage_used ?? null,
          estimatedRemainingMessages:
            costResult.estimated_remaining_messages ?? null,
          error: null,
        });
      }
    } catch (err) {
      setResult((prev) => ({
        ...prev,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [analyzeMutation, userId, sessionId, enabled]);

  useEffect(() => {
    fetchProjection();
  }, [fetchProjection]);

  return useMemo(
    () => ({
      currentCost: result.currentCost,
      projectedCost: result.projectedCost,
      costBreakdown: result.costBreakdown,
      budgetRemaining: result.budgetRemaining,
      budgetPercentageUsed: result.budgetPercentageUsed,
      estimatedRemainingMessages: result.estimatedRemainingMessages,
      isLoading,
      error: result.error,
      refetch: fetchProjection,
    }),
    [result, isLoading, fetchProjection],
  );
}

// =============================================================================
// useTokenPrediction
// =============================================================================

/**
 * Hook for predicting token usage.
 *
 * Uses the StudioOrchestrator's token_predict task type to forecast
 * token usage and provide optimization recommendations.
 *
 * @param options - Configuration options
 * @returns Token prediction with optimization info
 */
export function useTokenPrediction(
  options: TokenPredictionOptions,
): TokenPredictionResult {
  const { userId, sessionId, enabled = true } = options;

  const [analyzeMutation, { isLoading }] = useStudioAnalyzeMutation();

  const [result, setResult] = useState<{
    currentTokens: number | null;
    projectedTokens: number | null;
    contextUtilization: number | null;
    optimizationAvailable: boolean | null;
    optimizationSavings: number | null;
    recommendedAction: string | null;
    error: Error | null;
  }>({
    currentTokens: null,
    projectedTokens: null,
    contextUtilization: null,
    optimizationAvailable: null,
    optimizationSavings: null,
    recommendedAction: null,
    error: null,
  });

  const fetchPrediction = useCallback(async () => {
    if (!enabled) {
      setResult({
        currentTokens: null,
        projectedTokens: null,
        contextUtilization: null,
        optimizationAvailable: null,
        optimizationSavings: null,
        recommendedAction: null,
        error: null,
      });
      return;
    }

    try {
      const response = await analyzeMutation({
        user_id: userId,
        session_id: sessionId,
        tasks: [
          {
            category: "trace",
            type: "token_predict",
            data: { session_id: sessionId },
          },
        ],
      }).unwrap();

      const tokenResult = response.analyses?.token_predict as
        | {
            current_tokens?: number;
            projected_tokens?: number;
            context_utilization?: number;
            optimization_available?: boolean;
            optimization_savings?: number;
            recommended_action?: string;
          }
        | undefined;

      if (tokenResult) {
        setResult({
          currentTokens: tokenResult.current_tokens ?? null,
          projectedTokens: tokenResult.projected_tokens ?? null,
          contextUtilization: tokenResult.context_utilization ?? null,
          optimizationAvailable: tokenResult.optimization_available ?? null,
          optimizationSavings: tokenResult.optimization_savings ?? null,
          recommendedAction: tokenResult.recommended_action || null,
          error: null,
        });
      }
    } catch (err) {
      setResult((prev) => ({
        ...prev,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [analyzeMutation, userId, sessionId, enabled]);

  useEffect(() => {
    fetchPrediction();
  }, [fetchPrediction]);

  return useMemo(
    () => ({
      currentTokens: result.currentTokens,
      projectedTokens: result.projectedTokens,
      contextUtilization: result.contextUtilization,
      optimizationAvailable: result.optimizationAvailable,
      optimizationSavings: result.optimizationSavings,
      recommendedAction: result.recommendedAction,
      isLoading,
      error: result.error,
      refetch: fetchPrediction,
    }),
    [result, isLoading, fetchPrediction],
  );
}
