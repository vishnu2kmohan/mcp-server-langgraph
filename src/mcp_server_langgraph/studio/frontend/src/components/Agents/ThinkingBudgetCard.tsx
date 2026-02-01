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
      return <Zap size={14} className="text-success-9" />;
    case "complicated":
      return <Gauge size={14} className="text-warning-9" />;
    case "complex":
      return <Brain size={14} className="text-grafana-9" />;
    case "chaotic":
      return <AlertTriangle size={14} className="text-error-9" />;
    default:
      return <Gauge size={14} className="text-neutral-9" />;
  }
}

/**
 * Get color class for thinking level
 */
function getLevelColorClass(level: string): string {
  switch (level) {
    case "low":
      return "bg-success-3 text-success-11 bg-success-4 dark:text-success-7";
    case "medium":
      return "bg-warning-3 text-warning-11 dark:bg-warning-a4 dark:text-warning-9";
    case "high":
      return "bg-grafana-2 text-grafana-11 dark:bg-grafana-12/30 dark:text-grafana-5";
    case "ultra":
      return "bg-error-3 text-error-11 bg-error-4 dark:text-error-7";
    default:
      return "bg-neutral-2 text-neutral-12";
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
          <Brain size={24} className="text-insight-9" />
          <CardTitle>Thinking Budget</CardTitle>
        </div>
        <div className="flex items-center gap-2">
          {!isEditing ? (
            <>
              <span
                className={`px-2 py-1 text-xs font-medium rounded-full ${
                  data.enabled
                    ? "bg-success-3 text-success-11 bg-success-4 dark:text-success-7"
                    : "bg-neutral-2 text-neutral-11"
                }`}
              >
                {data.enabled ? "Enabled" : "Disabled"}
              </span>
              <Button
                size="icon"
                variant="secondary"
                className="p-1.5 rounded hover:bg-neutral-2"
                data-testid="edit-thinking-budget-button"
                onClick={handleEdit}
                title="Edit thinking budget configuration"
              >
                <Pencil size={16} className="text-neutral-10" />
              </Button>
            </>
          ) : (
            <>
              <Button
                size="icon"
                variant="secondary"
                className="p-1.5 rounded hover:bg-neutral-2"
                data-testid="cancel-edit-button"
                onClick={handleCancel}
                disabled={isSaving}
                title="Cancel editing"
              >
                <X size={16} className="text-neutral-10" />
              </Button>
              <Button
                size="icon"
                variant="primary"
                className="p-1.5 rounded bg-primary-9 hover:bg-primary-10"
                data-testid="save-thinking-budget-button"
                onClick={handleSave}
                disabled={isSaving}
                title="Save changes"
              >
                <Save size={16} className="text-neutral-12" />
              </Button>
            </>
          )}
        </div>
      </div>
      <CardContent>
        {/* Edit Controls (shown when editing) */}
        {isEditing && (
          <div className="mb-4 p-3 bg-primary-1 dark:bg-primary-a3 rounded-lg border border-primary-4 dark:border-primary-11">
            <div className="space-y-4">
              {/* Level Selector */}
              <div>
                <label
                  htmlFor="thinking-level-select"
                  className="block text-sm font-medium text-neutral-11 mb-1"
                >
                  Default Level
                </label>
                <Select
                  className="px-3 py-2 text-neutral-12 disabled:opacity-50"
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
            <p className="text-sm text-neutral-10 mb-1">Default Level</p>
            <span
              className={`inline-flex px-2 py-1 text-sm font-medium rounded ${getLevelColorClass(data.defaultLevel)}`}
            >
              {data.defaultLevel}
            </span>
          </div>
        )}

        {/* Complexity Mapping */}
        <div className="mb-4">
          <p className="text-sm text-neutral-10 mb-2">Complexity Mapping</p>
          <div className="grid grid-cols-2 gap-2">
            {Object.entries(data.complexityMapping).map(
              ([complexity, level]) => (
                <div
                  key={complexity}
                  className="flex items-center justify-between p-2 bg-neutral-1 rounded"
                >
                  <div className="flex items-center gap-2">
                    {getComplexityIcon(complexity)}
                    <span className="text-sm text-neutral-11 capitalize">
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
          <p className="text-sm text-neutral-10 mb-2">Available Levels</p>
          <div className="space-y-2">
            {data.levels.map((levelInfo) => (
              <div
                key={levelInfo.level}
                className="p-2 border border-neutral-5 rounded"
              >
                <div className="flex items-center justify-between mb-1">
                  <span
                    className={`px-2 py-0.5 text-xs font-medium rounded ${getLevelColorClass(levelInfo.level)}`}
                  >
                    {levelInfo.level}
                  </span>
                  <span className="text-xs text-neutral-10">
                    {levelInfo.otherModelsTokens.toLocaleString()} tokens
                  </span>
                </div>
                <p className="text-xs text-neutral-11">
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
