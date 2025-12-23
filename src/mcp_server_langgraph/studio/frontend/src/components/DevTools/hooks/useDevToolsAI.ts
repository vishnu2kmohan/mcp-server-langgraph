/**
 * useDevToolsAI Hook
 *
 * Provides AI-powered DevTools features including:
 * - Layout suggestions based on context
 * - Insights about anomalies and performance
 * - Smart tab recommendations
 */
import { useState, useCallback, useEffect, useMemo } from "react";

import { useStudioAI } from "../../../hooks/useStudioAI";
import type { DevToolsTabId } from "../../../store/slices/devToolsSlice";
import type { AIInsight } from "../types";

// =============================================================================
// Types
// =============================================================================

export interface UseDevToolsAIOptions {
  /** Context type */
  context: "session" | "workflow" | "global";
  /** Entity ID for the context */
  entityId: string;
  /** User ID for personalization */
  userId: string;
  /** Whether AI features are enabled */
  enabled: boolean;
  /** Callback when layout is applied */
  onApplyLayout?: (layout: DevToolsTabId[]) => void;
}

export interface UseDevToolsAIReturn {
  /** Suggested tab layout order */
  suggestedLayout: DevToolsTabId[] | null;
  /** Confidence score (0-1) */
  confidence: number;
  /** AI-generated insights */
  insights: AIInsight[];
  /** Whether suggestions are loading */
  isLoading: boolean;
  /** Error if fetching failed */
  error: Error | null;
  /** Apply the suggested layout */
  applyLayout: () => void;
  /** Dismiss an insight */
  dismissInsight: (id: string) => void;
  /** Fetch/refresh suggestions */
  fetchSuggestions: () => void;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useDevToolsAI(
  options: UseDevToolsAIOptions,
): UseDevToolsAIReturn {
  const { context, entityId, userId, enabled, onApplyLayout } = options;

  const [suggestedLayout, setSuggestedLayout] = useState<
    DevToolsTabId[] | null
  >(null);
  const [confidence, setConfidence] = useState(0);
  const [insights, setInsights] = useState<AIInsight[]>([]);
  const [localError, setLocalError] = useState<Error | null>(null);

  // Define tasks for DevTools AI analysis
  const tasks = useMemo(
    () => [
      {
        category: "trace" as const,
        type: "devtools_layout",
        data: {
          contextType: context,
          entityId,
        },
      },
    ],
    [context, entityId],
  );

  // Use the Studio AI hook
  const studioAI = useStudioAI({
    userId,
    sessionId: entityId,
    tasks,
    enabled,
    context: {
      contextType: context,
      entityId,
    },
  });

  // Process results from studioAI
  useEffect(() => {
    if (studioAI.results && studioAI.results.length > 0) {
      const layoutResult = studioAI.getResult("devtools_layout");
      if (layoutResult?.success && layoutResult.data) {
        const data = layoutResult.data as {
          suggestedLayout?: DevToolsTabId[];
          insights?: AIInsight[];
          confidence?: number;
        };
        if (data.suggestedLayout) {
          setSuggestedLayout(data.suggestedLayout);
        }
        if (data.insights) {
          setInsights(data.insights);
        }
        if (data.confidence !== undefined) {
          setConfidence(data.confidence);
        }
      }
    }
    // Only depend on specific properties to avoid re-renders when studioAI object reference changes
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [studioAI.results, studioAI.getResult]);

  // Handle errors
  useEffect(() => {
    if (studioAI.error) {
      setLocalError(studioAI.error);
    }
  }, [studioAI.error]);

  /**
   * Fetch/refresh AI suggestions
   */
  const fetchSuggestions = useCallback(() => {
    if (!enabled) return;
    setLocalError(null);
    studioAI.refetch();
  }, [enabled, studioAI]);

  /**
   * Apply the suggested layout.
   */
  const applyLayout = useCallback(() => {
    if (suggestedLayout && onApplyLayout) {
      onApplyLayout(suggestedLayout);
    }
  }, [suggestedLayout, onApplyLayout]);

  /**
   * Dismiss an insight by ID.
   */
  const dismissInsight = useCallback((id: string) => {
    setInsights((prev) => prev.filter((insight) => insight.id !== id));
  }, []);

  return {
    suggestedLayout,
    confidence,
    insights,
    isLoading: studioAI.isLoading,
    error: localError || studioAI.error,
    applyLayout,
    dismissInsight,
    fetchSuggestions,
  };
}

export default useDevToolsAI;
