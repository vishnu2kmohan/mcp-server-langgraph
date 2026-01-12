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
import { useTimelineContext } from "../context/DevToolsTimelineProvider";
import type { ProblemsTabProps } from "../types";
import { STATUS_TEXT_COLORS } from "../utils/devToolsColors";

import { Button } from "@/components/UI";

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

  const SeverityIcon =
    problem.severity === "error" ? AlertCircle : AlertTriangle;
  const severityColor =
    problem.severity === "error"
      ? STATUS_TEXT_COLORS.error
      : STATUS_TEXT_COLORS.warning;

  return (
    <li
      data-testid={`problem-${problem.id}`}
      className={cn(
        "flex items-start gap-2 px-3 py-2",
        "border-b border-neutral-100 dark:border-neutral-800",
        "hover:bg-neutral-50 dark:hover:bg-neutral-800/50",
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
        <p className="text-sm text-neutral-900 dark:text-neutral-100 break-words">
          {problem.message}
        </p>

        <div className="flex items-center gap-2 mt-1 text-xs text-neutral-500 dark:text-neutral-400">
          <span className="px-1.5 py-0.5 bg-neutral-100 dark:bg-neutral-800 rounded">
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
        <Button
          variant="secondary"
          className="p-1 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 rounded"
          data-testid="dismiss-button"
          type="button"
          onClick={onDismiss}
          aria-label="Dismiss problem"
        >
          <X size={14} />
        </Button>
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

  // Timeline integration for time-travel debugging
  const timeline = useTimelineContext();

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

  // Apply filter (including timeline filter)
  const filteredProblems = useMemo(() => {
    let result = problems;

    // Filter by timeline window for time-travel debugging
    if (timeline.timeWindow) {
      result = result.filter((p) => {
        return (
          p.timestamp >= timeline.timeWindow!.start &&
          p.timestamp <= timeline.timeWindow!.end
        );
      });
    }

    // Apply severity filter
    if (filter === "errors") {
      return result.filter((p) => p.severity === "error");
    }
    if (filter === "warnings") {
      return result.filter((p) => p.severity === "warning");
    }
    return result;
  }, [problems, filter, timeline.timeWindow]);

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
        "flex flex-col h-full bg-white dark:bg-neutral-900",
        compact && "compact",
      )}
    >
      {/* Toolbar */}
      <div className="flex items-center gap-2 px-2 py-1 border-b border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800">
        {/* Filter buttons */}
        <div className="flex items-center gap-1">
          <Button
            data-testid="filter-all"
            type="button"
            onClick={() => setFilter("all")}
            className={cn(
              "px-2 py-1 text-xs rounded",
              filter === "all"
                ? "bg-primary-100 dark:bg-primary-900/30 text-primary-700 dark:text-primary-300"
                : "hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700",
            )}
          >
            All
          </Button>
          <Button
            data-testid="filter-errors"
            type="button"
            onClick={() => setFilter("errors")}
            className={cn(
              "px-2 py-1 text-xs rounded flex items-center gap-1",
              filter === "errors"
                ? "bg-error-100 dark:bg-error-900/30 text-error-700 dark:text-error-300"
                : "hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700",
            )}
          >
            <AlertCircle size={12} />
            Errors
          </Button>
          <Button
            data-testid="filter-warnings"
            type="button"
            onClick={() => setFilter("warnings")}
            className={cn(
              "px-2 py-1 text-xs rounded flex items-center gap-1",
              filter === "warnings"
                ? "bg-warning-100 dark:bg-warning-900/30 text-warning-700 dark:text-warning-300"
                : "hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700",
            )}
          >
            <AlertTriangle size={12} />
            Warnings
          </Button>
        </div>

        {/* Counts */}
        {showCount && (
          <div className="flex items-center gap-2 ml-2">
            <span
              data-testid="error-count"
              className={cn(
                "flex items-center gap-1 text-xs",
                STATUS_TEXT_COLORS.error,
              )}
            >
              <AlertCircle size={12} />
              {errorCount}
            </span>
            <span
              data-testid="warning-count"
              className="flex items-center gap-1 text-xs text-warning-600 dark:text-warning-400"
            >
              <AlertTriangle size={12} />
              {warningCount}
            </span>
          </div>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Clear all */}
        <Button
          variant="secondary"
          className="p-1 hover:bg-neutral-200 dark:bg-neutral-700 dark:hover:bg-neutral-700 rounded text-neutral-500 dark:text-neutral-400 hover:text-error-500"
          data-testid="clear-all-button"
          type="button"
          onClick={clearAll}
          aria-label="Clear all problems"
        >
          <Trash2 size={14} />
        </Button>
      </div>
      {/* Problems list */}
      {filteredProblems.length === 0 ? (
        <div
          data-testid="problems-empty-state"
          className="flex-1 flex flex-col items-center justify-center text-neutral-400 dark:text-neutral-400"
        >
          <CheckCircle size={32} className="mb-2 opacity-50 text-success-500" />
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
