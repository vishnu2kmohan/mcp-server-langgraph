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
          className="text-success-9"
          data-testid="node-status-completed"
        />
      );
    case "running":
      return (
        <Loader2
          size={12}
          className="text-primary-9 animate-spin"
          data-testid="node-status-running"
        />
      );
    case "error":
      return (
        <XCircle
          size={12}
          className="text-error-9"
          data-testid="node-status-error"
        />
      );
    case "pending":
      return (
        <Circle
          size={12}
          className="text-neutral-9"
          data-testid="node-status-pending"
        />
      );
    case "skipped":
      return (
        <Circle
          size={12}
          className="text-neutral-9 opacity-50"
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
  if (status === "error") return "bg-error-3 border-error-7";
  if (status === "running") return "bg-primary-3 border-primary-7";
  if (status === "completed") return "bg-success-3 border-success-7";

  switch (type) {
    case "start":
      return "bg-success-3 border-success-6";
    case "end":
      return "bg-neutral-3 border-neutral-6";
    case "conditional":
      return "bg-warning-3 border-warning-6";
    case "tool":
      return "bg-insight-3 border-insight-6";
    case "agent":
      return "bg-primary-3 border-primary-6";
    default:
      return "bg-neutral-2 border-neutral-6";
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
                ${isActive ? "ring-2 ring-primary-7 ring-offset-1 dark:ring-offset-neutral-12" : ""}
                transition-all duration-200
              `}
            >
              {/* Type icon */}
              <span className="text-neutral-11">
                {getNodeTypeIcon(node.type)}
              </span>

              {/* Name */}
              <span className="flex-1 text-sm font-medium text-neutral-12">
                {node.name}
              </span>

              {/* Duration */}
              {node.duration !== undefined && (
                <span className="text-xs text-neutral-10">
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
                    className="flex items-center gap-1 text-xs text-neutral-9"
                  >
                    <ArrowRight size={10} />
                    {edge.condition && (
                      <span className="px-1.5 py-0.5 bg-neutral-2 rounded text-neutral-11">
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
