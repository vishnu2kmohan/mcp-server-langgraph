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
    ? "p-2 bg-neutral-1 rounded compact"
    : "p-4 bg-neutral-1 rounded-lg";

  // Input mode (no goal set)
  if (!currentGoal) {
    return (
      <div data-testid="session-goal-tracker" className={containerClass}>
        <div className="flex items-center gap-2 mb-2">
          <Target className="w-4 h-4 text-primary-9" />
          <span className="text-sm font-medium text-neutral-11">
            Session Goal
          </span>
        </div>
        <div className="flex gap-2">
          <Input
            className="flex-1 px-3 py-2 text-sm text-neutral-12 placeholder-neutral-9 focus:ring-primary-7"
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
          <Button variant="primary"
            className="px-4 py-2 text-sm rounded-lg"
            onClick={handleSetGoal}
            disabled={!inputValue.trim()}
            aria-label="Set Goal"
          >Set Goal</Button>
        </div>
      </div>
    );
  }

  // Edit mode
  if (isEditing) {
    return (
      <div data-testid="session-goal-tracker" className={containerClass}>
        <div className="flex items-center gap-2 mb-2">
          <Target className="w-4 h-4 text-primary-9" />
          <span className="text-sm font-medium text-neutral-11">
            Edit Goal
          </span>
        </div>
        <div className="flex gap-2">
          <Input
            className="flex-1 px-3 py-2 text-sm text-neutral-12 focus:ring-primary-7"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            aria-label="Edit session goal"
          />
          <Button
            variant="primary"
            className="px-3 py-2 text-sm bg-primary-10 text-neutral-12 rounded-lg hover:bg-primary-11"
            onClick={handleSaveEdit}
            aria-label="Save"
          >
            Save
          </Button>
          <Button variant="secondary"
            className="px-3 py-2 text-sm text-neutral-11 hover:text-neutral-12"
            onClick={handleCancelEdit}
            aria-label="Cancel edit"
          >Cancel</Button>
        </div>
      </div>
    );
  }

  // Active goal display
  return (
    <div data-testid="session-goal-tracker" className={containerClass}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-primary-9" />
          <span className="text-sm font-medium text-neutral-11">
            Current Goal
          </span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            className="p-1 text-neutral-9 hover:text-neutral-11 rounded"
            onClick={handleEdit}
            aria-label="Edit">
            <Edit2 className="w-3.5 h-3.5" />
          </Button>
          <Button size="icon" variant="ghost"
            className="p-1 text-neutral-9 hover:text-error-9 rounded"
            onClick={handleClear}
            aria-label="Clear"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>
      <p className="text-sm text-neutral-12 mb-3 p-2 bg-neutral-1 rounded border border-neutral-5">
        {currentGoal}
      </p>
      <div className="flex items-center gap-2">
        <span className="text-xs text-neutral-10">
          Was your goal achieved?
        </span>
        <div className="flex gap-1">
          <Button
            variant="success"
            size="sm"
            className="px-2 py-1 text-xs bg-success-3 text-success-11 bg-success-4 dark:text-success-11 rounded hover:bg-success-4 dark:hover:bg-success-a6 flex"
            onClick={() => handleComplete(true)}
            aria-label="Achieved"
          >
            <Check className="w-3 h-3" />
            Achieved
          </Button>
          <Button
            variant="warning"
            size="sm"
            className="px-2 py-1 text-xs bg-warning-3 text-warning-10 dark:bg-warning-a4 dark:text-warning-9 rounded hover:bg-warning-6 dark:hover:bg-warning-a6"
            onClick={() => handleComplete("partial")}
            aria-label="Partially"
          >
            Partially
          </Button>
          <Button
            variant="danger"
            size="sm"
            className="px-2 py-1 text-xs bg-error-3 text-error-11 bg-error-4 dark:text-error-11 rounded hover:bg-error-4 dark:hover:bg-error-a6 flex"
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
