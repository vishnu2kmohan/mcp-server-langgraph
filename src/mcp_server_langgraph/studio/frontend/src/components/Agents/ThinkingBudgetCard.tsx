/**
 * ThinkingBudgetCard
 *
 * Displays thinking budget configuration including default level,
 * complexity mapping, and available thinking levels.
 *
 * Enhanced in Sprint 2.5 with edit functionality:
 * - Edit button for admin/developer personas
 * - Level selector dropdown
 * - Enabled toggle switch
 * - Save/Cancel buttons with API mutation
 *
 * Visible only to admin and developer personas.
 */

import { useState } from "react";
import { useSelector } from "react-redux";
import {
  Brain,
  Zap,
  Gauge,
  AlertTriangle,
  Pencil,
  Save,
  X,
} from "lucide-react";
import { selectPersona } from "../../store/slices/personaSlice";
import { Card, CardTitle, CardContent } from "../UI/Card";
import { useUpdateThinkingBudgetMutation } from "../../api";
import type { ThinkingBudgetDefaults } from "../../types/api";

interface ThinkingBudgetCardProps {
  data: ThinkingBudgetDefaults | null | undefined;
}

// Valid thinking levels
const THINKING_LEVELS = ["low", "medium", "high", "ultra"] as const;

/**
 * Get icon for complexity level
 */
function getComplexityIcon(complexity: string) {
  switch (complexity) {
    case "simple":
      return <Zap size={14} className="text-green-500" />;
    case "complicated":
      return <Gauge size={14} className="text-yellow-500" />;
    case "complex":
      return <Brain size={14} className="text-orange-500" />;
    case "chaotic":
      return <AlertTriangle size={14} className="text-red-500" />;
    default:
      return <Gauge size={14} className="text-gray-400" />;
  }
}

/**
 * Get color class for thinking level
 */
function getLevelColorClass(level: string): string {
  switch (level) {
    case "low":
      return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400";
    case "medium":
      return "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400";
    case "high":
      return "bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400";
    case "ultra":
      return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400";
    default:
      return "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-400";
  }
}

export function ThinkingBudgetCard({ data }: ThinkingBudgetCardProps) {
  const persona = useSelector(selectPersona);

  // Edit mode state
  const [isEditing, setIsEditing] = useState(false);
  const [editLevel, setEditLevel] = useState(data?.defaultLevel ?? "medium");
  const [editEnabled, setEditEnabled] = useState(data?.enabled ?? true);

  // RTK Query mutation
  const [updateThinkingBudget, { isLoading: isSaving }] =
    useUpdateThinkingBudgetMutation();

  // Only show for admin and developer personas
  if (!["admin", "developer"].includes(persona)) {
    return null;
  }

  // Don't render if no data
  if (!data) {
    return null;
  }

  // Enter edit mode
  const handleEdit = () => {
    setEditLevel(data.defaultLevel);
    setEditEnabled(data.enabled);
    setIsEditing(true);
  };

  // Cancel edit mode
  const handleCancel = () => {
    setIsEditing(false);
  };

  // Save changes
  const handleSave = async () => {
    try {
      await updateThinkingBudget({
        default_level: editLevel,
        enabled: editEnabled,
      }).unwrap();
      setIsEditing(false);
    } catch {
      // Error is handled by RTK Query - could show toast here
      console.error("Failed to update thinking budget");
    }
  };

  return (
    <Card data-testid="thinking-budget-card">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <Brain size={24} className="text-purple-500" />
          <CardTitle>Thinking Budget</CardTitle>
        </div>
        <div className="flex items-center gap-2">
          {!isEditing ? (
            <>
              <span
                className={`px-2 py-1 text-xs font-medium rounded-full ${
                  data.enabled
                    ? "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400"
                    : "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400"
                }`}
              >
                {data.enabled ? "Enabled" : "Disabled"}
              </span>
              <button
                data-testid="edit-thinking-budget-button"
                onClick={handleEdit}
                className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                title="Edit thinking budget configuration"
              >
                <Pencil
                  size={16}
                  className="text-gray-500 dark:text-gray-400"
                />
              </button>
            </>
          ) : (
            <>
              <button
                data-testid="cancel-edit-button"
                onClick={handleCancel}
                disabled={isSaving}
                className="p-1.5 rounded hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors disabled:opacity-50"
                title="Cancel editing"
              >
                <X size={16} className="text-gray-500 dark:text-gray-400" />
              </button>
              <button
                data-testid="save-thinking-budget-button"
                onClick={handleSave}
                disabled={isSaving}
                className="p-1.5 rounded bg-blue-500 hover:bg-blue-600 transition-colors disabled:opacity-50"
                title="Save changes"
              >
                <Save size={16} className="text-white" />
              </button>
            </>
          )}
        </div>
      </div>

      <CardContent>
        {/* Edit Controls (shown when editing) */}
        {isEditing && (
          <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
            <div className="space-y-4">
              {/* Level Selector */}
              <div>
                <label
                  htmlFor="thinking-level-select"
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                >
                  Default Level
                </label>
                <select
                  id="thinking-level-select"
                  data-testid="thinking-level-selector"
                  value={editLevel}
                  onChange={(e) => setEditLevel(e.target.value)}
                  disabled={isSaving}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 disabled:opacity-50"
                >
                  {THINKING_LEVELS.map((level) => (
                    <option key={level} value={level}>
                      {level.charAt(0).toUpperCase() + level.slice(1)}
                    </option>
                  ))}
                </select>
              </div>

              {/* Enabled Toggle */}
              <div className="flex items-center justify-between">
                <label
                  htmlFor="thinking-enabled-toggle"
                  className="text-sm font-medium text-gray-700 dark:text-gray-300"
                >
                  Enable Thinking Budget
                </label>
                <button
                  id="thinking-enabled-toggle"
                  data-testid="thinking-enabled-toggle"
                  type="button"
                  role="switch"
                  aria-checked={editEnabled}
                  onClick={() => setEditEnabled(!editEnabled)}
                  disabled={isSaving}
                  className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors disabled:opacity-50 ${
                    editEnabled ? "bg-blue-600" : "bg-gray-300 dark:bg-gray-600"
                  }`}
                >
                  <span
                    className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                      editEnabled ? "translate-x-6" : "translate-x-1"
                    }`}
                  />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Default Level (read-only view) */}
        {!isEditing && (
          <div className="mb-4">
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-1">
              Default Level
            </p>
            <span
              className={`inline-flex px-2 py-1 text-sm font-medium rounded ${getLevelColorClass(data.defaultLevel)}`}
            >
              {data.defaultLevel}
            </span>
          </div>
        )}

        {/* Complexity Mapping */}
        <div className="mb-4">
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
            Complexity Mapping
          </p>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(data.complexityMapping).map(
              ([complexity, level]) => (
                <div
                  key={complexity}
                  className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-800 rounded"
                >
                  <div className="flex items-center gap-2">
                    {getComplexityIcon(complexity)}
                    <span className="text-sm text-gray-700 dark:text-gray-300 capitalize">
                      {complexity}
                    </span>
                  </div>
                  <span
                    className={`px-2 py-0.5 text-xs font-medium rounded ${getLevelColorClass(level)}`}
                  >
                    {level}
                  </span>
                </div>
              ),
            )}
          </div>
        </div>

        {/* Thinking Levels */}
        <div>
          <p className="text-sm text-gray-500 dark:text-gray-400 mb-2">
            Available Levels
          </p>
          <div className="space-y-2">
            {data.levels.map((levelInfo) => (
              <div
                key={levelInfo.level}
                className="p-2 border border-gray-200 dark:border-gray-700 rounded"
              >
                <div className="flex items-center justify-between mb-1">
                  <span
                    className={`px-2 py-0.5 text-xs font-medium rounded ${getLevelColorClass(levelInfo.level)}`}
                  >
                    {levelInfo.level}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {levelInfo.otherModelsTokens.toLocaleString()} tokens
                  </span>
                </div>
                <p className="text-xs text-gray-600 dark:text-gray-400">
                  {levelInfo.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
