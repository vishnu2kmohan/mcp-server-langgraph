/**
 * useWorkflowExecution Hook
 *
 * Fetches and manages workflow execution step data.
 * Transforms API response (snake_case) to frontend format (camelCase).
 */
import { useState, useEffect, useCallback } from "react";
import { authenticatedFetch } from "../../../utils/authenticatedFetch";
import { transformSnakeToCamel } from "../../../api/transforms";

// =============================================================================
// Types
// =============================================================================

/**
 * API response format from /api/v1/workflows/{workflowId}/execution
 * (uses snake_case from Python backend)
 */
interface WorkflowExecutionApiResponse {
  steps?: Array<{
    id: string;
    node_id: string;
    node_name: string;
    status: string;
    duration: number;
    start_time: number;
    end_time?: number;
    input?: Record<string, unknown>;
    output?: Record<string, unknown>;
    error?: string;
  }>;
  current_step_id?: string | null;
}

/**
 * Frontend format after transformation (camelCase)
 */
export interface ExecutionStep {
  /** Step ID */
  id: string;
  /** Node ID in the workflow */
  nodeId: string;
  /** Node display name */
  nodeName: string;
  /** Step status */
  status: "pending" | "running" | "completed" | "error" | "skipped";
  /** Duration in milliseconds */
  duration: number;
  /** Start timestamp */
  startTime: number;
  /** End timestamp (if completed) */
  endTime?: number;
  /** Input data */
  input?: Record<string, unknown>;
  /** Output data */
  output?: Record<string, unknown>;
  /** Error message if failed */
  error?: string;
}

export interface UseWorkflowExecutionOptions {
  /** Workflow ID to fetch execution for */
  workflowId: string;
  /** Whether to auto-refresh */
  autoRefresh?: boolean;
  /** Auto-refresh interval in milliseconds */
  refreshInterval?: number;
}

export interface UseWorkflowExecutionReturn {
  /** Execution steps */
  steps: ExecutionStep[];
  /** Whether loading */
  isLoading: boolean;
  /** Error if fetch failed */
  error: Error | null;
  /** Refetch execution data */
  refetch: () => void;
  /** Currently executing step ID */
  currentStepId: string | null;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useWorkflowExecution(
  options: UseWorkflowExecutionOptions,
): UseWorkflowExecutionReturn {
  const { workflowId, autoRefresh = false, refreshInterval = 2000 } = options;

  const [steps, setSteps] = useState<ExecutionStep[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [currentStepId, setCurrentStepId] = useState<string | null>(null);

  const fetchExecution = useCallback(async () => {
    if (!workflowId) return;

    setIsLoading(true);
    setError(null);

    try {
      const response = await authenticatedFetch(
        `/api/v1/workflows/${workflowId}/execution`,
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch execution: ${response.statusText}`);
      }

      const rawData: WorkflowExecutionApiResponse = await response.json();
      // Transform snake_case API response to camelCase frontend format
      const data = transformSnakeToCamel(rawData);
      setSteps((data.steps ?? []) as ExecutionStep[]);
      setCurrentStepId(data.currentStepId ?? null);
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Unknown error"));
      setSteps([]);
      setCurrentStepId(null);
    } finally {
      setIsLoading(false);
    }
  }, [workflowId]);

  const refetch = useCallback(() => {
    fetchExecution();
  }, [fetchExecution]);

  // Initial fetch
  useEffect(() => {
    fetchExecution();
  }, [fetchExecution]);

  // Auto-refresh
  useEffect(() => {
    if (!autoRefresh) return;

    const intervalId = setInterval(fetchExecution, refreshInterval);

    return () => clearInterval(intervalId);
  }, [autoRefresh, refreshInterval, fetchExecution]);

  return {
    steps,
    isLoading,
    error,
    refetch,
    currentStepId,
  };
}

export default useWorkflowExecution;
