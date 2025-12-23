/**
 * ProblemsTab Component
 *
 * Displays aggregated errors and warnings from various sources.
 * Enhanced version of ProblemsPanel for DevTools.
 */
import { useState, useMemo } from "react";
import {
  AlertCircle,
  AlertTriangle,
  X,
  Trash2,
  CheckCircle,
  FileCode,
} from "lucide-react";

import { cn } from "../../../utils/cn";
import { useAppSelector } from "../../../store/hooks";
import { selectSessionError } from "../../../store/slices/sessionSlice";
import { selectMCPError } from "../../../store/slices/mcpSlice";
import type { ProblemsTabProps } from "../types";

// =============================================================================
// Types
// =============================================================================

type FilterType = "all" | "errors" | "warnings";

interface Problem {
  id: string;
  severity: "error" | "warning";
  message: string;
  source: string;
  file?: string;
  line?: number;
  timestamp: number;
}

// =============================================================================
// Subcomponents
// =============================================================================

interface ProblemRowProps {
  problem: Problem;
  onDismiss?: () => void;
}

function ProblemRow({ problem, onDismiss }: ProblemRowProps) {
  const [isHovered, setIsHovered] = useState(false);

  const SeverityIcon = problem.severity === "error" ? AlertCircle : AlertTriangle;
  const severityColor =
    problem.severity === "error"
      ? "text-red-500 dark:text-red-400"
      : "text-amber-500 dark:text-amber-400";

  return (
    <li
      data-testid={`problem-${problem.id}`}
      className={cn(
        "flex items-start gap-2 px-3 py-2",
        "border-b border-gray-100 dark:border-gray-800",
        "hover:bg-gray-50 dark:hover:bg-gray-800/50"
      )}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Severity icon */}
      <SeverityIcon
        data-testid={`severity-${problem.severity}`}
        size={16}
        className={cn("mt-0.5 flex-shrink-0", severityColor)}
        aria-hidden="true"
      />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-gray-900 dark:text-gray-100 break-words">
          {problem.message}
        </p>

        <div className="flex items-center gap-2 mt-1 text-xs text-gray-500 dark:text-gray-400">
          <span className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-800 rounded">
            {problem.source}
          </span>

          {problem.file && (
            <span className="flex items-center gap-1">
              <FileCode size={12} aria-hidden="true" />
              <span>
                {problem.file}
                {problem.line && `:${problem.line}`}
              </span>
            </span>
          )}
        </div>
      </div>

      {/* Dismiss button */}
      {isHovered && onDismiss && (
        <button
          data-testid="dismiss-button"
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss problem"
          className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded"
        >
          <X size={14} />
        </button>
      )}
    </li>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function ProblemsTab({
  showCount = true,
  compact = false,
}: ProblemsTabProps) {
  const [filter, setFilter] = useState<FilterType>("all");
  const [dismissedIds, setDismissedIds] = useState<Set<string>>(new Set());

  // Get errors from Redux
  const sessionError = useAppSelector(selectSessionError);
  const mcpError = useAppSelector(selectMCPError);

  // Build problems list from Redux state
  const problems = useMemo((): Problem[] => {
    const result: Problem[] = [];

    if (sessionError) {
      result.push({
        id: "session-error",
        severity: "error",
        message: sessionError,
        source: "session",
        timestamp: Date.now(),
      });
    }

    if (mcpError) {
      result.push({
        id: "mcp-error",
        severity: "error",
        message: mcpError,
        source: "mcp",
        timestamp: Date.now(),
      });
    }

    return result.filter((p) => !dismissedIds.has(p.id));
  }, [sessionError, mcpError, dismissedIds]);

  // Apply filter
  const filteredProblems = useMemo(() => {
    if (filter === "errors") {
      return problems.filter((p) => p.severity === "error");
    }
    if (filter === "warnings") {
      return problems.filter((p) => p.severity === "warning");
    }
    return problems;
  }, [problems, filter]);

  // Calculate counts
  const errorCount = problems.filter((p) => p.severity === "error").length;
  const warningCount = problems.filter((p) => p.severity === "warning").length;

  const dismissProblem = (id: string) => {
    setDismissedIds((prev) => new Set([...prev, id]));
  };

  const clearAll = () => {
    setDismissedIds(new Set(problems.map((p) => p.id)));
  };

  return (
    <div
      data-testid="problems-tab"
      className={cn(
        "flex flex-col h-full bg-white dark:bg-gray-900",
        compact && "compact"
      )}
    >
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-2 py-1 border-b border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800">
        {/* Filter buttons */}
        <div className="flex items-center gap-1">
          <button
            data-testid="filter-all"
            type="button"
            onClick={() => setFilter("all")}
            className={cn(
              "px-2 py-1 text-xs rounded",
              filter === "all"
                ? "bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300"
                : "hover:bg-gray-200 dark:hover:bg-gray-700"
            )}
          >
            All
          </button>
          <button
            data-testid="filter-errors"
            type="button"
            onClick={() => setFilter("errors")}
            className={cn(
              "px-2 py-1 text-xs rounded flex items-center gap-1",
              filter === "errors"
                ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300"
                : "hover:bg-gray-200 dark:hover:bg-gray-700"
            )}
          >
            <AlertCircle size={12} />
            Errors
          </button>
          <button
            data-testid="filter-warnings"
            type="button"
            onClick={() => setFilter("warnings")}
            className={cn(
              "px-2 py-1 text-xs rounded flex items-center gap-1",
              filter === "warnings"
                ? "bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300"
                : "hover:bg-gray-200 dark:hover:bg-gray-700"
            )}
          >
            <AlertTriangle size={12} />
            Warnings
          </button>
        </div>

        {/* Counts */}
        {showCount && (
          <div className="flex items-center gap-2 ml-2">
            <span
              data-testid="error-count"
              className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400"
            >
              <AlertCircle size={12} />
              {errorCount}
            </span>
            <span
              data-testid="warning-count"
              className="flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400"
            >
              <AlertTriangle size={12} />
              {warningCount}
            </span>
          </div>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Clear all */}
        <button
          data-testid="clear-all-button"
          type="button"
          onClick={clearAll}
          aria-label="Clear all problems"
          className="p-1 hover:bg-gray-200 dark:hover:bg-gray-700 rounded text-gray-500 hover:text-red-500"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {/* Problems list */}
      {filteredProblems.length === 0 ? (
        <div
          data-testid="problems-empty-state"
          className="flex-1 flex flex-col items-center justify-center text-gray-400 dark:text-gray-500"
        >
          <CheckCircle size={32} className="mb-2 opacity-50 text-green-500" />
          <p>No problems detected</p>
          <p className="text-xs mt-1">Your code looks good!</p>
        </div>
      ) : (
        <ul
          role="list"
          aria-label="Problems"
          className="flex-1 overflow-y-auto"
        >
          {filteredProblems.map((problem) => (
            <ProblemRow
              key={problem.id}
              problem={problem}
              onDismiss={() => dismissProblem(problem.id)}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

export default ProblemsTab;
