/**
 * WorkflowCanvas Component
 *
 * Main React Flow canvas for visual workflow editing.
 * Features:
 * - Drag and drop nodes
 * - Connect nodes with edges
 * - Mini-map for navigation
 * - Controls (zoom, fit view)
 * - Background grid
 * - Node selection
 * - Execution visualization
 */

import {
  useCallback,
  useMemo,
  useRef,
  type MouseEvent,
  type DragEvent,
} from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  useReactFlow,
  type Connection,
  type Edge,
  type Node,
  type NodeTypes,
  ConnectionLineType,
  BackgroundVariant,
} from "reactflow";
import "reactflow/dist/style.css";

import { useAppDispatch, useAppSelector } from "../../store/hooks";
import {
  addNode as addNodeAction,
  addEdge as addEdgeAction,
  updateNodePositions,
  setSelectedNodes,
  setSelectedEdges,
  selectWorkflowNodes,
  selectWorkflowEdges,
  selectNodeStatuses,
} from "../../store/slices/workflowSlice";
import type { WorkflowNodeType } from "../../types/workflow";
import type { WorkflowNodeData } from "../../types/workflow";
import {
  StartNode,
  LLMNode,
  ToolNode,
  ConditionNode,
  ApprovalNode,
  EndNode,
} from "./nodes";

// Define custom node types for React Flow
const nodeTypes: NodeTypes = {
  start: StartNode,
  llm: LLMNode,
  tool: ToolNode,
  conditional: ConditionNode,
  approval: ApprovalNode,
  end: EndNode,
};

// =============================================================================
// Types
// =============================================================================

export interface WorkflowCanvasProps {
  /** Node ID to highlight (from ExecutionTracePanel hover) */
  highlightedNodeId?: string | null;
}

// =============================================================================
// Component
// =============================================================================

export function WorkflowCanvas({
  highlightedNodeId,
}: WorkflowCanvasProps = {}) {
  const dispatch = useAppDispatch();
  const storeNodes = useAppSelector(selectWorkflowNodes);
  const storeEdges = useAppSelector(selectWorkflowEdges);
  const nodeStatuses = useAppSelector(selectNodeStatuses);

  // Sync nodes with status and highlighting from store
  const nodesWithStatus = useMemo(() => {
    return (storeNodes || []).map((node) => ({
      ...node,
      type: node.data.nodeType, // Use nodeType as React Flow type
      // Apply highlight styling when node matches highlightedNodeId
      className:
        highlightedNodeId === node.id
          ? "ring-2 ring-primary-7 ring-offset-2"
          : undefined,
      data: {
        ...node.data,
        status: nodeStatuses?.[node.id] || node.data.status || "idle",
        isHighlighted: highlightedNodeId === node.id,
      },
    }));
  }, [storeNodes, nodeStatuses, highlightedNodeId]);

  const [nodes, setNodes, onNodesChange] = useNodesState(nodesWithStatus);
  const [edges, setEdges, onEdgesChange] = useEdgesState(storeEdges || []);

  // Sync local state with store
  useMemo(() => {
    setNodes(nodesWithStatus);
  }, [nodesWithStatus, setNodes]);

  useMemo(() => {
    setEdges(storeEdges || []);
  }, [storeEdges, setEdges]);

  // Handle new connections
  const onConnect = useCallback(
    (params: Connection) => {
      if (params.source && params.target) {
        dispatch(
          addEdgeAction(
            params.source,
            params.target,
            params.sourceHandle || undefined,
            params.targetHandle || undefined,
          ),
        );
      }
    },
    [dispatch],
  );

  // Handle node drag end (update positions in store)
  const onNodeDragStop = useCallback(
    (_event: MouseEvent, node: Node) => {
      dispatch(updateNodePositions([{ id: node.id, position: node.position }]));
    },
    [dispatch],
  );

  // Handle selection changes
  const onSelectionChange = useCallback(
    ({ nodes, edges }: { nodes: Node[]; edges: Edge[] }) => {
      dispatch(setSelectedNodes(nodes.map((n) => n.id)));
      dispatch(setSelectedEdges(edges.map((e) => e.id)));
    },
    [dispatch],
  );

  // Reference to the React Flow wrapper for drop position calculation
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const { screenToFlowPosition } = useReactFlow();

  // Handle drag over - allow drop
  const onDragOver = useCallback((event: DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  // Handle drop from NodePalette
  const onDrop = useCallback(
    (event: DragEvent) => {
      event.preventDefault();

      // Get the node type from the drag data
      const nodeType = event.dataTransfer.getData(
        "application/reactflow",
      ) as WorkflowNodeType;

      // Validate node type
      if (
        !nodeType ||
        ![
          "start",
          "end",
          "llm",
          "tool",
          "conditional",
          "approval",
          "custom",
        ].includes(nodeType)
      ) {
        return;
      }

      // Calculate the drop position in flow coordinates
      const position = screenToFlowPosition({
        x: event.clientX,
        y: event.clientY,
      });

      // Dispatch action to add the node
      dispatch(addNodeAction(nodeType, position));
    },
    [dispatch, screenToFlowPosition],
  );

  // Color nodes in minimap based on type
  const getNodeColor = (node: Node<WorkflowNodeData>) => {
    const status = node.data.status || "idle";
    switch (status) {
      case "running":
        return "#3b82f6"; // blue
      case "success":
        return "#22c55e"; // green
      case "error":
        return "#ef4444"; // red
      default:
        return "#9ca3af"; // gray
    }
  };

  return (
    <div
      ref={reactFlowWrapper}
      className="h-full w-full"
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeDragStop={onNodeDragStop}
        onSelectionChange={onSelectionChange}
        nodeTypes={nodeTypes}
        fitView
        snapToGrid
        snapGrid={[15, 15]}
        defaultEdgeOptions={{
          type: "smoothstep",
          animated: true,
          style: { strokeWidth: 2 },
        }}
        connectionLineType={ConnectionLineType.SmoothStep}
        deleteKeyCode={["Backspace", "Delete"]}
        multiSelectionKeyCode="Shift"
        proOptions={{ hideAttribution: true }}
      >
        <Background
          variant={BackgroundVariant.Dots}
          gap={15}
          size={1}
          className="bg-neutral-1"
        />
        <Controls className="bg-neutral-1 border border-neutral-5" />
        <MiniMap
          nodeColor={getNodeColor}
          maskColor="var(--neutral-a3)"
          className="bg-neutral-1 border border-neutral-5"
        />
      </ReactFlow>
    </div>
  );
}
