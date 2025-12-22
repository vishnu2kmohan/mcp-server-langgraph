/**
 * useAIIntelligenceConfig Hook
 *
 * Maps FeatureFlagContext flags to AIIntelligenceProvider config.
 * Bridges backend feature flags to the AI Intelligence system.
 *
 * Feature Flag Mapping:
 * - enable_studio_ai → global enabled
 * - enable_agent_hitl → riskAssessment, decisionHistory
 * - enable_ai_disclosure → contextualHelp
 * - enable_ai_onboarding → learningPath
 * - enable_ai_ux_websocket → webSocket.enabled
 */

import { useMemo } from "react";
import { useFeatureFlags } from "../contexts/FeatureFlagContext";
import { useAppSelector } from "../store/hooks";
import type { AIIntelligenceConfig } from "../contexts/AIIntelligenceContext";

// =============================================================================
// Types
// =============================================================================

interface UseAIIntelligenceConfigReturn extends AIIntelligenceConfig {
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
    const enabled = isEnabled("enable_studio_ai") || isEnabled("enable_ai_ux");

    // Helper to check granular flag with fallback to master flag
    const isIntelligenceEnabled = (granularFlag: string): boolean =>
      isEnabled(granularFlag) || isEnabled("enable_studio_ai");

    return {
      enabled,
      userId,
      persona: effectivePersona,
      features: {
        // Navigation prediction - maps from enable_studio_ai
        navPrediction: isEnabled("enable_studio_ai"),

        // Contextual help - maps from enable_ai_disclosure
        contextualHelp: isEnabled("enable_ai_disclosure"),

        // Learning path - maps from enable_ai_onboarding
        learningPath: isEnabled("enable_ai_onboarding"),

        // HITL features - map from enable_agent_hitl
        riskAssessment: isEnabled("enable_agent_hitl"),
        decisionHistory: isEnabled("enable_agent_hitl"),

        // Granular Intelligence features - map from specific flags with fallback
        sessionIntelligence: isIntelligenceEnabled("enable_session_intelligence"),
        conversationIntelligence: isIntelligenceEnabled("enable_conversation_intelligence"),
        canvasIntelligence: isIntelligenceEnabled("enable_canvas_intelligence"),
        traceIntelligence: isIntelligenceEnabled("enable_trace_intelligence"),
        diagramIntelligence: isIntelligenceEnabled("enable_diagram_intelligence"),
        hitlIntelligence: isEnabled("enable_hitl_ai"),
        genuiComponents: isEnabled("enable_genui"),
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
        enabled: isEnabled("enable_ai_ux_websocket"),
        endpoint: "/ws/ai/suggestions",
      },
      isLoading,
      isError,
    };
  }, [isLoading, isError, isEnabled, userId, effectivePersona]);

  return config;
}
