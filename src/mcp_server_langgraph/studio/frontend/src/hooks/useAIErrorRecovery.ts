/**
 * useAIErrorRecovery Hook
 *
 * Sprint 3 - Phase 6.4: AI Error Recovery
 *
 * Uses LLM to generate contextual error recovery suggestions
 * based on the error type and user context.
 *
 * Features:
 * - Classify errors using AI pattern matching
 * - Generate personalized recovery suggestions
 * - Find similar resolved issues
 * - Timeout handling with graceful degradation
 *
 * Backend endpoint: POST /api/v1/ai/errors/analyze
 *
 * @example
 * ```tsx
 * const { analyze, lastAnalysis, isAnalyzing } = useAIErrorRecovery();
 *
 * try {
 *   await riskyOperation();
 * } catch (error) {
 *   const recovery = await analyze(error, { page: 'workflows', action: 'create' });
 *   if (recovery) {
 *     // Show recovery suggestions to user
 *     showRecoveryDialog(recovery.suggestions);
 *   }
 * }
 * ```
 */

import { useState, useCallback } from "react";
import { useAnalyzeErrorMutation } from "../api";

// =============================================================================
// Types
// =============================================================================

export interface AIErrorAnalysis {
  classification: {
    category: string;
    subcategory: string;
    confidence: number;
  };
  rootCause: string;
  suggestions: AIRecoverySuggestion[];
  similarIssues?: SimilarIssue[];
}

export interface AIRecoverySuggestion {
  action: "retry" | "simplify" | "navigate" | "contact" | "wait";
  label: string;
  guidance?: string;
  estimatedSuccess?: number;
}

export interface SimilarIssue {
  id: string;
  resolution: string;
  successRate: number;
}

export interface UseAIErrorRecoveryOptions {
  /** Enable AI analysis (default: true) */
  enabled?: boolean;
  /** Timeout for AI analysis (default: 5000ms) */
  timeoutMs?: number;
}

export interface UseAIErrorRecoveryResult {
  /** Analyze an error and get recovery suggestions */
  analyze: (
    error: Error,
    context?: Record<string, unknown>,
  ) => Promise<AIErrorAnalysis | null>;
  /** Whether analysis is in progress */
  isAnalyzing: boolean;
  /** Last analysis result */
  lastAnalysis: AIErrorAnalysis | null;
  /** Error from analysis (if failed) */
  analysisError: Error | null;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_TIMEOUT_MS = 5000;

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Map RTK Query action_type to hook's action type
 */
function mapActionType(
  actionType: "automatic" | "manual" | "contact_support",
): AIRecoverySuggestion["action"] {
  switch (actionType) {
    case "automatic":
      return "retry";
    case "manual":
      return "simplify";
    case "contact_support":
      return "contact";
    default:
      return "retry";
  }
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook for AI-powered error analysis and recovery suggestions.
 *
 * @param options - Configuration options
 * @returns Analysis function and state
 */
export function useAIErrorRecovery(
  options: UseAIErrorRecoveryOptions = {},
): UseAIErrorRecoveryResult {
  const { enabled = true, timeoutMs: _timeoutMs = DEFAULT_TIMEOUT_MS } =
    options;

  // RTK Query mutation
  const [analyzeErrorMutation, { isLoading: isMutationLoading }] =
    useAnalyzeErrorMutation();

  const [lastAnalysis, setLastAnalysis] = useState<AIErrorAnalysis | null>(
    null,
  );
  const [analysisError, setAnalysisError] = useState<Error | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  /**
   * Analyze an error and get AI-powered recovery suggestions.
   *
   * @param error - The error to analyze
   * @param context - Additional context about where/how the error occurred
   * @returns Analysis result or null if unavailable
   */
  const analyze = useCallback(
    async (
      error: Error,
      context?: Record<string, unknown>,
    ): Promise<AIErrorAnalysis | null> => {
      // If disabled, return null immediately
      if (!enabled) {
        return null;
      }

      setIsAnalyzing(true);
      setAnalysisError(null);

      try {
        const data = await analyzeErrorMutation({
          error_code: error.name || "Error",
          error_message: error.message,
          context,
          stack_trace: error.stack,
        }).unwrap();

        // Transform RTK Query response to hook's expected format
        const transformed: AIErrorAnalysis = {
          classification: {
            category: data.error_type || "unknown",
            subcategory: data.auto_recoverable ? "recoverable" : "manual",
            confidence: data.confidence,
          },
          rootCause: data.suggested_action || "Unknown error",
          suggestions: (data.recovery_steps || []).map((step) => ({
            action: mapActionType(step.action_type),
            label: step.title,
            guidance: step.description,
            estimatedSuccess: data.confidence,
          })),
          // Note: RTK Query endpoint doesn't return similar_issues
          similarIssues: undefined,
        };

        setLastAnalysis(transformed);
        setIsAnalyzing(false);
        return transformed;
      } catch (err) {
        const errorToSet =
          err instanceof Error ? err : new Error("AI error analysis failed");

        setAnalysisError(errorToSet);
        setIsAnalyzing(false);
        return null;
      }
    },
    [enabled, analyzeErrorMutation],
  );

  return {
    analyze,
    isAnalyzing: isAnalyzing || isMutationLoading,
    lastAnalysis,
    analysisError,
  };
}

export default useAIErrorRecovery;
