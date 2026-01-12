/**
 * StartNode Component
 *
 * Entry point node for workflow execution.
 * - Visual indicator: Play icon
 * - Only has source handle (no target)
 * - Status visualization: idle/running/success/error
 */

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { Play, Loader2, CheckCircle, XCircle } from "lucide-react";
import type { WorkflowNodeData } from "../../../types/workflow";

export const StartNode = memo(
  ({ data, selected }: NodeProps<WorkflowNodeData>) => {
    const { label, status = "idle" } = data;

    // Border color based on status and selection
    const getBorderClass = () => {
      if (selected && status === "idle") return "border-primary-500";
      if (status === "running") return "border-primary-500 animate-pulse";
      if (status === "success") return "border-success-500";
      if (status === "error") return "border-error-500";
      return "border-neutral-300 dark:border-neutral-600";
    };

    // Status icon
    const StatusIcon = () => {
      if (status === "running")
        return <Loader2 className="w-4 h-4 animate-spin text-primary-500" />;
      if (status === "success")
        return <CheckCircle className="w-4 h-4 text-success-500" />;
      if (status === "error")
        return <XCircle className="w-4 h-4 text-error-500" />;
      return null;
    };

    return (
      <>
        <div
          data-status={status}
          data-selected={selected}
          className={`
          rounded-lg border-2 p-3 min-w-[180px] bg-white dark:bg-neutral-800
          shadow-sm hover:shadow-md transition-shadow
          ${getBorderClass()}
        `}
        >
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <Play className="w-5 h-5 text-success-500" />
              <span className="font-medium text-neutral-900 dark:text-neutral-100">
                {label}
              </span>
            </div>
            <StatusIcon />
          </div>
        </div>

        {/* Source handle (output) on right */}
        <Handle
          type="source"
          position={Position.Right}
          className="w-3 h-3 bg-primary-500 border-2 border-white dark:border-neutral-800"
        />
      </>
    );
  },
);

StartNode.displayName = "StartNode";
