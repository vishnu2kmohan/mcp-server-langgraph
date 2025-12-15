/**
 * useOnboarding Hook
 *
 * Manages onboarding state for first-time users.
 * Tracks whether the user has completed onboarding using localStorage.
 */

import { useState, useCallback, useEffect } from "react";

const ONBOARDING_KEY = "langgraph_onboarding_completed";

export interface UseOnboardingReturn {
  /** Whether onboarding has been completed */
  isCompleted: boolean;
  /** Whether the onboarding modal should be shown */
  shouldShowModal: boolean;
  /** Mark onboarding as completed */
  complete: () => void;
  /** Skip onboarding without completing */
  skip: () => void;
  /** Reset onboarding state (for testing) */
  reset: () => void;
  /** Whether the state is still loading from localStorage */
  isLoading: boolean;
}

export function useOnboarding(): UseOnboardingReturn {
  const [isCompleted, setIsCompleted] = useState(true); // Default to true to prevent flash
  const [isLoading, setIsLoading] = useState(true);

  // Load state from localStorage on mount
  useEffect(() => {
    try {
      const stored = localStorage.getItem(ONBOARDING_KEY);
      setIsCompleted(stored === "true");
    } catch {
      // localStorage not available (SSR, private browsing, etc.)
      setIsCompleted(true);
    }
    setIsLoading(false);
  }, []);

  const complete = useCallback(() => {
    try {
      localStorage.setItem(ONBOARDING_KEY, "true");
    } catch {
      // Ignore localStorage errors
    }
    setIsCompleted(true);
  }, []);

  const skip = useCallback(() => {
    // Skip without marking as completed - will show again next time
    // But for this session, don't show again
    setIsCompleted(true);
  }, []);

  const reset = useCallback(() => {
    try {
      localStorage.removeItem(ONBOARDING_KEY);
    } catch {
      // Ignore localStorage errors
    }
    setIsCompleted(false);
  }, []);

  return {
    isCompleted,
    shouldShowModal: !isLoading && !isCompleted,
    complete,
    skip,
    reset,
    isLoading,
  };
}
