/**
 * TelemetryContext
 *
 * Provides injectable telemetry via React context for easier testing
 * and customization of telemetry behavior.
 *
 * Usage:
 * ```tsx
 * // In your app root
 * <TelemetryProvider>
 *   <App />
 * </TelemetryProvider>
 *
 * // In components
 * const telemetry = useSessionTelemetry();
 * telemetry.trackSessionCreation({ success: true, durationMs: 100 });
 *
 * // For testing - inject a custom instance
 * const testTelemetry = new SessionTelemetry();
 * <TelemetryProvider sessionTelemetry={testTelemetry}>
 *   <ComponentUnderTest />
 * </TelemetryProvider>
 * ```
 */
/* eslint-disable react-refresh/only-export-components -- Context files export both providers and hooks by design */
import { createContext, useContext, useMemo, useEffect, type ReactNode } from "react";
import { SessionTelemetry, sessionTelemetry as defaultSessionTelemetry } from "../utils/sessionTelemetry";
import { WebVitalsTracker, webVitals as defaultWebVitals } from "../utils/webVitals";

// =============================================================================
// Types
// =============================================================================

interface TelemetryContextValue {
  /** Session telemetry instance */
  sessionTelemetry: SessionTelemetry;
  /** Web Vitals tracker instance */
  webVitals: WebVitalsTracker;
}

interface TelemetryProviderProps {
  children: ReactNode;
  /** Custom session telemetry instance (for testing or customization) */
  sessionTelemetry?: SessionTelemetry;
  /** Custom Web Vitals tracker instance (for testing or customization) */
  webVitals?: WebVitalsTracker;
  /** Auto-start Web Vitals tracking on mount (default: false) */
  autoStartWebVitals?: boolean;
}

// =============================================================================
// Context
// =============================================================================

const TelemetryContext = createContext<TelemetryContextValue | null>(null);

// =============================================================================
// Provider
// =============================================================================

/**
 * Provider component for telemetry context.
 * Wraps your app to make telemetry available via hooks.
 */
export function TelemetryProvider({
  children,
  sessionTelemetry = defaultSessionTelemetry,
  webVitals = defaultWebVitals,
  autoStartWebVitals = false,
}: TelemetryProviderProps) {
  // Auto-start Web Vitals tracking if enabled
  useEffect(() => {
    if (autoStartWebVitals) {
      webVitals.start();
    }
  }, [autoStartWebVitals, webVitals]);

  const value = useMemo(
    () => ({
      sessionTelemetry,
      webVitals,
    }),
    [sessionTelemetry, webVitals],
  );

  return (
    <TelemetryContext.Provider value={value}>
      {children}
    </TelemetryContext.Provider>
  );
}

// =============================================================================
// Hooks
// =============================================================================

/**
 * Get all telemetry instances from context.
 * Throws if used outside of TelemetryProvider.
 */
export function useTelemetry(): TelemetryContextValue {
  const context = useContext(TelemetryContext);
  if (!context) {
    throw new Error("useTelemetry must be used within a TelemetryProvider");
  }
  return context;
}

/**
 * Get session telemetry instance from context.
 * Convenience hook that returns just the session telemetry.
 */
export function useSessionTelemetry(): SessionTelemetry {
  const { sessionTelemetry } = useTelemetry();
  return sessionTelemetry;
}

/**
 * Get Web Vitals tracker instance from context.
 * Convenience hook that returns just the Web Vitals tracker.
 */
export function useWebVitals(): WebVitalsTracker {
  const { webVitals } = useTelemetry();
  return webVitals;
}

// =============================================================================
// Re-export for convenience
// =============================================================================

export { SessionTelemetry } from "../utils/sessionTelemetry";
export { WebVitalsTracker } from "../utils/webVitals";
