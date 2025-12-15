/**
 * EndNode Component
 *
 * Termination node for workflow.
 * - Visual indicator: CircleStop icon
 * - Only has target handle (no source)
 * - Status visualization: idle/running/success/error
 */

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { CircleStop, Loader2, CheckCircle, XCircle } from "lucide-react";
import type { WorkflowNodeData } from "../../../types/workflow";

export const EndNode = memo(
  ({ data, selected }: NodeProps<WorkflowNodeData>) => {
    const { label, status = "idle" } = data;

    const getBorderClass = () => {
      if (selected && status === "idle") return "border-blue-500";
      if (status === "running") return "border-blue-500 animate-pulse";
      if (status === "success") return "border-green-500";
      if (status === "error") return "border-red-500";
      return "border-gray-300";
    };

    const StatusIcon = () => {
      if (status === "running")
        return <Loader2 className="w-4 h-4 animate-spin text-blue-500" />;
      if (status === "success")
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      if (status === "error")
        return <XCircle className="w-4 h-4 text-red-500" />;
      return null;
    };

    return (
      <>
        <Handle
          type="target"
          position={Position.Left}
          className="w-3 h-3 bg-blue-500 border-2 border-white dark:border-gray-800"
        />

        <div
          data-status={status}
          data-selected={selected}
          className={`
          rounded-lg border-2 p-3 min-w-[180px] bg-white dark:bg-gray-800
          shadow-sm hover:shadow-md transition-shadow
          ${getBorderClass()}
        `}
        >
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <CircleStop className="w-5 h-5 text-red-500" />
              <span className="font-medium text-gray-900 dark:text-gray-100">
                {label}
              </span>
            </div>
            <StatusIcon />
          </div>
        </div>
      </>
    );
  },
);

EndNode.displayName = "EndNode";
