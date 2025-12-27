/**
 * useAIIntelligenceConfig Hook
 *
 * Maps FeatureFlagContext flags to AIIntelligenceProvider config.
 * Bridges backend feature flags to the AI Intelligence system.
 *
 * Feature Flag Mapping (uses backend key names without 'enable_' prefix):
 * - studio_ai → global enabled
 * - agent_hitl → riskAssessment, decisionHistory
 * - ai_disclosure → contextualHelp
 * - ai_onboarding → learningPath
 * - ai_ux_websocket → webSocket.enabled
 *
 * NOTE: The backend get_ui_features_for_role() returns flags without the
 * 'enable_' prefix for cleaner frontend code. Always use the short names.
 */

import { useMemo } from "react";
import { useFeatureFlags } from "../contexts/FeatureFlagContext";
import { useAppSelector } from "../store/hooks";
import type { AIIntelligenceConfig } from "../contexts/AIIntelligenceContext";

// =============================================================================
// Types
// =============================================================================

export interface UseAIIntelligenceConfigReturn extends AIIntelligenceConfig {
  isLoading: boolean;
  isError: boolean;
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook that maps backend feature flags to AIIntelligenceProvider config.
 *
 * Usage:
 * ```tsx
 * const config = useAIIntelligenceConfig();
 * return <AIIntelligenceProvider config={config}>{children}</AIIntelligenceProvider>;
 * ```
 */
export function useAIIntelligenceConfig(): UseAIIntelligenceConfigReturn {
  const { isLoading, isError, isEnabled } = useFeatureFlags();

  // Get user context from Redux
  const persona = useAppSelector((state) => state.persona.persona);
  const subPersona = useAppSelector((state) => state.persona.subPersona);
  const userId = useAppSelector((state) => state.auth.user?.id ?? "");

  // Determine effective persona (prefer subPersona if available)
  const effectivePersona = subPersona ?? persona;

  // Map feature flags to AI config
  const config = useMemo<UseAIIntelligenceConfigReturn>(() => {
    // Disable all features while loading or on error
    if (isLoading || isError) {
      return {
        enabled: false,
        userId: "",
        persona: undefined,
        features: {},
        webSocket: { enabled: false },
        isLoading,
        isError,
      };
    }

    // Map backend flags to AIIntelligenceConfig
    // NOTE: Backend returns flags WITHOUT 'enable_' prefix (e.g., 'studio_ai' not 'enable_studio_ai')
    const enabled = isEnabled("studio_ai") || isEnabled("ai_ux");

    // Helper to check granular flag with fallback to master flag
    const isIntelligenceEnabled = (granularFlag: string): boolean =>
      isEnabled(granularFlag) || isEnabled("studio_ai");

    return {
      enabled,
      userId,
      persona: effectivePersona,
      features: {
        // Navigation prediction - maps from studio_ai
        navPrediction: isEnabled("studio_ai"),

        // Contextual help - maps from ai_disclosure
        contextualHelp: isEnabled("ai_disclosure"),

        // Learning path - maps from ai_onboarding
        learningPath: isEnabled("ai_onboarding"),

        // HITL features - map from agent_hitl
        riskAssessment: isEnabled("agent_hitl"),
        decisionHistory: isEnabled("agent_hitl"),

        // Granular Intelligence features - map from specific flags with fallback
        sessionIntelligence: isIntelligenceEnabled("session_intelligence"),
        conversationIntelligence: isIntelligenceEnabled(
          "conversation_intelligence",
        ),
        canvasIntelligence: isIntelligenceEnabled("canvas_intelligence"),
        traceIntelligence: isIntelligenceEnabled("trace_intelligence"),
        diagramIntelligence: isIntelligenceEnabled("diagram_intelligence"),
        hitlIntelligence: isEnabled("hitl_ai"),
        genuiComponents: isEnabled("genui"),
      },
      cacheConfig: {
        // Default cache configuration - can be extended later
        navPredictionStaleTime: 5 * 60 * 1000, // 5 minutes
        contextualHelpStaleTime: 10 * 60 * 1000, // 10 minutes
        learningPathStaleTime: 30 * 60 * 1000, // 30 minutes
        riskAssessmentStaleTime: 1 * 60 * 1000, // 1 minute
        decisionHistoryStaleTime: 5 * 60 * 1000, // 5 minutes
      },
      webSocket: {
        enabled: isEnabled("ai_ux_websocket"),
        endpoint: "/api/v1/ws/ai/suggestions",
      },
      isLoading,
      isError,
    };
  }, [isLoading, isError, isEnabled, userId, effectivePersona]);

  return config;
}
