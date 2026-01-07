/**
 * useAIOnboarding Hook
 *
 * AI-powered onboarding personalization hook.
 * Phase 6.5: AI Onboarding Personalization
 *
 * Detects user intent from initial actions and provides
 * a personalized onboarding path with recommendations.
 *
 * Features:
 * - Intent detection from user actions
 * - Personalized onboarding path generation
 * - Skip step recommendations for advanced users
 * - Persona prediction based on behavior
 * - Graceful error handling with fallback
 *
 * @example
 * ```tsx
 * const {
 *   detectedIntent,
 *   confidence,
 *   recommendedPath,
 *   skipSteps,
 *   personaPrediction,
 *   isLoading,
 *   error,
 *   refresh,
 * } = useAIOnboarding({
 *   userId: 'new-user-123',
 *   initialActions: ['viewed_workflows', 'clicked_templates'],
 *   signupContext: { referrer: 'github', utm_source: 'docs' },
 * });
 * ```
 */

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useSelector } from "react-redux";
import { selectCurrentSession } from "../store/slices/sessionSlice";
import { usePersonalizeOnboardingMutation } from "../api";
import { sessionStore } from "../utils/storage";

// =============================================================================
// Constants for Deduplication
// =============================================================================

/**
 * Stable empty array constant to prevent reference changes in dependency arrays.
 * Using inline `[]` creates a new array on every render, causing unnecessary
 * useCallback/useEffect re-evaluations.
 */
const EMPTY_ARRAY: readonly string[] = Object.freeze([]);

/**
 * Session storage key for tracking if personalization was already fetched.
 * This provides cross-remount deduplication protection.
 * Uses the sessionStore utility for consistent storage abstraction.
 */
const SESSION_STORAGE_KEY = "studio-ai-onboarding-fetched";

/**
 * Onboarding path step from AI backend
 */
export interface OnboardingStep {
  /** Step identifier */
  step: string;
  /** Optional template for template selection step */
  template?: string;
  /** Whether this step should be guided */
  guided?: boolean;
  /** Focus area for the step */
  focus?: string;
  /** Duration for timed steps */
  duration?: string;
  /** Filter criteria for gallery steps */
  filter?: string;
  /** Feature to highlight */
  highlight?: string;
}

/**
 * Signup context for better personalization
 */
export interface SignupContext {
  /** Referrer URL or source */
  referrer?: string;
  /** UTM source parameter */
  utm_source?: string;
  /** UTM campaign parameter */
  utm_campaign?: string;
  /** UTM medium parameter */
  utm_medium?: string;
}

/**
 * Hook configuration options
 */
export interface UseAIOnboardingOptions {
  /** User ID for personalization (optional, uses session ID if not provided) */
  userId?: string;
  /** Initial actions taken by the user */
  initialActions?: string[];
  /** Signup context for additional signals */
  signupContext?: SignupContext;
  /** Whether to fetch personalization (default: true) */
  enabled?: boolean;
  /** Request timeout in milliseconds (default: 5000ms) */
  timeoutMs?: number;
}

// Note: Default timeout of 5000ms no longer used - RTK Query handles timeouts internally

/**
 * Hook result
 */
export interface UseAIOnboardingResult {
  /** Detected user intent */
  detectedIntent: string | null;
  /** Confidence score for intent detection (0-1) */
  confidence: number;
  /** Recommended onboarding path steps */
  recommendedPath: OnboardingStep[];
  /** Steps to skip for this user */
  skipSteps: string[];
  /** Predicted persona based on behavior */
  personaPrediction: string | null;
  /** Whether personalization is being fetched */
  isLoading: boolean;
  /** Error if fetch failed */
  error: Error | null;
  /** Manually refresh personalization */
  refresh: () => void;
}

// =============================================================================
// Helper Functions
// =============================================================================

/**
 * Map experience level from signup context to RTK Query format
 */
function _inferExperienceLevel(
  initialActions: string[],
): "beginner" | "intermediate" | "expert" {
  // Advanced users typically have more targeted initial actions
  if (initialActions.length > 3) {
    return "expert";
  } else if (initialActions.length > 1) {
    return "intermediate";
  }
  return "beginner";
}

/**
 * Check if personalization was already fetched in this session.
 * Uses sessionStore utility for cross-remount deduplication.
 */
function wasAlreadyFetched(userId: string | undefined): boolean {
  const key = `${SESSION_STORAGE_KEY}-${userId || "anonymous"}`;
  return sessionStore.get<boolean>(key, false) === true;
}

/**
 * Mark personalization as fetched for this session.
 */
function markAsFetched(userId: string | undefined): void {
  const key = `${SESSION_STORAGE_KEY}-${userId || "anonymous"}`;
  sessionStore.set(key, true);
}

/**
 * Clear the fetched flag (for manual refresh).
 */
function clearFetchedFlag(userId: string | undefined): void {
  const key = `${SESSION_STORAGE_KEY}-${userId || "anonymous"}`;
  sessionStore.remove(key);
}

/**
 * Hook for AI-powered onboarding personalization.
 *
 * @param options - Hook options
 * @returns Personalized onboarding recommendations
 */
export function useAIOnboarding(
  options: UseAIOnboardingOptions,
): UseAIOnboardingResult {
  const {
    userId,
    initialActions,
    signupContext,
    enabled = true,
    timeoutMs: _timeoutMs, // Kept for API compatibility
  } = options;

  // Memoize initialActions to prevent reference changes causing refetches
  // Use stable EMPTY_ARRAY when no actions provided
  const stableInitialActions = useMemo(
    () => initialActions ?? EMPTY_ARRAY,
    // Use JSON.stringify for deep comparison of array contents
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(initialActions)],
  );

  // Memoize signupContext to prevent reference changes
  const stableSignupContext = useMemo(
    () => signupContext,
    // Use JSON.stringify for deep comparison of object contents
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [JSON.stringify(signupContext)],
  );

  // RTK Query mutation
  const [personalizeOnboarding, { isLoading: isMutationLoading }] =
    usePersonalizeOnboardingMutation();

  // Get session context from Redux
  const _currentSession = useSelector(selectCurrentSession);

  // State
  const [detectedIntent, setDetectedIntent] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number>(0);
  const [recommendedPath, setRecommendedPath] = useState<OnboardingStep[]>([]);
  const [skipSteps, setSkipSteps] = useState<string[]>([]);
  const [personaPrediction, setPersonaPrediction] = useState<string | null>(
    null,
  );
  const [isLoading, setIsLoading] = useState(enabled);
  const [error, setError] = useState<Error | null>(null);

  // Ref to track if fetch was triggered in this hook instance
  const hasFetchedRef = useRef(false);

  // Check if already fetched in sessionStorage (survives remounts)
  const wasSessionFetched = useRef(wasAlreadyFetched(userId));

  /**
   * Fetch personalization from AI backend via RTK Query
   *
   * Schema: OnboardingPersonalizeRequest (ai_ux.py:307)
   * - user_id: str (required)
   * - initial_actions: list[str] (optional)
   * - signup_context: SignupContext | None (optional)
   */
  const fetchPersonalization = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await personalizeOnboarding({
        user_id: userId || "anonymous",
        initial_actions: stableInitialActions as string[],
        signup_context: stableSignupContext
          ? {
              referrer: stableSignupContext.referrer,
              utm_source: stableSignupContext.utm_source,
            }
          : undefined,
      }).unwrap();

      // OnboardingPersonalizeResponse from generated-api.ts (ADR-0091)
      // Fields: detected_intent, confidence, recommended_path, skip_steps?, persona_prediction?
      setDetectedIntent(data.detected_intent);
      setConfidence(data.confidence);
      // Transform generated OnboardingStep[] to hook's OnboardingStep format
      setRecommendedPath(
        (data.recommended_path || []).map((step) => ({
          step: step.step,
          guided: step.guided,
          focus: step.focus ?? undefined,
          template: step.template ?? undefined,
        })),
      );
      setSkipSteps(data.skip_steps || []);
      setPersonaPrediction(data.persona_prediction ?? null);

      // Mark as fetched in sessionStorage for cross-remount deduplication
      markAsFetched(userId);
    } catch (err) {
      const errorToSet =
        err instanceof Error
          ? err
          : new Error("Failed to personalize onboarding");

      setError(errorToSet);

      // Reset to defaults on error
      setDetectedIntent(null);
      setConfidence(0);
      setRecommendedPath([]);
      setSkipSteps([]);
      setPersonaPrediction(null);
    } finally {
      setIsLoading(false);
      hasFetchedRef.current = true;
    }
  }, [
    userId,
    stableInitialActions,
    stableSignupContext,
    personalizeOnboarding,
  ]);

  /**
   * Refresh personalization (manual trigger).
   * Clears the session storage flag to allow a fresh fetch.
   */
  const refresh = useCallback(() => {
    // Clear the session flag to allow re-fetch
    clearFetchedFlag(userId);
    wasSessionFetched.current = false;
    hasFetchedRef.current = false;
    fetchPersonalization();
  }, [fetchPersonalization, userId]);

  // Initial fetch on mount (with multi-layer deduplication)
  useEffect(() => {
    if (!enabled) {
      setIsLoading(false);
      return;
    }

    // Layer 1: Check if already fetched in this hook instance
    if (hasFetchedRef.current) {
      return;
    }

    // Layer 2: Check if already fetched in this browser session
    // (survives component remounts)
    if (wasSessionFetched.current) {
      setIsLoading(false);
      return;
    }

    fetchPersonalization();
  }, [enabled, fetchPersonalization]);

  return {
    detectedIntent,
    confidence,
    recommendedPath,
    skipSteps,
    personaPrediction,
    isLoading: isLoading || isMutationLoading,
    error,
    refresh,
  };
}

export default useAIOnboarding;
