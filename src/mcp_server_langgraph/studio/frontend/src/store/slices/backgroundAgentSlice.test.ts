/**
 * BackgroundAgentSlice Tests
 *
 * Phase 7: Integration - State Management
 * Tests for background agent state management.
 */
import { describe, it, expect, beforeEach } from "vitest";
import backgroundAgentReducer, {
  addAgent,
  updateAgentStatus,
  updateAgentProgress,
  removeAgent,
  clearCompletedAgents,
  selectAllAgents,
  selectRunningAgents,
  selectAgentById,
  type BackgroundAgent,
  type BackgroundAgentState,
} from "./backgroundAgentSlice";

describe("backgroundAgentSlice", () => {
  const mockAgent: BackgroundAgent = {
    id: "agent-1",
    name: "Data Processor",
    task: "Processing dataset",
    status: "queued",
    progress: 0,
    artifacts: [],
    startedAt: Date.now(),
  };

  let initialState: BackgroundAgentState;

  beforeEach(() => {
    initialState = {
      agents: {},
      agentIds: [],
    };
  });

  describe("addAgent", () => {
    it("adds a new agent to state", () => {
      const state = backgroundAgentReducer(initialState, addAgent(mockAgent));

      expect(state.agents["agent-1"]).toEqual(mockAgent);
      expect(state.agentIds).toContain("agent-1");
    });

    it("adds multiple agents", () => {
      const agent2: BackgroundAgent = {
        ...mockAgent,
        id: "agent-2",
        name: "Code Generator",
      };

      let state = backgroundAgentReducer(initialState, addAgent(mockAgent));
      state = backgroundAgentReducer(state, addAgent(agent2));

      expect(Object.keys(state.agents)).toHaveLength(2);
      expect(state.agentIds).toHaveLength(2);
    });
  });

  describe("updateAgentStatus", () => {
    it("updates agent status", () => {
      let state = backgroundAgentReducer(initialState, addAgent(mockAgent));
      state = backgroundAgentReducer(
        state,
        updateAgentStatus({ id: "agent-1", status: "running" }),
      );

      expect(state.agents["agent-1"].status).toBe("running");
    });

    it("does nothing for non-existent agent", () => {
      const state = backgroundAgentReducer(
        initialState,
        updateAgentStatus({ id: "non-existent", status: "running" }),
      );

      expect(state).toEqual(initialState);
    });
  });

  describe("updateAgentProgress", () => {
    it("updates agent progress", () => {
      let state = backgroundAgentReducer(initialState, addAgent(mockAgent));
      state = backgroundAgentReducer(
        state,
        updateAgentProgress({ id: "agent-1", progress: 50 }),
      );

      expect(state.agents["agent-1"].progress).toBe(50);
    });

    it("clamps progress between 0 and 100", () => {
      let state = backgroundAgentReducer(initialState, addAgent(mockAgent));

      state = backgroundAgentReducer(
        state,
        updateAgentProgress({ id: "agent-1", progress: 150 }),
      );
      expect(state.agents["agent-1"].progress).toBe(100);

      state = backgroundAgentReducer(
        state,
        updateAgentProgress({ id: "agent-1", progress: -10 }),
      );
      expect(state.agents["agent-1"].progress).toBe(0);
    });
  });

  describe("removeAgent", () => {
    it("removes an agent from state", () => {
      let state = backgroundAgentReducer(initialState, addAgent(mockAgent));
      state = backgroundAgentReducer(state, removeAgent("agent-1"));

      expect(state.agents["agent-1"]).toBeUndefined();
      expect(state.agentIds).not.toContain("agent-1");
    });
  });

  describe("clearCompletedAgents", () => {
    it("removes all completed and failed agents", () => {
      const runningAgent: BackgroundAgent = {
        ...mockAgent,
        id: "running",
        status: "running",
      };
      const completedAgent: BackgroundAgent = {
        ...mockAgent,
        id: "completed",
        status: "completed",
      };
      const failedAgent: BackgroundAgent = {
        ...mockAgent,
        id: "failed",
        status: "failed",
      };

      let state = backgroundAgentReducer(initialState, addAgent(runningAgent));
      state = backgroundAgentReducer(state, addAgent(completedAgent));
      state = backgroundAgentReducer(state, addAgent(failedAgent));
      state = backgroundAgentReducer(state, clearCompletedAgents());

      expect(state.agentIds).toContain("running");
      expect(state.agentIds).not.toContain("completed");
      expect(state.agentIds).not.toContain("failed");
    });
  });

  describe("Selectors", () => {
    const stateWithAgents = {
      backgroundAgent: {
        agents: {
          "agent-1": { ...mockAgent, status: "running" as const },
          "agent-2": {
            ...mockAgent,
            id: "agent-2",
            status: "completed" as const,
          },
          "agent-3": { ...mockAgent, id: "agent-3", status: "queued" as const },
        },
        agentIds: ["agent-1", "agent-2", "agent-3"],
      },
    };

    it("selectAllAgents returns all agents as array", () => {
      const agents = selectAllAgents(stateWithAgents);
      expect(agents).toHaveLength(3);
    });

    it("selectRunningAgents returns only running/queued agents", () => {
      const running = selectRunningAgents(stateWithAgents);
      expect(running).toHaveLength(2);
      expect(
        running.every((a) => ["running", "queued"].includes(a.status)),
      ).toBe(true);
    });

    it("selectAgentById returns specific agent", () => {
      const agent = selectAgentById(stateWithAgents, "agent-1");
      expect(agent?.id).toBe("agent-1");
    });

    it("selectAgentById returns undefined for non-existent", () => {
      const agent = selectAgentById(stateWithAgents, "non-existent");
      expect(agent).toBeUndefined();
    });
  });
});
