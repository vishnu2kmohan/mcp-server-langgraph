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

import { Button, Select, Toggle } from "@/components/UI";

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
      return <Zap size={14} className="text-success-500" />;
    case "complicated":
      return <Gauge size={14} className="text-warning-500" />;
    case "complex":
      return <Brain size={14} className="text-grafana-500" />;
    case "chaotic":
      return <AlertTriangle size={14} className="text-error-500" />;
    default:
      return (
        <Gauge size={14} className="text-neutral-400 dark:text-neutral-400" />
      );
  }
}

/**
 * Get color class for thinking level
 */
function getLevelColorClass(level: string): string {
  switch (level) {
    case "low":
      return "bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-400";
    case "medium":
      return "bg-warning-100 text-warning-800 dark:bg-warning-900/30 dark:text-warning-400";
    case "high":
      return "bg-grafana-100 text-grafana-800 dark:bg-grafana-900/30 dark:text-grafana-400";
    case "ultra":
      return "bg-error-100 text-error-800 dark:bg-error-900/30 dark:text-error-400";
    default:
      return "bg-neutral-100 dark:bg-neutral-800 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-400";
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
          <Brain size={24} className="text-insight-500" />
          <CardTitle>Thinking Budget</CardTitle>
        </div>
        <div className="flex items-center gap-2">
          {!isEditing ? (
            <>
              <span
                className={`px-2 py-1 text-xs font-medium rounded-full ${
                  data.enabled
                    ? "bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-400"
                    : "bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400"
                }`}
              >
                {data.enabled ? "Enabled" : "Disabled"}
              </span>
              <Button
                variant="secondary"
                className="p-1.5 rounded hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-800"
                data-testid="edit-thinking-budget-button"
                onClick={handleEdit}
                title="Edit thinking budget configuration"
              >
                <Pencil
                  size={16}
                  className="text-neutral-500 dark:text-neutral-400"
                />
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="secondary"
                className="p-1.5 rounded hover:bg-neutral-100 dark:bg-neutral-800 dark:hover:bg-neutral-800"
                data-testid="cancel-edit-button"
                onClick={handleCancel}
                disabled={isSaving}
                title="Cancel editing"
              >
                <X
                  size={16}
                  className="text-neutral-500 dark:text-neutral-400"
                />
              </Button>
              <Button
                variant="primary"
                className="p-1.5 rounded bg-primary-500 hover:bg-primary-600"
                data-testid="save-thinking-budget-button"
                onClick={handleSave}
                disabled={isSaving}
                title="Save changes"
              >
                <Save size={16} className="text-white" />
              </Button>
            </>
          )}
        </div>
      </div>
      <CardContent>
        {/* Edit Controls (shown when editing) */}
        {isEditing && (
          <div className="mb-4 p-3 bg-primary-50 dark:bg-primary-900/20 rounded-lg border border-primary-200 dark:border-primary-800">
            <div className="space-y-4">
              {/* Level Selector */}
              <div>
                <label
                  htmlFor="thinking-level-select"
                  className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1"
                >
                  Default Level
                </label>
                <Select
                  className="px-3 py-2 text-neutral-900 dark:text-neutral-100 disabled:opacity-50"
                  id="thinking-level-select"
                  data-testid="thinking-level-selector"
                  value={editLevel}
                  onChange={(e) => setEditLevel(e.target.value)}
                  disabled={isSaving}
                >
                  {THINKING_LEVELS.map((level) => (
                    <option key={level} value={level}>
                      {level.charAt(0).toUpperCase() + level.slice(1)}
                    </option>
                  ))}
                </Select>
              </div>

              {/* Enabled Toggle */}
              <Toggle
                id="thinking-enabled-toggle"
                data-testid="thinking-enabled-toggle"
                checked={editEnabled}
                onChange={setEditEnabled}
                label="Enable Thinking Budget"
                disabled={isSaving}
              />
            </div>
          </div>
        )}

        {/* Default Level (read-only view) */}
        {!isEditing && (
          <div className="mb-4">
            <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-1">
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
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-2">
            Complexity Mapping
          </p>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(data.complexityMapping).map(
              ([complexity, level]) => (
                <div
                  key={complexity}
                  className="flex items-center justify-between p-2 bg-neutral-50 dark:bg-neutral-800 rounded"
                >
                  <div className="flex items-center gap-2">
                    {getComplexityIcon(complexity)}
                    <span className="text-sm text-neutral-700 dark:text-neutral-300 capitalize">
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
          <p className="text-sm text-neutral-500 dark:text-neutral-400 mb-2">
            Available Levels
          </p>
          <div className="space-y-2">
            {data.levels.map((levelInfo) => (
              <div
                key={levelInfo.level}
                className="p-2 border border-neutral-200 dark:border-neutral-700 rounded"
              >
                <div className="flex items-center justify-between mb-1">
                  <span
                    className={`px-2 py-0.5 text-xs font-medium rounded ${getLevelColorClass(levelInfo.level)}`}
                  >
                    {levelInfo.level}
                  </span>
                  <span className="text-xs text-neutral-500 dark:text-neutral-400">
                    {levelInfo.otherModelsTokens.toLocaleString()} tokens
                  </span>
                </div>
                <p className="text-xs text-neutral-600 dark:text-neutral-400">
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
