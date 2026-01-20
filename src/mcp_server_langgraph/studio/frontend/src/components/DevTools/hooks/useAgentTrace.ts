/**
 * useAgentTrace Hook
 *
 * Fetches and manages agent execution trace data for a session.
 * Transforms API response (snake_case SessionTraceResponse) to frontend format
 * (camelCase AgentExecutionTrace with nodes derived from steps).
 */
import { useState, useEffect, useCallback } from "react";

import type { AgentExecutionTrace, LangGraphNode } from "../../../types/chat";
import { authenticatedFetch } from "../../../utils/authenticatedFetch";

// =============================================================================
// Types
// =============================================================================

/**
 * API response format from /api/v1/sessions/{sessionId}/trace
 * (SessionTraceResponse - uses snake_case)
 */
interface SessionTraceApiResponse {
  raw_output?: string;
  steps?: Array<{ name: string; status: string; duration?: number }>;
  tokens?: { input: number; output: number };
  current_node?: string;
  start_time?: number;
  end_time?: number;
  // Future-proofing: API may return nodes/edges directly
  nodes?: LangGraphNode[];
  edges?: Array<{ from: string; to: string; condition?: string }>;
}

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
// Transformation
// =============================================================================

/**
 * Transform API response to frontend AgentExecutionTrace format.
 * - Converts snake_case to camelCase
 * - Derives nodes from steps if not already present
 */
function transformApiResponse(
  data: SessionTraceApiResponse,
): AgentExecutionTrace {
  // If API returns nodes directly, use them; otherwise derive from steps
  let nodes: LangGraphNode[] | undefined = data.nodes;

  if (!nodes && data.steps) {
    nodes = data.steps.map((step, index) => ({
      id: `step-${index}`,
      name: step.name,
      type: "default" as const,
      status: step.status as LangGraphNode["status"],
      duration: step.duration,
    }));
  }

  return {
    rawOutput: data.raw_output,
    steps: data.steps,
    tokens: data.tokens,
    nodes,
    edges: data.edges,
    currentNode: data.current_node ?? undefined,
    startTime: data.start_time,
    endTime: data.end_time,
  };
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useAgentTrace(
  options: UseAgentTraceOptions,
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
      const response = await authenticatedFetch(
        `/api/v1/sessions/${sessionId}/trace`,
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch trace: ${response.statusText}`);
      }

      const data: SessionTraceApiResponse = await response.json();
      const transformed = transformApiResponse(data);
      setTrace(transformed);
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
