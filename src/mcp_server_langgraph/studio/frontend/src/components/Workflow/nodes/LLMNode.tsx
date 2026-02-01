/**
 * LLMNode Component
 *
 * LLM completion node for AI responses.
 * - Visual indicator: Brain icon
 * - Has both target and source handles
 * - Status visualization: idle/running/success/error
 */

import { memo } from "react";
import { Handle, Position, type NodeProps } from "reactflow";
import { Brain, Loader2, CheckCircle, XCircle } from "lucide-react";
import type { WorkflowNodeData } from "../../../types/workflow";

export const LLMNode = memo(
  ({ data, selected }: NodeProps<WorkflowNodeData>) => {
    const { label, status = "idle", config } = data;
    const model = (config?.model as string) || "gemini-2.5-flash";

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
              <Brain className="w-5 h-5 text-insight-9" />
              <div className="flex flex-col">
                <span className="font-medium text-neutral-12">{label}</span>
                <span className="text-xs text-neutral-10">{model}</span>
              </div>
            </div>
            <StatusIcon />
          </div>
        </div>

        <Handle
          type="source"
          position={Position.Right}
          className="w-3 h-3 bg-primary-9 border-2 border-neutral-1"
        />
      </>
    );
  },
);

LLMNode.displayName = "LLMNode";
