/**
 * SessionGoalTracker Component
 *
 * Tracks multi-turn conversation goals.
 * Allows users to set goals and track achievement.
 */

import { useState, useCallback } from "react";
import { Target, Check, X, Edit2, Trash2 } from "lucide-react";

import { Button, Input } from "@/components/UI";

export type GoalAchievement = boolean | "partial";

export interface GoalSetData {
  sessionId: string;
  goal: string;
  timestamp: number;
}

export interface GoalResult {
  sessionId: string;
  goal: string;
  achieved: GoalAchievement;
  timestamp: number;
}

export interface SessionGoalTrackerProps {
  sessionId: string;
  currentGoal?: string;
  onGoalSet: (data: GoalSetData) => void;
  onGoalComplete: (result: GoalResult) => void;
  onGoalClear?: () => void;
  compact?: boolean;
}

export function SessionGoalTracker({
  sessionId,
  currentGoal,
  onGoalSet,
  onGoalComplete,
  onGoalClear,
  compact = false,
}: SessionGoalTrackerProps) {
  const [inputValue, setInputValue] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState("");

  const handleSetGoal = useCallback(() => {
    if (inputValue.trim()) {
      onGoalSet({
        sessionId,
        goal: inputValue.trim(),
        timestamp: Date.now(),
      });
      setInputValue("");
    }
  }, [sessionId, inputValue, onGoalSet]);

  const handleComplete = useCallback(
    (achieved: GoalAchievement) => {
      if (currentGoal) {
        onGoalComplete({
          sessionId,
          goal: currentGoal,
          achieved,
          timestamp: Date.now(),
        });
      }
    },
    [sessionId, currentGoal, onGoalComplete],
  );

  const handleEdit = useCallback(() => {
    setEditValue(currentGoal || "");
    setIsEditing(true);
  }, [currentGoal]);

  const handleSaveEdit = useCallback(() => {
    if (editValue.trim()) {
      onGoalSet({
        sessionId,
        goal: editValue.trim(),
        timestamp: Date.now(),
      });
      setIsEditing(false);
      setEditValue("");
    }
  }, [sessionId, editValue, onGoalSet]);

  const handleCancelEdit = useCallback(() => {
    setIsEditing(false);
    setEditValue("");
  }, []);

  const handleClear = useCallback(() => {
    if (onGoalClear) {
      onGoalClear();
    }
  }, [onGoalClear]);

  const containerClass = compact
    ? "p-2 bg-neutral-50 dark:bg-neutral-800 rounded compact"
    : "p-4 bg-neutral-50 dark:bg-neutral-800 rounded-lg";

  // Input mode (no goal set)
  if (!currentGoal) {
    return (
      <div data-testid="session-goal-tracker" className={containerClass}>
        <div className="flex items-center gap-2 mb-2">
          <Target className="w-4 h-4 text-primary-500" />
          <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
            Session Goal
          </span>
        </div>
        <div className="flex gap-2">
          <Input
            className="flex-1 px-3 py-2 dark:border-neutral-600 text-sm text-neutral-900 dark:text-neutral-100 placeholder-neutral-500 focus:ring-primary-500"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="What would you like to accomplish?"
            aria-label="Session goal input"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleSetGoal();
              }
            }}
          />
          <Button
            className="px-4 py-2 text-sm rounded-lg"
            onClick={handleSetGoal}
            disabled={!inputValue.trim()}
            aria-label="Set Goal"
          >
            Set Goal
          </Button>
        </div>
      </div>
    );
  }

  // Edit mode
  if (isEditing) {
    return (
      <div data-testid="session-goal-tracker" className={containerClass}>
        <div className="flex items-center gap-2 mb-2">
          <Target className="w-4 h-4 text-primary-500" />
          <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
            Edit Goal
          </span>
        </div>
        <div className="flex gap-2">
          <Input
            className="flex-1 px-3 py-2 dark:border-neutral-600 text-sm text-neutral-900 dark:text-neutral-100 focus:ring-primary-500"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            aria-label="Edit session goal"
          />
          <Button
            variant="primary"
            className="px-3 py-2 text-sm bg-primary-600 text-white rounded-lg hover:bg-primary-700"
            onClick={handleSaveEdit}
            aria-label="Save"
          >
            Save
          </Button>
          <Button
            className="px-3 py-2 text-sm text-neutral-600 dark:text-neutral-400 hover:text-neutral-800 dark:hover:text-neutral-200"
            onClick={handleCancelEdit}
            aria-label="Cancel edit"
          >
            Cancel
          </Button>
        </div>
      </div>
    );
  }

  // Active goal display
  return (
    <div data-testid="session-goal-tracker" className={containerClass}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-primary-500" />
          <span className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
            Current Goal
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            className="p-1 text-neutral-400 dark:text-neutral-400 hover:text-neutral-600 dark:text-neutral-300 dark:hover:text-neutral-300 rounded"
            onClick={handleEdit}
            aria-label="Edit"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </Button>
          <Button
            className="p-1 text-neutral-400 dark:text-neutral-400 hover:text-error-500 rounded"
            onClick={handleClear}
            aria-label="Clear"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>
      <p className="text-sm text-neutral-900 dark:text-neutral-100 mb-3 p-2 bg-white dark:bg-neutral-700 rounded border border-neutral-200 dark:border-neutral-700 dark:border-neutral-600">
        {currentGoal}
      </p>
      <div className="flex items-center gap-2">
        <span className="text-xs text-neutral-500 dark:text-neutral-400">
          Was your goal achieved?
        </span>
        <div className="flex gap-1">
          <Button
            variant="success"
            size="sm"
            className="px-2 py-1 text-xs bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-400 rounded hover:bg-success-200 dark:hover:bg-success-900/50 flex"
            onClick={() => handleComplete(true)}
            aria-label="Achieved"
          >
            <Check className="w-3 h-3" />
            Achieved
          </Button>
          <Button
            variant="warning"
            size="sm"
            className="px-2 py-1 text-xs bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-400 rounded hover:bg-warning-200 dark:hover:bg-warning-900/50"
            onClick={() => handleComplete("partial")}
            aria-label="Partially"
          >
            Partially
          </Button>
          <Button
            variant="danger"
            size="sm"
            className="px-2 py-1 text-xs bg-error-100 text-error-700 dark:bg-error-900/30 dark:text-error-400 rounded hover:bg-error-200 dark:hover:bg-error-900/50 flex"
            onClick={() => handleComplete(false)}
            aria-label="Not Achieved"
          >
            <X className="w-3 h-3" />
            Not Achieved
          </Button>
        </div>
      </div>
    </div>
  );
}

export default SessionGoalTracker;
