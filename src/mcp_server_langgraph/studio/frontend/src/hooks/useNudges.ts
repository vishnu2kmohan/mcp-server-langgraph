/**
 * useNudges Hook
 *
 * Sprint 3 - Phase 1.3 + 6.3: Nudge System + AI Smart Nudges
 *
 * Provides contextual hints and feature discovery prompts
 * with AI-powered timing and personalization.
 *
 * Features:
 * - First-time feature hints
 * - Keyboard shortcut reminders
 * - Feature upgrade prompts
 * - Contextual suggestions
 * - AI-powered nudge timing (Phase 6.3)
 *
 * Backend endpoint: POST /api/v1/ai/nudges/recommend
 *
 * @example
 * ```tsx
 * const { activeNudge, dismiss, trackAcceptance } = useNudges();
 *
 * // Show nudge when active
 * {activeNudge && (
 *   <NudgeTooltip
 *     message={activeNudge.message}
 *     onDismiss={() => dismiss(activeNudge.id)}
 *     onAccept={() => trackAcceptance(activeNudge.id)}
 *   />
 * )}
 * ```
 */

import { useState, useCallback, useEffect, useRef } from "react";
import { storage, STORAGE_KEYS } from "../utils/storage";

// =============================================================================
// Types
// =============================================================================

export type NudgeType = "tooltip" | "spotlight" | "banner" | "modal";
export type NudgePriority = "low" | "medium" | "high";

export interface Nudge {
  id: string;
  type: NudgeType;
  targetElement?: string;
  message: string;
  priority: NudgePriority;
  showAfterMs?: number;
  category: string;
}

export interface NudgeHistory {
  id: string;
  shownAt: Date;
  action: "accepted" | "dismissed" | "ignored";
}

export interface UseNudgesOptions {
  /** Enable AI-powered nudge recommendations (default: false) */
  enableAI?: boolean;
  /** Current page context */
  pageContext?: string;
  /** Maximum nudges to show per session */
  maxPerSession?: number;
}

export interface UseNudgesResult {
  /** Currently active nudge to display */
  activeNudge: Nudge | null;
  /** Dismiss a nudge */
  dismiss: (nudgeId: string) => void;
  /** Track nudge acceptance */
  trackAcceptance: (nudgeId: string) => void;
  /** Check if a specific nudge has been shown */
  hasShown: (nudgeId: string) => boolean;
  /** Get nudge history */
  getNudgeHistory: () => NudgeHistory[];
  /** Reset all nudge history (for testing) */
  resetHistory: () => void;
}

// =============================================================================
// Constants
// =============================================================================

const NUDGE_RECOMMEND_ENDPOINT = "/api/v1/ai/nudges/recommend";
const STORAGE_KEY = STORAGE_KEYS.NUDGE_HISTORY;

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook for contextual nudges and feature discovery prompts.
 */
export function useNudges(options: UseNudgesOptions = {}): UseNudgesResult {
  const { enableAI = false, pageContext, maxPerSession = 5 } = options;

  const [activeNudge, setActiveNudge] = useState<Nudge | null>(null);
  const [history, setHistory] = useState<NudgeHistory[]>(() => {
    const stored = storage.get<NudgeHistory[]>(STORAGE_KEY);
    if (stored && Array.isArray(stored)) {
      return stored.map((item) => ({
        ...item,
        shownAt: new Date(item.shownAt),
      }));
    }
    return [];
  });
  const [shownIds, setShownIds] = useState<Set<string>>(new Set());
  const sessionNudgeCount = useRef(0);
  const isMounted = useRef(true);
  const showTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Persist history to storage
  useEffect(() => {
    storage.set(STORAGE_KEY, history);
  }, [history]);

  // Cleanup on unmount
  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
      if (showTimeoutRef.current) {
        clearTimeout(showTimeoutRef.current);
      }
    };
  }, []);

  /**
   * Fetch nudge recommendation from AI
   */
  const fetchNudge = useCallback(async () => {
    if (!enableAI || sessionNudgeCount.current >= maxPerSession) {
      return;
    }

    try {
      const response = await fetch(NUDGE_RECOMMEND_ENDPOINT, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_context: {
            page: pageContext,
          },
          nudge_history: history.map((h) => ({
            id: h.id,
            shown_at: h.shownAt.toISOString(),
            action: h.action,
          })),
        }),
      });

      if (!response.ok) {
        return;
      }

      const data = await response.json();

      if (!isMounted.current) {
        return;
      }

      if (data.should_show && data.nudge) {
        const nudge = data.nudge as Nudge;
        const showDelay = nudge.showAfterMs ?? 0;

        if (showTimeoutRef.current) {
          clearTimeout(showTimeoutRef.current);
        }

        if (showDelay > 0) {
          showTimeoutRef.current = setTimeout(() => {
            if (isMounted.current) {
              setActiveNudge(nudge);
              setShownIds((prev) => new Set([...prev, nudge.id]));
              sessionNudgeCount.current++;
            }
          }, showDelay);
        } else {
          setActiveNudge(nudge);
          setShownIds((prev) => new Set([...prev, nudge.id]));
          sessionNudgeCount.current++;
        }
      }
    } catch {
      // Silently fail - nudges are not critical
    }
  }, [enableAI, pageContext, maxPerSession, history]);

  // Fetch nudge on mount when AI is enabled
  useEffect(() => {
    if (enableAI && pageContext) {
      fetchNudge();
    }
  }, [enableAI, pageContext, fetchNudge]);

  /**
   * Dismiss a nudge
   */
  const dismiss = useCallback((nudgeId: string) => {
    setActiveNudge((current) => {
      if (current?.id === nudgeId) {
        return null;
      }
      return current;
    });

    setHistory((prev) => [
      ...prev,
      {
        id: nudgeId,
        shownAt: new Date(),
        action: "dismissed",
      },
    ]);
  }, []);

  /**
   * Track nudge acceptance
   */
  const trackAcceptance = useCallback((nudgeId: string) => {
    setActiveNudge((current) => {
      if (current?.id === nudgeId) {
        return null;
      }
      return current;
    });

    setHistory((prev) => [
      ...prev,
      {
        id: nudgeId,
        shownAt: new Date(),
        action: "accepted",
      },
    ]);
  }, []);

  /**
   * Check if a nudge has been shown
   */
  const hasShown = useCallback(
    (nudgeId: string): boolean => {
      return shownIds.has(nudgeId) || history.some((h) => h.id === nudgeId);
    },
    [shownIds, history],
  );

  /**
   * Get nudge history
   */
  const getNudgeHistory = useCallback((): NudgeHistory[] => {
    return [...history];
  }, [history]);

  /**
   * Reset nudge history
   */
  const resetHistory = useCallback(() => {
    setHistory([]);
    setShownIds(new Set());
    sessionNudgeCount.current = 0;
    storage.remove(STORAGE_KEY);
  }, []);

  return {
    activeNudge,
    dismiss,
    trackAcceptance,
    hasShown,
    getNudgeHistory,
    resetHistory,
  };
}

export default useNudges;
