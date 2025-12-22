/**
 * Contexts Index
 *
 * Central export for all React contexts in the application.
 */

// =============================================================================
// AI Intelligence Context (Architecture: Centralized AI Feature Management)
// =============================================================================

export {
  AIIntelligenceProvider,
  AIIntelligenceContext,
  useAIIntelligence,
} from "./AIIntelligenceContext";
export type {
  AIFeatureFlags,
  AICacheConfig,
  AIWebSocketConfig,
  AIIntelligenceConfig,
  AIIntelligenceContextValue,
  AIIntelligenceProviderProps,
} from "./AIIntelligenceContext";

// =============================================================================
// Preferences Context
// =============================================================================

export {
  PreferencesProvider,
  PreferencesContext,
  usePreferences,
} from "./PreferencesContext";

// =============================================================================
// Telemetry Context
// =============================================================================

export {
  TelemetryProvider,
  TelemetryContext,
  useTelemetry,
} from "./TelemetryContext";
