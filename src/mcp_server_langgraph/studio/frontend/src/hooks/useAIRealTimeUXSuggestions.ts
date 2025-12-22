/**
 * useAIRealTimeUXSuggestions
 *
 * Integrates real-time AI suggestions with AIIntelligence context.
 * Provides WebSocket-based real-time UX suggestions using centralized configuration.
 *
 * Features:
 * - Uses AIIntelligence context for configuration
 * - Respects global AI feature toggle
 * - Respects WebSocket-specific toggle
 * - Integrates with error reporting
 * - Uses cached suggestions when appropriate
 */

import { useEffect, useMemo } from "react";
import { useAIIntelligence } from "../contexts/AIIntelligenceContext";
import {
  useAIRealTimeSuggestions,
  type Suggestion,
  type SuggestionRequestContext,
} from "./useAIRealTimeSuggestions";

// =============================================================================
// Types
// =============================================================================

export interface UseAIRealTimeUXSuggestionsOptions {
  /** Override reconnection interval (uses default from context if not provided) */
  reconnectInterval?: number;
  /** Override max reconnection attempts */
  maxReconnectAttempts?: number;
  /** Override heartbeat interval */
  heartbeatInterval?: number;
}

export interface UseAIRealTimeUXSuggestionsResult {
  /** Whether WebSocket is connected */
  isConnected: boolean;
  /** Current connection error, if any */
  error: Error | null;
  /** Current list of active suggestions */
  suggestions: Suggestion[];
  /** IDs of dismissed suggestions */
  dismissedIds: string[];
  /** Number of reconnection attempts made */
  reconnectAttempts: number;
  /** Timestamp of last successful heartbeat */
  lastHeartbeat: number | null;
  /** Whether real-time UX suggestions are enabled */
  isEnabled: boolean;
  /** Request new suggestions with context */
  requestSuggestions: (context: SuggestionRequestContext) => void;
  /** Clear all current suggestions */
  clearSuggestions: () => void;
  /** Dismiss a specific suggestion by ID */
  dismissSuggestion: (id: string) => void;
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook for real-time UX suggestions integrated with AIIntelligence context.
 *
 * Uses the centralized AIIntelligence configuration for:
 * - Global AI feature toggle
 * - WebSocket-specific toggle
 * - Error reporting
 *
 * @param options - Optional configuration overrides
 * @returns WebSocket state and control functions
 *
 * @example
 * ```tsx
 * const {
 *   isConnected,
 *   isEnabled,
 *   suggestions,
 *   requestSuggestions,
 * } = useAIRealTimeUXSuggestions();
 *
 * // Request suggestions for current context
 * if (isEnabled) {
 *   requestSuggestions({ page: 'chat', action: 'typing' });
 * }
 * ```
 */
export function useAIRealTimeUXSuggestions(
  options: UseAIRealTimeUXSuggestionsOptions = {}
): UseAIRealTimeUXSuggestionsResult {
  const { reconnectInterval, maxReconnectAttempts, heartbeatInterval } =
    options;

  // Get configuration from AIIntelligence context
  const { enabled: aiEnabled, webSocket, reportError } = useAIIntelligence();

  // Determine if WebSocket suggestions are enabled
  // Both global AI and WebSocket-specific toggle must be enabled
  const isEnabled = aiEnabled && webSocket.enabled;

  // Use the base WebSocket hook
  const {
    isConnected,
    error,
    suggestions,
    dismissedIds,
    reconnectAttempts,
    lastHeartbeat,
    requestSuggestions,
    clearSuggestions,
    dismissSuggestion,
  } = useAIRealTimeSuggestions({
    enabled: isEnabled,
    reconnectInterval: reconnectInterval,
    maxReconnectAttempts: maxReconnectAttempts,
    heartbeatInterval: heartbeatInterval,
  });

  // Report errors to the AIIntelligence context
  useEffect(() => {
    if (error) {
      reportError(error);
    }
  }, [error, reportError]);

  // Return memoized result
  return useMemo(
    () => ({
      isConnected,
      error,
      suggestions,
      dismissedIds,
      reconnectAttempts,
      lastHeartbeat,
      isEnabled,
      requestSuggestions,
      clearSuggestions,
      dismissSuggestion,
    }),
    [
      isConnected,
      error,
      suggestions,
      dismissedIds,
      reconnectAttempts,
      lastHeartbeat,
      isEnabled,
      requestSuggestions,
      clearSuggestions,
      dismissSuggestion,
    ]
  );
}

// Re-export types from base hook for convenience
export type { Suggestion, SuggestionRequestContext };
