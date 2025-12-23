/**
 * useProblems Hook
 *
 * Manages problems (errors and warnings) for the DevTools Problems tab.
 */
import { useState, useCallback, useMemo } from "react";

// =============================================================================
// Types
// =============================================================================

export type ProblemSeverity = "error" | "warning";

export interface Problem {
  id: string;
  severity: ProblemSeverity;
  message: string;
  source: string;
  file?: string;
  line?: number;
  column?: number;
  timestamp: number;
  dismissed?: boolean;
}

export interface UseProblemsOptions {
  filter?: "all" | "errors" | "warnings";
}

export interface UseProblemsReturn {
  problems: Problem[];
  errorCount: number;
  warningCount: number;
  addProblem: (problem: Problem) => void;
  dismissProblem: (id: string) => void;
  clearProblems: () => void;
}

// =============================================================================
// Hook Implementation
// =============================================================================

export function useProblems(
  options: UseProblemsOptions = {},
): UseProblemsReturn {
  const { filter = "all" } = options;

  const [problems, setProblems] = useState<Problem[]>([]);

  /**
   * Add a new problem.
   */
  const addProblem = useCallback((problem: Problem) => {
    setProblems((prev) => {
      // Avoid duplicates by ID
      if (prev.some((p) => p.id === problem.id)) {
        return prev;
      }
      return [...prev, problem];
    });
  }, []);

  /**
   * Dismiss a problem by ID.
   */
  const dismissProblem = useCallback((id: string) => {
    setProblems((prev) =>
      prev.map((p) => (p.id === id ? { ...p, dismissed: true } : p)),
    );
  }, []);

  /**
   * Clear all problems.
   */
  const clearProblems = useCallback(() => {
    setProblems([]);
  }, []);

  /**
   * Get filtered problems (excluding dismissed).
   */
  const filteredProblems = useMemo(() => {
    let result = problems.filter((p) => !p.dismissed);

    if (filter === "errors") {
      result = result.filter((p) => p.severity === "error");
    } else if (filter === "warnings") {
      result = result.filter((p) => p.severity === "warning");
    }

    // Sort by timestamp descending (newest first)
    return result.sort((a, b) => b.timestamp - a.timestamp);
  }, [problems, filter]);

  /**
   * Calculate counts.
   */
  const { errorCount, warningCount } = useMemo(() => {
    const active = problems.filter((p) => !p.dismissed);
    return {
      errorCount: active.filter((p) => p.severity === "error").length,
      warningCount: active.filter((p) => p.severity === "warning").length,
    };
  }, [problems]);

  return {
    problems: filteredProblems,
    errorCount,
    warningCount,
    addProblem,
    dismissProblem,
    clearProblems,
  };
}

export default useProblems;
