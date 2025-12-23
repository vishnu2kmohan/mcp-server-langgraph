/**
 * useCrossInsightsPanel Hook
 *
 * Encapsulates all CrossInsightsPanel state management:
 * - Dismissed state with localStorage persistence
 * - Keyboard shortcut handling (Cmd+I / Ctrl+I)
 * - Integration with batch composite analysis
 * - Feature flag awareness
 *
 * Extracted from HybridShellLayout to reduce component complexity.
 */
import { useState, useEffect, useCallback } from "react";
import { useFeatureFlag } from "../contexts/FeatureFlagContext";
import {
  useBatchCompositeAnalysis,
  type PersonaAnalysisResult,
  type DisclosureAnalysisResult,
} from "./useBatchCompositeAnalysis";
import { useAppSelector } from "../store/hooks";
import { selectCurrentSession } from "../store/slices/sessionSlice";
import { selectUsername } from "../store/slices/personaSlice";
import { storage, STORAGE_KEYS } from "../utils/storage";

/**
 * Return type for the useCrossInsightsPanel hook
 */
export interface UseCrossInsightsPanelReturn {
  /** Whether the panel is dismissed */
  dismissed: boolean;
  /** Function to set dismissed state */
  setDismissed: (value: boolean | ((prev: boolean) => boolean)) => void;
  /** Function to toggle dismissed state */
  toggle: () => void;
  /** Whether the panel should be shown (not dismissed + has insights) */
  shouldShow: boolean;
  /** Cross-insights from batch analysis */
  crossInsights: string[];
  /** Confidence score from batch analysis */
  confidence: number;
  /** Whether batch analysis is loading */
  isLoading: boolean;
  /** Persona result from batch analysis */
  personaResult: PersonaAnalysisResult | null;
  /** Disclosure result from batch analysis */
  disclosureResult: DisclosureAnalysisResult | null;
  /** Whether session-based dismissal is enabled */
  sessionDismissalEnabled: boolean;
  /** Whether batch composite analysis is enabled */
  batchAnalysisEnabled: boolean;
}

/**
 * Hook for managing CrossInsightsPanel state
 *
 * Handles:
 * - Initial state from localStorage (unless session-based dismissal enabled)
 * - Persistence to localStorage on state changes
 * - Keyboard shortcut (Cmd+I / Ctrl+I) for toggling
 * - Integration with batch composite analysis
 *
 * @example
 * ```tsx
 * const {
 *   dismissed,
 *   toggle,
 *   shouldShow,
 *   crossInsights,
 * } = useCrossInsightsPanel();
 *
 * // In JSX:
 * {shouldShow && <CrossInsightsPanel insights={crossInsights} onDismiss={toggle} />}
 * ```
 */
export function useCrossInsightsPanel(): UseCrossInsightsPanelReturn {
  // Feature flags
  const sessionDismissalEnabled = useFeatureFlag("insights_session_dismissal");
  const batchAnalysisEnabled = useFeatureFlag("batch_composite_analysis");

  // Session context for batch analysis
  const currentSession = useAppSelector(selectCurrentSession);
  const username = useAppSelector(selectUsername);

  // Initialize dismissed state
  const [dismissed, setDismissedState] = useState<boolean>(() => {
    // If session-based dismissal is enabled, always start undismissed
    if (sessionDismissalEnabled) {
      return false;
    }
    // Read from localStorage for persistence across sessions
    // Validate that we get a boolean, handling invalid JSON/values gracefully
    const storedValue = storage.get<boolean>(
      STORAGE_KEYS.CROSS_INSIGHTS_DISMISSED,
      false,
    );
    // Ensure the result is actually a boolean (storage might return raw string on parse error)
    if (typeof storedValue === "boolean") {
      return storedValue;
    }
    // Any non-boolean value (including raw strings from invalid JSON) defaults to false
    return false;
  });

  // Batch composite analysis integration
  const {
    personaResult,
    disclosureResult,
    crossInsights,
    confidence,
    isLoading,
  } = useBatchCompositeAnalysis({
    userId: username || "anonymous",
    sessionId: currentSession?.id || "no-session",
    includePersona: true,
    includeDisclosure: true,
    includeError: false,
    enabled: batchAnalysisEnabled && !!currentSession?.id,
  });

  // Persist to localStorage when state changes (only if not session-based)
  useEffect(() => {
    if (!sessionDismissalEnabled) {
      storage.set(STORAGE_KEYS.CROSS_INSIGHTS_DISMISSED, dismissed);
    }
  }, [dismissed, sessionDismissalEnabled]);

  // Wrapper for setDismissed that supports functional updates
  const setDismissed = useCallback(
    (value: boolean | ((prev: boolean) => boolean)) => {
      setDismissedState(value);
    },
    [],
  );

  // Toggle function for convenience
  const toggle = useCallback(() => {
    setDismissedState((prev) => !prev);
  }, []);

  // Keyboard shortcut handling (Cmd+I / Ctrl+I)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Check for Cmd+I (Mac) or Ctrl+I (Windows/Linux)
      if ((e.metaKey || e.ctrlKey) && e.key === "i") {
        e.preventDefault();
        setDismissedState((prev) => !prev);
      }
    };

    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Compute whether panel should be shown
  const shouldShow = !dismissed && crossInsights.length > 0;

  return {
    dismissed,
    setDismissed,
    toggle,
    shouldShow,
    crossInsights,
    confidence,
    isLoading,
    personaResult,
    disclosureResult,
    sessionDismissalEnabled,
    batchAnalysisEnabled,
  };
}

export default useCrossInsightsPanel;
