/**
 * AgentTraceToggleButton Component
 *
 * A toggle button for showing/hiding the agent execution trace panel.
 * Consolidates duplicate toggle logic from ChatMessages.tsx.
 *
 * Extracted from ChatMessages.tsx for DRY principle.
 */

import { GitBranch } from "lucide-react";

export interface AgentTraceToggleButtonProps {
  /** Whether the trace panel is currently expanded */
  isExpanded: boolean;
  /** Callback when the toggle button is clicked */
  onToggle: () => void;
}

export function AgentTraceToggleButton({
  isExpanded,
  onToggle,
}: AgentTraceToggleButtonProps) {
  return (
    <button
      onClick={onToggle}
      className={`p-1.5 rounded transition-colors ${
        isExpanded
          ? "bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400"
          : "text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700"
      }`}
      aria-expanded={isExpanded}
      aria-label="Toggle agent execution trace"
      title={isExpanded ? "Hide execution trace" : "Show execution trace"}
    >
      <GitBranch size={14} />
    </button>
  );
}
