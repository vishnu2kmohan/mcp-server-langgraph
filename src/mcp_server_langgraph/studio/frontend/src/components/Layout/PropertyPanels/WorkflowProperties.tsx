/**
 * WorkflowProperties Component
 *
 * Property panel for workflows, showing workflow info,
 * node counts, execution status, and selected node details.
 */

import { useAppSelector } from "../../../store/hooks";
import {
  selectWorkflowMetadata,
  selectWorkflowNodes,
  selectWorkflowEdges,
  selectSelectedNodeIds,
  selectExecutionState,
  selectValidation,
} from "../../../store/slices/workflowSlice";
import type { TabState } from "../../../store/slices/workspaceSlice";
import { PropertySection } from "./PropertySection";
import { PropertyRow } from "./PropertyRow";

// =============================================================================
// Types
// =============================================================================

export interface WorkflowPropertiesProps {
  tab: TabState;
  isSectionExpanded: (id: string) => boolean;
  onToggleSection: (id: string) => void;
}

// =============================================================================
// Component
// =============================================================================

export function WorkflowProperties({
  tab,
  isSectionExpanded,
  onToggleSection,
}: WorkflowPropertiesProps) {
  const metadata = useAppSelector(selectWorkflowMetadata);
  const nodes = useAppSelector(selectWorkflowNodes);
  const edges = useAppSelector(selectWorkflowEdges);
  const selectedNodeIds = useAppSelector(selectSelectedNodeIds);
  const executionState = useAppSelector(selectExecutionState);
  const validation = useAppSelector(selectValidation);

  // Count nodes by type
  const nodeTypeCounts = nodes.reduce(
    (acc, node) => {
      const type = node.type || "unknown";
      acc[type] = (acc[type] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  // Find selected node
  const selectedNode =
    selectedNodeIds.length === 1
      ? nodes.find((n) => n.id === selectedNodeIds[0])
      : null;

  // Format date
  const formatDate = (timestamp?: number) => {
    if (!timestamp) return "N/A";
    return new Date(timestamp).toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div data-testid="workflow-properties">
      <PropertySection
        id="workflow-info"
        title="Workflow Info"
        isExpanded={isSectionExpanded("workflow-info")}
        onToggle={() => onToggleSection("workflow-info")}
      >
        <PropertyRow label="ID" value={tab.entityId || "N/A"} mono />
        <PropertyRow label="Name" value={metadata?.name || tab.title} />
        <PropertyRow label="Version" value={metadata?.version ?? 1} />
        <PropertyRow label="Updated" value={formatDate(metadata?.updatedAt)} />
      </PropertySection>

      <PropertySection
        id="nodes-info"
        title="Graph"
        isExpanded={isSectionExpanded("nodes-info")}
        onToggle={() => onToggleSection("nodes-info")}
        badge={
          <span className="text-[10px] text-gray-400">
            {nodes.length} nodes
          </span>
        }
      >
        <PropertyRow label="Nodes" value={nodes.length} />
        <PropertyRow label="Edges" value={edges.length} />
        {Object.entries(nodeTypeCounts).map(([type, count]) => (
          <PropertyRow key={type} label={type} value={count} />
        ))}
      </PropertySection>

      <PropertySection
        id="execution-info"
        title="Execution"
        isExpanded={isSectionExpanded("execution-info")}
        onToggle={() => onToggleSection("execution-info")}
        badge={
          <span
            className={`text-[10px] px-1.5 py-0.5 rounded ${
              executionState === "running"
                ? "bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                : executionState === "completed"
                  ? "bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300"
                  : executionState === "error"
                    ? "bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300"
                    : "bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400"
            }`}
          >
            {executionState}
          </span>
        }
      >
        <PropertyRow label="Status" value={executionState} />
        <PropertyRow label="Valid" value={validation.isValid ? "Yes" : "No"} />
        {validation.errors.length > 0 && (
          <PropertyRow label="Errors" value={validation.errors.length} />
        )}
        {validation.warnings.length > 0 && (
          <PropertyRow label="Warnings" value={validation.warnings.length} />
        )}
      </PropertySection>

      {selectedNode && (
        <PropertySection
          id="selected-node"
          title="Selected Node"
          isExpanded={isSectionExpanded("selected-node")}
          onToggle={() => onToggleSection("selected-node")}
        >
          <PropertyRow label="ID" value={selectedNode.id} mono />
          <PropertyRow label="Type" value={selectedNode.type || "unknown"} />
          <PropertyRow
            label="Position"
            value={`(${Math.round(selectedNode.position.x)}, ${Math.round(selectedNode.position.y)})`}
          />
          {selectedNode.data?.label && (
            <PropertyRow label="Label" value={selectedNode.data.label} />
          )}
        </PropertySection>
      )}
    </div>
  );
}

export default WorkflowProperties;
