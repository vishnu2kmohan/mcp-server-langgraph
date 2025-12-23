/**
 * LangGraph Slice Tests
 *
 * TDD tests for Redux slice managing LangGraph execution events.
 * Enables DevTools time-travel debugging for LangGraph nodes.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import langGraphReducer, {
  addNode,
  updateNode,
  clearNodes,
  setCurrentSessionId,
  selectLangGraphNodes,
  selectLangGraphNodesBySession,
  selectCurrentSessionNodes,
  type LangGraphNode,
  type LangGraphState,
} from "./langGraphSlice";

// =============================================================================
// Test Fixtures
// =============================================================================

const mockNode: LangGraphNode = {
  id: "node-1",
  sessionId: "session-123",
  name: "AgentNode",
  type: "agent",
  status: "completed",
  startTime: 1700000000000,
  endTime: 1700000001000,
  duration: 1000,
  output: "Agent response",
};

const mockNode2: LangGraphNode = {
  id: "node-2",
  sessionId: "session-123",
  name: "ToolNode",
  type: "tool",
  status: "running",
  startTime: 1700000001000,
};

const mockNodeOtherSession: LangGraphNode = {
  id: "node-3",
  sessionId: "session-456",
  name: "StartNode",
  type: "start",
  status: "completed",
  startTime: 1700000000000,
};

// =============================================================================
// Tests
// =============================================================================

describe("langGraphSlice", () => {
  let initialState: LangGraphState;

  beforeEach(() => {
    initialState = {
      nodes: [],
      currentSessionId: null,
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("initial state", () => {
    it("should have empty nodes array", () => {
      const state = langGraphReducer(undefined, { type: "unknown" });
      expect(state.nodes).toEqual([]);
    });

    it("should have null currentSessionId", () => {
      const state = langGraphReducer(undefined, { type: "unknown" });
      expect(state.currentSessionId).toBeNull();
    });
  });

  describe("addNode", () => {
    it("should add a new node to the state", () => {
      const state = langGraphReducer(initialState, addNode(mockNode));
      expect(state.nodes).toHaveLength(1);
      expect(state.nodes[0]).toEqual(mockNode);
    });

    it("should add multiple nodes", () => {
      let state = langGraphReducer(initialState, addNode(mockNode));
      state = langGraphReducer(state, addNode(mockNode2));
      expect(state.nodes).toHaveLength(2);
    });

    it("should not add duplicate nodes with same id", () => {
      let state = langGraphReducer(initialState, addNode(mockNode));
      state = langGraphReducer(state, addNode(mockNode));
      expect(state.nodes).toHaveLength(1);
    });

    it("should update existing node if id matches", () => {
      const updatedNode = { ...mockNode, status: "error" as const };
      let state = langGraphReducer(initialState, addNode(mockNode));
      state = langGraphReducer(state, addNode(updatedNode));
      expect(state.nodes).toHaveLength(1);
      expect(state.nodes[0].status).toBe("error");
    });
  });

  describe("updateNode", () => {
    it("should update an existing node", () => {
      const state = langGraphReducer(
        { ...initialState, nodes: [mockNode] },
        updateNode({ id: mockNode.id, changes: { status: "error" } }),
      );
      expect(state.nodes[0].status).toBe("error");
    });

    it("should update duration when endTime is set", () => {
      const runningNode = {
        ...mockNode,
        status: "running" as const,
        endTime: undefined,
      };
      const state = langGraphReducer(
        { ...initialState, nodes: [runningNode] },
        updateNode({
          id: runningNode.id,
          changes: { status: "completed", endTime: 1700000002000 },
        }),
      );
      expect(state.nodes[0].status).toBe("completed");
      expect(state.nodes[0].endTime).toBe(1700000002000);
    });

    it("should not modify state if node id not found", () => {
      const state = langGraphReducer(
        { ...initialState, nodes: [mockNode] },
        updateNode({ id: "nonexistent", changes: { status: "error" } }),
      );
      expect(state.nodes[0].status).toBe("completed");
    });
  });

  describe("clearNodes", () => {
    it("should clear all nodes", () => {
      const state = langGraphReducer(
        { ...initialState, nodes: [mockNode, mockNode2] },
        clearNodes(),
      );
      expect(state.nodes).toHaveLength(0);
    });

    it("should clear nodes for specific session when sessionId provided", () => {
      const stateWithNodes = {
        ...initialState,
        nodes: [mockNode, mockNode2, mockNodeOtherSession],
      };
      const state = langGraphReducer(stateWithNodes, clearNodes("session-123"));
      expect(state.nodes).toHaveLength(1);
      expect(state.nodes[0].sessionId).toBe("session-456");
    });
  });

  describe("setCurrentSessionId", () => {
    it("should set current session id", () => {
      const state = langGraphReducer(
        initialState,
        setCurrentSessionId("session-123"),
      );
      expect(state.currentSessionId).toBe("session-123");
    });

    it("should allow setting to null", () => {
      const state = langGraphReducer(
        { ...initialState, currentSessionId: "session-123" },
        setCurrentSessionId(null),
      );
      expect(state.currentSessionId).toBeNull();
    });
  });

  describe("selectors", () => {
    const mockState = {
      langGraph: {
        nodes: [mockNode, mockNode2, mockNodeOtherSession],
        currentSessionId: "session-123",
      },
    };

    describe("selectLangGraphNodes", () => {
      it("should return all nodes", () => {
        const nodes = selectLangGraphNodes(mockState as never);
        expect(nodes).toHaveLength(3);
      });
    });

    describe("selectLangGraphNodesBySession", () => {
      it("should return nodes for specific session", () => {
        const nodes = selectLangGraphNodesBySession(
          mockState as never,
          "session-123",
        );
        expect(nodes).toHaveLength(2);
        expect(nodes.every((n) => n.sessionId === "session-123")).toBe(true);
      });

      it("should return empty array for unknown session", () => {
        const nodes = selectLangGraphNodesBySession(
          mockState as never,
          "unknown",
        );
        expect(nodes).toHaveLength(0);
      });
    });

    describe("selectCurrentSessionNodes", () => {
      it("should return nodes for current session", () => {
        const nodes = selectCurrentSessionNodes(mockState as never);
        expect(nodes).toHaveLength(2);
      });

      it("should return empty array when no current session", () => {
        const stateWithoutSession = {
          langGraph: {
            nodes: [mockNode],
            currentSessionId: null,
          },
        };
        const nodes = selectCurrentSessionNodes(stateWithoutSession as never);
        expect(nodes).toHaveLength(0);
      });
    });
  });
});
