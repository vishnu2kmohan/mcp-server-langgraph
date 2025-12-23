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
// Connected AI Intelligence Provider (Bridges Feature Flags to AI Config)
// ADR-0068: WebSocket Standardization - Auto-configures from FeatureFlagContext
// =============================================================================

export { ConnectedAIIntelligenceProvider } from "./ConnectedAIIntelligenceProvider";
export type { ConnectedAIIntelligenceProviderProps } from "./ConnectedAIIntelligenceProvider";

// =============================================================================
// Preferences Context
// =============================================================================

export { PreferencesProvider, usePreferences } from "./PreferencesContext";

// =============================================================================
// Telemetry Context
// =============================================================================

export { TelemetryProvider, useTelemetry } from "./TelemetryContext";
