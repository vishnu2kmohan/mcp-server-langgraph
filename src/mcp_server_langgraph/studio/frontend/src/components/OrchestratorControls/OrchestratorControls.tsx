/**
 * OrchestratorControls Component
 *
 * Configuration controls for agent orchestration settings.
 * Allows users to configure:
 * - Orchestrator mode (standard/swarm/studio/ux/alert)
 * - Thinking budget (none/light/medium/deep)
 * - Critique rounds (0-3)
 * - Auto-approve toggle
 */

import { Settings, Brain, MessageSquare, CheckCircle } from "lucide-react";

// =============================================================================
// Types
// =============================================================================

export type OrchestratorMode = "standard" | "swarm" | "studio" | "ux" | "alert";
export type ThinkingBudget = "none" | "light" | "medium" | "deep";

export interface OrchestratorConfig {
  /** Orchestrator pattern to use */
  orchestrator: OrchestratorMode;
  /** Extended thinking level */
  thinkingBudget: ThinkingBudget;
  /** Number of critique iterations (0-3) */
  critiqueRounds: number;
  /** Whether to auto-approve low-risk plans */
  autoApprove: boolean;
}

export interface OrchestratorControlsProps {
  /** Current configuration */
  config: OrchestratorConfig;
  /** Callback when configuration changes */
  onChange: (config: OrchestratorConfig) => void;
  /** Whether controls are disabled */
  disabled?: boolean;
}

// =============================================================================
// Constants
// =============================================================================

const ORCHESTRATOR_OPTIONS: {
  value: OrchestratorMode;
  label: string;
  description: string;
}[] = [
  {
    value: "standard",
    label: "Standard",
    description: "Sequential task execution",
  },
  {
    value: "swarm",
    label: "Swarm",
    description: "Parallel multi-agent orchestration",
  },
  { value: "studio", label: "Studio", description: "Interactive agent studio" },
  { value: "ux", label: "UX", description: "User experience focused" },
  { value: "alert", label: "Alert", description: "Alert-triggered automation" },
];

const THINKING_BUDGET_OPTIONS: {
  value: ThinkingBudget;
  label: string;
  tokens: string;
}[] = [
  { value: "none", label: "None", tokens: "0" },
  { value: "light", label: "Light", tokens: "1K" },
  { value: "medium", label: "Medium", tokens: "8K" },
  { value: "deep", label: "Deep", tokens: "32K" },
];

// =============================================================================
// Main Component
// =============================================================================

export function OrchestratorControls({
  config,
  onChange,
  disabled = false,
}: OrchestratorControlsProps) {
  // Handler for orchestrator mode change
  const handleOrchestratorChange = (
    e: React.ChangeEvent<HTMLSelectElement>,
  ) => {
    onChange({
      ...config,
      orchestrator: e.target.value as OrchestratorMode,
    });
  };

  // Handler for thinking budget change
  const handleThinkingBudgetChange = (
    e: React.ChangeEvent<HTMLSelectElement>,
  ) => {
    onChange({
      ...config,
      thinkingBudget: e.target.value as ThinkingBudget,
    });
  };

  // Handler for critique rounds change
  const handleCritiqueRoundsChange = (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const value = parseInt(e.target.value, 10);
    if (!isNaN(value) && value >= 0 && value <= 3) {
      onChange({
        ...config,
        critiqueRounds: value,
      });
    }
  };

  // Handler for auto-approve toggle
  const handleAutoApproveChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onChange({
      ...config,
      autoApprove: e.target.checked,
    });
  };

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4">
      {/* Header */}
      <h3 className="text-sm font-medium text-gray-900 dark:text-white flex items-center gap-2 mb-4">
        <Settings className="w-4 h-4 text-blue-500" />
        Orchestrator Configuration
      </h3>

      <div className="space-y-4">
        {/* Orchestrator Mode */}
        <div>
          <label
            htmlFor="orchestrator-mode"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
          >
            Orchestrator Mode
          </label>
          <select
            id="orchestrator-mode"
            data-testid="orchestrator-selector"
            value={config.orchestrator}
            onChange={handleOrchestratorChange}
            disabled={disabled}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {ORCHESTRATOR_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {/* Thinking Budget */}
        <div>
          <label
            htmlFor="thinking-budget"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 flex items-center gap-1"
          >
            <Brain className="w-3 h-3" />
            Thinking Budget
          </label>
          <select
            id="thinking-budget"
            value={config.thinkingBudget}
            onChange={handleThinkingBudgetChange}
            disabled={disabled}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {THINKING_BUDGET_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label} ({option.tokens} tokens)
              </option>
            ))}
          </select>
        </div>

        {/* Critique Rounds */}
        <div>
          <label
            htmlFor="critique-rounds"
            className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1 flex items-center gap-1"
          >
            <MessageSquare className="w-3 h-3" />
            Critique Rounds
          </label>
          <input
            type="number"
            id="critique-rounds"
            value={config.critiqueRounds}
            onChange={handleCritiqueRoundsChange}
            disabled={disabled}
            min={0}
            max={3}
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
          />
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Number of critique iterations (0-3)
          </p>
        </div>

        {/* Auto-Approve Toggle */}
        <div className="flex items-center justify-between">
          <label
            htmlFor="auto-approve"
            className="text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-1"
          >
            <CheckCircle className="w-3 h-3" />
            Auto-Approve Low Risk
          </label>
          <input
            type="checkbox"
            id="auto-approve"
            checked={config.autoApprove}
            onChange={handleAutoApproveChange}
            disabled={disabled}
            className="w-4 h-4 text-blue-600 bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 rounded focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          />
        </div>
      </div>
    </div>
  );
}
