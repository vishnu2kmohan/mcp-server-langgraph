/**
 * BackgroundAgentSlice Tests
 *
 * Phase 7: Integration - State Management
 * Tests for background agent state management.
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import backgroundAgentReducer, {
  addAgent,
  updateAgentStatus,
  updateAgentProgress,
  addAgentArtifact,
  removeAgent,
  clearCompletedAgents,
  resetAgents,
  selectAllAgents,
  selectRunningAgents,
  selectCompletedAgents,
  selectAgentById,
  selectAgentCount,
  selectRunningAgentCount,
  // HITL Extensions
  setAgentAwaitingApproval,
  setAgentAwaitingClarification,
  clearAgentHitlStatus,
  selectAwaitingApprovalAgents,
  selectAwaitingClarificationAgents,
  selectAwaitingHitlAgents,
  selectAwaitingHitlCount,
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

  afterEach(() => {
    vi.clearAllMocks();
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

    it("does not duplicate agentId when adding same agent twice", () => {
      let state = backgroundAgentReducer(initialState, addAgent(mockAgent));
      // Add agent with same ID again
      state = backgroundAgentReducer(
        state,
        addAgent({ ...mockAgent, name: "Updated Name" }),
      );

      // Should not duplicate the ID in agentIds
      expect(state.agentIds).toHaveLength(1);
      expect(state.agentIds.filter((id) => id === "agent-1")).toHaveLength(1);
      // But should update the agent data
      expect(state.agents["agent-1"].name).toBe("Updated Name");
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

    it("sets error message when provided", () => {
      let state = backgroundAgentReducer(initialState, addAgent(mockAgent));
      state = backgroundAgentReducer(
        state,
        updateAgentStatus({
          id: "agent-1",
          status: "failed",
          error: "Connection timeout",
        }),
      );

      expect(state.agents["agent-1"].status).toBe("failed");
      expect(state.agents["agent-1"].error).toBe("Connection timeout");
    });

    it("does not set error when not provided", () => {
      let state = backgroundAgentReducer(initialState, addAgent(mockAgent));
      state = backgroundAgentReducer(
        state,
        updateAgentStatus({ id: "agent-1", status: "running" }),
      );

      expect(state.agents["agent-1"].error).toBeUndefined();
    });

    it("sets completedAt when status is completed", () => {
      let state = backgroundAgentReducer(initialState, addAgent(mockAgent));
      const beforeUpdate = Date.now();
      state = backgroundAgentReducer(
        state,
        updateAgentStatus({ id: "agent-1", status: "completed" }),
      );
      const afterUpdate = Date.now();

      expect(state.agents["agent-1"].completedAt).toBeGreaterThanOrEqual(
        beforeUpdate,
      );
      expect(state.agents["agent-1"].completedAt).toBeLessThanOrEqual(
        afterUpdate,
      );
    });

    it("sets completedAt when status is failed", () => {
      let state = backgroundAgentReducer(initialState, addAgent(mockAgent));
      state = backgroundAgentReducer(
        state,
        updateAgentStatus({ id: "agent-1", status: "failed" }),
      );

      expect(state.agents["agent-1"].completedAt).toBeDefined();
    });

    it("does not set completedAt when status is running", () => {
      let state = backgroundAgentReducer(initialState, addAgent(mockAgent));
      state = backgroundAgentReducer(
        state,
        updateAgentStatus({ id: "agent-1", status: "running" }),
      );

      expect(state.agents["agent-1"].completedAt).toBeUndefined();
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

    it("does nothing for non-existent agent", () => {
      const state = backgroundAgentReducer(
        initialState,
        updateAgentProgress({ id: "non-existent", progress: 50 }),
      );

      expect(state).toEqual(initialState);
    });
  });

  describe("addAgentArtifact", () => {
    it("adds artifact to agent", () => {
      let state = backgroundAgentReducer(initialState, addAgent(mockAgent));
      state = backgroundAgentReducer(
        state,
        addAgentArtifact({ id: "agent-1", artifactId: "artifact-1" }),
      );

      expect(state.agents["agent-1"].artifacts).toContain("artifact-1");
    });

    it("does not add duplicate artifacts", () => {
      const agentWithArtifact = { ...mockAgent, artifacts: ["artifact-1"] };
      let state = backgroundAgentReducer(
        initialState,
        addAgent(agentWithArtifact),
      );
      state = backgroundAgentReducer(
        state,
        addAgentArtifact({ id: "agent-1", artifactId: "artifact-1" }),
      );

      expect(state.agents["agent-1"].artifacts).toHaveLength(1);
    });

    it("does nothing for non-existent agent", () => {
      const state = backgroundAgentReducer(
        initialState,
        addAgentArtifact({ id: "non-existent", artifactId: "artifact-1" }),
      );

      expect(state).toEqual(initialState);
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

  describe("resetAgents", () => {
    it("resets to initial state", () => {
      let state = backgroundAgentReducer(initialState, addAgent(mockAgent));
      state = backgroundAgentReducer(state, resetAgents());

      expect(state.agents).toEqual({});
      expect(state.agentIds).toEqual([]);
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

    it("selectCompletedAgents returns only completed agents", () => {
      const completed = selectCompletedAgents(stateWithAgents);
      expect(completed).toHaveLength(1);
      expect(completed[0].id).toBe("agent-2");
    });

    it("selectAgentCount returns total agent count", () => {
      const count = selectAgentCount(stateWithAgents);
      expect(count).toBe(3);
    });

    it("selectRunningAgentCount returns running agent count", () => {
      const count = selectRunningAgentCount(stateWithAgents);
      expect(count).toBe(2);
    });

    describe("memoization", () => {
      it("selectAllAgents returns same reference for unchanged state", () => {
        const result1 = selectAllAgents(stateWithAgents);
        const result2 = selectAllAgents(stateWithAgents);

        // With memoization, the same reference should be returned
        expect(result1).toBe(result2);
      });

      it("selectAllAgents returns different reference when state changes", () => {
        const result1 = selectAllAgents(stateWithAgents);

        // Create a new state with a new agent
        const newState = {
          backgroundAgent: {
            ...stateWithAgents.backgroundAgent,
            agentIds: [...stateWithAgents.backgroundAgent.agentIds, "agent-4"],
            agents: {
              ...stateWithAgents.backgroundAgent.agents,
              "agent-4": {
                ...mockAgent,
                id: "agent-4",
                status: "running" as const,
              },
            },
          },
        };

        const result2 = selectAllAgents(newState);

        // With memoization, a new reference should be returned when state changes
        expect(result1).not.toBe(result2);
        expect(result2).toHaveLength(4);
      });

      it("selectRunningAgents returns same reference for unchanged state", () => {
        const result1 = selectRunningAgents(stateWithAgents);
        const result2 = selectRunningAgents(stateWithAgents);

        // With memoization, the same reference should be returned
        expect(result1).toBe(result2);
      });
    });
  });

  // =========================================================================
  // Phase 8: HITL Extensions Tests
  // =========================================================================
  describe("HITL Extensions", () => {
    describe("AgentStatus type", () => {
      it("includes awaiting_approval status", () => {
        const agentWithApproval: BackgroundAgent = {
          ...mockAgent,
          status: "awaiting_approval",
        };
        const state = backgroundAgentReducer(
          initialState,
          addAgent(agentWithApproval),
        );
        expect(state.agents["agent-1"].status).toBe("awaiting_approval");
      });

      it("includes awaiting_clarification status", () => {
        const agentWithClarification: BackgroundAgent = {
          ...mockAgent,
          status: "awaiting_clarification",
        };
        const state = backgroundAgentReducer(
          initialState,
          addAgent(agentWithClarification),
        );
        expect(state.agents["agent-1"].status).toBe("awaiting_clarification");
      });
    });

    describe("BackgroundAgent HITL fields", () => {
      it("supports optional confidence field", () => {
        const agentWithConfidence: BackgroundAgent = {
          ...mockAgent,
          confidence: 0.65,
        };
        const state = backgroundAgentReducer(
          initialState,
          addAgent(agentWithConfidence),
        );
        expect(state.agents["agent-1"].confidence).toBe(0.65);
      });

      it("supports optional approvalId field", () => {
        const agentWithApproval: BackgroundAgent = {
          ...mockAgent,
          status: "awaiting_approval",
          approvalId: "approval_123",
        };
        const state = backgroundAgentReducer(
          initialState,
          addAgent(agentWithApproval),
        );
        expect(state.agents["agent-1"].approvalId).toBe("approval_123");
      });

      it("supports optional approvalReason field", () => {
        const agentWithApproval: BackgroundAgent = {
          ...mockAgent,
          status: "awaiting_approval",
          approvalReason: "low_confidence",
        };
        const state = backgroundAgentReducer(
          initialState,
          addAgent(agentWithApproval),
        );
        expect(state.agents["agent-1"].approvalReason).toBe("low_confidence");
      });

      it("supports optional threshold field", () => {
        const agentWithThreshold: BackgroundAgent = {
          ...mockAgent,
          threshold: 0.7,
        };
        const state = backgroundAgentReducer(
          initialState,
          addAgent(agentWithThreshold),
        );
        expect(state.agents["agent-1"].threshold).toBe(0.7);
      });
    });

    describe("setAgentAwaitingApproval action", () => {
      it("sets agent status to awaiting_approval", () => {
        let state = backgroundAgentReducer(initialState, addAgent(mockAgent));
        state = backgroundAgentReducer(
          state,
          setAgentAwaitingApproval({
            id: "agent-1",
            approvalId: "approval_123",
            confidence: 0.65,
            reason: "low_confidence",
          }),
        );

        expect(state.agents["agent-1"].status).toBe("awaiting_approval");
        expect(state.agents["agent-1"].approvalId).toBe("approval_123");
        expect(state.agents["agent-1"].confidence).toBe(0.65);
        expect(state.agents["agent-1"].approvalReason).toBe("low_confidence");
      });

      it("does nothing for non-existent agent", () => {
        const state = backgroundAgentReducer(
          initialState,
          setAgentAwaitingApproval({
            id: "non-existent",
            approvalId: "approval_123",
            confidence: 0.65,
            reason: "low_confidence",
          }),
        );

        expect(state).toEqual(initialState);
      });
    });

    describe("setAgentAwaitingClarification action", () => {
      it("sets agent status to awaiting_clarification", () => {
        let state = backgroundAgentReducer(initialState, addAgent(mockAgent));
        state = backgroundAgentReducer(
          state,
          setAgentAwaitingClarification({
            id: "agent-1",
            requestId: "clarify_123",
            question: "Which format?",
          }),
        );

        expect(state.agents["agent-1"].status).toBe("awaiting_clarification");
        expect(state.agents["agent-1"].clarificationRequestId).toBe(
          "clarify_123",
        );
        expect(state.agents["agent-1"].clarificationQuestion).toBe(
          "Which format?",
        );
      });

      it("does nothing for non-existent agent", () => {
        const state = backgroundAgentReducer(
          initialState,
          setAgentAwaitingClarification({
            id: "non-existent",
            requestId: "clarify_123",
            question: "Which format?",
          }),
        );

        expect(state).toEqual(initialState);
      });
    });

    describe("clearAgentHitlStatus action", () => {
      it("clears HITL fields and sets status to running", () => {
        const agentWithHitl: BackgroundAgent = {
          ...mockAgent,
          status: "awaiting_approval",
          approvalId: "approval_123",
          confidence: 0.65,
          approvalReason: "low_confidence",
        };
        let state = backgroundAgentReducer(
          initialState,
          addAgent(agentWithHitl),
        );
        state = backgroundAgentReducer(state, clearAgentHitlStatus("agent-1"));

        expect(state.agents["agent-1"].status).toBe("running");
        expect(state.agents["agent-1"].approvalId).toBeUndefined();
        expect(state.agents["agent-1"].approvalReason).toBeUndefined();
        expect(state.agents["agent-1"].clarificationRequestId).toBeUndefined();
        expect(state.agents["agent-1"].clarificationQuestion).toBeUndefined();
        // Confidence may be preserved for display
      });
    });

    describe("HITL selectors", () => {
      const stateWithHitlAgents = {
        backgroundAgent: {
          agents: {
            "agent-1": { ...mockAgent, status: "running" as const },
            "agent-2": {
              ...mockAgent,
              id: "agent-2",
              status: "awaiting_approval" as const,
              approvalId: "approval_123",
              confidence: 0.65,
            },
            "agent-3": {
              ...mockAgent,
              id: "agent-3",
              status: "awaiting_clarification" as const,
              clarificationRequestId: "clarify_456",
            },
            "agent-4": {
              ...mockAgent,
              id: "agent-4",
              status: "completed" as const,
            },
          },
          agentIds: ["agent-1", "agent-2", "agent-3", "agent-4"],
        },
      };

      it("selectAwaitingApprovalAgents returns agents awaiting approval", () => {
        const awaiting = selectAwaitingApprovalAgents(stateWithHitlAgents);
        expect(awaiting).toHaveLength(1);
        expect(awaiting[0].id).toBe("agent-2");
        expect(awaiting[0].status).toBe("awaiting_approval");
      });

      it("selectAwaitingClarificationAgents returns agents awaiting clarification", () => {
        const awaiting = selectAwaitingClarificationAgents(stateWithHitlAgents);
        expect(awaiting).toHaveLength(1);
        expect(awaiting[0].id).toBe("agent-3");
        expect(awaiting[0].status).toBe("awaiting_clarification");
      });

      it("selectAwaitingHitlAgents returns all agents needing user input", () => {
        const awaiting = selectAwaitingHitlAgents(stateWithHitlAgents);
        expect(awaiting).toHaveLength(2);
        expect(awaiting.some((a) => a.id === "agent-2")).toBe(true);
        expect(awaiting.some((a) => a.id === "agent-3")).toBe(true);
      });

      it("selectAwaitingHitlCount returns count of agents needing input", () => {
        const count = selectAwaitingHitlCount(stateWithHitlAgents);
        expect(count).toBe(2);
      });
    });
  });
});
