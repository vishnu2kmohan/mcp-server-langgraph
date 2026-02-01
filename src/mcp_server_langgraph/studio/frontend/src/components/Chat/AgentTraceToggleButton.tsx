/**
 * AgentTraceToggleButton Component
 *
 * A toggle button for showing/hiding the agent execution trace panel.
 * Consolidates duplicate toggle logic from ChatMessages.tsx.
 *
 * Extracted from ChatMessages.tsx for DRY principle.
 */

import { GitBranch } from "lucide-react";

import { Button } from "@/components/UI";

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
    <Button
      variant="primary"
      className="p-1.5 rounded"
      onClick={onToggle}
      aria-expanded={isExpanded}
      aria-label="Toggle agent execution trace"
      title={isExpanded ? "Hide execution trace" : "Show execution trace"}
    >
      <GitBranch size={14} />
    </Button>
  );
}
