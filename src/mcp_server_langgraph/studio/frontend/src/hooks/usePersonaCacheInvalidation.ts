/**
 * usePersonaCacheInvalidation Hook
 *
 * Automatically invalidates AI cache when persona changes.
 * Ensures cache consistency when user switches roles/personas.
 *
 * Features:
 * - Monitors persona changes in Redux
 * - Clears frontend AI cache on persona change
 * - Optional backend cache invalidation
 * - Manual invalidation function
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { useAppSelector } from "../store/hooks";
import { clearAllAICache } from "./useAICache";

// =============================================================================
// Types
// =============================================================================

export interface UsePersonaCacheInvalidationOptions {
  /** Whether to enable automatic invalidation on persona change (default: true) */
  enabled?: boolean;
  /** Whether to call backend to invalidate user-specific cache (default: false) */
  invalidateBackend?: boolean;
}

export interface UsePersonaCacheInvalidationResult {
  /** Whether cache invalidation is in progress */
  isInvalidating: boolean;
  /** Last time cache was invalidated */
  lastInvalidatedAt: Date | null;
  /** Manually trigger cache invalidation */
  invalidateNow: () => Promise<void>;
}

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook that invalidates AI cache when persona changes.
 *
 * Usage:
 * ```tsx
 * // In App or HybridShellLayout
 * usePersonaCacheInvalidation();
 * ```
 */
export function usePersonaCacheInvalidation(
  options: UsePersonaCacheInvalidationOptions = {}
): UsePersonaCacheInvalidationResult {
  const { enabled = true, invalidateBackend = false } = options;

  // Track invalidation state
  const [isInvalidating, setIsInvalidating] = useState(false);
  const [lastInvalidatedAt, setLastInvalidatedAt] = useState<Date | null>(null);

  // Get current persona from Redux
  const persona = useAppSelector((state) => state.persona.persona);
  const subPersona = useAppSelector((state) => state.persona.subPersona);
  const userId = useAppSelector((state) => state.auth.user?.id);

  // Track previous persona to detect changes
  const prevPersonaRef = useRef<string | null>(null);
  const prevSubPersonaRef = useRef<string | null>(null);
  const isInitialMount = useRef(true);

  /**
   * Perform cache invalidation
   */
  const invalidateCache = useCallback(async () => {
    setIsInvalidating(true);
    try {
      // Clear frontend AI cache
      clearAllAICache();

      // Optionally call backend to invalidate user-specific cache
      if (invalidateBackend && userId) {
        try {
          // TODO: Add API call when endpoint is available
          // await invalidateUserCache({ userId });
        } catch (error) {
          console.warn("[PersonaCacheInvalidation] Backend invalidation failed:", error);
        }
      }

      setLastInvalidatedAt(new Date());
    } finally {
      setIsInvalidating(false);
    }
  }, [invalidateBackend, userId]);

  /**
   * Manual invalidation function
   */
  const invalidateNow = useCallback(async () => {
    await invalidateCache();
  }, [invalidateCache]);

  // Monitor persona changes and invalidate cache
  useEffect(() => {
    if (!enabled) return;

    // Skip initial mount
    if (isInitialMount.current) {
      isInitialMount.current = false;
      prevPersonaRef.current = persona;
      prevSubPersonaRef.current = subPersona;
      return;
    }

    // Check if persona or subPersona changed
    const personaChanged = prevPersonaRef.current !== persona;
    const subPersonaChanged = prevSubPersonaRef.current !== subPersona;

    if (personaChanged || subPersonaChanged) {
      // Update refs
      prevPersonaRef.current = persona;
      prevSubPersonaRef.current = subPersona;

      // Invalidate cache
      invalidateCache();
    }
  }, [enabled, persona, subPersona, invalidateCache]);

  return {
    isInvalidating,
    lastInvalidatedAt,
    invalidateNow,
  };
}
