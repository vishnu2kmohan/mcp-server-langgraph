/**
 * useAIPersonaAnalysis Hook
 *
 * AI-powered persona behavior analysis hook.
 * Phase 6.7: AI Persona Behavior Analyzer
 *
 * Analyzes real user behavior patterns to detect actual persona
 * vs assigned persona, providing UI adaptation recommendations.
 *
 * Features:
 * - Behavior pattern analysis
 * - Persona mismatch detection
 * - UI adaptation recommendations
 * - Upgrade suggestions for power users
 * - Confidence scoring
 *
 * @example
 * ```tsx
 * const {
 *   assignedPersona,
 *   detectedPersona,
 *   confidence,
 *   behaviorSignals,
 *   recommendation,
 *   uiAdaptations,
 *   isPersonaMismatch,
 *   isLoading,
 *   error,
 *   refresh,
 * } = useAIPersonaAnalysis({
 *   userId: 'user-123',
 *   recentActions: ['create_workflow', 'edit_node', 'run_test'],
 *   featureUsage: { workflow_builder: 25, traces: 15, chat: 5 },
 * });
 * ```
 */

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useSelector } from "react-redux";
import { selectPersona, selectSubPersona } from "../store/slices/personaSlice";
import { useAnalyzePersonaMutation } from "../api";

/**
 * UI Adaptation recommendation
 */
export interface UIAdaptation {
  /** Feature to adapt */
  feature: string;
  /** Adaptation action */
  action: "unlock" | "promote" | "highlight" | "hide";
}

/**
 * Feature usage tracking
 */
export type FeatureUsage = Record<string, number>;

/**
 * Hook configuration options
 */
export interface UseAIPersonaAnalysisOptions {
  /** User ID for analysis (optional, uses session if not provided) */
  userId?: string;
  /** Recent actions taken by the user */
  recentActions?: string[];
  /** Feature usage counts */
  featureUsage?: FeatureUsage;
  /** Whether to analyze (default: true) */
  enabled?: boolean;
  /** Request timeout in milliseconds (default: 5000ms) */
  timeoutMs?: number;
}

/** Default timeout for AI requests */
const DEFAULT_TIMEOUT_MS = 5000;
const EMPTY_RECENT_ACTIONS: string[] = [];
const EMPTY_FEATURE_USAGE: FeatureUsage = {};

/**
 * Hook result
 */
export interface UseAIPersonaAnalysisResult {
  /** Assigned persona from system */
  assignedPersona: string | null;
  /** Detected persona from behavior */
  detectedPersona: string | null;
  /** Confidence score for detection (0-1) */
  confidence: number;
  /** Behavior signals explaining detection */
  behaviorSignals: string[];
  /** Upgrade/change recommendation if applicable */
  recommendation: string | null;
  /** UI adaptations to apply */
  uiAdaptations: UIAdaptation[];
  /** Whether detected persona differs from assigned */
  isPersonaMismatch: boolean;
  /** Whether analysis is being performed */
  isLoading: boolean;
  /** Error if analysis failed */
  error: Error | null;
  /** Manually refresh analysis */
  refresh: () => void;
}

// Note: DEFAULT_TIMEOUT_MS kept for API compatibility but not used with RTK Query

/**
 * Hook for AI-powered persona behavior analysis.
 *
 * @param options - Hook options
 * @returns Persona analysis results and UI adaptations
 */
export function useAIPersonaAnalysis(
  options: UseAIPersonaAnalysisOptions,
): UseAIPersonaAnalysisResult {
  const {
    userId,
    recentActions: recentActionsProp,
    featureUsage: featureUsageProp,
    enabled = true,
    timeoutMs: _timeoutMs = DEFAULT_TIMEOUT_MS, // Kept for API compatibility
  } = options;

  // Avoid recreating default array/object literals on every render
  // (which can cause effect re-runs and duplicate requests on mount).
  const recentActions = recentActionsProp ?? EMPTY_RECENT_ACTIONS;
  const featureUsage = featureUsageProp ?? EMPTY_FEATURE_USAGE;

  // RTK Query mutation
  const [analyzePersonaMutation, { isLoading: isMutationLoading }] =
    useAnalyzePersonaMutation();

  // Get assigned persona from Redux
  const persona = useSelector(selectPersona);
  const subPersona = useSelector(selectSubPersona);
  const assignedPersonaFromStore = subPersona || persona || "user";

  // State
  const [assignedPersona, setAssignedPersona] = useState<string | null>(null);
  const [detectedPersona, setDetectedPersona] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number>(0);
  const [behaviorSignals, setBehaviorSignals] = useState<string[]>([]);
  const [recommendation, setRecommendation] = useState<string | null>(null);
  const [uiAdaptations, setUiAdaptations] = useState<UIAdaptation[]>([]);
  const [isLoading, setIsLoading] = useState(enabled);
  const [error, setError] = useState<Error | null>(null);
  const hasFetchedRef = useRef(false);

  /**
   * Fetch persona analysis from AI backend via RTK Query
   *
   * Schema: PersonaAnalyzeRequest (ai_ux.py:373)
   * - user_id: str (required)
   * - assigned_persona: str (required)
   * - recent_actions: list[str] (optional)
   * - feature_usage: dict[str, int] (optional)
   */
  const fetchAnalysis = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await analyzePersonaMutation({
        user_id: userId || "anonymous",
        assigned_persona: assignedPersonaFromStore,
        recent_actions: recentActions,
        feature_usage: featureUsage,
      }).unwrap();

      // PersonaAnalyzeResponse from generated-api.ts (ADR-0091)
      // Fields: assigned_persona, detected_persona, confidence, behavior_signals, recommendation?, ui_adaptations?
      setAssignedPersona(data.assigned_persona);
      setDetectedPersona(data.detected_persona);
      setConfidence(data.confidence);
      setBehaviorSignals(data.behavior_signals || []);
      setRecommendation(data.recommendation ?? null);

      // Map generated UIAdaptation[] to hook's UIAdaptation format
      const adaptations: UIAdaptation[] = (data.ui_adaptations || []).map(
        (adaptation) => ({
          feature: adaptation.feature,
          action: adaptation.action as UIAdaptation["action"],
        }),
      );
      setUiAdaptations(adaptations);
    } catch (err) {
      const errorToSet =
        err instanceof Error ? err : new Error("Failed to analyze persona");

      setError(errorToSet);

      // Set assigned persona even on error
      setAssignedPersona(assignedPersonaFromStore);
      setDetectedPersona(null);
      setConfidence(0);
      setBehaviorSignals([]);
      setRecommendation(null);
      setUiAdaptations([]);
    } finally {
      setIsLoading(false);
      hasFetchedRef.current = true;
    }
  }, [
    userId,
    assignedPersonaFromStore,
    recentActions,
    featureUsage,
    analyzePersonaMutation,
  ]);

  /**
   * Refresh analysis
   */
  const refresh = useCallback(() => {
    fetchAnalysis();
  }, [fetchAnalysis]);

  // Initial fetch on mount
  useEffect(() => {
    if (!enabled) {
      setIsLoading(false);
      setAssignedPersona(assignedPersonaFromStore);
      return;
    }

    // Only fetch once per hook instance
    if (!hasFetchedRef.current) {
      // Mark as fetched before the async call to avoid duplicate requests during rapid re-renders
      // (e.g., layout-level hooks initializing, StrictMode double-invoke, etc.).
      hasFetchedRef.current = true;
      fetchAnalysis();
    }
  }, [enabled, fetchAnalysis, assignedPersonaFromStore]);

  // Compute persona mismatch
  const isPersonaMismatch = useMemo(() => {
    if (!assignedPersona || !detectedPersona) return false;
    return assignedPersona !== detectedPersona;
  }, [assignedPersona, detectedPersona]);

  return {
    assignedPersona,
    detectedPersona,
    confidence,
    behaviorSignals,
    recommendation,
    uiAdaptations,
    isPersonaMismatch,
    isLoading: isLoading || isMutationLoading,
    error,
    refresh,
  };
}

export default useAIPersonaAnalysis;
