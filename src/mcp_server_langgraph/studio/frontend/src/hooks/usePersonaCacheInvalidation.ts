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
import { useNavigate } from "react-router";
import { useAppSelector } from "../store/hooks";
import { clearAllAICache } from "./useAICache";
import { devLogger } from "../utils/devLogger";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { saveCurrentRouteAsIntended } from "../utils/intendedRoute";

// Create prefixed logger for this hook
const logger = devLogger.withPrefix("[PersonaCacheInvalidation]");

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
 * // In App or StudioShellLayout
 * usePersonaCacheInvalidation();
 * ```
 */
export function usePersonaCacheInvalidation(
  options: UsePersonaCacheInvalidationOptions = {},
): UsePersonaCacheInvalidationResult {
  const navigate = useNavigate();
  const { enabled = true, invalidateBackend = false } = options;

  // Handle auth failure - redirect to login
  const handleAuthFailure = useCallback(() => {
    saveCurrentRouteAsIntended();
    navigate("/login", { replace: true });
  }, [navigate]);

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
          // Delete all cache entries for this user's prefix
          const userCachePrefix = `user:${userId}:`;
          const response = await authenticatedFetch(
            `/api/v1/cache/prefix/${encodeURIComponent(userCachePrefix)}`,
            {
              method: "DELETE",
              onAuthFailure: handleAuthFailure,
            },
          );

          if (!response.ok) {
            throw new Error(`Cache invalidation failed: ${response.status}`);
          }

          const result = await response.json();
          logger.debug(`Cleared ${result.deleted_count} backend cache entries`);
        } catch (error) {
          logger.warn("Backend invalidation failed:", error);
        }
      }

      setLastInvalidatedAt(new Date());
    } finally {
      setIsInvalidating(false);
    }
  }, [invalidateBackend, userId, handleAuthFailure]);

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
