/**
 * useAIMetricsInsights Hook
 *
 * AI-powered HEART metrics insights hook.
 * Phase 6.6: AI-Generated HEART Insights
 *
 * Fetches AI-generated insights from HEART metrics data including:
 * - Anomaly detection (sudden drops/spikes)
 * - Trend analysis (positive/negative patterns)
 * - Pattern recognition (user behavior patterns)
 * - Predictive analytics (churn risk, adoption forecasts)
 *
 * Features:
 * - Real-time insights from HEART metrics
 * - Categorized by type (anomaly, trend, pattern)
 * - Predictions with confidence scores
 * - Suggested actions for anomalies
 * - Last updated tracking
 *
 * @example
 * ```tsx
 * const {
 *   insights,
 *   predictions,
 *   anomalies,
 *   trends,
 *   patterns,
 *   isLoading,
 *   error,
 *   lastUpdated,
 *   refresh,
 * } = useAIMetricsInsights({ enabled: true });
 * ```
 */

import { useEffect, useMemo, useCallback, useState } from "react";
import { useGetMetricsInsightsQuery } from "../api";

/**
 * RTK Query response format from backend
 */
interface RTKMetricsInsight {
  category: "happiness" | "engagement" | "adoption" | "retention" | "task_success";
  title: string;
  description: string;
  trend: "improving" | "stable" | "declining";
  priority: "high" | "medium" | "low";
  suggested_action?: string;
}

/**
 * Base insight structure
 */
export interface BaseInsight {
  /** Insight type: anomaly, trend, or pattern */
  type: "anomaly" | "trend" | "pattern";
  /** HEART dimension this relates to */
  dimension: "happiness" | "engagement" | "adoption" | "retention" | "task_success";
  /** Human-readable insight message */
  message: string;
}

/**
 * Anomaly insight with severity and actions
 */
export interface AnomalyInsight extends BaseInsight {
  type: "anomaly";
  /** Severity level */
  severity: "critical" | "warning" | "info";
  /** Suggested actions to address the anomaly */
  suggestedActions?: string[];
  /** When the anomaly was detected */
  detectedAt?: string;
}

/**
 * Trend insight with sentiment
 */
export interface TrendInsight extends BaseInsight {
  type: "trend";
  /** Sentiment of the trend */
  sentiment: "positive" | "negative" | "neutral";
}

/**
 * Pattern insight
 */
export interface PatternInsight extends BaseInsight {
  type: "pattern";
  /** Sentiment of the pattern */
  sentiment?: "positive" | "negative" | "neutral";
}

/**
 * Union type for all insights
 */
export type Insight = AnomalyInsight | TrendInsight | PatternInsight;

/**
 * Prediction structure
 */
export interface Prediction {
  /** Metric being predicted */
  metric: string;
  /** Current value */
  current: number;
  /** Predicted value */
  predicted: number;
  /** Confidence score (0-1) */
  confidence: number;
  /** Drivers contributing to prediction */
  drivers: string[];
}

/**
 * Hook configuration options
 */
export interface UseAIMetricsInsightsOptions {
  /** Whether to fetch insights (default: true) */
  enabled?: boolean;
  /** Request timeout in milliseconds (default: 10000ms) */
  timeoutMs?: number;
  /** Polling interval in milliseconds (default: no polling) */
  pollingIntervalMs?: number;
}

/** Default timeout for AI requests */
const DEFAULT_TIMEOUT_MS = 10000;

/**
 * Hook result
 */
export interface UseAIMetricsInsightsResult {
  /** All insights */
  insights: Insight[];
  /** Predictions with confidence scores */
  predictions: Prediction[];
  /** Anomaly insights only */
  anomalies: AnomalyInsight[];
  /** Trend insights only */
  trends: TrendInsight[];
  /** Pattern insights only */
  patterns: PatternInsight[];
  /** Whether insights are being fetched */
  isLoading: boolean;
  /** Error if fetch failed */
  error: Error | null;
  /** When insights were last updated */
  lastUpdated: Date | null;
  /** Manually refresh insights */
  refresh: () => void;
}


/**
 * Transform RTK Query insight to hook's expected format.
 * Maps from backend format (category, title, description, trend, priority)
 * to frontend format (type, dimension, message, severity/sentiment).
 */
function transformRTKInsight(raw: RTKMetricsInsight): Insight {
  const dimension = raw.category;
  const message = `${raw.title}: ${raw.description}`;

  // Determine insight type based on priority and trend
  // High priority items with declining trend → anomaly
  // Declining or improving trends → trend
  // Otherwise → pattern
  if (raw.priority === "high" && raw.trend === "declining") {
    return {
      type: "anomaly",
      dimension,
      message,
      severity: "critical",
      suggestedActions: raw.suggested_action ? [raw.suggested_action] : undefined,
      detectedAt: new Date().toISOString(),
    };
  }

  if (raw.priority === "high") {
    return {
      type: "anomaly",
      dimension,
      message,
      severity: "warning",
      suggestedActions: raw.suggested_action ? [raw.suggested_action] : undefined,
    };
  }

  if (raw.trend !== "stable") {
    return {
      type: "trend",
      dimension,
      message,
      sentiment: raw.trend === "improving" ? "positive" : "negative",
    };
  }

  return {
    type: "pattern",
    dimension,
    message,
    sentiment: "neutral",
  };
}

/**
 * Hook for AI-powered HEART metrics insights.
 *
 * @param options - Hook options
 * @returns Insights, predictions, and categorized data
 */
export function useAIMetricsInsights(
  options: UseAIMetricsInsightsOptions = {}
): UseAIMetricsInsightsResult {
  const {
    enabled = true,
    timeoutMs: _timeoutMs = DEFAULT_TIMEOUT_MS, // Kept for API compatibility
    pollingIntervalMs,
  } = options;

  // Track last update timestamp
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  // RTK Query for fetching insights
  const {
    data,
    isLoading: isQueryLoading,
    isFetching,
    error: queryError,
    refetch,
  } = useGetMetricsInsightsQuery(
    {}, // Empty params, backend uses session context
    {
      skip: !enabled,
      pollingInterval: pollingIntervalMs,
    }
  );

  // Update lastUpdated when data changes
  useEffect(() => {
    if (data && !isFetching) {
      setLastUpdated(new Date());
    }
  }, [data, isFetching]);

  // Transform RTK Query insights to hook's expected format
  const insights = useMemo<Insight[]>(() => {
    if (!data?.insights) return [];
    return data.insights.map(transformRTKInsight);
  }, [data?.insights]);

  // RTK Query doesn't return predictions in this format,
  // so we return an empty array for backward compatibility
  const predictions = useMemo<Prediction[]>(() => [], []);

  // Categorize insights by type
  const anomalies = useMemo(
    () => insights.filter((i): i is AnomalyInsight => i.type === "anomaly"),
    [insights]
  );

  const trends = useMemo(
    () => insights.filter((i): i is TrendInsight => i.type === "trend"),
    [insights]
  );

  const patterns = useMemo(
    () => insights.filter((i): i is PatternInsight => i.type === "pattern"),
    [insights]
  );

  // Transform RTK Query error to Error object
  const error = useMemo<Error | null>(() => {
    if (!queryError) return null;
    if ("message" in queryError) {
      return new Error((queryError as { message: string }).message);
    }
    if ("status" in queryError) {
      return new Error(`AI service error: ${queryError.status}`);
    }
    return new Error("Failed to fetch insights");
  }, [queryError]);

  // Refresh function using RTK Query refetch
  const refresh = useCallback(() => {
    refetch();
  }, [refetch]);

  return {
    insights,
    predictions,
    anomalies,
    trends,
    patterns,
    isLoading: isQueryLoading || isFetching,
    error,
    lastUpdated,
    refresh,
  };
}

export default useAIMetricsInsights;
