/**
 * useTierLimits Hook
 *
 * Provides tier-based limits and usage information.
 * Used to display usage indicators and upgrade prompts.
 * Part of Bob's user journey - surfacing tier limits to prevent confusion.
 */

import { useMemo } from "react";
import { useAppSelector } from "../store/hooks";
import { selectCurrentOrg } from "../store/slices/authSlice";
import { useListSessionsQuery } from "../api";

/**
 * Tier limits configuration
 * -1 means unlimited
 */
const TIER_LIMITS = {
  shared: {
    maxSessions: 5,
    maxWorkflows: 3,
    maxConnectionsPerProject: 2,
  },
  hybrid: {
    maxSessions: 20,
    maxWorkflows: 10,
    maxConnectionsPerProject: 10,
  },
  dedicated: {
    maxSessions: -1, // unlimited
    maxWorkflows: -1, // unlimited
    maxConnectionsPerProject: -1, // unlimited
  },
} as const;

type Tier = keyof typeof TIER_LIMITS;

export interface TierLimitsResult {
  /** Current organization tier */
  tier: Tier;
  /** Maximum sessions allowed (-1 for unlimited) */
  maxSessions: number;
  /** Maximum workflows allowed (-1 for unlimited) */
  maxWorkflows: number;
  /** Maximum connections per project (-1 for unlimited) */
  maxConnectionsPerProject: number;
  /** Current active session count */
  activeSessions: number;
  /** Whether usage is approaching the limit (>= 80%) */
  isApproachingLimit: boolean;
  /** Whether usage is at or over the limit */
  isAtLimit: boolean;
  /** Suggested tier to upgrade to, or null if already on highest */
  nextTier: "hybrid" | "dedicated" | null;
  /** Whether data is still loading */
  isLoading: boolean;
}

/**
 * Hook for accessing tier-based limits and current usage.
 *
 * @example
 * ```tsx
 * const {
 *   tier,
 *   maxSessions,
 *   activeSessions,
 *   isApproachingLimit,
 *   nextTier
 * } = useTierLimits();
 *
 * return (
 *   <>
 *     <TierUsageBar
 *       current={activeSessions}
 *       max={maxSessions}
 *       tier={tier}
 *       label="Active Sessions"
 *     />
 *     {isApproachingLimit && nextTier && (
 *       <UpgradePrompt
 *         show={true}
 *         targetTier={nextTier}
 *         feature="unlimited sessions"
 *       />
 *     )}
 *   </>
 * );
 * ```
 */
export function useTierLimits(): TierLimitsResult {
  const currentOrg = useAppSelector(selectCurrentOrg);

  // Determine tier from organization, default to "shared"
  const tier: Tier = (currentOrg?.tier as Tier) ?? "shared";

  // Get tier limits
  const limits = TIER_LIMITS[tier];

  // Fetch current sessions to count active sessions
  const { data: sessionsData, isLoading } = useListSessionsQuery({
    limit: 100, // Get enough to count
    status: "active",
  });

  // Calculate active session count
  const activeSessions = useMemo(() => {
    return sessionsData?.items?.length ?? 0;
  }, [sessionsData]);

  // Check if approaching limit (>= 80%)
  const isApproachingLimit = useMemo(() => {
    if (limits.maxSessions === -1) return false; // unlimited
    return activeSessions >= limits.maxSessions * 0.8;
  }, [activeSessions, limits.maxSessions]);

  // Check if at limit
  const isAtLimit = useMemo(() => {
    if (limits.maxSessions === -1) return false; // unlimited
    return activeSessions >= limits.maxSessions;
  }, [activeSessions, limits.maxSessions]);

  // Determine next tier for upgrade
  const nextTier = useMemo((): "hybrid" | "dedicated" | null => {
    switch (tier) {
      case "shared":
        return "hybrid";
      case "hybrid":
        return "dedicated";
      case "dedicated":
        return null;
      default:
        return "hybrid";
    }
  }, [tier]);

  return {
    tier,
    maxSessions: limits.maxSessions,
    maxWorkflows: limits.maxWorkflows,
    maxConnectionsPerProject: limits.maxConnectionsPerProject,
    activeSessions,
    isApproachingLimit,
    isAtLimit,
    nextTier,
    isLoading,
  };
}

export default useTierLimits;
