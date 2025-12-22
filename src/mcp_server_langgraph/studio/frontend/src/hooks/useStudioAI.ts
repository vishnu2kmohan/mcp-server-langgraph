/**
 * useStudioAI Hook
 *
 * Unified hook for Studio AI analysis via the StudioOrchestrator backend.
 *
 * Uses POST /api/v1/studio/analyze endpoint which:
 * - Executes multiple AI analysis tasks in parallel
 * - Supports all 8 task categories (UX, SESSION, CONVERSATION, CANVAS,
 *   DIAGRAM, TRACE, HITL, COMMAND)
 * - Returns synthesized cross-category insights
 * - Tracks total cost of analysis
 *
 * Features:
 * - Task-based API (specify category and type)
 * - Multiple analyses in single request
 * - Category-specific result accessors
 * - Cross-insights generation
 * - Loading and error state management
 * - Refetch capability
 *
 * Feature Flag: Enable with "enable_studio_ai" feature flag.
 *
 * @example
 * ```tsx
 * const {
 *   results,
 *   analyses,
 *   crossInsights,
 *   failedAnalyses,
 *   totalCost,
 *   isLoading,
 *   error,
 *   refetch,
 *   getResult,
 * } = useStudioAI({
 *   userId: 'user-123',
 *   sessionId: 'session-456',
 *   persona: 'alice-builder',
 *   tasks: [
 *     { category: 'ux', type: 'persona_analysis', data: {} },
 *     { category: 'session', type: 'session_summarize', data: {} },
 *   ],
 * });
 * ```
 *
 * Reference: HybridShell AI Enhancement Analysis Plan
 */

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useStudioAnalyzeMutation } from "../api";

// =============================================================================
// Types
// =============================================================================

/**
 * Task category for Studio AI
 */
export type TaskCategory =
  | "ux"
  | "session"
  | "conversation"
  | "canvas"
  | "diagram"
  | "trace"
  | "hitl"
  | "command";

/**
 * Task type for Studio AI analysis
 */
export interface StudioTask {
  /** Task category */
  category: TaskCategory | string;
  /** Task type (e.g., "persona_analysis", "session_summarize") */
  type: string;
  /** Task-specific data */
  data?: Record<string, unknown>;
}

/**
 * Individual analysis result
 */
export interface StudioAnalysisResult {
  /** Task type that produced this result */
  task_type: string;
  /** Whether the analysis succeeded */
  success: boolean;
  /** Analysis result data */
  data: Record<string, unknown>;
  /** Confidence score (0-1) */
  confidence?: number;
  /** Error message if failed */
  error?: string;
}

/**
 * Hook options
 */
export interface UseStudioAIOptions {
  /** User ID for analysis */
  userId: string;
  /** Session ID for analysis */
  sessionId: string;
  /** User persona for RBAC filtering */
  persona?: string;
  /** List of tasks to execute */
  tasks: StudioTask[];
  /** Additional context for analysis */
  context?: Record<string, unknown>;
  /** Whether to run the analysis (default: true) */
  enabled?: boolean;
}

/**
 * Hook result
 */
export interface UseStudioAIResult {
  /** Array of analysis results (null if not yet fetched) */
  results: StudioAnalysisResult[] | null;
  /** Analysis results by task type */
  analyses: Record<string, unknown>;
  /** Cross-category synthesized insights */
  crossInsights: string[];
  /** List of failed task types */
  failedAnalyses: string[];
  /** Total cost of analysis as string (Decimal-compatible) */
  totalCost: string;
  /** Whether the analysis is in progress */
  isLoading: boolean;
  /** Error if the request failed */
  error: Error | null;
  /** Function to manually refetch the analysis */
  refetch: () => void;
  /** Get result for a specific task type */
  getResult: (taskType: string) => StudioAnalysisResult | undefined;
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook for unified Studio AI analysis.
 *
 * Executes multiple AI analysis tasks in parallel via StudioOrchestrator,
 * returning combined results with cross-category insights.
 *
 * @param options - Hook configuration options
 * @returns Studio AI analysis results
 */
export function useStudioAI(options: UseStudioAIOptions): UseStudioAIResult {
  const {
    userId,
    sessionId,
    persona,
    tasks,
    context,
    enabled = true,
  } = options;

  // RTK Query mutation
  const [studioAnalyzeMutation, { isLoading: isMutationLoading }] =
    useStudioAnalyzeMutation();

  // State
  const [results, setResults] = useState<StudioAnalysisResult[] | null>(null);
  const [analyses, setAnalyses] = useState<Record<string, unknown>>({});
  const [crossInsights, setCrossInsights] = useState<string[]>([]);
  const [failedAnalyses, setFailedAnalyses] = useState<string[]>([]);
  const [totalCost, setTotalCost] = useState<string>("0");
  const [isLoading, setIsLoading] = useState(enabled && tasks.length > 0);
  const [error, setError] = useState<Error | null>(null);
  const hasFetchedRef = useRef(false);

  /**
   * Fetch Studio AI analysis from backend via RTK Query
   */
  const fetchAnalysis = useCallback(async () => {
    // Skip if nothing is requested or disabled
    if (!enabled || tasks.length === 0) {
      setIsLoading(false);
      setResults([]);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await studioAnalyzeMutation({
        user_id: userId,
        session_id: sessionId,
        persona,
        tasks: tasks.map((t) => ({
          category: t.category,
          type: t.type,
          data: t.data,
        })),
        context,
      }).unwrap();

      // Transform response to results array
      const analysisResults: StudioAnalysisResult[] = [];
      const analysesMap: Record<string, unknown> = data.analyses || {};

      // Create result entries for each analysis in the response
      for (const [taskType, analysisData] of Object.entries(analysesMap)) {
        const isFailed = data.failed_analyses?.includes(taskType);
        analysisResults.push({
          task_type: taskType,
          success: !isFailed,
          data: analysisData as Record<string, unknown>,
          confidence: (analysisData as Record<string, unknown>)?.confidence as number | undefined,
          error: isFailed ? `Analysis failed for ${taskType}` : undefined,
        });
      }

      // Add entries for failed analyses not in the analyses map
      for (const failedType of data.failed_analyses || []) {
        if (!analysesMap[failedType]) {
          analysisResults.push({
            task_type: failedType,
            success: false,
            data: {},
            error: `Analysis failed for ${failedType}`,
          });
        }
      }

      setResults(analysisResults);
      setAnalyses(analysesMap);
      setCrossInsights(data.cross_insights || []);
      setFailedAnalyses(data.failed_analyses || []);
      setTotalCost(data.total_cost || "0");
    } catch (err) {
      const errorToSet =
        err instanceof Error ? err : new Error("Studio AI analysis failed");

      setError(errorToSet);

      // Reset results on error
      setResults(null);
      setAnalyses({});
      setCrossInsights([]);
      setFailedAnalyses([]);
      setTotalCost("0");
    } finally {
      setIsLoading(false);
      hasFetchedRef.current = true;
    }
  }, [
    userId,
    sessionId,
    persona,
    tasks,
    context,
    enabled,
    studioAnalyzeMutation,
  ]);

  /**
   * Refetch the analysis
   */
  const refetch = useCallback(() => {
    hasFetchedRef.current = false;
    fetchAnalysis();
  }, [fetchAnalysis]);

  /**
   * Get result for a specific task type
   */
  const getResult = useCallback(
    (taskType: string): StudioAnalysisResult | undefined => {
      return results?.find((r) => r.task_type === taskType);
    },
    [results]
  );

  // Serialize tasks for dependency comparison
  const tasksKey = useMemo(() => JSON.stringify(tasks), [tasks]);

  // Initial fetch on mount
  useEffect(() => {
    if (!enabled) {
      setIsLoading(false);
      return;
    }

    if (!hasFetchedRef.current) {
      fetchAnalysis();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled, tasksKey]);

  return {
    results,
    analyses,
    crossInsights,
    failedAnalyses,
    totalCost,
    isLoading: isLoading || isMutationLoading,
    error,
    refetch,
    getResult,
  };
}

export default useStudioAI;
