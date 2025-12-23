/**
 * ProblemsPanel Component
 *
 * @deprecated This component is superseded by DevTools ProblemsTab.
 * The ProblemsTab provides enhanced functionality including:
 * - Aggregates more error sources (session, MCP, validation, API)
 * - Severity-based filtering
 * - Error details with stack traces
 * - Copy error to clipboard
 *
 * Migration: Use DevTools panel (Cmd+Shift+I) Problems tab instead.
 * See: components/DevTools/CONSOLIDATION.md for migration guide.
 *
 * Displays aggregated errors and warnings from various sources.
 * Used in the BottomPanel's Problems tab.
 *
 * Features:
 * - Aggregates session and MCP errors
 * - Visual error/warning styling
 * - Problem count indicator
 */

import { AlertCircle, CheckCircle } from "lucide-react";
import { useAppSelector } from "../../store/hooks";
import { selectSessionError } from "../../store/slices/sessionSlice";
import { selectMCPError } from "../../store/slices/mcpSlice";

// =============================================================================
// Utility
// =============================================================================

function cn(...classes: (string | undefined | boolean)[]): string {
  return classes.filter(Boolean).join(" ");
}

// =============================================================================
// Types
// =============================================================================

export interface ProblemsPanelProps {
  /** Show problem count badge */
  showCount?: boolean;
  /** Compact mode with reduced spacing */
  compact?: boolean;
  /** Additional CSS classes */
  className?: string;
}

// =============================================================================
// Problem Item Component
// =============================================================================

interface ProblemItemProps {
  title: string;
  message: string;
  severity: "error" | "warning";
  compact?: boolean;
}

function ProblemItem({ title, message, severity, compact }: ProblemItemProps) {
  const isError = severity === "error";

  return (
    <div
      className={cn(
        "flex items-start gap-2 rounded-md",
        compact ? "p-1.5" : "p-2",
        isError
          ? "bg-red-50 dark:bg-red-900/20"
          : "bg-yellow-50 dark:bg-yellow-900/20",
      )}
    >
      <AlertCircle
        size={compact ? 12 : 14}
        className={cn(
          "mt-0.5 flex-shrink-0",
          isError ? "text-red-500" : "text-yellow-500",
        )}
      />
      <div className="min-w-0">
        <p
          className={cn(
            "font-medium",
            compact ? "text-xs" : "text-sm",
            isError
              ? "text-red-700 dark:text-red-400"
              : "text-yellow-700 dark:text-yellow-400",
          )}
        >
          {title}
        </p>
        <p
          className={cn(
            compact ? "text-[10px]" : "text-xs",
            isError
              ? "text-red-600 dark:text-red-300"
              : "text-yellow-600 dark:text-yellow-300",
          )}
        >
          {message}
        </p>
      </div>
    </div>
  );
}

// =============================================================================
// Main Component
// =============================================================================

export function ProblemsPanel({
  showCount = false,
  compact = false,
  className,
}: ProblemsPanelProps) {
  const sessionError = useAppSelector(selectSessionError);
  const mcpError = useAppSelector(selectMCPError);

  // Calculate problem count
  const problemCount = (sessionError ? 1 : 0) + (mcpError ? 1 : 0);
  const hasProblems = problemCount > 0;

  return (
    <div
      data-testid="problems-panel"
      className={cn(
        "text-sm text-gray-500 dark:text-gray-400",
        compact ? "p-2" : "p-4",
        className,
      )}
    >
      {/* Optional count badge */}
      {showCount && (
        <span
          data-testid="problem-count"
          className={cn(
            "inline-flex items-center justify-center px-2 py-0.5 rounded-full text-xs font-medium mb-2",
            hasProblems
              ? "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
              : "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
          )}
        >
          {problemCount}
        </span>
      )}

      {!hasProblems ? (
        <div className="flex items-center gap-2">
          <CheckCircle size={compact ? 14 : 16} className="text-green-500" />
          <span>No problems detected</span>
        </div>
      ) : (
        <div className={cn("space-y-2", compact && "space-y-1")}>
          {sessionError && (
            <ProblemItem
              title="Session Error"
              message={sessionError}
              severity="error"
              compact={compact}
            />
          )}
          {mcpError && (
            <ProblemItem
              title="MCP Error"
              message={mcpError}
              severity="error"
              compact={compact}
            />
          )}
        </div>
      )}
    </div>
  );
}

export default ProblemsPanel;
