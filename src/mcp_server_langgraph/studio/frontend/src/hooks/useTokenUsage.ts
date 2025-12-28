/**
 * useTokenUsage Hook
 *
 * Hook to track and display token usage for chat sessions.
 * Features:
 * - Per-session token usage tracking
 * - Input vs output token breakdown
 * - Cost estimation (when pricing configured)
 * - Context window usage indicator
 * - Historical usage data
 *
 * Based on Claude Code data tracking patterns.
 */

import { useState, useEffect, useCallback, useMemo } from "react";
import { useNavigate } from "react-router";
import { authenticatedFetch } from "../utils/authenticatedFetch";
import { saveCurrentRouteAsIntended } from "../utils/intendedRoute";

// ==============================================================================
// Types
// ==============================================================================

export interface TokenHistoryEntry {
  timestamp: string;
  tokens: number;
}

export interface TokenUsageData {
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  inputCostPer1k?: number;
  outputCostPer1k?: number;
  contextWindowSize?: number;
  history?: TokenHistoryEntry[];
}

export interface TokenUsageState {
  /** Number of input tokens */
  inputTokens: number;
  /** Number of output tokens */
  outputTokens: number;
  /** Total tokens (input + output) */
  totalTokens: number;
  /** Estimated cost in USD (null if pricing not configured) */
  estimatedCost: number | null;
  /** Context window size (e.g., 128000 for GPT-4) */
  contextWindowSize: number | null;
  /** Percentage of context window used */
  contextWindowUsage: number;
  /** Whether context window usage is near limit (>75%) */
  isContextWindowNearLimit: boolean;
  /** Historical token usage data */
  history: TokenHistoryEntry[] | null;
  /** Whether data is loading */
  isLoading: boolean;
  /** Error message if any */
  error: string | null;
  /** Refresh token usage data */
  refresh: () => Promise<void>;
}

// ==============================================================================
// Constants
// ==============================================================================

const API_BASE = "/api/v1/sessions";
const CONTEXT_WINDOW_WARNING_THRESHOLD = 75; // Warn at 75% usage

// ==============================================================================
// Hook
// ==============================================================================

export function useTokenUsage(sessionId: string): TokenUsageState {
  const navigate = useNavigate();
  const [data, setData] = useState<TokenUsageData>({
    inputTokens: 0,
    outputTokens: 0,
    totalTokens: 0,
  });
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Handle auth failure - redirect to login
  const handleAuthFailure = useCallback(() => {
    saveCurrentRouteAsIntended();
    navigate("/login", { replace: true });
  }, [navigate]);

  // Fetch token usage data
  const fetchTokenUsage = useCallback(async () => {
    if (!sessionId) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await authenticatedFetch(
        `${API_BASE}/${sessionId}/token-usage`,
        { onAuthFailure: handleAuthFailure },
      );

      if (!response.ok) {
        throw new Error("Failed to fetch token usage");
      }

      const result = await response.json();
      setData(result);
    } catch {
      setError("Failed to load token usage");
      setData({
        inputTokens: 0,
        outputTokens: 0,
        totalTokens: 0,
      });
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, handleAuthFailure]);

  // Fetch on mount and when session changes
  useEffect(() => {
    fetchTokenUsage();
  }, [fetchTokenUsage]);

  // Calculate estimated cost
  const estimatedCost = useMemo(() => {
    if (!data.inputCostPer1k || !data.outputCostPer1k) {
      return null;
    }

    const inputCost = (data.inputTokens / 1000) * data.inputCostPer1k;
    const outputCost = (data.outputTokens / 1000) * data.outputCostPer1k;

    return inputCost + outputCost;
  }, [
    data.inputTokens,
    data.outputTokens,
    data.inputCostPer1k,
    data.outputCostPer1k,
  ]);

  // Calculate context window usage
  const contextWindowUsage = useMemo(() => {
    if (!data.contextWindowSize) return 0;
    return (data.totalTokens / data.contextWindowSize) * 100;
  }, [data.totalTokens, data.contextWindowSize]);

  const isContextWindowNearLimit =
    contextWindowUsage > CONTEXT_WINDOW_WARNING_THRESHOLD;

  return {
    inputTokens: data.inputTokens,
    outputTokens: data.outputTokens,
    totalTokens: data.totalTokens,
    estimatedCost,
    contextWindowSize: data.contextWindowSize || null,
    contextWindowUsage,
    isContextWindowNearLimit,
    history: data.history || null,
    isLoading,
    error,
    refresh: fetchTokenUsage,
  };
}

export default useTokenUsage;
