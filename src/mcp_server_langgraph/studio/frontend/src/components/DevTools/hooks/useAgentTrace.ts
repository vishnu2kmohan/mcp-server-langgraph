/**
 * useAgentTrace Hook
 *
 * Fetches and manages agent execution trace data for a session.
 */
import { useState, useEffect, useCallback } from "react";

import type { AgentExecutionTrace } from "../../../types/chat";

// =============================================================================
// Types
// =============================================================================

export interface UseAgentTraceOptions {
  /** Session ID to fetch trace for */
  sessionId: string;
  /** Whether to auto-refresh */
  autoRefresh?: boolean;
  /** Auto-refresh interval in milliseconds */
  refreshInterval?: number;
}

export interface UseAgentTraceReturn {
  /** Current trace data */
  trace: AgentExecutionTrace | null;
  /** Whether trace is loading */
  isLoading: boolean;
  /** Error if fetch failed */
  error: Error | null;
  /** Refetch trace data */
  refetch: () => void;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useAgentTrace(
  options: UseAgentTraceOptions
): UseAgentTraceReturn {
  const { sessionId, autoRefresh = false, refreshInterval = 5000 } = options;

  const [trace, setTrace] = useState<AgentExecutionTrace | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  const fetchTrace = useCallback(async () => {
    if (!sessionId) return;

    setIsLoading(true);
    setError(null);

    try {
      // In a real implementation, this would call an API endpoint
      // For now, we'll simulate fetching from the session state
      const response = await fetch(`/api/v1/sessions/${sessionId}/trace`);

      if (!response.ok) {
        throw new Error(`Failed to fetch trace: ${response.statusText}`);
      }

      const data = await response.json();
      setTrace(data);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Unknown error"));
      setTrace(null);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  const refetch = useCallback(() => {
    fetchTrace();
  }, [fetchTrace]);

  // Initial fetch
  useEffect(() => {
    fetchTrace();
  }, [fetchTrace]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const intervalId = setInterval(fetchTrace, refreshInterval);

    return () => clearInterval(intervalId);
  }, [autoRefresh, refreshInterval, fetchTrace]);

  return {
    trace,
    isLoading,
    error,
    refetch,
  };
}

export default useAgentTrace;
