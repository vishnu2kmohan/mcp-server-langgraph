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

import { Button, Input, Select } from "@/components/UI";

// =============================================================================
// Types
// =============================================================================

export type PlanStatus = "awaiting_approval" | "approved" | "rejected";

export interface ExecutionPlanView {
  /** Unique plan identifier */
  planId: string;
  /** Session this plan belongs to */
  sessionId: string;
  /** Current plan status */
  status: PlanStatus;
  /** Task complexity level */
  complexity: string;
  /** Risk level assessment */
  riskLevel: string;
  /** Type of task */
  taskType: string;
  /** Model for execution */
  executorModel: string;
  /** Model for critique */
  criticModel: string;
  /** Estimated cost in USD */
  estimatedCost: string;
  /** Original user message */
  message: string;
  /** Tools required for execution */
  toolsNeeded: string[];
  /** Thinking budget level */
  thinkingBudget: string;
  /** Number of critique rounds */
  critiqueRounds: number;
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
      return "bg-success-3 text-success-11 bg-success-4 dark:text-success-7";
    case "medium":
      return "bg-warning-3 text-warning-11 dark:bg-warning-a4 dark:text-warning-9";
    case "high":
      return "bg-error-3 text-error-11 bg-error-4 dark:text-error-7";
    case "critical":
      return "bg-error-4 text-error-12 dark:bg-error-a6 dark:text-error-9";
    default:
      return "bg-neutral-2 text-neutral-12";
  }
}

/**
 * Get color classes for status badge
 */
function getStatusColor(status: PlanStatus): string {
  switch (status) {
    case "approved":
      return "bg-success-3 text-success-11 bg-success-4 dark:text-success-7";
    case "rejected":
      return "bg-error-3 text-error-11 bg-error-4 dark:text-error-7";
    case "awaiting_approval":
    default:
      return "bg-warning-3 text-warning-11 dark:bg-warning-a4 dark:text-warning-9";
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
  const [thinkingBudget, setThinkingBudget] = useState(plan.thinkingBudget);
  const [critiqueRounds, setCritiqueRounds] = useState(plan.critiqueRounds);

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
    onSave({ thinkingBudget: e.target.value });
  };

  const handleCritiqueRoundsChange = (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const value = parseInt(e.target.value, 10);
    if (!isNaN(value) && value >= 0 && value <= 3) {
      setCritiqueRounds(value);
      onSave({ critiqueRounds: value });
    }
  };

  return (
    <div className="bg-neutral-1 rounded-lg shadow-md border border-neutral-5">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-neutral-5">
        <h2 className="text-lg font-semibold text-neutral-12 flex items-center gap-2">
          <Settings className="w-5 h-5 text-primary-9" />
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
            <span className="text-neutral-10">
              Plan ID:
            </span>
            <span className="ml-2 font-mono text-neutral-12">
              {plan.planId}
            </span>
          </div>
          <div>
            <span className="text-neutral-10">
              Session:
            </span>
            <span className="ml-2 font-mono text-neutral-12">
              {plan.sessionId}
            </span>
          </div>
        </div>

        {/* Complexity and Risk */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-warning-9" />
            <span className="text-sm text-neutral-11">
              Complexity:
            </span>
            <span className="px-2 py-0.5 rounded text-xs font-medium bg-primary-3 text-primary-11 bg-primary-4 dark:text-primary-7">
              {plan.complexity}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-warning-9" />
            <span className="text-sm text-neutral-11">
              Risk:
            </span>
            <span
              className={`px-2 py-0.5 rounded text-xs font-medium ${getRiskLevelColor(plan.riskLevel)}`}
            >
              {plan.riskLevel}
            </span>
          </div>
        </div>

        {/* Cost and Model */}
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-success-9" />
            <span className="text-sm text-neutral-11">
              Estimated Cost:
            </span>
            <span className="font-mono text-sm text-neutral-12">
              ${plan.estimatedCost}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Brain className="w-4 h-4 text-insight-9" />
            <span className="text-sm text-neutral-11">
              Executor:
            </span>
            <span className="font-mono text-sm text-neutral-12">
              {plan.executorModel}
            </span>
          </div>
        </div>

        {/* Tools Needed */}
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-sm text-neutral-11">
            <Wrench className="w-4 h-4" />
            <span>Tools Needed:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {plan.toolsNeeded.map((tool) => (
              <span
                key={tool}
                className="px-2 py-1 bg-neutral-2 text-neutral-11 rounded text-xs font-mono"
              >
                {tool}
              </span>
            ))}
          </div>
        </div>

        {/* Configuration Fields */}
        <div className="border-t border-neutral-5 pt-4 mt-4 space-y-4">
          <h3 className="text-sm font-medium text-neutral-12 flex items-center gap-2">
            <Settings className="w-4 h-4" />
            Configuration
          </h3>

          {/* Orchestrator Select */}
          <div>
            <label
              htmlFor="orchestrator"
              className="block text-sm font-medium text-neutral-11 mb-1"
            >
              Orchestrator
            </label>
            <Select
              className="px-3 py-2 text-sm text-neutral-12 focus:ring-primary-7 disabled:opacity-50 disabled:cursor-not-allowed"
              id="orchestrator"
              value={orchestrator}
              onChange={handleOrchestratorChange}
              disabled={readOnly}
            >
              <option value="standard">Standard</option>
              <option value="swarm">Swarm</option>
              <option value="studio">Studio</option>
              <option value="ux">UX</option>
              <option value="alert">Alert</option>
            </Select>
          </div>

          {/* Thinking Budget Select */}
          <div>
            <label
              htmlFor="thinking_budget"
              className="block text-sm font-medium text-neutral-11 mb-1"
            >
              Thinking Budget
            </label>
            <Select
              className="px-3 py-2 text-sm text-neutral-12 focus:ring-primary-7 disabled:opacity-50 disabled:cursor-not-allowed"
              id="thinking_budget"
              value={thinkingBudget}
              onChange={handleThinkingBudgetChange}
              disabled={readOnly}
            >
              <option value="none">None</option>
              <option value="light">Light</option>
              <option value="medium">Medium</option>
              <option value="deep">Deep</option>
            </Select>
          </div>

          {/* Critique Rounds Input */}
          <div>
            <label
              htmlFor="critique_rounds"
              className="block text-sm font-medium text-neutral-11 mb-1"
            >
              Critique Rounds
            </label>
            <Input
              className="px-3 py-2 text-sm text-neutral-12 focus:ring-primary-7 disabled:opacity-50 disabled:cursor-not-allowed"
              type="number"
              id="critique_rounds"
              value={critiqueRounds}
              onChange={handleCritiqueRoundsChange}
              disabled={readOnly}
              min={0}
              max={3}
            />
          </div>
        </div>
      </div>
      {/* Actions Footer */}
      <div className="flex items-center justify-end gap-3 p-4 border-t border-neutral-5 bg-neutral-1">
        <Button
          variant="danger"
          className="flex px-4 py-2 text-sm text-error-11 dark:text-error-7 bg-error-3 bg-error-4 rounded-lg hover:bg-error-4 dark:hover:bg-error-a6"
          type="button"
          onClick={onReject}
          disabled={readOnly}
        >
          <XCircle className="w-4 h-4" />
          Reject
        </Button>
        <Button
          variant="success"
          className="flex px-4 py-2 text-sm text-neutral-12 bg-success-10 rounded-lg hover:bg-success-11"
          type="button"
          onClick={onApprove}
          disabled={readOnly}
        >
          <CheckCircle className="w-4 h-4" />
          Approve
        </Button>
      </div>
    </div>
  );
}
