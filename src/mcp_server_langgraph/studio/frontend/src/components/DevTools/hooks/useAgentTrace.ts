/**
 * useAgentTrace Hook
 *
 * Fetches and manages agent execution trace data for a session.
 *
 * Phase 4D: Updated to use new `/api/v1/sessions/{id}/agent-execution-trace`
 * endpoint which returns LangGraph node execution traces (not OTEL traces from Tempo).
 *
 * Transforms API response to frontend AgentExecutionTrace format.
 */
import { useState, useEffect, useCallback } from "react";

import type { AgentExecutionTrace, LangGraphNode } from "../../../types/chat";
import { authenticatedFetch } from "../../../utils/authenticatedFetch";

// =============================================================================
// Types
// =============================================================================

/**
 * Individual trace entry from the new API endpoint.
 * Represents a single LangGraph node execution.
 */
interface AgentExecutionTraceEntry {
  trace_id: string;
  node_name: string;
  status: string;
  start_time: number;
  end_time?: number;
  duration_ms?: number;
  sequence_number: number;
}

/**
 * API response format from /api/v1/sessions/{sessionId}/agent-execution-trace
 * (Phase 4: LangGraph Execution Trace Persistence)
 */
interface AgentExecutionTraceApiResponse {
  session_id: string;
  traces: AgentExecutionTraceEntry[];
  total: number;
  has_more: boolean;
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
 * Transform new agent execution trace API response to frontend format.
 * Phase 4D: Uses `/api/v1/sessions/{id}/agent-execution-trace` response.
 */
function transformAgentExecutionTraceResponse(
  data: AgentExecutionTraceApiResponse,
): AgentExecutionTrace {
  const { traces } = data;

  // Transform trace entries to LangGraphNode format
  const nodes: LangGraphNode[] = traces.map((trace) => ({
    id: trace.trace_id,
    name: trace.node_name,
    type: "default" as const,
    status: trace.status as LangGraphNode["status"],
    duration: trace.duration_ms,
  }));

  // Transform to steps for backward compatibility
  const steps = traces.map((trace) => ({
    name: trace.node_name,
    status: trace.status,
    duration: trace.duration_ms,
  }));

  // Calculate overall start/end times from traces
  const startTime = traces.length > 0 ? traces[0].start_time : undefined;
  const endTime =
    traces.length > 0 ? traces[traces.length - 1].end_time : undefined;

  return {
    rawOutput: undefined,
    steps,
    tokens: undefined,
    nodes,
    edges: undefined,
    currentNode: undefined,
    startTime,
    endTime,
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
      // Phase 4D: Fetch LangGraph execution traces from new endpoint
      const response = await authenticatedFetch(
        `/api/v1/sessions/${sessionId}/agent-execution-trace`,
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch trace: ${response.statusText}`);
      }

      const data: AgentExecutionTraceApiResponse = await response.json();
      const transformed = transformAgentExecutionTraceResponse(data);
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
