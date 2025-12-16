/**
 * SessionGoalTracker Component
 *
 * Tracks multi-turn conversation goals.
 * Allows users to set goals and track achievement.
 */

import { useState, useCallback } from "react";
import { Target, Check, X, Edit2, Trash2 } from "lucide-react";

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
    ? "p-2 bg-gray-50 dark:bg-gray-800 rounded compact"
    : "p-4 bg-gray-50 dark:bg-gray-800 rounded-lg";

  // Input mode (no goal set)
  if (!currentGoal) {
    return (
      <div data-testid="session-goal-tracker" className={containerClass}>
        <div className="flex items-center gap-2 mb-2">
          <Target className="w-4 h-4 text-blue-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Session Goal
          </span>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={inputValue}
            onChange={(e) => setInputValue(e.target.value)}
            placeholder="What would you like to accomplish?"
            aria-label="Session goal input"
            className="flex-1 px-3 py-2 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-gray-100 placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                handleSetGoal();
              }
            }}
          />
          <button
            onClick={handleSetGoal}
            disabled={!inputValue.trim()}
            aria-label="Set Goal"
            className={`px-4 py-2 text-sm rounded-lg ${
              inputValue.trim()
                ? "bg-blue-600 text-white hover:bg-blue-700"
                : "bg-gray-200 text-gray-400 cursor-not-allowed"
            }`}
          >
            Set Goal
          </button>
        </div>
      </div>
    );
  }

  // Edit mode
  if (isEditing) {
    return (
      <div data-testid="session-goal-tracker" className={containerClass}>
        <div className="flex items-center gap-2 mb-2">
          <Target className="w-4 h-4 text-blue-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Edit Goal
          </span>
        </div>
        <div className="flex gap-2">
          <input
            type="text"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            aria-label="Edit session goal"
            className="flex-1 px-3 py-2 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSaveEdit}
            aria-label="Save"
            className="px-3 py-2 text-sm bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Save
          </button>
          <button
            onClick={handleCancelEdit}
            aria-label="Cancel edit"
            className="px-3 py-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-800 dark:hover:text-gray-200"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  // Active goal display
  return (
    <div data-testid="session-goal-tracker" className={containerClass}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <Target className="w-4 h-4 text-blue-500" />
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            Current Goal
          </span>
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleEdit}
            aria-label="Edit"
            className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 rounded"
          >
            <Edit2 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={handleClear}
            aria-label="Clear"
            className="p-1 text-gray-400 hover:text-red-500 rounded"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      <p className="text-sm text-gray-900 dark:text-gray-100 mb-3 p-2 bg-white dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600">
        {currentGoal}
      </p>

      <div className="flex items-center gap-2">
        <span className="text-xs text-gray-500 dark:text-gray-400">
          Was your goal achieved?
        </span>
        <div className="flex gap-1">
          <button
            onClick={() => handleComplete(true)}
            aria-label="Achieved"
            className="px-2 py-1 text-xs bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded hover:bg-green-200 dark:hover:bg-green-900/50 flex items-center gap-1"
          >
            <Check className="w-3 h-3" />
            Achieved
          </button>
          <button
            onClick={() => handleComplete("partial")}
            aria-label="Partially"
            className="px-2 py-1 text-xs bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400 rounded hover:bg-yellow-200 dark:hover:bg-yellow-900/50"
          >
            Partially
          </button>
          <button
            onClick={() => handleComplete(false)}
            aria-label="Not Achieved"
            className="px-2 py-1 text-xs bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded hover:bg-red-200 dark:hover:bg-red-900/50 flex items-center gap-1"
          >
            <X className="w-3 h-3" />
            Not Achieved
          </button>
        </div>
      </div>
    </div>
  );
}

export default SessionGoalTracker;
