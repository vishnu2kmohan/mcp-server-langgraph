/**
 * Workflow Slice Tests
 *
 * TDD tests for workflow Redux slice.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import workflowReducer, {
  initialWorkflowState,
  createWorkflow,
  loadWorkflow,
  saveWorkflow,
  executeWorkflow,
  addNode,
  updateNode,
  deleteNode,
  deleteNodes,
  addEdge,
  deleteEdge,
  updateNodePositions,
  setSelectedNodes,
  setSelectedEdges,
  clearSelection,
  takeSnapshot,
  undo,
  redo,
  validate,
  clearError,
  resetWorkflow,
  updateNodeStatus,
  addExecutionLog,
  clearExecutionLogs,
  selectWorkflowMetadata,
  selectWorkflowNodes,
  selectWorkflowEdges,
  selectSelectedNodeIds,
  selectIsDirty,
  selectCanUndo,
  selectCanRedo,
  selectValidation,
  selectWorkflowError,
  selectExecutionState,
  selectNodeStatuses,
  selectExecutionLogs,
} from "./workflowSlice";
import type { WorkflowSliceState } from "./workflowSlice";
import type { WorkflowNode } from "../../types/workflow";

// Helper to create a test store
const createTestStore = (preloadedState?: Partial<WorkflowSliceState>) => {
  return configureStore({
    reducer: { workflow: workflowReducer },
    preloadedState: preloadedState
      ? { workflow: { ...initialWorkflowState, ...preloadedState } }
      : undefined,
  });
};

// Mock node for testing
const mockNode: WorkflowNode = {
  id: "node-1",
  type: "default",
  position: { x: 100, y: 100 },
  data: {
    label: "Test Node",
    nodeType: "llm",
    config: {},
  },
};

describe("workflowSlice", () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    mockFetch.mockReset();
    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  describe("Initial State", () => {
    it("should have null metadata initially", () => {
      const store = createTestStore();
      expect(selectWorkflowMetadata(store.getState())).toBeNull();
    });

    it("should have empty nodes array initially", () => {
      const store = createTestStore();
      expect(selectWorkflowNodes(store.getState())).toEqual([]);
    });

    it("should have empty edges array initially", () => {
      const store = createTestStore();
      expect(selectWorkflowEdges(store.getState())).toEqual([]);
    });

    it("should have empty selection initially", () => {
      const store = createTestStore();
      expect(selectSelectedNodeIds(store.getState())).toEqual([]);
    });

    it("should not be dirty initially", () => {
      const store = createTestStore();
      expect(selectIsDirty(store.getState())).toBe(false);
    });

    it("should have idle execution state initially", () => {
      const store = createTestStore();
      expect(selectExecutionState(store.getState())).toBe("idle");
    });
  });

  describe("createWorkflow", () => {
    it("should create a new workflow with metadata", () => {
      const store = createTestStore();
      store.dispatch(
        createWorkflow({ name: "Test Workflow", description: "A test" }),
      );

      const metadata = selectWorkflowMetadata(store.getState());
      expect(metadata).not.toBeNull();
      expect(metadata?.name).toBe("Test Workflow");
      expect(metadata?.description).toBe("A test");
      expect(metadata?.version).toBe(1);
    });

    it("should reset nodes and edges", () => {
      const store = createTestStore({
        nodes: [mockNode],
        edges: [{ id: "e1", source: "n1", target: "n2" }],
      });
      store.dispatch(createWorkflow({ name: "New Workflow" }));

      expect(selectWorkflowNodes(store.getState())).toEqual([]);
      expect(selectWorkflowEdges(store.getState())).toEqual([]);
    });
  });

  describe("Node Operations", () => {
    describe("addNode", () => {
      it("should add a node with the given type and position", () => {
        const store = createTestStore();
        store.dispatch(addNode("llm", { x: 100, y: 200 }));

        const nodes = selectWorkflowNodes(store.getState());
        expect(nodes).toHaveLength(1);
        expect(nodes[0].data.nodeType).toBe("llm");
        expect(nodes[0].position).toEqual({ x: 100, y: 200 });
      });

      it("should use default label if not provided", () => {
        const store = createTestStore();
        store.dispatch(addNode("tool", { x: 0, y: 0 }));

        const nodes = selectWorkflowNodes(store.getState());
        expect(nodes[0].data.label).toBe("Tool");
      });

      it("should use custom label if provided", () => {
        const store = createTestStore();
        store.dispatch(addNode("tool", { x: 0, y: 0 }, "Custom Label"));

        const nodes = selectWorkflowNodes(store.getState());
        expect(nodes[0].data.label).toBe("Custom Label");
      });

      it("should set isDirty to true", () => {
        const store = createTestStore();
        store.dispatch(addNode("llm", { x: 0, y: 0 }));

        expect(selectIsDirty(store.getState())).toBe(true);
      });
    });

    describe("updateNode", () => {
      it("should update node data", () => {
        const store = createTestStore({ nodes: [mockNode] });
        store.dispatch(
          updateNode({ nodeId: "node-1", data: { label: "Updated Label" } }),
        );

        const nodes = selectWorkflowNodes(store.getState());
        expect(nodes[0].data.label).toBe("Updated Label");
      });

      it("should preserve other data fields", () => {
        const store = createTestStore({ nodes: [mockNode] });
        store.dispatch(
          updateNode({ nodeId: "node-1", data: { label: "Updated" } }),
        );

        const nodes = selectWorkflowNodes(store.getState());
        expect(nodes[0].data.nodeType).toBe("llm");
      });
    });

    describe("deleteNode", () => {
      it("should remove the node", () => {
        const store = createTestStore({ nodes: [mockNode] });
        store.dispatch(deleteNode("node-1"));

        expect(selectWorkflowNodes(store.getState())).toHaveLength(0);
      });

      it("should remove connected edges", () => {
        const store = createTestStore({
          nodes: [mockNode, { ...mockNode, id: "node-2" }],
          edges: [{ id: "edge-1", source: "node-1", target: "node-2" }],
        });
        store.dispatch(deleteNode("node-1"));

        expect(selectWorkflowEdges(store.getState())).toHaveLength(0);
      });
    });

    describe("deleteNodes", () => {
      it("should remove multiple nodes", () => {
        const store = createTestStore({
          nodes: [
            mockNode,
            { ...mockNode, id: "node-2" },
            { ...mockNode, id: "node-3" },
          ],
        });
        store.dispatch(deleteNodes(["node-1", "node-2"]));

        const nodes = selectWorkflowNodes(store.getState());
        expect(nodes).toHaveLength(1);
        expect(nodes[0].id).toBe("node-3");
      });
    });
  });

  describe("Edge Operations", () => {
    describe("addEdge", () => {
      it("should add an edge between nodes", () => {
        const store = createTestStore({
          nodes: [mockNode, { ...mockNode, id: "node-2" }],
        });
        store.dispatch(addEdge("node-1", "node-2"));

        const edges = selectWorkflowEdges(store.getState());
        expect(edges).toHaveLength(1);
        expect(edges[0].source).toBe("node-1");
        expect(edges[0].target).toBe("node-2");
      });

      it("should prevent self-loops", () => {
        const store = createTestStore({ nodes: [mockNode] });
        store.dispatch(addEdge("node-1", "node-1"));

        expect(selectWorkflowEdges(store.getState())).toHaveLength(0);
      });
    });

    describe("deleteEdge", () => {
      it("should remove the edge", () => {
        const store = createTestStore({
          edges: [{ id: "edge-1", source: "node-1", target: "node-2" }],
        });
        store.dispatch(deleteEdge("edge-1"));

        expect(selectWorkflowEdges(store.getState())).toHaveLength(0);
      });
    });
  });

  describe("Position Updates", () => {
    it("should update node positions", () => {
      const store = createTestStore({ nodes: [mockNode] });
      store.dispatch(
        updateNodePositions([{ id: "node-1", position: { x: 500, y: 600 } }]),
      );

      const nodes = selectWorkflowNodes(store.getState());
      expect(nodes[0].position).toEqual({ x: 500, y: 600 });
    });
  });

  describe("Selection", () => {
    it("should set selected nodes", () => {
      const store = createTestStore();
      store.dispatch(setSelectedNodes(["node-1", "node-2"]));

      expect(selectSelectedNodeIds(store.getState())).toEqual([
        "node-1",
        "node-2",
      ]);
    });

    it("should set selected edges", () => {
      const store = createTestStore();
      store.dispatch(setSelectedEdges(["edge-1"]));

      expect(store.getState().workflow.selectedEdgeIds).toEqual(["edge-1"]);
    });

    it("should clear selection", () => {
      const store = createTestStore({
        selectedNodeIds: ["node-1"],
        selectedEdgeIds: ["edge-1"],
      });
      store.dispatch(clearSelection());

      expect(selectSelectedNodeIds(store.getState())).toEqual([]);
      expect(store.getState().workflow.selectedEdgeIds).toEqual([]);
    });
  });

  describe("Undo/Redo", () => {
    it("should take snapshot", () => {
      const store = createTestStore({ nodes: [mockNode] });
      store.dispatch(takeSnapshot());

      expect(selectCanUndo(store.getState())).toBe(true);
    });

    it("should undo to previous state", () => {
      const store = createTestStore({ nodes: [mockNode] });
      store.dispatch(takeSnapshot());
      store.dispatch(addNode("tool", { x: 0, y: 0 }));

      expect(selectWorkflowNodes(store.getState())).toHaveLength(2);

      store.dispatch(undo());
      expect(selectWorkflowNodes(store.getState())).toHaveLength(1);
      expect(selectCanRedo(store.getState())).toBe(true);
    });

    it("should redo undone action", () => {
      const store = createTestStore({ nodes: [mockNode] });
      store.dispatch(takeSnapshot());
      store.dispatch(addNode("tool", { x: 0, y: 0 }));
      store.dispatch(undo());
      store.dispatch(redo());

      expect(selectWorkflowNodes(store.getState())).toHaveLength(2);
    });
  });

  describe("Validation", () => {
    it("should validate workflow with no errors", () => {
      const store = createTestStore({ nodes: [mockNode] });
      store.dispatch(validate());

      const validation = selectValidation(store.getState());
      expect(validation.isValid).toBe(true);
      expect(validation.errors).toHaveLength(0);
    });

    it("should detect empty label error", () => {
      const nodeWithEmptyLabel: WorkflowNode = {
        ...mockNode,
        data: { ...mockNode.data, label: "" },
      };
      const store = createTestStore({ nodes: [nodeWithEmptyLabel] });
      store.dispatch(validate());

      const validation = selectValidation(store.getState());
      expect(validation.isValid).toBe(false);
      expect(validation.errors).toHaveLength(1);
      expect(validation.errors[0].message).toBe("Node must have a label");
    });

    it("should detect disconnected nodes warning", () => {
      const store = createTestStore({
        nodes: [
          mockNode,
          {
            ...mockNode,
            id: "node-2",
            data: { ...mockNode.data, label: "Node 2" },
          },
        ],
        edges: [],
      });
      store.dispatch(validate());

      const validation = selectValidation(store.getState());
      expect(validation.warnings.length).toBeGreaterThan(0);
    });
  });

  describe("Error Handling", () => {
    it("should clear error", () => {
      const store = createTestStore({ error: "Some error" });
      store.dispatch(clearError());

      expect(selectWorkflowError(store.getState())).toBeNull();
    });
  });

  describe("Reset", () => {
    it("should reset to initial state", () => {
      const store = createTestStore({
        nodes: [mockNode],
        isDirty: true,
        error: "Some error",
      });
      store.dispatch(resetWorkflow());

      const state = store.getState();
      expect(selectWorkflowNodes(state)).toEqual([]);
      expect(selectIsDirty(state)).toBe(false);
      expect(selectWorkflowError(state)).toBeNull();
    });
  });

  describe("Execution", () => {
    it("should update node status", () => {
      const store = createTestStore();
      store.dispatch(updateNodeStatus({ nodeId: "node-1", status: "running" }));

      expect(selectNodeStatuses(store.getState())["node-1"]).toBe("running");
    });

    it("should add execution log", () => {
      const store = createTestStore();
      store.dispatch(addExecutionLog({ level: "info", message: "Test log" }));

      const logs = selectExecutionLogs(store.getState());
      expect(logs).toHaveLength(1);
      expect(logs[0].message).toBe("Test log");
    });

    it("should clear execution logs", () => {
      const store = createTestStore({
        executionLogs: [
          { id: "1", timestamp: 0, level: "info", message: "Log" },
        ],
      });
      store.dispatch(clearExecutionLogs());

      expect(selectExecutionLogs(store.getState())).toHaveLength(0);
    });
  });

  describe("Async Thunks", () => {
    describe("loadWorkflow", () => {
      it("should load workflow from API", async () => {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () =>
            Promise.resolve({
              metadata: {
                id: "wf-1",
                name: "Loaded Workflow",
                description: "",
                version: 1,
                createdAt: 0,
                updatedAt: 0,
              },
              nodes: [mockNode],
              edges: [],
            }),
        });

        const store = createTestStore();
        await store.dispatch(loadWorkflow("wf-1"));

        expect(mockFetch).toHaveBeenCalledWith("/api/v1/workflows/wf-1", {
          credentials: "include",
        });
        expect(selectWorkflowMetadata(store.getState())?.name).toBe(
          "Loaded Workflow",
        );
        expect(selectWorkflowNodes(store.getState())).toHaveLength(1);
      });

      it("should set error on load failure", async () => {
        mockFetch.mockResolvedValueOnce({
          ok: false,
          json: () => Promise.resolve({ detail: "Not found" }),
        });

        const store = createTestStore();
        await store.dispatch(loadWorkflow("nonexistent"));

        expect(selectWorkflowError(store.getState())).toBe("Not found");
      });
    });

    describe("saveWorkflow", () => {
      it("should save workflow to API", async () => {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({}),
        });

        const store = createTestStore({
          metadata: {
            id: "wf-1",
            name: "Test",
            description: "",
            version: 1,
            createdAt: 0,
            updatedAt: 0,
          },
          nodes: [mockNode],
          isDirty: true,
        });
        await store.dispatch(saveWorkflow());

        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/workflows/wf-1",
          expect.objectContaining({ method: "PUT" }),
        );
        expect(selectIsDirty(store.getState())).toBe(false);
      });

      it("should set error if no workflow to save", async () => {
        const store = createTestStore();
        await store.dispatch(saveWorkflow());

        expect(selectWorkflowError(store.getState())).toBe(
          "No workflow to save",
        );
      });
    });

    describe("executeWorkflow", () => {
      it("should execute workflow via API", async () => {
        mockFetch.mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({}),
        });

        const store = createTestStore({
          metadata: {
            id: "wf-1",
            name: "Test",
            description: "",
            version: 1,
            createdAt: 0,
            updatedAt: 0,
          },
          nodes: [mockNode],
        });
        await store.dispatch(executeWorkflow());

        expect(mockFetch).toHaveBeenCalledWith(
          "/api/v1/workflows/wf-1/execute",
          expect.objectContaining({ method: "POST" }),
        );
        expect(selectExecutionState(store.getState())).toBe("completed");
      });

      it("should set error state on execution failure", async () => {
        mockFetch.mockResolvedValueOnce({
          ok: false,
          json: () => Promise.resolve({ detail: "Execution failed" }),
        });

        const store = createTestStore({
          metadata: {
            id: "wf-1",
            name: "Test",
            description: "",
            version: 1,
            createdAt: 0,
            updatedAt: 0,
          },
          nodes: [mockNode],
        });
        await store.dispatch(executeWorkflow());

        expect(selectExecutionState(store.getState())).toBe("error");
        expect(selectWorkflowError(store.getState())).toBe("Execution failed");
      });
    });
  });
});
