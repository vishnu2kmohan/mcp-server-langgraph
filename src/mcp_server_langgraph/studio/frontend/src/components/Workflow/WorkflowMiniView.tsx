/**
 * WorkflowMiniView Component
 *
 * A compact, real-time workflow visualization for embedding in the chat panel.
 * Shows node execution status as the conversation progresses.
 *
 * Features:
 * - Compact horizontal/vertical layout options
 * - Real-time node status updates
 * - Animated transitions
 * - Click to expand to full canvas
 */

import { useMemo } from "react";
import {
  Play,
  CheckCircle,
  XCircle,
  Circle,
  Loader2,
  Bot,
  Wrench,
  GitBranch,
  UserCheck,
  Flag,
  ChevronRight,
} from "lucide-react";

export type NodeStatus = "idle" | "pending" | "running" | "success" | "error";

export interface WorkflowNode {
  id: string;
  name: string;
  type: "start" | "llm" | "tool" | "conditional" | "approval" | "end";
  status: NodeStatus;
  duration?: number; // ms
}

export interface WorkflowMiniViewProps {
  nodes: WorkflowNode[];
  layout?: "horizontal" | "vertical";
  onExpand?: () => void;
  className?: string;
}

const nodeTypeIcons: Record<WorkflowNode["type"], React.ReactNode> = {
  start: <Play size={14} />,
  llm: <Bot size={14} />,
  tool: <Wrench size={14} />,
  conditional: <GitBranch size={14} />,
  approval: <UserCheck size={14} />,
  end: <Flag size={14} />,
};

const statusStyles: Record<
  NodeStatus,
  { bg: string; border: string; text: string; icon: React.ReactNode }
> = {
  idle: {
    bg: "bg-gray-100 dark:bg-gray-800",
    border: "border-gray-300 dark:border-gray-600",
    text: "text-gray-500 dark:text-gray-400",
    icon: <Circle size={12} className="text-gray-400 dark:text-gray-400" />,
  },
  pending: {
    bg: "bg-gray-100 dark:bg-gray-800",
    border: "border-gray-400 dark:border-gray-500 dark:border-gray-500",
    text: "text-gray-600 dark:text-gray-300",
    icon: <Circle size={12} className="text-gray-400 dark:text-gray-400" />,
  },
  running: {
    bg: "bg-primary-50 dark:bg-primary-900/30",
    border: "border-primary-500",
    text: "text-primary-700 dark:text-primary-300",
    icon: <Loader2 size={12} className="text-primary-500 animate-spin" />,
  },
  success: {
    bg: "bg-success-50 dark:bg-success-900/30",
    border: "border-success-500",
    text: "text-success-700 dark:text-success-300",
    icon: <CheckCircle size={12} className="text-success-500" />,
  },
  error: {
    bg: "bg-error-50 dark:bg-error-900/30",
    border: "border-error-500",
    text: "text-error-700 dark:text-error-300",
    icon: <XCircle size={12} className="text-error-500" />,
  },
};

function WorkflowNodeBadge({ node }: { node: WorkflowNode }) {
  const style = statusStyles[node.status];
  const icon = nodeTypeIcons[node.type];

  return (
    <div
      className={`flex items-center gap-1.5 px-2 py-1 rounded-lg border-2 transition-all duration-300 ${style.bg} ${style.border}`}
      title={`${node.name}: ${node.status}${node.duration ? ` (${node.duration}ms)` : ""}`}
    >
      <span className={style.text}>{icon}</span>
      <span
        className={`text-xs font-medium ${style.text} truncate max-w-[80px]`}
      >
        {node.name}
      </span>
      {style.icon}
    </div>
  );
}

export function WorkflowMiniView({
  nodes,
  layout = "horizontal",
  onExpand,
  className = "",
}: WorkflowMiniViewProps) {
  const isHorizontal = layout === "horizontal";

  // Calculate progress
  const progress = useMemo(() => {
    const completed = nodes.filter(
      (n) => n.status === "success" || n.status === "error",
    ).length;
    return nodes.length > 0 ? Math.round((completed / nodes.length) * 100) : 0;
  }, [nodes]);

  const activeNode = nodes.find((n) => n.status === "running");

  if (nodes.length === 0) {
    return null;
  }

  return (
    <div
      className={`bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-lg p-3 ${className}`}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-gray-500 dark:text-gray-400">
            Workflow
          </span>
          {activeNode && (
            <span className="text-xs text-primary-600 dark:text-primary-400 flex items-center gap-1">
              <Loader2 size={10} className="animate-spin" />
              {activeNode.name}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 dark:text-gray-400">
            {progress}%
          </span>
          {onExpand && (
            <button
              onClick={onExpand}
              className="p-1 hover:bg-gray-100 dark:bg-gray-800 dark:hover:bg-gray-800 rounded transition-colors"
              title="Expand workflow view"
            >
              <ChevronRight
                size={14}
                className="text-gray-400 dark:text-gray-400"
              />
            </button>
          )}
        </div>
      </div>

      {/* Progress bar */}
      <div className="h-1 bg-gray-200 dark:bg-gray-700 rounded-full mb-3 overflow-hidden">
        <div
          className="h-full bg-primary-500 transition-all duration-500 ease-out"
          style={{ width: `${progress}%` }}
        />
      </div>

      {/* Nodes */}
      <div
        className={`flex gap-2 ${isHorizontal ? "flex-row flex-wrap" : "flex-col"}`}
      >
        {nodes.map((node, index) => (
          <div key={node.id} className="flex items-center gap-1">
            <WorkflowNodeBadge node={node} />
            {isHorizontal && index < nodes.length - 1 && (
              <ChevronRight
                size={12}
                className="text-gray-400 dark:text-gray-400 flex-shrink-0"
              />
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Hook to generate workflow nodes from session messages
 * This extracts tool calls and LLM interactions from the chat
 */
// eslint-disable-next-line react-refresh/only-export-components
export function useWorkflowFromMessages(
  messages: Array<{
    id: string;
    role: string;
    content: string;
    toolCalls?: Array<{ name: string; status?: string }>;
  }>,
): WorkflowNode[] {
  return useMemo(() => {
    const nodes: WorkflowNode[] = [
      { id: "start", name: "Start", type: "start", status: "success" },
    ];

    let stepIndex = 1;
    for (const msg of messages) {
      if (msg.role === "user") {
        // User messages don't add nodes
        continue;
      }

      if (msg.role === "assistant") {
        // Add LLM node for assistant response
        nodes.push({
          id: `llm-${stepIndex}`,
          name: `LLM ${stepIndex}`,
          type: "llm",
          status: "success",
        });
        stepIndex++;

        // Check for tool calls
        if (msg.toolCalls) {
          for (const tool of msg.toolCalls) {
            nodes.push({
              id: `tool-${tool.name}-${stepIndex}`,
              name: tool.name,
              type: "tool",
              status: (tool.status as NodeStatus) || "success",
            });
            stepIndex++;
          }
        }
      }
    }

    // Add end node if we have messages
    if (messages.length > 0) {
      nodes.push({ id: "end", name: "End", type: "end", status: "idle" });
    }

    return nodes;
  }, [messages]);
}
