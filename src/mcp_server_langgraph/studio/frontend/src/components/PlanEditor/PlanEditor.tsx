/**
 * PlanEditor Component
 *
 * Displays and allows configuration of execution plans for agent orchestration.
 * Users can view plan details, adjust configuration, and approve/reject plans.
 *
 * Features:
 * - Plan summary with ID, complexity, risk, cost, model info
 * - Configuration fields for orchestrator, thinking budget, critique rounds
 * - Approve/reject actions with readOnly mode support
 * - Status display (awaiting_approval, approved, rejected)
 * - Tools needed display
 */

import { useState } from "react";
import {
  CheckCircle,
  XCircle,
  AlertCircle,
  Settings,
  Brain,
  Wrench,
  DollarSign,
  AlertTriangle,
} from "lucide-react";

// =============================================================================
// Types
// =============================================================================

export type PlanStatus = "awaiting_approval" | "approved" | "rejected";

export interface ExecutionPlanView {
  /** Unique plan identifier */
  plan_id: string;
  /** Session this plan belongs to */
  session_id: string;
  /** Current plan status */
  status: PlanStatus;
  /** Task complexity level */
  complexity: string;
  /** Risk level assessment */
  risk_level: string;
  /** Type of task */
  task_type: string;
  /** Model for execution */
  executor_model: string;
  /** Model for critique */
  critic_model: string;
  /** Estimated cost in USD */
  estimated_cost: string;
  /** Original user message */
  message: string;
  /** Tools required for execution */
  tools_needed: string[];
  /** Thinking budget level */
  thinking_budget: string;
  /** Number of critique rounds */
  critique_rounds: number;
  /** Orchestrator pattern */
  orchestrator: string;
}

export interface PlanEditorProps {
  /** The execution plan to display/edit */
  plan: ExecutionPlanView;
  /** Callback when plan is approved */
  onApprove: () => void;
  /** Callback when plan is rejected */
  onReject: () => void;
  /** Callback when plan configuration is saved */
  onSave: (plan: Partial<ExecutionPlanView>) => void;
  /** Whether the editor is in read-only mode */
  readOnly?: boolean;
}

// =============================================================================
// Utility Functions
// =============================================================================

/**
 * Get color classes for risk level badge
 */
function getRiskLevelColor(level: string): string {
  switch (level.toLowerCase()) {
    case "low":
      return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400";
    case "medium":
      return "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400";
    case "high":
      return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400";
    case "critical":
      return "bg-red-200 text-red-900 dark:bg-red-900/50 dark:text-red-300";
    default:
      return "bg-gray-100 text-gray-800 dark:bg-gray-900/30 dark:text-gray-400";
  }
}

/**
 * Get color classes for status badge
 */
function getStatusColor(status: PlanStatus): string {
  switch (status) {
    case "approved":
      return "bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400";
    case "rejected":
      return "bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400";
    case "awaiting_approval":
    default:
      return "bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400";
  }
}

/**
 * Format status for display
 */
function formatStatus(status: PlanStatus): string {
  switch (status) {
    case "awaiting_approval":
      return "Awaiting Approval";
    case "approved":
      return "Approved";
    case "rejected":
      return "Rejected";
    default:
      return status;
  }
}

// =============================================================================
// Main Component
// =============================================================================

export function PlanEditor({
  plan,
  onApprove,
  onReject,
  onSave,
  readOnly = false,
}: PlanEditorProps) {
  // Local state for editable fields
  const [orchestrator, setOrchestrator] = useState(plan.orchestrator);
  const [thinkingBudget, setThinkingBudget] = useState(plan.thinking_budget);
  const [critiqueRounds, setCritiqueRounds] = useState(plan.critique_rounds);

  // Handle configuration changes
  const handleOrchestratorChange = (
    e: React.ChangeEvent<HTMLSelectElement>,
  ) => {
    setOrchestrator(e.target.value);
    onSave({ orchestrator: e.target.value });
  };

  const handleThinkingBudgetChange = (
    e: React.ChangeEvent<HTMLSelectElement>,
  ) => {
    setThinkingBudget(e.target.value);
    onSave({ thinking_budget: e.target.value });
  };

  const handleCritiqueRoundsChange = (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const value = parseInt(e.target.value, 10);
    if (!isNaN(value) && value >= 0 && value <= 3) {
      setCritiqueRounds(value);
      onSave({ critique_rounds: value });
    }
  };

  return (
    <div className="bg-white dark:bg-gray-900 rounded-lg shadow-md border border-gray-200 dark:border-gray-700">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
          <Settings className="w-5 h-5 text-blue-500" />
          Execution Plan
        </h2>
        <span
          className={`px-2 py-1 rounded text-xs font-medium ${getStatusColor(plan.status)}`}
        >
          {formatStatus(plan.status)}
        </span>
      </div>

      {/* Plan Summary */}
      <div className="p-4 space-y-4">
        {/* Plan ID and Session */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span className="text-gray-500 dark:text-gray-400">Plan ID:</span>
            <span className="ml-2 font-mono text-gray-900 dark:text-white">
              {plan.plan_id}
            </span>
          </div>
          <div>
            <span className="text-gray-500 dark:text-gray-400">Session:</span>
            <span className="ml-2 font-mono text-gray-900 dark:text-white">
              {plan.session_id}
            </span>
          </div>
        </div>

        {/* Complexity and Risk */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-amber-500" />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Complexity:
            </span>
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
              {plan.complexity}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-amber-500" />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Risk:
            </span>
            <span
              className={`px-2 py-0.5 rounded text-xs font-medium ${getRiskLevelColor(plan.risk_level)}`}
            >
              {plan.risk_level}
            </span>
          </div>
        </div>

        {/* Cost and Model */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-green-500" />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Estimated Cost:
            </span>
            <span className="font-mono text-sm text-gray-900 dark:text-white">
              ${plan.estimated_cost}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-purple-500" />
            <span className="text-sm text-gray-600 dark:text-gray-400">
              Executor:
            </span>
            <span className="font-mono text-sm text-gray-900 dark:text-white">
              {plan.executor_model}
            </span>
          </div>
        </div>

        {/* Tools Needed */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
            <Wrench className="w-4 h-4" />
            <span>Tools Needed:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {plan.tools_needed.map((tool) => (
              <span
                key={tool}
                className="px-2 py-1 bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded text-xs font-mono"
              >
                {tool}
              </span>
            ))}
          </div>
        </div>

        {/* Configuration Fields */}
        <div className="border-t border-gray-200 dark:border-gray-700 pt-4 mt-4 space-y-4">
          <h3 className="text-sm font-medium text-gray-900 dark:text-white flex items-center gap-2">
            <Settings className="w-4 h-4" />
            Configuration
          </h3>

          {/* Orchestrator Select */}
          <div>
            <label
              htmlFor="orchestrator"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Orchestrator
            </label>
            <select
              id="orchestrator"
              value={orchestrator}
              onChange={handleOrchestratorChange}
              disabled={readOnly}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="standard">Standard</option>
              <option value="swarm">Swarm</option>
              <option value="studio">Studio</option>
              <option value="ux">UX</option>
              <option value="alert">Alert</option>
            </select>
          </div>

          {/* Thinking Budget Select */}
          <div>
            <label
              htmlFor="thinking_budget"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Thinking Budget
            </label>
            <select
              id="thinking_budget"
              value={thinkingBudget}
              onChange={handleThinkingBudgetChange}
              disabled={readOnly}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <option value="none">None</option>
              <option value="light">Light</option>
              <option value="medium">Medium</option>
              <option value="deep">Deep</option>
            </select>
          </div>

          {/* Critique Rounds Input */}
          <div>
            <label
              htmlFor="critique_rounds"
              className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
            >
              Critique Rounds
            </label>
            <input
              type="number"
              id="critique_rounds"
              value={critiqueRounds}
              onChange={handleCritiqueRoundsChange}
              disabled={readOnly}
              min={0}
              max={3}
              className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm text-gray-900 dark:text-white bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:opacity-50 disabled:cursor-not-allowed"
            />
          </div>
        </div>
      </div>

      {/* Actions Footer */}
      <div className="flex items-center justify-end gap-3 p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
        <button
          type="button"
          onClick={onReject}
          disabled={readOnly}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-700 dark:text-red-400 bg-red-100 dark:bg-red-900/30 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <XCircle className="w-4 h-4" />
          Reject
        </button>
        <button
          type="button"
          onClick={onApprove}
          disabled={readOnly}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <CheckCircle className="w-4 h-4" />
          Approve
        </button>
      </div>
    </div>
  );
}
