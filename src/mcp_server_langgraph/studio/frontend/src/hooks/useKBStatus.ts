/**
 * useKBStatus Hook
 *
 * Hook for fetching and managing Knowledge Base status.
 * Provides status information for UI components like StatusBar and ChatInputForm.
 *
 * Features:
 * - Fetches KB status from backend API
 * - Provides derived state for UI components
 * - Supports polling for status updates
 * - Handles loading and error states gracefully
 */

import { useMemo } from "react";
import { useGetKBStatusQuery } from "../api";
import type {
  KBStatusValue,
  KBStatusResponseCamelCase,
  KBContextStats,
} from "../types/api";

// Re-export for consumers
export type { KBStatusValue, KBContextStats };

// =============================================================================
// Types
// =============================================================================

/** KB Status response from API (camelCase) - alias for local use */
export type KBStatusData = KBStatusResponseCamelCase;

/** Hook options */
export interface UseKBStatusOptions {
  /** Polling interval in milliseconds (default: 5 minutes) */
  pollingInterval?: number;
  /** Skip fetching (useful when KB features are disabled) */
  skip?: boolean;
}

/** Hook return type */
export interface UseKBStatusResult {
  // Raw data
  data: KBStatusData | undefined;
  status: KBStatusValue | undefined;
  statusMessage: string | undefined;

  // Loading/error states
  isLoading: boolean;
  isError: boolean;
  error: unknown;

  // Derived boolean states
  isReady: boolean;
  isMisconfigured: boolean;
  isUnavailable: boolean;

  // Collection info
  collectionName: string | undefined;
  vectorsCount: number;

  // Context stats for StatusBar
  contextStats: KBContextStats | undefined;

  // UI-compatible status
  kbStatusForUI: KBStatusValue | undefined;

  // Actions
  refetch: () => void;
}

// =============================================================================
// Constants
// =============================================================================

/** Default polling interval: 5 minutes */
const DEFAULT_POLLING_INTERVAL = 300000;

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook for fetching and managing KB status.
 *
 * @param options - Hook options including polling interval
 * @returns KB status data and derived states for UI components
 */
export function useKBStatus(
  options: UseKBStatusOptions = {},
): UseKBStatusResult {
  const { pollingInterval = DEFAULT_POLLING_INTERVAL, skip = false } = options;

  // Fetch KB status from API
  const { data, isLoading, isError, error, refetch } = useGetKBStatusQuery(
    undefined,
    {
      pollingInterval,
      skip,
    },
  );

  // Derive boolean states
  const status = data?.status;
  const isReady = status === "ready";
  const isMisconfigured = status === "misconfigured";
  const isUnavailable = status === "unavailable";

  // Build context stats for StatusBar
  const contextStats = useMemo((): KBContextStats | undefined => {
    if (!data || !isReady) return undefined;

    return {
      refsCount: data.contextTopK ?? 5,
      tokensUsed: 0, // Will be populated by actual usage tracking
      tokenBudget: data.contextTokenBudget ?? 2000,
    };
  }, [data, isReady]);

  return {
    // Raw data
    data,
    status,
    statusMessage: data?.message ?? undefined,

    // Loading/error states
    isLoading,
    isError,
    error,

    // Derived boolean states
    isReady,
    isMisconfigured,
    isUnavailable,

    // Collection info
    collectionName: data?.collectionName ?? undefined,
    vectorsCount: data?.vectorsCount ?? 0,

    // Context stats
    contextStats,

    // UI-compatible status (undefined when loading)
    kbStatusForUI: isLoading ? undefined : status,

    // Actions
    refetch,
  };
}
