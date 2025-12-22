/**
 * useThresholdSettings Hook
 *
 * Hook for managing rotating threshold settings and recommendations.
 *
 * Features:
 * - Fetch threshold recommendations based on approval history
 * - Fetch and update user threshold settings
 * - Apply recommended threshold adjustments
 * - Loading and error states
 *
 * Reference: Plan - Confidence-Based Human-in-the-Loop (HITL) for Multi-Agent Orchestrator
 */

import { useState, useCallback } from "react";
import { getAuthToken } from "../utils/storage";

// =============================================================================
// Types
// =============================================================================

export interface ThresholdRecommendation {
  current_threshold: number;
  recommended_threshold: number;
  reason: string;
  confidence_level: number;
  sample_size: number;
}

export interface UserThresholdSettings {
  user_id: string;
  base_threshold: number;
  adjusted_threshold: number;
  auto_adjust_enabled: boolean;
  min_threshold: number;
  max_threshold: number;
}

export interface UpdateThresholdSettingsRequest {
  base_threshold?: number;
  auto_adjust_enabled?: boolean;
  min_threshold?: number;
  max_threshold?: number;
}

export interface UseThresholdSettingsReturn {
  /** Current threshold recommendation */
  recommendation: ThresholdRecommendation | undefined;
  /** Current user threshold settings */
  settings: UserThresholdSettings | undefined;
  /** Whether a request is in progress */
  isLoading: boolean;
  /** Error message if last operation failed */
  error: string | null;
  /** Fetch threshold recommendation */
  fetchRecommendation: () => Promise<ThresholdRecommendation | null>;
  /** Fetch user threshold settings */
  fetchSettings: () => Promise<UserThresholdSettings | null>;
  /** Update user threshold settings */
  updateSettings: (
    updates: UpdateThresholdSettingsRequest
  ) => Promise<UserThresholdSettings | null>;
  /** Apply the current recommendation to settings */
  applyRecommendation: () => Promise<UserThresholdSettings | null>;
}

// =============================================================================
// Constants
// =============================================================================

const API_BASE =
  typeof window !== "undefined"
    ? `${window.location.protocol}//${window.location.host}/api/v1`
    : "/api/v1";

// =============================================================================
// Hook
// =============================================================================

export function useThresholdSettings(): UseThresholdSettingsReturn {
  const [recommendation, setRecommendation] = useState<
    ThresholdRecommendation | undefined
  >(undefined);
  const [settings, setSettings] = useState<UserThresholdSettings | undefined>(
    undefined
  );
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /**
   * Get authorization headers
   */
  const getHeaders = useCallback((): Record<string, string> => {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    const token = getAuthToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    return headers;
  }, []);

  /**
   * Fetch threshold recommendation
   */
  const fetchRecommendation =
    useCallback(async (): Promise<ThresholdRecommendation | null> => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `${API_BASE}/agents/requests/threshold/recommendation`,
          {
            method: "GET",
            headers: getHeaders(),
          }
        );

        if (!response.ok) {
          const errorMessage = `Failed to fetch recommendation: ${response.status} ${response.statusText}`;
          setError(errorMessage);
          return null;
        }

        const data = await response.json();
        setRecommendation(data as ThresholdRecommendation);
        return data as ThresholdRecommendation;
      } catch (err) {
        const errorMessage =
          err instanceof Error
            ? err.message
            : "Failed to fetch recommendation";
        setError(errorMessage);
        return null;
      } finally {
        setIsLoading(false);
      }
    }, [getHeaders]);

  /**
   * Fetch user threshold settings
   */
  const fetchSettings =
    useCallback(async (): Promise<UserThresholdSettings | null> => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `${API_BASE}/agents/requests/threshold/settings`,
          {
            method: "GET",
            headers: getHeaders(),
          }
        );

        if (!response.ok) {
          const errorMessage = `Failed to fetch settings: ${response.status} ${response.statusText}`;
          setError(errorMessage);
          return null;
        }

        const data = await response.json();
        setSettings(data as UserThresholdSettings);
        return data as UserThresholdSettings;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to fetch settings";
        setError(errorMessage);
        return null;
      } finally {
        setIsLoading(false);
      }
    }, [getHeaders]);

  /**
   * Update user threshold settings
   */
  const updateSettings = useCallback(
    async (
      updates: UpdateThresholdSettingsRequest
    ): Promise<UserThresholdSettings | null> => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch(
          `${API_BASE}/agents/requests/threshold/settings`,
          {
            method: "PUT",
            headers: getHeaders(),
            body: JSON.stringify(updates),
          }
        );

        if (!response.ok) {
          const errorMessage = `Failed to update settings: ${response.status} ${response.statusText}`;
          setError(errorMessage);
          return null;
        }

        const data = await response.json();
        setSettings(data as UserThresholdSettings);
        return data as UserThresholdSettings;
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Failed to update settings";
        setError(errorMessage);
        return null;
      } finally {
        setIsLoading(false);
      }
    },
    [getHeaders]
  );

  /**
   * Apply the current recommendation to settings
   */
  const applyRecommendation =
    useCallback(async (): Promise<UserThresholdSettings | null> => {
      if (!recommendation) {
        setError("No recommendation available to apply");
        return null;
      }

      return updateSettings({
        base_threshold: recommendation.recommended_threshold,
      });
    }, [recommendation, updateSettings]);

  return {
    recommendation,
    settings,
    isLoading,
    error,
    fetchRecommendation,
    fetchSettings,
    updateSettings,
    applyRecommendation,
  };
}
