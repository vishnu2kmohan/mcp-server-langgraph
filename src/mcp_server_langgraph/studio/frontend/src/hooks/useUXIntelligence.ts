/**
 * UX Intelligence Hooks
 *
 * Sprint 6: UX Intelligence
 * - Nav prediction: Predict and reorder navigation items
 * - Contextual help: Show context-aware help content
 * - Learning path: Personalized learning recommendations
 *
 * These hooks use the unified StudioOrchestrator via RTK Query.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useStudioAnalyzeMutation } from "../api";

// =============================================================================
// Types
// =============================================================================

export interface PredictedNavItem {
  id: string;
  score: number;
  reason: string;
}

export interface NavPredictionOptions {
  userId: string;
  currentPage: string;
  recentPages: string[];
  enabled?: boolean;
}

export interface NavPredictionResult {
  predictedItems: PredictedNavItem[];
  currentContext: string | null;
  confidence: number | null;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export interface HelpTopic {
  id: string;
  title: string;
  summary: string;
  relevance: number;
}

export interface QuickAction {
  label: string;
  action: string;
}

export interface ContextualHelpOptions {
  userId: string;
  currentPage: string;
  activeFeature: string;
  enabled?: boolean;
}

export interface ContextualHelpResult {
  helpTopics: HelpTopic[];
  quickActions: QuickAction[];
  suggestedReading: string[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

export interface LearningStep {
  id: string;
  title: string;
  description: string;
  estimated_time_min: number;
  priority: "high" | "medium" | "low";
}

export type SkillLevel = "beginner" | "intermediate" | "advanced" | "expert";

export interface LearningPathOptions {
  userId: string;
  persona?: string;
  enabled?: boolean;
}

export interface LearningPathResult {
  currentLevel: SkillLevel | null;
  progressPercentage: number | null;
  nextSteps: LearningStep[];
  completedItems: string[];
  recommendedFeatures: string[];
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
}

// =============================================================================
// useNavPrediction
// =============================================================================

/**
 * Hook for predicting navigation preferences.
 *
 * Uses the StudioOrchestrator's nav_prediction task type to predict
 * and reorder navigation items based on user behavior.
 *
 * @param options - Configuration options
 * @returns Predicted navigation with scores and reasons
 */
export function useNavPrediction(
  options: NavPredictionOptions
): NavPredictionResult {
  const { userId, currentPage, recentPages, enabled = true } = options;

  const [analyzeMutation, { isLoading }] = useStudioAnalyzeMutation();

  const [result, setResult] = useState<{
    predictedItems: PredictedNavItem[];
    currentContext: string | null;
    confidence: number | null;
    error: Error | null;
  }>({
    predictedItems: [],
    currentContext: null,
    confidence: null,
    error: null,
  });

  const fetchPrediction = useCallback(async () => {
    if (!enabled) {
      setResult({
        predictedItems: [],
        currentContext: null,
        confidence: null,
        error: null,
      });
      return;
    }

    try {
      const response = await analyzeMutation({
        user_id: userId,
        session_id: "",
        tasks: [
          {
            category: "ux",
            type: "nav_prediction",
            data: {
              current_page: currentPage,
              recent_pages: recentPages,
            },
          },
        ],
      }).unwrap();

      const navResult = response.analyses?.nav_prediction as
        | {
            predicted_items?: PredictedNavItem[];
            current_context?: string;
            confidence?: number;
          }
        | undefined;

      if (navResult) {
        setResult({
          predictedItems: navResult.predicted_items || [],
          currentContext: navResult.current_context || null,
          confidence: navResult.confidence ?? null,
          error: null,
        });
      }
    } catch (err) {
      setResult((prev) => ({
        ...prev,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [analyzeMutation, userId, currentPage, recentPages, enabled]);

  useEffect(() => {
    fetchPrediction();
  }, [fetchPrediction]);

  return useMemo(
    () => ({
      predictedItems: result.predictedItems,
      currentContext: result.currentContext,
      confidence: result.confidence,
      isLoading,
      error: result.error,
      refetch: fetchPrediction,
    }),
    [result, isLoading, fetchPrediction]
  );
}

// =============================================================================
// useContextualHelp
// =============================================================================

/**
 * Hook for context-aware help content.
 *
 * Uses the StudioOrchestrator's contextual_help task type to provide
 * relevant help based on user's current context.
 *
 * @param options - Configuration options
 * @returns Contextual help with topics and actions
 */
export function useContextualHelp(
  options: ContextualHelpOptions
): ContextualHelpResult {
  const { userId, currentPage, activeFeature, enabled = true } = options;

  const [analyzeMutation, { isLoading }] = useStudioAnalyzeMutation();

  const [result, setResult] = useState<{
    helpTopics: HelpTopic[];
    quickActions: QuickAction[];
    suggestedReading: string[];
    error: Error | null;
  }>({
    helpTopics: [],
    quickActions: [],
    suggestedReading: [],
    error: null,
  });

  const fetchHelp = useCallback(async () => {
    if (!enabled) {
      setResult({
        helpTopics: [],
        quickActions: [],
        suggestedReading: [],
        error: null,
      });
      return;
    }

    try {
      const response = await analyzeMutation({
        user_id: userId,
        session_id: "",
        tasks: [
          {
            category: "ux",
            type: "contextual_help",
            data: {
              current_page: currentPage,
              active_feature: activeFeature,
            },
          },
        ],
      }).unwrap();

      const helpResult = response.analyses?.contextual_help as
        | {
            help_topics?: HelpTopic[];
            quick_actions?: QuickAction[];
            suggested_reading?: string[];
          }
        | undefined;

      if (helpResult) {
        setResult({
          helpTopics: helpResult.help_topics || [],
          quickActions: helpResult.quick_actions || [],
          suggestedReading: helpResult.suggested_reading || [],
          error: null,
        });
      }
    } catch (err) {
      setResult((prev) => ({
        ...prev,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [analyzeMutation, userId, currentPage, activeFeature, enabled]);

  useEffect(() => {
    fetchHelp();
  }, [fetchHelp]);

  return useMemo(
    () => ({
      helpTopics: result.helpTopics,
      quickActions: result.quickActions,
      suggestedReading: result.suggestedReading,
      isLoading,
      error: result.error,
      refetch: fetchHelp,
    }),
    [result, isLoading, fetchHelp]
  );
}

// =============================================================================
// useLearningPath
// =============================================================================

/**
 * Hook for personalized learning recommendations.
 *
 * Uses the StudioOrchestrator's learning_path task type to provide
 * personalized learning recommendations based on usage.
 *
 * @param options - Configuration options
 * @returns Learning path with progress and next steps
 */
export function useLearningPath(
  options: LearningPathOptions
): LearningPathResult {
  const { userId, persona, enabled = true } = options;

  const [analyzeMutation, { isLoading }] = useStudioAnalyzeMutation();

  const [result, setResult] = useState<{
    currentLevel: SkillLevel | null;
    progressPercentage: number | null;
    nextSteps: LearningStep[];
    completedItems: string[];
    recommendedFeatures: string[];
    error: Error | null;
  }>({
    currentLevel: null,
    progressPercentage: null,
    nextSteps: [],
    completedItems: [],
    recommendedFeatures: [],
    error: null,
  });

  const fetchLearningPath = useCallback(async () => {
    if (!enabled) {
      setResult({
        currentLevel: null,
        progressPercentage: null,
        nextSteps: [],
        completedItems: [],
        recommendedFeatures: [],
        error: null,
      });
      return;
    }

    try {
      const response = await analyzeMutation({
        user_id: userId,
        session_id: "",
        tasks: [
          {
            category: "ux",
            type: "learning_path",
            data: {
              persona,
            },
          },
        ],
      }).unwrap();

      const pathResult = response.analyses?.learning_path as
        | {
            current_level?: SkillLevel;
            progress_percentage?: number;
            next_steps?: LearningStep[];
            completed_items?: string[];
            recommended_features?: string[];
          }
        | undefined;

      if (pathResult) {
        setResult({
          currentLevel: pathResult.current_level ?? null,
          progressPercentage: pathResult.progress_percentage ?? null,
          nextSteps: pathResult.next_steps || [],
          completedItems: pathResult.completed_items || [],
          recommendedFeatures: pathResult.recommended_features || [],
          error: null,
        });
      }
    } catch (err) {
      setResult((prev) => ({
        ...prev,
        error: err instanceof Error ? err : new Error(String(err)),
      }));
    }
  }, [analyzeMutation, userId, persona, enabled]);

  useEffect(() => {
    fetchLearningPath();
  }, [fetchLearningPath]);

  return useMemo(
    () => ({
      currentLevel: result.currentLevel,
      progressPercentage: result.progressPercentage,
      nextSteps: result.nextSteps,
      completedItems: result.completedItems,
      recommendedFeatures: result.recommendedFeatures,
      isLoading,
      error: result.error,
      refetch: fetchLearningPath,
    }),
    [result, isLoading, fetchLearningPath]
  );
}
