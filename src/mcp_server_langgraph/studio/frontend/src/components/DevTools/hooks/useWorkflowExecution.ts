/**
 * useWorkflowExecution Hook
 *
 * Fetches and manages workflow execution step data.
 */
import { useState, useEffect, useCallback } from "react";

// =============================================================================
// Types
// =============================================================================

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
  options: UseWorkflowExecutionOptions
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
      const response = await fetch(
        `/api/v1/workflows/${workflowId}/execution`
      );

      if (!response.ok) {
        throw new Error(`Failed to fetch execution: ${response.statusText}`);
      }

      const data = await response.json();
      setSteps(data.steps ?? []);
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
