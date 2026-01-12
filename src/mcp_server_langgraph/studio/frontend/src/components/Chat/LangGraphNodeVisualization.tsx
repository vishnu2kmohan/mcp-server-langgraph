/**
 * LangGraphNodeVisualization Component
 *
 * Visual representation of LangGraph workflow execution.
 * Displays nodes with status indicators and edges connecting them.
 *
 * Extracted from ChatMessages.tsx for reusability.
 *
 * @example
 * ```tsx
 * <LangGraphNodeVisualization
 *   nodes={[
 *     { id: "1", name: "Start", type: "start", status: "completed" },
 *     { id: "2", name: "Agent", type: "agent", status: "running" },
 *   ]}
 *   edges={[{ from: "1", to: "2" }]}
 *   currentNode="2"
 * />
 * ```
 */

import {
  Play,
  Square,
  Wrench,
  GitFork,
  Bot,
  Circle,
  CheckCircle,
  XCircle,
  Loader2,
  ArrowRight,
} from "lucide-react";
import type {
  LangGraphNode,
  LangGraphEdge,
  LangGraphNodeType,
  LangGraphNodeStatus,
} from "../../types/chat";

/**
 * Props for the LangGraphNodeVisualization component
 */
export interface LangGraphNodeVisualizationProps {
  /** Array of nodes to visualize */
  nodes: LangGraphNode[];
  /** Array of edges connecting nodes */
  edges?: LangGraphEdge[];
  /** ID of the currently active node */
  currentNode?: string;
}

/**
 * Get icon for node type
 */
// eslint-disable-next-line react-refresh/only-export-components
export function getNodeTypeIcon(type: LangGraphNodeType, size: number = 14) {
  const iconProps = { size, className: "flex-shrink-0" };
  switch (type) {
    case "start":
      return <Play {...iconProps} data-testid="node-type-start" />;
    case "end":
      return <Square {...iconProps} data-testid="node-type-end" />;
    case "tool":
      return <Wrench {...iconProps} data-testid="node-type-tool" />;
    case "conditional":
      return <GitFork {...iconProps} data-testid="node-type-conditional" />;
    case "agent":
      return <Bot {...iconProps} data-testid="node-type-agent" />;
    default:
      return <Circle {...iconProps} data-testid="node-type-default" />;
  }
}

/**
 * Get status indicator for node
 */
// eslint-disable-next-line react-refresh/only-export-components
export function getNodeStatusIndicator(status: LangGraphNodeStatus) {
  switch (status) {
    case "completed":
      return (
        <CheckCircle
          size={12}
          className="text-success-500"
          data-testid="node-status-completed"
        />
      );
    case "running":
      return (
        <Loader2
          size={12}
          className="text-primary-500 animate-spin"
          data-testid="node-status-running"
        />
      );
    case "error":
      return (
        <XCircle
          size={12}
          className="text-error-500"
          data-testid="node-status-error"
        />
      );
    case "pending":
      return (
        <Circle
          size={12}
          className="text-neutral-400 dark:text-neutral-400"
          data-testid="node-status-pending"
        />
      );
    case "skipped":
      return (
        <Circle
          size={12}
          className="text-neutral-300 opacity-50"
          data-testid="node-status-skipped"
        />
      );
  }
}

/**
 * Get node background color based on type and status
 */
// eslint-disable-next-line react-refresh/only-export-components
export function getNodeColor(
  type: LangGraphNodeType,
  status: LangGraphNodeStatus,
): string {
  if (status === "error")
    return "bg-error-50 dark:bg-error-900/20 border-error-300 dark:border-error-700";
  if (status === "running")
    return "bg-primary-50 dark:bg-primary-900/20 border-primary-300 dark:border-primary-700";
  if (status === "completed")
    return "bg-success-50 dark:bg-success-900/20 border-success-300 dark:border-success-700";

  switch (type) {
    case "start":
      return "bg-emerald-50 dark:bg-emerald-900/20 border-emerald-300 dark:border-emerald-700";
    case "end":
      return "bg-slate-50 dark:bg-slate-900/20 border-slate-300 dark:border-slate-700";
    case "conditional":
      return "bg-warning-50 dark:bg-warning-900/20 border-warning-300 dark:border-warning-700";
    case "tool":
      return "bg-insight-50 dark:bg-insight-900/20 border-insight-300 dark:border-insight-700";
    case "agent":
      return "bg-indigo-50 dark:bg-indigo-900/20 border-indigo-300 dark:border-indigo-700";
    default:
      return "bg-neutral-50 dark:bg-neutral-900/20 border-neutral-300 dark:border-neutral-600 dark:border-neutral-700";
  }
}

/**
 * LangGraph node visualization component
 * Displays a visual representation of the workflow execution
 */
export function LangGraphNodeVisualization({
  nodes,
  edges = [],
  currentNode,
}: LangGraphNodeVisualizationProps) {
  return (
    <div
      data-testid="langgraph-node-visualization"
      className="flex flex-col gap-2"
    >
      {/* Node list with edges */}
      {nodes.map((node, index) => {
        const isActive = node.id === currentNode;
        const outgoingEdges = edges.filter((e) => e.from === node.id);

        return (
          <div key={node.id} className="flex flex-col">
            {/* Node */}
            <div
              data-testid={`node-${node.id}`}
              className={`
                flex items-center gap-2 px-3 py-2 rounded-lg border
                ${getNodeColor(node.type, node.status)}
                ${isActive ? "ring-2 ring-primary-500 ring-offset-1 dark:ring-offset-neutral-900" : ""}
                transition-all duration-200
              `}
            >
              {/* Type icon */}
              <span className="text-neutral-600 dark:text-neutral-400">
                {getNodeTypeIcon(node.type)}
              </span>

              {/* Name */}
              <span className="flex-1 text-sm font-medium text-neutral-800 dark:text-neutral-200">
                {node.name}
              </span>

              {/* Duration */}
              {node.duration !== undefined && (
                <span className="text-xs text-neutral-500 dark:text-neutral-400">
                  {node.duration}ms
                </span>
              )}

              {/* Status indicator */}
              {getNodeStatusIndicator(node.status)}
            </div>

            {/* Edges from this node */}
            {outgoingEdges.length > 0 && index < nodes.length - 1 && (
              <div className="flex flex-col gap-1 ml-4 my-1">
                {outgoingEdges.map((edge) => (
                  <div
                    key={`${edge.from}-${edge.to}`}
                    data-testid={`edge-${edge.from}-to-${edge.to}`}
                    className="flex items-center gap-1 text-xs text-neutral-400 dark:text-neutral-400"
                  >
                    <ArrowRight size={10} />
                    {edge.condition && (
                      <span className="px-1.5 py-0.5 bg-neutral-100 dark:bg-neutral-700 rounded text-neutral-600 dark:text-neutral-300">
                        {edge.condition}
                      </span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default LangGraphNodeVisualization;
