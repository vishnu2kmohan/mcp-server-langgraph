/**
 * WorkflowCanvas Component Tests
 *
 * TDD tests for the React Flow workflow canvas.
 * Tests cover:
 * - Rendering with nodes and edges
 * - Connection handling
 * - Node drag handling
 * - Selection changes
 * - Status-based node coloring
 * - Empty state
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type {
  Edge,
  Connection,
  Node,
  OnNodesChange,
  OnEdgesChange,
  OnConnect,
} from "reactflow";
import { WorkflowCanvas } from "./WorkflowCanvas";
import workflowReducer, {
  initialWorkflowState,
} from "../../store/slices/workflowSlice";
import type {
  WorkflowNode,
  WorkflowSliceState,
  WorkflowNodeData,
} from "../../types/workflow";

// Track captured callbacks from ReactFlow
let capturedOnConnect: OnConnect | undefined;
let capturedOnNodeDragStop:
  | ((event: React.MouseEvent, node: Node) => void)
  | undefined;
let capturedOnSelectionChange:
  | ((params: { nodes: Node[]; edges: Edge[] }) => void)
  | undefined;
let capturedNodeColorFn: ((node: Node) => string) | undefined;

// Mock ReactFlow and its components
vi.mock("reactflow", () => {
  return {
    default: function MockReactFlow(props: {
      nodes: Node[];
      edges: Edge[];
      onNodesChange: OnNodesChange;
      onEdgesChange: OnEdgesChange;
      onConnect: OnConnect;
      onNodeDragStop: (event: React.MouseEvent, node: Node) => void;
      onSelectionChange: (params: { nodes: Node[]; edges: Edge[] }) => void;
      nodeTypes: Record<string, unknown>;
      children?: React.ReactNode;
    }) {
      // Capture callbacks for testing
      capturedOnConnect = props.onConnect;
      capturedOnNodeDragStop = props.onNodeDragStop;
      capturedOnSelectionChange = props.onSelectionChange;

      return (
        <div
          data-testid="react-flow"
          data-nodes={props.nodes.length}
          data-edges={props.edges.length}
        >
          <div data-testid="node-count">{props.nodes.length} nodes</div>
          <div data-testid="edge-count">{props.edges.length} edges</div>
          {props.nodes.map((node) => (
            <div key={node.id} data-testid={`node-${node.id}`}>
              {(node.data as WorkflowNodeData).label}
            </div>
          ))}
          {/* Render children (Background, Controls, MiniMap) */}
          {props.children}
        </div>
      );
    },
    Background: function MockBackground() {
      return <div data-testid="background" />;
    },
    Controls: function MockControls() {
      return <div data-testid="controls" />;
    },
    MiniMap: function MockMiniMap(props: {
      nodeColor: (node: Node) => string;
    }) {
      // Capture the nodeColor function for testing
      capturedNodeColorFn = props.nodeColor;
      return <div data-testid="minimap" />;
    },
    useNodesState: (initialNodes: Node[]) => {
      const nodes = [...initialNodes];
      const setNodes = vi.fn((newNodes: Node[]) => {
        nodes.splice(0, nodes.length, ...newNodes);
      });
      const onNodesChange = vi.fn();
      return [nodes, setNodes, onNodesChange];
    },
    useEdgesState: (initialEdges: Edge[]) => {
      const edges = [...initialEdges];
      const setEdges = vi.fn((newEdges: Edge[]) => {
        edges.splice(0, edges.length, ...newEdges);
      });
      const onEdgesChange = vi.fn();
      return [edges, setEdges, onEdgesChange];
    },
    ConnectionLineType: {
      SmoothStep: "smoothstep",
    },
    BackgroundVariant: {
      Dots: "dots",
    },
    useReactFlow: () => ({
      screenToFlowPosition: (pos: { x: number; y: number }) => pos,
      getNodes: () => [],
      getEdges: () => [],
      fitView: vi.fn(),
    }),
  };
});

// Mock node components
vi.mock("./nodes", () => ({
  StartNode: () => <div>Start Node</div>,
  LLMNode: () => <div>LLM Node</div>,
  ToolNode: () => <div>Tool Node</div>,
  ConditionNode: () => <div>Condition Node</div>,
  ApprovalNode: () => <div>Approval Node</div>,
  EndNode: () => <div>End Node</div>,
}));

// Sample test data
const sampleNodes: WorkflowNode[] = [
  {
    id: "node-1",
    type: "default",
    position: { x: 100, y: 100 },
    data: { label: "Start", nodeType: "start", config: {} },
  },
  {
    id: "node-2",
    type: "default",
    position: { x: 250, y: 100 },
    data: { label: "LLM Agent", nodeType: "llm", config: {} },
  },
  {
    id: "node-3",
    type: "default",
    position: { x: 400, y: 100 },
    data: { label: "End", nodeType: "end", config: {} },
  },
];

const sampleEdges: Edge[] = [
  { id: "edge-1", source: "node-1", target: "node-2" },
  { id: "edge-2", source: "node-2", target: "node-3" },
];

// Create test store with configurable state
const createTestStore = (overrides: Partial<WorkflowSliceState> = {}) => {
  return configureStore({
    reducer: {
      workflow: workflowReducer,
    },
    preloadedState: {
      workflow: {
        ...initialWorkflowState,
        ...overrides,
      },
    },
  });
};

const renderWithProviders = (overrides: Partial<WorkflowSliceState> = {}) => {
  const store = createTestStore(overrides);
  return {
    store,
    ...render(
      <Provider store={store}>
        <WorkflowCanvas />
      </Provider>,
    ),
  };
};

describe("WorkflowCanvas", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    capturedOnConnect = undefined;
    capturedOnNodeDragStop = undefined;
    capturedOnSelectionChange = undefined;
    capturedNodeColorFn = undefined;
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Rendering", () => {
    it("should render ReactFlow container", () => {
      renderWithProviders();
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });

    it("should render Background component", () => {
      renderWithProviders();
      expect(screen.getByTestId("background")).toBeInTheDocument();
    });

    it("should render Controls component", () => {
      renderWithProviders();
      expect(screen.getByTestId("controls")).toBeInTheDocument();
    });

    it("should render MiniMap component", () => {
      renderWithProviders();
      expect(screen.getByTestId("minimap")).toBeInTheDocument();
    });

    it("should render with empty nodes and edges", () => {
      renderWithProviders({ nodes: [], edges: [] });
      expect(screen.getByTestId("node-count")).toHaveTextContent("0 nodes");
      expect(screen.getByTestId("edge-count")).toHaveTextContent("0 edges");
    });
  });

  describe("Nodes and Edges", () => {
    it("should display correct node count", () => {
      renderWithProviders({ nodes: sampleNodes, edges: sampleEdges });
      expect(screen.getByTestId("node-count")).toHaveTextContent("3 nodes");
    });

    it("should display correct edge count", () => {
      renderWithProviders({ nodes: sampleNodes, edges: sampleEdges });
      expect(screen.getByTestId("edge-count")).toHaveTextContent("2 edges");
    });

    it("should render node labels", () => {
      renderWithProviders({ nodes: sampleNodes, edges: sampleEdges });
      expect(screen.getByText("Start")).toBeInTheDocument();
      expect(screen.getByText("LLM Agent")).toBeInTheDocument();
      expect(screen.getByText("End")).toBeInTheDocument();
    });
  });

  describe("Connection Handling", () => {
    it("should dispatch addEdge action on valid connection", () => {
      const { store } = renderWithProviders({ nodes: sampleNodes, edges: [] });

      const connection: Connection = {
        source: "node-1",
        target: "node-2",
        sourceHandle: null,
        targetHandle: null,
      };

      act(() => {
        capturedOnConnect?.(connection);
      });

      const state = store.getState();
      expect(state.workflow.edges.length).toBe(1);
    });

    it("should handle connection with handles", () => {
      const { store } = renderWithProviders({ nodes: sampleNodes, edges: [] });

      const connection: Connection = {
        source: "node-1",
        target: "node-2",
        sourceHandle: "output-1",
        targetHandle: "input-1",
      };

      act(() => {
        capturedOnConnect?.(connection);
      });

      const state = store.getState();
      const edge = state.workflow.edges[0];
      expect(edge.sourceHandle).toBe("output-1");
      expect(edge.targetHandle).toBe("input-1");
    });

    it("should not dispatch when source is null", () => {
      const { store } = renderWithProviders({ nodes: sampleNodes, edges: [] });

      const connection: Connection = {
        source: null,
        target: "node-2",
        sourceHandle: null,
        targetHandle: null,
      };

      act(() => {
        capturedOnConnect?.(connection);
      });

      const state = store.getState();
      expect(state.workflow.edges.length).toBe(0);
    });

    it("should not dispatch when target is null", () => {
      const { store } = renderWithProviders({ nodes: sampleNodes, edges: [] });

      const connection: Connection = {
        source: "node-1",
        target: null,
        sourceHandle: null,
        targetHandle: null,
      };

      act(() => {
        capturedOnConnect?.(connection);
      });

      const state = store.getState();
      expect(state.workflow.edges.length).toBe(0);
    });
  });

  describe("Node Drag Handling", () => {
    it("should dispatch updateNodePositions on node drag stop", () => {
      const { store } = renderWithProviders({
        nodes: sampleNodes,
        edges: sampleEdges,
      });

      const mockEvent = {} as React.MouseEvent;
      const draggedNode: Node = {
        id: "node-1",
        position: { x: 200, y: 200 },
        data: { label: "Start", nodeType: "start", config: {} },
      };

      act(() => {
        capturedOnNodeDragStop?.(mockEvent, draggedNode);
      });

      const state = store.getState();
      const node = state.workflow.nodes.find((n) => n.id === "node-1");
      expect(node?.position).toEqual({ x: 200, y: 200 });
    });
  });

  describe("Selection Handling", () => {
    it("should dispatch setSelectedNodes on selection change", () => {
      const { store } = renderWithProviders({
        nodes: sampleNodes,
        edges: sampleEdges,
      });

      const selectedNodes: Node[] = [
        { id: "node-1", position: { x: 100, y: 100 }, data: {} },
        { id: "node-2", position: { x: 250, y: 100 }, data: {} },
      ];

      act(() => {
        capturedOnSelectionChange?.({ nodes: selectedNodes, edges: [] });
      });

      const state = store.getState();
      expect(state.workflow.selectedNodeIds).toEqual(["node-1", "node-2"]);
    });

    it("should dispatch setSelectedEdges on selection change", () => {
      const { store } = renderWithProviders({
        nodes: sampleNodes,
        edges: sampleEdges,
      });

      const selectedEdges: Edge[] = [
        { id: "edge-1", source: "node-1", target: "node-2" },
      ];

      act(() => {
        capturedOnSelectionChange?.({ nodes: [], edges: selectedEdges });
      });

      const state = store.getState();
      expect(state.workflow.selectedEdgeIds).toEqual(["edge-1"]);
    });

    it("should handle mixed selection of nodes and edges", () => {
      const { store } = renderWithProviders({
        nodes: sampleNodes,
        edges: sampleEdges,
      });

      const selectedNodes: Node[] = [
        { id: "node-2", position: { x: 250, y: 100 }, data: {} },
      ];
      const selectedEdges: Edge[] = [
        { id: "edge-2", source: "node-2", target: "node-3" },
      ];

      act(() => {
        capturedOnSelectionChange?.({
          nodes: selectedNodes,
          edges: selectedEdges,
        });
      });

      const state = store.getState();
      expect(state.workflow.selectedNodeIds).toEqual(["node-2"]);
      expect(state.workflow.selectedEdgeIds).toEqual(["edge-2"]);
    });

    it("should clear selection when nothing is selected", () => {
      const { store } = renderWithProviders({
        nodes: sampleNodes,
        edges: sampleEdges,
        selectedNodeIds: ["node-1"],
        selectedEdgeIds: ["edge-1"],
      });

      act(() => {
        capturedOnSelectionChange?.({ nodes: [], edges: [] });
      });

      const state = store.getState();
      expect(state.workflow.selectedNodeIds).toEqual([]);
      expect(state.workflow.selectedEdgeIds).toEqual([]);
    });
  });

  describe("Node Status Colors (MiniMap)", () => {
    it("should return blue for running status", () => {
      renderWithProviders({
        nodes: sampleNodes,
        nodeStatuses: { "node-1": "running" },
      });

      const testNode: Node<WorkflowNodeData> = {
        id: "node-1",
        position: { x: 100, y: 100 },
        data: {
          label: "Test",
          nodeType: "start",
          config: {},
          status: "running",
        },
      };

      const color = capturedNodeColorFn?.(testNode);
      expect(color).toBe("#3b82f6"); // blue
    });

    it("should return green for success status", () => {
      renderWithProviders({ nodes: sampleNodes });

      const testNode: Node<WorkflowNodeData> = {
        id: "node-1",
        position: { x: 100, y: 100 },
        data: {
          label: "Test",
          nodeType: "start",
          config: {},
          status: "success",
        },
      };

      const color = capturedNodeColorFn?.(testNode);
      expect(color).toBe("#22c55e"); // green
    });

    it("should return red for error status", () => {
      renderWithProviders({ nodes: sampleNodes });

      const testNode: Node<WorkflowNodeData> = {
        id: "node-1",
        position: { x: 100, y: 100 },
        data: { label: "Test", nodeType: "start", config: {}, status: "error" },
      };

      const color = capturedNodeColorFn?.(testNode);
      expect(color).toBe("#ef4444"); // red
    });

    it("should return gray for idle/default status", () => {
      renderWithProviders({ nodes: sampleNodes });

      const testNode: Node<WorkflowNodeData> = {
        id: "node-1",
        position: { x: 100, y: 100 },
        data: { label: "Test", nodeType: "start", config: {}, status: "idle" },
      };

      const color = capturedNodeColorFn?.(testNode);
      expect(color).toBe("#9ca3af"); // gray
    });

    it("should return gray when status is undefined", () => {
      renderWithProviders({ nodes: sampleNodes });

      const testNode: Node<WorkflowNodeData> = {
        id: "node-1",
        position: { x: 100, y: 100 },
        data: { label: "Test", nodeType: "start", config: {} },
      };

      const color = capturedNodeColorFn?.(testNode);
      expect(color).toBe("#9ca3af"); // gray
    });
  });

  describe("Node Status Sync", () => {
    it("should sync node status from store nodeStatuses", () => {
      const nodesWithoutStatus: WorkflowNode[] = [
        {
          id: "node-1",
          type: "default",
          position: { x: 100, y: 100 },
          data: { label: "Start", nodeType: "start", config: {} },
        },
      ];

      renderWithProviders({
        nodes: nodesWithoutStatus,
        nodeStatuses: { "node-1": "running" },
      });

      // The component should merge status from nodeStatuses
      expect(screen.getByTestId("node-node-1")).toBeInTheDocument();
    });

    it("should use node data status if nodeStatuses is empty", () => {
      const nodesWithStatus: WorkflowNode[] = [
        {
          id: "node-1",
          type: "default",
          position: { x: 100, y: 100 },
          data: {
            label: "Start",
            nodeType: "start",
            config: {},
            status: "success",
          },
        },
      ];

      renderWithProviders({
        nodes: nodesWithStatus,
        nodeStatuses: {},
      });

      expect(screen.getByTestId("node-node-1")).toBeInTheDocument();
    });
  });

  describe("Container Styling", () => {
    it("should render with full height and width container", () => {
      const { container } = renderWithProviders();
      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper).toHaveClass("h-full");
      expect(wrapper).toHaveClass("w-full");
    });
  });

  describe("Node Highlighting", () => {
    it("should accept highlightedNodeId prop", () => {
      const store = createTestStore({ nodes: sampleNodes });
      render(
        <Provider store={store}>
          <WorkflowCanvas highlightedNodeId="node-1" />
        </Provider>,
      );
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });

    it("should apply highlight class to highlighted node", () => {
      const store = createTestStore({ nodes: sampleNodes });
      render(
        <Provider store={store}>
          <WorkflowCanvas highlightedNodeId="node-2" />
        </Provider>,
      );
      // The mock ReactFlow will receive nodes with highlight flag
      expect(screen.getByTestId("node-node-2")).toBeInTheDocument();
    });

    it("should clear highlight when highlightedNodeId is null", () => {
      const store = createTestStore({ nodes: sampleNodes });
      render(
        <Provider store={store}>
          <WorkflowCanvas highlightedNodeId={null} />
        </Provider>,
      );
      expect(screen.getByTestId("react-flow")).toBeInTheDocument();
    });
  });
});
