/**
 * useAIDisclosure Hook
 *
 * Sprint 3 - Phase 6.1: AI-Augmented Progressive Disclosure
 *
 * Uses AI to dynamically adjust UI complexity based on user behavior patterns.
 * Extends the base useProgressiveDisclosure hook with AI recommendations.
 *
 * Features:
 * - Analyze click patterns and feature usage
 * - Predict optimal disclosure level transitions
 * - Generate personalized "level up" nudges when ready
 * - Configurable confidence threshold
 *
 * Backend endpoint: POST /api/v1/ai/disclosure/analyze
 *
 * @example
 * ```tsx
 * const {
 *   level,
 *   recommendedLevel,
 *   confidence,
 *   unlockFeatures,
 *   personalizedMessage,
 * } = useAIDisclosure();
 *
 * // Show level-up prompt when recommended
 * {recommendedLevel !== level && confidence > 0.8 && (
 *   <LevelUpPrompt
 *     message={personalizedMessage}
 *     features={unlockFeatures}
 *     onAccept={() => setLevel(recommendedLevel)}
 *   />
 * )}
 * ```
 */

import { useState, useCallback, useRef, useEffect } from "react";
import {
  type DisclosureLevel,
  setDisclosureLevel,
} from "../store/slices/disclosureSlice";
import { useAppDispatch, useAppSelector } from "../store/hooks";
import { useAnalyzeDisclosureMutation } from "../api";

export interface AIDisclosureAnalysis {
  currentLevel: DisclosureLevel;
  recommendedLevel: DisclosureLevel;
  confidence: number;
  unlockFeatures: string[];
  personalizedMessage: string;
  reasoning?: string;
}

export interface UseAIDisclosureOptions {
  /** Enable AI analysis (default: false) */
  enabled?: boolean;
  /** Minimum confidence to show recommendations (default: 0.7) */
  minConfidence?: number;
  /** How often to re-analyze (default: 5 minutes) */
  analyzeIntervalMs?: number;
  /** Sync with Redux disclosureSlice (default: false) */
  useRedux?: boolean;
}

export interface UseAIDisclosureResult {
  /** Current disclosure level */
  level: DisclosureLevel;
  /** AI-recommended level */
  recommendedLevel: DisclosureLevel | null;
  /** Confidence in recommendation */
  confidence: number;
  /** Features that would be unlocked */
  unlockFeatures: string[];
  /** Personalized message for level-up prompt */
  personalizedMessage: string | null;
  /** Whether AI analysis is available */
  isAIAvailable: boolean;
  /** Whether analysis is in progress */
  isAnalyzing: boolean;
  /** Manually trigger analysis */
  analyze: () => Promise<AIDisclosureAnalysis | null>;
  /** Accept the AI recommendation */
  acceptRecommendation: () => void;
  /** Dismiss the recommendation (don't show again for a while) */
  dismissRecommendation: () => void;
}

// =============================================================================
// Constants
// =============================================================================

const DEFAULT_MIN_CONFIDENCE = 0.7;

// =============================================================================
// Hook Implementation
// =============================================================================

/**
 * Hook for AI-augmented progressive disclosure.
 * Analyzes user behavior to recommend UI complexity level.
 */
export function useAIDisclosure(
  options: UseAIDisclosureOptions = {},
): UseAIDisclosureResult {
  const {
    enabled = false,
    minConfidence = DEFAULT_MIN_CONFIDENCE,
    useRedux = false,
  } = options;

  // RTK Query mutation
  const [analyzeDisclosure, { isLoading: isAnalyzing }] =
    useAnalyzeDisclosureMutation();

  // Redux hooks - always called to satisfy Rules of Hooks
  // Only actually used when useRedux is true and hook is wrapped in Provider
  const dispatch = useAppDispatch();
  const reduxLevel = useAppSelector((state) =>
    useRedux ? (state.disclosure?.level ?? "beginner") : "beginner",
  );
  const hasReduxContext = useRedux;

  // Local state (used when useRedux is false or no Redux context)
  const [localLevel, setLocalLevel] = useState<DisclosureLevel>("beginner");
  const [recommendedLevel, setRecommendedLevel] =
    useState<DisclosureLevel | null>(null);
  const [confidence, setConfidence] = useState<number>(0);
  const [unlockFeatures, setUnlockFeatures] = useState<string[]>([]);
  const [personalizedMessage, setPersonalizedMessage] = useState<string | null>(
    null,
  );
  const isMounted = useRef(true);

  // Cleanup on unmount
  useEffect(() => {
    isMounted.current = true;
    return () => {
      isMounted.current = false;
    };
  }, []);

  // Use Redux level or local level based on option and context availability
  const level = hasReduxContext ? reduxLevel : localLevel;
  const setLevel = useCallback(
    (newLevel: DisclosureLevel) => {
      if (hasReduxContext) {
        dispatch(setDisclosureLevel(newLevel));
      } else {
        setLocalLevel(newLevel);
      }
    },
    [hasReduxContext, dispatch],
  );

  /**
   * Analyze user behavior and get AI recommendation
   */
  const analyze =
    useCallback(async (): Promise<AIDisclosureAnalysis | null> => {
      if (!enabled) {
        return null;
      }

      try {
        const data = await analyzeDisclosure({
          current_level: level,
        }).unwrap();

        if (!isMounted.current) {
          return null;
        }

        // Transform snake_case to camelCase
        const analysis: AIDisclosureAnalysis = {
          currentLevel: data.current_level as DisclosureLevel,
          recommendedLevel: data.recommended_level as DisclosureLevel,
          confidence: data.confidence,
          unlockFeatures: data.unlock_features,
          personalizedMessage: data.personalized_message,
          reasoning: data.reasoning,
        };

        // Update state - only update local level from API response when not using Redux
        if (!useRedux) {
          setLocalLevel(analysis.currentLevel);
        }
        setConfidence(analysis.confidence);
        setUnlockFeatures(analysis.unlockFeatures);
        setPersonalizedMessage(analysis.personalizedMessage);

        // Only set recommended level if above minConfidence threshold
        if (analysis.confidence >= minConfidence) {
          setRecommendedLevel(analysis.recommendedLevel);
        } else {
          setRecommendedLevel(null);
        }

        return analysis;
      } catch {
        return null;
      }
    }, [enabled, level, minConfidence, useRedux, analyzeDisclosure]);

  /**
   * Accept the AI recommendation
   */
  const acceptRecommendation = useCallback(() => {
    if (recommendedLevel) {
      setLevel(recommendedLevel);
    }
    setRecommendedLevel(null);
    setPersonalizedMessage(null);
    setUnlockFeatures([]);
  }, [recommendedLevel, setLevel]);

  /**
   * Dismiss the recommendation
   */
  const dismissRecommendation = useCallback(() => {
    setRecommendedLevel(null);
    setPersonalizedMessage(null);
    setUnlockFeatures([]);
  }, []);

  return {
    level,
    recommendedLevel,
    confidence,
    unlockFeatures,
    personalizedMessage,
    isAIAvailable: enabled,
    isAnalyzing,
    analyze,
    acceptRecommendation,
    dismissRecommendation,
  };
}

export default useAIDisclosure;
