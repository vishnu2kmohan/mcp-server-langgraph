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

import { useState, useEffect, useCallback, useRef } from "react";
import { useSelector } from "react-redux";
import { selectCurrentSession } from "../store/slices/sessionSlice";
import { usePersonalizeOnboardingMutation } from "../api";

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

/** Default timeout for AI requests - kept for API compatibility but not used with RTK Query */
const _DEFAULT_TIMEOUT_MS = 5000;

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
function inferExperienceLevel(
  initialActions: string[]
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
 * Hook for AI-powered onboarding personalization.
 *
 * @param options - Hook options
 * @returns Personalized onboarding recommendations
 */
export function useAIOnboarding(
  options: UseAIOnboardingOptions
): UseAIOnboardingResult {
  const {
    userId,
    initialActions = [],
    signupContext,
    enabled = true,
    timeoutMs: _timeoutMs, // Kept for API compatibility
  } = options;

  // RTK Query mutation
  const [personalizeOnboarding, { isLoading: isMutationLoading }] =
    usePersonalizeOnboardingMutation();

  // Get session context from Redux
  const currentSession = useSelector(selectCurrentSession);
  const _sessionId = currentSession?.id;

  // State
  const [detectedIntent, setDetectedIntent] = useState<string | null>(null);
  const [confidence, setConfidence] = useState<number>(0);
  const [recommendedPath, setRecommendedPath] = useState<OnboardingStep[]>([]);
  const [skipSteps, setSkipSteps] = useState<string[]>([]);
  const [personaPrediction, setPersonaPrediction] = useState<string | null>(
    null
  );
  const [isLoading, setIsLoading] = useState(enabled);
  const [error, setError] = useState<Error | null>(null);
  const hasFetchedRef = useRef(false);

  /**
   * Fetch personalization from AI backend via RTK Query
   */
  const fetchPersonalization = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const data = await personalizeOnboarding({
        detected_persona: userId,
        experience_level: inferExperienceLevel(initialActions),
        goals: initialActions,
        previous_tool_experience: signupContext?.referrer
          ? [signupContext.referrer]
          : undefined,
      }).unwrap();

      // Transform RTK Query response to hook's expected format
      // RTK Query returns: recommended_steps, skip_steps, estimated_duration_minutes, personalization_applied, reasoning
      // Hook expects: detected_intent, confidence, recommended_path, skip_steps, persona_prediction

      // Infer detected intent from recommended steps
      const firstStep = data.recommended_steps?.[0];
      const inferredIntent = firstStep
        ? firstStep.includes("template")
          ? "build_chatbot"
          : firstStep.includes("tour")
            ? "general_exploration"
            : "documentation_seeker"
        : "general_exploration";

      setDetectedIntent(inferredIntent);
      // Use personalization_applied as a confidence proxy
      setConfidence(data.personalization_applied ? 0.85 : 0.65);
      // Transform string steps to OnboardingStep objects
      setRecommendedPath(
        (data.recommended_steps || []).map((step) => ({
          step,
          guided: true,
        }))
      );
      setSkipSteps(data.skip_steps || []);
      // Infer persona from experience level or first step
      setPersonaPrediction(
        inferExperienceLevel(initialActions) === "expert"
          ? "alice-builder"
          : "bob"
      );
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
  }, [userId, initialActions, signupContext, personalizeOnboarding]);

  /**
   * Refresh personalization
   */
  const refresh = useCallback(() => {
    fetchPersonalization();
  }, [fetchPersonalization]);

  // Initial fetch on mount
  useEffect(() => {
    if (!enabled) {
      setIsLoading(false);
      return;
    }

    // Only fetch once per hook instance
    if (!hasFetchedRef.current) {
      fetchPersonalization();
    }
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
