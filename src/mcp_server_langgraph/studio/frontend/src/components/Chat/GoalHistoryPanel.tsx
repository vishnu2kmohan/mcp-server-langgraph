/**
 * GoalHistoryPanel Component
 *
 * Displays completed goals for a session with achievement status.
 * Supports filtering, collapsible behavior, and compact mode.
 */

import { useState, useMemo, useCallback } from "react";
import {
  History,
  ChevronDown,
  ChevronUp,
  Check,
  X,
  AlertCircle,
  Trash2,
} from "lucide-react";

import { Button, Dialog } from "@/components/UI";

/**
 * Format a timestamp as a relative time string (e.g., "2 hours ago")
 */
function formatRelativeTime(timestamp: number): string {
  const now = Date.now();
  const diffMs = now - timestamp;
  const diffSeconds = Math.floor(diffMs / 1000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) {
    return "just now";
  }
  if (diffMinutes < 60) {
    return `${diffMinutes} minute${diffMinutes === 1 ? "" : "s"} ago`;
  }
  if (diffHours < 24) {
    return `${diffHours} hour${diffHours === 1 ? "" : "s"} ago`;
  }
  if (diffDays < 7) {
    return `${diffDays} day${diffDays === 1 ? "" : "s"} ago`;
  }
  // For older dates, show the date
  return new Date(timestamp).toLocaleDateString();
}

import type { GoalAchievement } from "./SessionGoalTracker";

export interface SessionGoalHistory {
  id: string;
  goal: string;
  achieved: GoalAchievement;
  feedback?: string | null;
  setAt: number;
  completedAt: number;
}

export type GoalFilter = "all" | "achieved" | "partial" | "not-achieved";
export type GoalOrder = "chronological" | "reverse-chronological";

export interface GoalHistoryPanelProps {
  goals: SessionGoalHistory[];
  isLoading?: boolean;
  emptyMessage?: string;
  compact?: boolean;
  collapsible?: boolean;
  /** Initial collapsed state (uncontrolled mode) */
  defaultCollapsed?: boolean;
  /** Controlled collapsed state - when provided, component uses controlled mode */
  isCollapsed?: boolean;
  /** Callback when collapse state changes (controlled mode) */
  onCollapsedChange?: (collapsed: boolean) => void;
  filter?: GoalFilter;
  order?: GoalOrder;
  maxItems?: number;
  onDelete?: (goalId: string) => void;
  showDeleteConfirmation?: boolean;
}

function getAchievementLabel(achieved: GoalAchievement): string {
  if (achieved === true) return "Achieved";
  if (achieved === "partial") return "Partial";
  return "Not Achieved";
}

function getAchievementAriaLabel(achieved: GoalAchievement): string {
  if (achieved === true) return "Status: achieved";
  if (achieved === "partial") return "Status: partial";
  return "Status: not achieved";
}

function getAchievementClasses(achieved: GoalAchievement): string {
  if (achieved === true) {
    return "bg-success-3 text-success-11";
  }
  if (achieved === "partial") {
    return "bg-warning-3 text-warning-10";
  }
  return "bg-error-3 text-error-11";
}

function getAchievementIcon(achieved: GoalAchievement) {
  if (achieved === true) {
    return <Check className="w-3 h-3" />;
  }
  if (achieved === "partial") {
    return <AlertCircle className="w-3 h-3" />;
  }
  return <X className="w-3 h-3" />;
}

function GoalSkeleton({ index }: { index: number }) {
  return (
    <div
      data-testid={`goal-skeleton-${index}`}
      className="animate-pulse p-3 border border-neutral-6 rounded-lg"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1">
          <div className="h-4 bg-neutral-5 rounded w-3/4 mb-2" />
          <div className="h-3 bg-neutral-5 rounded w-1/2" />
        </div>
        <div className="h-5 w-16 bg-neutral-5 rounded" />
      </div>
    </div>
  );
}

function GoalItem({
  goal,
  compact,
  onDelete,
}: {
  goal: SessionGoalHistory;
  compact: boolean;
  onDelete?: (goalId: string) => void;
}) {
  const completedTime = useMemo(
    () => formatRelativeTime(goal.completedAt),
    [goal.completedAt],
  );

  const handleDelete = useCallback(() => {
    if (onDelete) {
      onDelete(goal.id);
    }
  }, [onDelete, goal.id]);

  return (
    <li
      data-testid={`goal-item-${goal.id}`}
      className="p-3 border border-neutral-6 rounded-lg bg-neutral-2"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-neutral-12 truncate">
            {goal.goal}
          </p>
          <p className="text-xs text-neutral-10 mt-1">
            Completed {completedTime}
          </p>
          {!compact && goal.feedback && (
            <p className="text-xs text-neutral-11 mt-2 italic">
              {goal.feedback}
            </p>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span
            aria-label={getAchievementAriaLabel(goal.achieved)}
            className={`flex items-center gap-1 px-2 py-1 text-xs font-medium rounded ${getAchievementClasses(goal.achieved)}`}
          >
            {getAchievementIcon(goal.achieved)}
            {getAchievementLabel(goal.achieved)}
          </span>
          {onDelete && (
            <Button
              variant="ghost"
              size="icon"
              type="button"
              onClick={handleDelete}
              aria-label="Delete goal"
              className="p-1 text-neutral-9 hover:text-error-9 dark:hover:text-error-7 transition-colors rounded hover:bg-neutral-4"
            >
              <Trash2 className="w-4 h-4" />
            </Button>
          )}
        </div>
      </div>
    </li>
  );
}

export function GoalHistoryPanel({
  goals,
  isLoading = false,
  emptyMessage = "No goals recorded yet",
  compact = false,
  collapsible = false,
  defaultCollapsed = false,
  isCollapsed: controlledIsCollapsed,
  onCollapsedChange,
  filter = "all",
  order = "reverse-chronological",
  maxItems,
  onDelete,
  showDeleteConfirmation = false,
}: GoalHistoryPanelProps) {
  // Internal state for uncontrolled mode
  const [internalIsCollapsed, setInternalIsCollapsed] =
    useState(defaultCollapsed);
  const [showAll, setShowAll] = useState(false);
  const [deleteConfirmGoalId, setDeleteConfirmGoalId] = useState<string | null>(
    null,
  );

  // Determine if controlled mode (isCollapsed prop is explicitly provided)
  const isControlled = controlledIsCollapsed !== undefined;

  // Use controlled value if provided, otherwise use internal state
  const isCollapsed = isControlled
    ? controlledIsCollapsed
    : internalIsCollapsed;

  const toggleCollapsed = useCallback(() => {
    const newValue = !isCollapsed;
    if (isControlled) {
      // Controlled mode: notify parent, don't update internal state
      onCollapsedChange?.(newValue);
    } else {
      // Uncontrolled mode: update internal state
      setInternalIsCollapsed(newValue);
    }
  }, [isCollapsed, isControlled, onCollapsedChange]);

  const handleShowMore = useCallback(() => {
    setShowAll(true);
  }, []);

  const handleDeleteClick = useCallback(
    (goalId: string) => {
      if (showDeleteConfirmation) {
        setDeleteConfirmGoalId(goalId);
      } else if (onDelete) {
        onDelete(goalId);
      }
    },
    [showDeleteConfirmation, onDelete],
  );

  const handleConfirmDelete = useCallback(() => {
    if (deleteConfirmGoalId && onDelete) {
      onDelete(deleteConfirmGoalId);
    }
    setDeleteConfirmGoalId(null);
  }, [deleteConfirmGoalId, onDelete]);

  const handleCancelDelete = useCallback(() => {
    setDeleteConfirmGoalId(null);
  }, []);

  // Filter goals based on filter prop
  const filteredGoals = useMemo(() => {
    if (filter === "all") return goals;
    if (filter === "achieved") return goals.filter((g) => g.achieved === true);
    if (filter === "partial")
      return goals.filter((g) => g.achieved === "partial");
    return goals.filter((g) => g.achieved === false);
  }, [goals, filter]);

  // Sort goals based on order prop
  const sortedGoals = useMemo(() => {
    const sorted = [...filteredGoals].sort((a, b) => {
      return order === "chronological"
        ? a.completedAt - b.completedAt
        : b.completedAt - a.completedAt;
    });
    return sorted;
  }, [filteredGoals, order]);

  // Apply maxItems limit
  const displayedGoals = useMemo(() => {
    if (!maxItems || showAll) return sortedGoals;
    return sortedGoals.slice(0, maxItems);
  }, [sortedGoals, maxItems, showAll]);

  const hiddenCount =
    maxItems && !showAll ? Math.max(0, sortedGoals.length - maxItems) : 0;

  const containerClass = compact
    ? "p-2 bg-neutral-1 rounded compact"
    : "p-4 bg-neutral-1 rounded-lg";

  // Loading state
  if (isLoading) {
    return (
      <div
        data-testid="goal-history-panel"
        data-loading="true"
        role="region"
        aria-label="Goal History"
        className={containerClass}
      >
        <div className="flex items-center gap-2 mb-3">
          <History className="w-4 h-4 text-primary-9" />
          <span className="text-sm font-medium text-neutral-11">
            Goal History
          </span>
        </div>
        <div data-testid="goal-history-loading" className="space-y-2">
          {[0, 1, 2].map((i) => (
            <GoalSkeleton key={i} index={i} />
          ))}
        </div>
      </div>
    );
  }

  const headerContent = (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2">
        <History className="w-4 h-4 text-primary-9" />
        <span className="text-sm font-medium text-neutral-11">
          Goal History
        </span>
        {goals.length > 0 && (
          <span
            data-testid="goal-count-badge"
            className="px-1.5 py-0.5 text-xs font-medium bg-primary-3 text-primary-11 rounded-full"
          >
            {goals.length}
          </span>
        )}
      </div>
      {collapsible && (
        <span className="text-neutral-9">
          {isCollapsed ? (
            <ChevronDown className="w-4 h-4" />
          ) : (
            <ChevronUp className="w-4 h-4" />
          )}
        </span>
      )}
    </div>
  );

  return (
    <div
      data-testid="goal-history-panel"
      role="region"
      aria-label="Goal History"
      className={containerClass}
    >
      {collapsible ? (
        <Button
          variant="ghost"
          onClick={toggleCollapsed}
          className="w-full text-left mb-3 justify-start"
          aria-expanded={!isCollapsed}
          aria-label="Goal History"
        >
          {headerContent}
        </Button>
      ) : (
        <div className="mb-3">{headerContent}</div>
      )}

      {(!collapsible || !isCollapsed) && (
        <>
          {displayedGoals.length === 0 ? (
            <p className="text-sm text-neutral-10 text-center py-4">
              {emptyMessage}
            </p>
          ) : (
            <ul role="list" className="space-y-2">
              {displayedGoals.map((goal) => (
                <GoalItem
                  key={goal.id}
                  goal={goal}
                  compact={compact}
                  onDelete={onDelete ? handleDeleteClick : undefined}
                />
              ))}
            </ul>
          )}

          {hiddenCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              onClick={handleShowMore}
              className="w-full mt-2 text-xs text-primary-11 hover:text-primary-11 dark:hover:text-primary-5"
            >
              Show {hiddenCount} more
            </Button>
          )}
        </>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog
        open={deleteConfirmGoalId !== null}
        onClose={handleCancelDelete}
        title="Delete Goal"
        footer={
          <>
            <Button variant="outline" onClick={handleCancelDelete}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleConfirmDelete}>
              Confirm
            </Button>
          </>
        }
      >
        <p className="text-neutral-11">
          Are you sure you want to delete this goal? This action cannot be
          undone.
        </p>
      </Dialog>
    </div>
  );
}

export default GoalHistoryPanel;
