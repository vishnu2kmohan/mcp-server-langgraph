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

import { useCallback, useMemo, type MouseEvent } from "react";
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
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
  addEdge as addEdgeAction,
  updateNodePositions,
  setSelectedNodes,
  setSelectedEdges,
  selectWorkflowNodes,
  selectWorkflowEdges,
  selectNodeStatuses,
} from "../../store/slices/workflowSlice";
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

export function WorkflowCanvas() {
  const dispatch = useAppDispatch();
  const storeNodes = useAppSelector(selectWorkflowNodes);
  const storeEdges = useAppSelector(selectWorkflowEdges);
  const nodeStatuses = useAppSelector(selectNodeStatuses);

  // Sync nodes with status from store
  const nodesWithStatus = useMemo(() => {
    return (storeNodes || []).map((node) => ({
      ...node,
      type: node.data.nodeType, // Use nodeType as React Flow type
      data: {
        ...node.data,
        status: nodeStatuses?.[node.id] || node.data.status || "idle",
      },
    }));
  }, [storeNodes, nodeStatuses]);

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
    <div className="h-full w-full">
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
          className="bg-gray-50 dark:bg-gray-900"
        />
        <Controls className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700" />
        <MiniMap
          nodeColor={getNodeColor}
          maskColor="rgba(0,0,0,0.1)"
          className="bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700"
        />
      </ReactFlow>
    </div>
  );
}
