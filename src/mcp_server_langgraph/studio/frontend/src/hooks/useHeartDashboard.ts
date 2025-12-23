/**
 * useHeartDashboard Hook
 *
 * Sprint 4 - Phase 3.3: HEART Metrics Analytics Dashboard
 *
 * Hook for fetching and managing HEART metrics dashboard data:
 * - Time range selection (7d/30d/90d)
 * - Data fetching with loading/error states
 * - Dimension data extraction
 * - Manual and auto-refresh functionality
 *
 * @example
 * ```tsx
 * const {
 *   loading,
 *   error,
 *   data,
 *   dimensions,
 *   overallScore,
 *   timeRange,
 *   setTimeRange,
 *   refresh,
 * } = useHeartDashboard({ autoRefreshMs: 60000 });
 *
 * if (loading) return <Loading />;
 * if (error) return <Error message={error} />;
 *
 * return (
 *   <>
 *     <OverallScore score={overallScore} />
 *     {dimensions.map(dim => <DimensionCard key={dim.dimension} {...dim} />)}
 *   </>
 * );
 * ```
 */

import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import type { MetricsSummary, DimensionScore } from "../analytics/gsm";
import { getAuthToken } from "../utils/storage";

// =============================================================================
// Types
// =============================================================================

export type TimeRange = "7d" | "30d" | "90d";

export interface UseHeartDashboardOptions {
  /** Initial time range (default: "30d") */
  initialTimeRange?: TimeRange;
  /** Auto-refresh interval in ms (disabled if not set) */
  autoRefreshMs?: number;
}

export interface UseHeartDashboardResult {
  /** Loading state */
  loading: boolean;
  /** Error message if fetch failed */
  error: string | null;
  /** Raw metrics data */
  data: MetricsSummary | null;
  /** HEART dimensions array */
  dimensions: DimensionScore[];
  /** Overall health score (0-100) */
  overallScore: number;
  /** Data point count */
  dataPointCount: number;
  /** Current time range */
  timeRange: TimeRange;
  /** Set time range (triggers refetch) */
  setTimeRange: (range: TimeRange) => void;
  /** Manual refresh function */
  refresh: () => Promise<void>;
}

// =============================================================================
// Constants
// =============================================================================

const API_ENDPOINT = "/api/v1/metrics/heart/aggregate";

// =============================================================================
// Hook Implementation
// =============================================================================

export function useHeartDashboard(
  options: UseHeartDashboardOptions = {},
): UseHeartDashboardResult {
  const { initialTimeRange = "30d", autoRefreshMs } = options;

  // State
  const [timeRange, setTimeRange] = useState<TimeRange>(initialTimeRange);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [data, setData] = useState<MetricsSummary | null>(null);

  // Refs
  const refreshTimerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const isMountedRef = useRef(true);

  /**
   * Fetch metrics data from API
   */
  const fetchData = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);

    try {
      const token = getAuthToken();
      const response = await fetch(`${API_ENDPOINT}?range=${timeRange}`, {
        headers: {
          ...(token && { Authorization: `Bearer ${token}` }),
        },
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch analytics: ${response.status}`);
      }

      const metricsData: MetricsSummary = await response.json();

      if (isMountedRef.current) {
        setData(metricsData);
        setError(null);
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError(err instanceof Error ? err.message : "Unknown error");
        setData(null);
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false);
      }
    }
  }, [timeRange]);

  /**
   * Manual refresh function
   */
  const refresh = useCallback(async (): Promise<void> => {
    await fetchData();
  }, [fetchData]);

  // Extract dimensions from data
  const dimensions = useMemo<DimensionScore[]>(() => {
    return data?.dimensions ?? [];
  }, [data]);

  // Extract overall score
  const overallScore = useMemo(() => {
    return data?.overallHealthScore ?? 0;
  }, [data]);

  // Extract data point count
  const dataPointCount = useMemo(() => {
    return data?.dataPointCount ?? 0;
  }, [data]);

  // Fetch data on mount and when timeRange changes
  useEffect(() => {
    isMountedRef.current = true;
    fetchData();

    return () => {
      isMountedRef.current = false;
    };
  }, [fetchData]);

  // Auto-refresh timer
  useEffect(() => {
    if (!autoRefreshMs) {
      return;
    }

    refreshTimerRef.current = setInterval(() => {
      if (isMountedRef.current) {
        fetchData();
      }
    }, autoRefreshMs);

    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current);
        refreshTimerRef.current = null;
      }
    };
  }, [autoRefreshMs, fetchData]);

  return {
    loading,
    error,
    data,
    dimensions,
    overallScore,
    dataPointCount,
    timeRange,
    setTimeRange,
    refresh,
  };
}

export default useHeartDashboard;
