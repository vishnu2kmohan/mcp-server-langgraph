/**
 * BackgroundAgentSlice - Phase 7
 *
 * State management for background AI agents.
 * Tracks agent status, progress, and artifacts.
 *
 * WebSocket events from /ws/v1/agents update this slice.
 */
import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

// =============================================================================
// Types
// =============================================================================

export type AgentStatus = "queued" | "running" | "completed" | "failed";

export interface BackgroundAgent {
  id: string;
  name: string;
  task: string;
  status: AgentStatus;
  progress: number;
  artifacts: string[];
  startedAt: number;
  completedAt?: number;
  error?: string;
}

export interface BackgroundAgentState {
  /** Normalized agents by ID */
  agents: Record<string, BackgroundAgent>;
  /** Ordered list of agent IDs */
  agentIds: string[];
}

// =============================================================================
// Initial State
// =============================================================================

const initialState: BackgroundAgentState = {
  agents: {},
  agentIds: [],
};

// =============================================================================
// Slice
// =============================================================================

const backgroundAgentSlice = createSlice({
  name: "backgroundAgent",
  initialState,
  reducers: {
    /**
     * Add a new background agent
     */
    addAgent(state, action: PayloadAction<BackgroundAgent>) {
      const agent = action.payload;
      state.agents[agent.id] = agent;
      if (!state.agentIds.includes(agent.id)) {
        state.agentIds.push(agent.id);
      }
    },

    /**
     * Update agent status
     */
    updateAgentStatus(
      state,
      action: PayloadAction<{
        id: string;
        status: AgentStatus;
        error?: string;
      }>,
    ) {
      const { id, status, error } = action.payload;
      const agent = state.agents[id];
      if (agent) {
        agent.status = status;
        if (error) {
          agent.error = error;
        }
        if (status === "completed" || status === "failed") {
          agent.completedAt = Date.now();
        }
      }
    },

    /**
     * Update agent progress (clamped 0-100)
     */
    updateAgentProgress(
      state,
      action: PayloadAction<{ id: string; progress: number }>,
    ) {
      const { id, progress } = action.payload;
      const agent = state.agents[id];
      if (agent) {
        agent.progress = Math.max(0, Math.min(100, progress));
      }
    },

    /**
     * Add artifact to agent
     */
    addAgentArtifact(
      state,
      action: PayloadAction<{ id: string; artifactId: string }>,
    ) {
      const { id, artifactId } = action.payload;
      const agent = state.agents[id];
      if (agent && !agent.artifacts.includes(artifactId)) {
        agent.artifacts.push(artifactId);
      }
    },

    /**
     * Remove an agent
     */
    removeAgent(state, action: PayloadAction<string>) {
      const id = action.payload;
      delete state.agents[id];
      state.agentIds = state.agentIds.filter((agentId) => agentId !== id);
    },

    /**
     * Clear completed and failed agents
     */
    clearCompletedAgents(state) {
      const toRemove = state.agentIds.filter((id) => {
        const status = state.agents[id]?.status;
        return status === "completed" || status === "failed";
      });
      toRemove.forEach((id) => {
        delete state.agents[id];
      });
      state.agentIds = state.agentIds.filter((id) => !toRemove.includes(id));
    },

    /**
     * Reset all agents
     */
    resetAgents() {
      return initialState;
    },
  },
});

// =============================================================================
// Selectors
// =============================================================================

type StateWithBackgroundAgent = { backgroundAgent: BackgroundAgentState };

export const selectAllAgents = (
  state: StateWithBackgroundAgent,
): BackgroundAgent[] =>
  state.backgroundAgent.agentIds.map((id) => state.backgroundAgent.agents[id]);

export const selectRunningAgents = (
  state: StateWithBackgroundAgent,
): BackgroundAgent[] =>
  selectAllAgents(state).filter(
    (agent) => agent.status === "running" || agent.status === "queued",
  );

export const selectCompletedAgents = (
  state: StateWithBackgroundAgent,
): BackgroundAgent[] =>
  selectAllAgents(state).filter((agent) => agent.status === "completed");

export const selectAgentById = (
  state: StateWithBackgroundAgent,
  id: string,
): BackgroundAgent | undefined => state.backgroundAgent.agents[id];

export const selectAgentCount = (state: StateWithBackgroundAgent): number =>
  state.backgroundAgent.agentIds.length;

export const selectRunningAgentCount = (
  state: StateWithBackgroundAgent,
): number => selectRunningAgents(state).length;

// =============================================================================
// Exports
// =============================================================================

export const {
  addAgent,
  updateAgentStatus,
  updateAgentProgress,
  addAgentArtifact,
  removeAgent,
  clearCompletedAgents,
  resetAgents,
} = backgroundAgentSlice.actions;

export default backgroundAgentSlice.reducer;
