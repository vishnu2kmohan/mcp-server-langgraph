/**
 * FeatureFlagContext
 *
 * React context for feature flags management.
 * Provides feature flag data from the API to all child components.
 * Enables feature gating throughout the application.
 */

import { createContext, useContext, useMemo, ReactNode } from "react";
import { useGetFeatureFlagsQuery } from "../api";
import type { FeatureFlags } from "../types/api";

/**
 * Context value type
 */
export interface FeatureFlagContextValue {
  /** All feature flags */
  flags: FeatureFlags;
  /** Whether flags are loading */
  isLoading: boolean;
  /** Whether there was an error loading flags */
  isError: boolean;
  /** Check if a specific feature is enabled */
  isEnabled: (flagName: string) => boolean;
}

/**
 * Default context value
 */
const defaultContextValue: FeatureFlagContextValue = {
  flags: {},
  isLoading: true,
  isError: false,
  isEnabled: () => false,
};

/**
 * Feature flag context
 */
const FeatureFlagContext =
  createContext<FeatureFlagContextValue>(defaultContextValue);

/**
 * Feature flag provider props
 */
export interface FeatureFlagProviderProps {
  children: ReactNode;
}

/**
 * Feature flag provider component.
 * Wraps the application to provide feature flags to all children.
 *
 * @example
 * ```tsx
 * // In App.tsx
 * <FeatureFlagProvider>
 *   <App />
 * </FeatureFlagProvider>
 * ```
 */
export function FeatureFlagProvider({ children }: FeatureFlagProviderProps) {
  const { data, isLoading, isError } = useGetFeatureFlagsQuery();

  const value = useMemo<FeatureFlagContextValue>(() => {
    const flags: FeatureFlags = data ?? {};

    return {
      flags,
      isLoading,
      isError,
      isEnabled: (flagName: string) => {
        if (isLoading || isError) return false;
        return flags[flagName] === true;
      },
    };
  }, [data, isLoading, isError]);

  return (
    <FeatureFlagContext.Provider value={value}>
      {children}
    </FeatureFlagContext.Provider>
  );
}

/**
 * Hook to access all feature flags and state.
 *
 * @example
 * ```tsx
 * const { flags, isLoading, isEnabled } = useFeatureFlags();
 *
 * if (isLoading) return <Loading />;
 *
 * return (
 *   <div>
 *     {isEnabled('cost_dashboard') && <CostDashboard />}
 *   </div>
 * );
 * ```
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useFeatureFlags(): FeatureFlagContextValue {
  return useContext(FeatureFlagContext);
}

/**
 * Hook to check if a specific feature is enabled.
 * Returns false while loading or on error.
 *
 * @param flagName - Name of the feature flag to check
 * @returns boolean indicating if the feature is enabled
 *
 * @example
 * ```tsx
 * const isObservabilityEnabled = useFeatureFlag('observability');
 *
 * return (
 *   <>
 *     {isObservabilityEnabled && (
 *       <Link to="/studio/observability">Traces</Link>
 *     )}
 *   </>
 * );
 * ```
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useFeatureFlag(flagName: string): boolean {
  const { isEnabled } = useFeatureFlags();
  return isEnabled(flagName);
}

export default FeatureFlagProvider;
