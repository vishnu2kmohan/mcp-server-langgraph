/**
 * AIIntelligenceContext
 *
 * Provides unified context for AI Intelligence feature flags and configuration.
 * This centralizes AI feature management across all components.
 *
 * Features:
 * - Centralized AI feature flag management
 * - User context propagation
 * - Cache configuration
 * - WebSocket connection state
 * - Error tracking and reporting
 *
 * Usage:
 * ```tsx
 * <AIIntelligenceProvider config={{ enabled: true, userId: "user-123" }}>
 *   <App />
 * </AIIntelligenceProvider>
 *
 * // In components:
 * const { isNavPredictionEnabled, userId } = useAIIntelligence();
 * ```
 */
/* eslint-disable react-refresh/only-export-components -- Exports context types and hook alongside component */

import {
  createContext,
  useContext,
  useMemo,
  useState,
  useCallback,
  type ReactNode,
} from "react";

// =============================================================================
// Types
// =============================================================================

export interface AIFeatureFlags {
  /** Navigation prediction (ActivityBar smart ordering) */
  navPrediction?: boolean;
  /** Context-aware help content */
  contextualHelp?: boolean;
  /** Personalized learning path */
  learningPath?: boolean;
  /** HITL risk assessment */
  riskAssessment?: boolean;
  /** HITL decision history */
  decisionHistory?: boolean;
  /** Trace intelligence (summary, anomaly) */
  traceIntelligence?: boolean;
  /** Canvas intelligence (code analysis, diff) */
  canvasIntelligence?: boolean;
  /** Session intelligence (summary, grouping) */
  sessionIntelligence?: boolean;
  /** Conversation intelligence (intent, goal) */
  conversationIntelligence?: boolean;
  /** Diagram intelligence (analysis, to-code) */
  diagramIntelligence?: boolean;
  /** HITL AI intelligence (risk assessment beyond basic HITL) */
  hitlIntelligence?: boolean;
  /** Generative UI components */
  genuiComponents?: boolean;
}

export interface AICacheConfig {
  /** Stale time for navigation predictions (default: 5 min) */
  navPredictionStaleTime?: number;
  /** Stale time for contextual help (default: 10 min) */
  contextualHelpStaleTime?: number;
  /** Stale time for learning path (default: 30 min) */
  learningPathStaleTime?: number;
  /** Stale time for risk assessment (default: 1 min) */
  riskAssessmentStaleTime?: number;
  /** Stale time for decision history (default: 5 min) */
  decisionHistoryStaleTime?: number;
}

export interface AIWebSocketConfig {
  /** Whether WebSocket is enabled for real-time updates */
  enabled?: boolean;
  /** WebSocket endpoint URL */
  endpoint?: string;
}

export interface AIIntelligenceConfig {
  /** Master toggle for all AI features */
  enabled?: boolean;
  /** Current user ID for AI context */
  userId?: string;
  /** Current user persona */
  persona?: string;
  /** Individual feature flags */
  features?: AIFeatureFlags;
  /** Cache configuration */
  cacheConfig?: AICacheConfig;
  /** WebSocket configuration */
  webSocket?: AIWebSocketConfig;
}

export interface AIIntelligenceContextValue {
  /** Whether AI features are globally enabled */
  enabled: boolean;
  /** Current user ID */
  userId: string;
  /** Current persona */
  persona: string | null;
  /** Individual feature flags */
  features: Required<AIFeatureFlags>;
  /** Cache configuration with defaults */
  cacheConfig: Required<AICacheConfig>;
  /** WebSocket configuration */
  webSocket: Required<AIWebSocketConfig>;
  /** Whether there's a global AI error */
  hasError: boolean;
  /** Current error if any */
  error: Error | null;
  /** Report an AI error */
  reportError: (error: Error) => void;
  /** Clear current error */
  clearError: () => void;

  // Convenience helpers (check both global and feature flags)
  isNavPredictionEnabled: boolean;
  isContextualHelpEnabled: boolean;
  isLearningPathEnabled: boolean;
  isRiskAssessmentEnabled: boolean;
  isDecisionHistoryEnabled: boolean;
  isTraceIntelligenceEnabled: boolean;
  isCanvasIntelligenceEnabled: boolean;
  isSessionIntelligenceEnabled: boolean;
  isConversationIntelligenceEnabled: boolean;
}

// =============================================================================
// Defaults
// =============================================================================

const DEFAULT_FEATURES: Required<AIFeatureFlags> = {
  navPrediction: false,
  contextualHelp: false,
  learningPath: false,
  riskAssessment: false,
  decisionHistory: false,
  traceIntelligence: false,
  canvasIntelligence: false,
  sessionIntelligence: false,
  conversationIntelligence: false,
  diagramIntelligence: false,
  hitlIntelligence: false,
  genuiComponents: false,
};

const DEFAULT_CACHE_CONFIG: Required<AICacheConfig> = {
  navPredictionStaleTime: 5 * 60 * 1000, // 5 minutes
  contextualHelpStaleTime: 10 * 60 * 1000, // 10 minutes
  learningPathStaleTime: 30 * 60 * 1000, // 30 minutes
  riskAssessmentStaleTime: 1 * 60 * 1000, // 1 minute
  decisionHistoryStaleTime: 5 * 60 * 1000, // 5 minutes
};

const DEFAULT_WEBSOCKET_CONFIG: Required<AIWebSocketConfig> = {
  enabled: false,
  endpoint: "/ws/ai/suggestions",
};

const DEFAULT_CONTEXT_VALUE: AIIntelligenceContextValue = {
  enabled: false,
  userId: "",
  persona: null,
  features: DEFAULT_FEATURES,
  cacheConfig: DEFAULT_CACHE_CONFIG,
  webSocket: DEFAULT_WEBSOCKET_CONFIG,
  hasError: false,
  error: null,
  reportError: () => {},
  clearError: () => {},
  isNavPredictionEnabled: false,
  isContextualHelpEnabled: false,
  isLearningPathEnabled: false,
  isRiskAssessmentEnabled: false,
  isDecisionHistoryEnabled: false,
  isTraceIntelligenceEnabled: false,
  isCanvasIntelligenceEnabled: false,
  isSessionIntelligenceEnabled: false,
  isConversationIntelligenceEnabled: false,
};

// =============================================================================
// Context
// =============================================================================

const AIIntelligenceContext = createContext<AIIntelligenceContextValue>(
  DEFAULT_CONTEXT_VALUE,
);

// =============================================================================
// Provider
// =============================================================================

export interface AIIntelligenceProviderProps {
  children: ReactNode;
  config?: AIIntelligenceConfig;
}

export function AIIntelligenceProvider({
  children,
  config = {},
}: AIIntelligenceProviderProps) {
  const [error, setError] = useState<Error | null>(null);

  const enabled = config.enabled ?? false;
  const userId = config.userId ?? "";
  const persona = config.persona ?? null;

  const features: Required<AIFeatureFlags> = useMemo(
    () => ({
      ...DEFAULT_FEATURES,
      ...config.features,
    }),
    [config.features],
  );

  const cacheConfig: Required<AICacheConfig> = useMemo(
    () => ({
      ...DEFAULT_CACHE_CONFIG,
      ...config.cacheConfig,
    }),
    [config.cacheConfig],
  );

  const webSocket: Required<AIWebSocketConfig> = useMemo(
    () => ({
      ...DEFAULT_WEBSOCKET_CONFIG,
      ...config.webSocket,
    }),
    [config.webSocket],
  );

  const reportError = useCallback((err: Error) => {
    setError(err);
    // Could also send to error tracking service
    console.error("[AIIntelligence] Error:", err);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const value: AIIntelligenceContextValue = useMemo(
    () => ({
      enabled,
      userId,
      persona,
      features,
      cacheConfig,
      webSocket,
      hasError: error !== null,
      error,
      reportError,
      clearError,

      // Convenience helpers - check both global and feature flag
      isNavPredictionEnabled: enabled && features.navPrediction,
      isContextualHelpEnabled: enabled && features.contextualHelp,
      isLearningPathEnabled: enabled && features.learningPath,
      isRiskAssessmentEnabled: enabled && features.riskAssessment,
      isDecisionHistoryEnabled: enabled && features.decisionHistory,
      isTraceIntelligenceEnabled: enabled && features.traceIntelligence,
      isCanvasIntelligenceEnabled: enabled && features.canvasIntelligence,
      isSessionIntelligenceEnabled: enabled && features.sessionIntelligence,
      isConversationIntelligenceEnabled:
        enabled && features.conversationIntelligence,
    }),
    [
      enabled,
      userId,
      persona,
      features,
      cacheConfig,
      webSocket,
      error,
      reportError,
      clearError,
    ],
  );

  return (
    <AIIntelligenceContext.Provider value={value}>
      {children}
    </AIIntelligenceContext.Provider>
  );
}

// =============================================================================
// Hook
// =============================================================================

/**
 * Hook to access AI Intelligence context.
 *
 * Can be used outside of provider (returns disabled defaults).
 */
export function useAIIntelligence(): AIIntelligenceContextValue {
  return useContext(AIIntelligenceContext);
}

// =============================================================================
// Exports
// =============================================================================

export { AIIntelligenceContext };
