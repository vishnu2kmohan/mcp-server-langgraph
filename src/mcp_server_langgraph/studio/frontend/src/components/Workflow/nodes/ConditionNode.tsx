/**
 * ConditionNode Component
 *
 * Conditional branching node (if/else).
 * - Visual indicator: GitBranch icon
 * - Has 1 target handle and 2 source handles (true/false)
 * - Status visualization: idle/running/success/error
 */

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { GitBranch, Loader2, CheckCircle, XCircle } from "lucide-react";
import type { WorkflowNodeData } from "../../../types/workflow";

export const ConditionNode = memo(
  ({ data, selected }: NodeProps<WorkflowNodeData>) => {
    const { label, status = "idle" } = data;

    const getBorderClass = () => {
      if (selected && status === "idle") return "border-primary-9";
      if (status === "running") return "border-primary-9 animate-pulse";
      if (status === "success") return "border-success-9";
      if (status === "error") return "border-error-9";
      return "border-neutral-5";
    };

    const StatusIcon = () => {
      if (status === "running")
        return <Loader2 className="w-4 h-4 animate-spin text-primary-9" />;
      if (status === "success")
        return <CheckCircle className="w-4 h-4 text-success-9" />;
      if (status === "error")
        return <XCircle className="w-4 h-4 text-error-9" />;
      return null;
    };

    return (
      <>
        <Handle
          type="target"
          position={Position.Left}
          className="w-3 h-3 bg-primary-9 border-2 border-neutral-1"
        />

        <div
          data-status={status}
          data-selected={selected}
          className={`
          rounded-lg border-2 p-3 min-w-[180px] bg-neutral-1
          shadow-sm hover:shadow-md transition-shadow
          ${getBorderClass()}
        `}
        >
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2">
              <GitBranch className="w-5 h-5 text-warning-9" />
              <span className="font-medium text-neutral-12">{label}</span>
            </div>
            <StatusIcon />
          </div>
          <div className="mt-2 flex justify-between text-xs text-neutral-10">
            <span>True</span>
            <span>False</span>
          </div>
        </div>

        {/* True branch */}
        <Handle
          type="source"
          position={Position.Right}
          id="true"
          style={{ top: "30%" }}
          className="w-3 h-3 bg-success-9 border-2 border-neutral-1"
        />

        {/* False branch */}
        <Handle
          type="source"
          position={Position.Right}
          id="false"
          style={{ top: "70%" }}
          className="w-3 h-3 bg-error-9 border-2 border-neutral-1"
        />
      </>
    );
  },
);

ConditionNode.displayName = "ConditionNode";
