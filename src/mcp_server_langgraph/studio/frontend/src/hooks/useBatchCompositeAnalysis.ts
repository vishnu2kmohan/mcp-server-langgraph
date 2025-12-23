/**
 * useBatchCompositeAnalysis Hook
 *
 * Hook for composite analysis that runs persona, disclosure,
 * and error analyses in parallel via the backend API.
 *
 * Uses POST /api/v1/ai/composite/analyze endpoint which:
 * - Runs multiple AI analyses in a single request for efficiency
 * - Orchestrates persona, disclosure, and error analyses in parallel
 * - Stores results to session context for future reference
 * - Generates cross-service insights from combined results
 *
 * Features:
 * - Runs multiple AI analyses in a single request
 * - Partial analysis support (select which analyses to run)
 * - Cross-service insights generation
 * - Overall confidence scoring
 * - Loading and error state management
 * - Refresh capability
 *
 * Feature Flag: Enable with "batch_composite_analysis" feature flag.
 *
 * @example
 * ```tsx
 * const {
 *   personaResult,
 *   disclosureResult,
 *   errorResult,
 *   crossInsights,
 *   confidence,
 *   isLoading,
 *   error,
 *   refresh,
 * } = useBatchCompositeAnalysis({
 *   userId: 'user-123',
 *   sessionId: 'session-456',
 *   includePersona: true,
 *   includeDisclosure: true,
 *   includeError: false,
 *   personaData: { assignedPersona: 'bob' },
 *   disclosureData: { currentLevel: 'intermediate' },
 * });
 * ```
 */

import { useState, useEffect, useCallback, useRef } from "react";
import { useAnalyzeCompositeMutation } from "../api";

/**
 * Disclosure level type
 */
export type DisclosureLevel =
  | "beginner"
  | "intermediate"
  | "advanced"
  | "expert";

/**
 * Persona analysis result
 */
export interface PersonaAnalysisResult {
  assigned_persona: string;
  detected_persona: string;
  confidence: number;
  behavior_signals: string[];
  recommendation: string | null;
  ui_adaptations: Array<{ feature: string; action: string }>;
}

/**
 * Disclosure analysis result
 */
export interface DisclosureAnalysisResult {
  current_level: DisclosureLevel;
  recommended_level: DisclosureLevel;
  confidence: number;
  unlock_features: string[];
  personalized_message: string;
}

/**
 * Error analysis suggestion
 */
export interface ErrorAnalysisSuggestion {
  action: "retry" | "simplify" | "navigate" | "contact" | "wait";
  label: string;
  guidance?: string;
  estimatedSuccess?: number;
}

/**
 * Error analysis result
 */
export interface ErrorAnalysisResult {
  classification: {
    category: string;
    subcategory: string;
    confidence: number;
  };
  rootCause: string;
  suggestions: ErrorAnalysisSuggestion[];
  similarIssues?: Array<{
    id: string;
    resolution: string;
    successRate: number;
  }>;
}

/**
 * Hook options
 */
export interface UseBatchCompositeAnalysisOptions {
  /** User ID for analysis */
  userId: string;
  /** Session ID for analysis */
  sessionId: string;
  /** Include persona analysis */
  includePersona?: boolean;
  /** Include disclosure analysis */
  includeDisclosure?: boolean;
  /** Include error analysis */
  includeError?: boolean;
  /** Persona analysis input data */
  personaData?: {
    assignedPersona?: string;
    recentActions?: string[];
    featureUsage?: Record<string, number>;
  };
  /** Disclosure analysis input data */
  disclosureData?: {
    currentLevel?: DisclosureLevel;
    featureUsage?: Record<string, number>;
  };
  /** Error analysis input data */
  errorData?: {
    error: { message: string; name: string; stack?: string };
    context?: Record<string, unknown>;
  };
  /** Whether to run the analysis (default: true) */
  enabled?: boolean;
  /** Request timeout in ms (default: 10000) */
  timeoutMs?: number;
}

/**
 * Hook result
 */
export interface UseBatchCompositeAnalysisResult {
  /** Persona analysis result (null if not requested or not yet available) */
  personaResult: PersonaAnalysisResult | null;
  /** Disclosure analysis result (null if not requested or not yet available) */
  disclosureResult: DisclosureAnalysisResult | null;
  /** Error analysis result (null if not requested or not yet available) */
  errorResult: ErrorAnalysisResult | null;
  /** Cross-service insights generated from combined results */
  crossInsights: string[];
  /** Overall confidence score (0-1) */
  confidence: number;
  /** Whether the analysis is in progress */
  isLoading: boolean;
  /** Error if the request failed */
  error: Error | null;
  /** Function to manually refresh the analysis */
  refresh: () => void;
}

/** Default timeout - kept for API compatibility */
const DEFAULT_TIMEOUT_MS = 10000;

/**
 * Hook for batch composite AI analysis.
 *
 * Runs persona, disclosure, and error analyses in parallel via a single
 * backend request, returning combined results with cross-service insights.
 *
 * @param options - Hook configuration options
 * @returns Batch composite analysis results
 */
export function useBatchCompositeAnalysis(
  options: UseBatchCompositeAnalysisOptions,
): UseBatchCompositeAnalysisResult {
  const {
    userId,
    sessionId,
    includePersona = false,
    includeDisclosure = false,
    includeError = false,
    personaData,
    disclosureData,
    errorData,
    enabled = true,
    timeoutMs: _timeoutMs = DEFAULT_TIMEOUT_MS, // Kept for API compatibility
  } = options;

  // RTK Query mutation
  const [analyzeCompositeMutation, { isLoading: isMutationLoading }] =
    useAnalyzeCompositeMutation();

  // State
  const [personaResult, setPersonaResult] =
    useState<PersonaAnalysisResult | null>(null);
  const [disclosureResult, setDisclosureResult] =
    useState<DisclosureAnalysisResult | null>(null);
  const [errorResult, setErrorResult] = useState<ErrorAnalysisResult | null>(
    null,
  );
  const [crossInsights, setCrossInsights] = useState<string[]>([]);
  const [confidence, setConfidence] = useState<number>(0);
  const [isLoading, setIsLoading] = useState(enabled);
  const [error, setError] = useState<Error | null>(null);
  const hasFetchedRef = useRef(false);

  /**
   * Fetch batch composite analysis from backend via RTK Query
   */
  const fetchAnalysis = useCallback(async () => {
    // Skip if nothing is requested
    if (!includePersona && !includeDisclosure && !includeError) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const data = await analyzeCompositeMutation({
        include_persona: includePersona,
        include_disclosure: includeDisclosure,
        include_errors: includeError,
        session_id: sessionId,
        context: {
          user_id: userId,
          persona_data: personaData
            ? {
                assigned_persona: personaData.assignedPersona,
                recent_actions: personaData.recentActions,
                feature_usage: personaData.featureUsage,
              }
            : undefined,
          disclosure_data: disclosureData
            ? {
                current_level: disclosureData.currentLevel,
                feature_usage: disclosureData.featureUsage,
              }
            : undefined,
          error_data: errorData,
        },
      }).unwrap();

      // Transform RTK Query response to hook's expected format
      // RTK Query returns: persona?, disclosure?, errors?, overall_confidence
      // Hook expects: personaResult, disclosureResult, errorResult, crossInsights

      // Transform persona result
      if (data.persona) {
        setPersonaResult({
          assigned_persona: personaData?.assignedPersona || "user",
          detected_persona: data.persona.detected_persona,
          confidence: data.persona.confidence,
          behavior_signals: [], // Not provided by RTK Query
          recommendation: null, // Not provided by RTK Query
          ui_adaptations: [],
        });
      } else {
        setPersonaResult(null);
      }

      // Transform disclosure result
      if (data.disclosure) {
        setDisclosureResult({
          current_level: (disclosureData?.currentLevel ||
            "intermediate") as DisclosureLevel,
          recommended_level: data.disclosure
            .recommended_level as DisclosureLevel,
          confidence: data.disclosure.confidence,
          unlock_features: [], // Not provided by RTK Query
          personalized_message: "",
        });
      } else {
        setDisclosureResult(null);
      }

      // Transform error result
      if (data.errors && data.errors.length > 0) {
        const firstError = data.errors[0];
        setErrorResult({
          classification: {
            category: firstError.error_type,
            subcategory: firstError.auto_recoverable ? "recoverable" : "manual",
            confidence: data.overall_confidence,
          },
          rootCause: firstError.error_type,
          suggestions: [],
          similarIssues: undefined,
        });
      } else {
        setErrorResult(null);
      }

      // Generate cross-insights from combined results
      const insights: string[] = [];
      if (data.persona && data.disclosure) {
        insights.push(
          `Persona ${data.persona.detected_persona} aligns with ${data.disclosure.recommended_level} disclosure level`,
        );
      }
      setCrossInsights(insights);

      setConfidence(data.overall_confidence);
    } catch (err) {
      const errorToSet =
        err instanceof Error
          ? err
          : new Error("Batch composite analysis failed");

      setError(errorToSet);

      // Reset results on error
      setPersonaResult(null);
      setDisclosureResult(null);
      setErrorResult(null);
      setCrossInsights([]);
      setConfidence(0);
    } finally {
      setIsLoading(false);
      hasFetchedRef.current = true;
    }
  }, [
    userId,
    sessionId,
    includePersona,
    includeDisclosure,
    includeError,
    personaData,
    disclosureData,
    errorData,
    analyzeCompositeMutation,
  ]);

  /**
   * Refresh the analysis
   */
  const refresh = useCallback(() => {
    hasFetchedRef.current = false;
    fetchAnalysis();
  }, [fetchAnalysis]);

  // Initial fetch on mount
  useEffect(() => {
    if (!enabled) {
      setIsLoading(false);
      return;
    }

    if (!hasFetchedRef.current) {
      fetchAnalysis();
    }
  }, [enabled, fetchAnalysis]);

  return {
    personaResult,
    disclosureResult,
    errorResult,
    crossInsights,
    confidence,
    isLoading: isLoading || isMutationLoading,
    error,
    refresh,
  };
}

export default useBatchCompositeAnalysis;
