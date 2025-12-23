/**
 * BackgroundAgentSlice - Phase 7
 *
 * State management for background AI agents.
 * Tracks agent status, progress, and artifacts.
 *
 * WebSocket events from /ws/v1/agents update this slice.
 */
import {
  createSlice,
  createSelector,
  type PayloadAction,
} from "@reduxjs/toolkit";

// =============================================================================
// Types
// =============================================================================

export type AgentStatus =
  | "queued"
  | "running"
  | "completed"
  | "failed"
  | "awaiting_approval"
  | "awaiting_clarification";

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
  // HITL fields
  /** Confidence score from agent (0-1) */
  confidence?: number;
  /** Threshold that triggered HITL */
  threshold?: number;
  /** ID of the approval request */
  approvalId?: string;
  /** Reason for requiring approval */
  approvalReason?: string;
  /** ID of the clarification request */
  clarificationRequestId?: string;
  /** Question being asked for clarification */
  clarificationQuestion?: string;
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

    // =========================================================================
    // HITL Actions
    // =========================================================================

    /**
     * Set agent status to awaiting_approval with HITL context
     */
    setAgentAwaitingApproval(
      state,
      action: PayloadAction<{
        id: string;
        approvalId: string;
        confidence: number;
        reason: string;
      }>,
    ) {
      const { id, approvalId, confidence, reason } = action.payload;
      const agent = state.agents[id];
      if (agent) {
        agent.status = "awaiting_approval";
        agent.approvalId = approvalId;
        agent.confidence = confidence;
        agent.approvalReason = reason;
      }
    },

    /**
     * Set agent status to awaiting_clarification with HITL context
     */
    setAgentAwaitingClarification(
      state,
      action: PayloadAction<{
        id: string;
        requestId: string;
        question: string;
      }>,
    ) {
      const { id, requestId, question } = action.payload;
      const agent = state.agents[id];
      if (agent) {
        agent.status = "awaiting_clarification";
        agent.clarificationRequestId = requestId;
        agent.clarificationQuestion = question;
      }
    },

    /**
     * Clear HITL fields and resume agent to running status
     */
    clearAgentHitlStatus(state, action: PayloadAction<string>) {
      const id = action.payload;
      const agent = state.agents[id];
      if (agent) {
        agent.status = "running";
        agent.approvalId = undefined;
        agent.approvalReason = undefined;
        agent.clarificationRequestId = undefined;
        agent.clarificationQuestion = undefined;
        // Note: confidence may be preserved for display
      }
    },
  },
});

// =============================================================================
// Selectors (Memoized with createSelector)
// =============================================================================

type StateWithBackgroundAgent = { backgroundAgent: BackgroundAgentState };

// Base selectors (not memoized - simple property access)
const selectAgentIds = (state: StateWithBackgroundAgent) =>
  state.backgroundAgent.agentIds;

const selectAgentsMap = (state: StateWithBackgroundAgent) =>
  state.backgroundAgent.agents;

/**
 * Select all agents as an array (memoized)
 * Only recomputes when agentIds or agents map changes
 */
export const selectAllAgents = createSelector(
  [selectAgentIds, selectAgentsMap],
  (agentIds, agents): BackgroundAgent[] => {
    const result: BackgroundAgent[] = [];
    for (const id of agentIds) {
      const agent = agents[id];
      if (agent) result.push(agent);
    }
    return result;
  },
);

/**
 * Select running and queued agents (memoized)
 * Only recomputes when selectAllAgents result changes
 */
export const selectRunningAgents = createSelector(
  [selectAllAgents],
  (agents): BackgroundAgent[] =>
    agents.filter(
      (agent) => agent.status === "running" || agent.status === "queued",
    ),
);

/**
 * Select completed agents (memoized)
 * Only recomputes when selectAllAgents result changes
 */
export const selectCompletedAgents = createSelector(
  [selectAllAgents],
  (agents): BackgroundAgent[] =>
    agents.filter((agent) => agent.status === "completed"),
);

/**
 * Select agent by ID (not memoized - simple property access)
 */
export const selectAgentById = (
  state: StateWithBackgroundAgent,
  id: string,
): BackgroundAgent | undefined => state.backgroundAgent.agents[id];

/**
 * Select total agent count (memoized)
 */
export const selectAgentCount = createSelector(
  [selectAgentIds],
  (agentIds): number => agentIds.length,
);

/**
 * Select running agent count (memoized)
 */
export const selectRunningAgentCount = createSelector(
  [selectRunningAgents],
  (runningAgents): number => runningAgents.length,
);

// =============================================================================
// HITL Selectors (Memoized with createSelector)
// =============================================================================

/**
 * Select agents awaiting approval (memoized)
 */
export const selectAwaitingApprovalAgents = createSelector(
  [selectAllAgents],
  (agents): BackgroundAgent[] =>
    agents.filter((agent) => agent.status === "awaiting_approval"),
);

/**
 * Select agents awaiting clarification (memoized)
 */
export const selectAwaitingClarificationAgents = createSelector(
  [selectAllAgents],
  (agents): BackgroundAgent[] =>
    agents.filter((agent) => agent.status === "awaiting_clarification"),
);

/**
 * Select all agents needing HITL input (approval or clarification) (memoized)
 */
export const selectAwaitingHitlAgents = createSelector(
  [selectAllAgents],
  (agents): BackgroundAgent[] =>
    agents.filter(
      (agent) =>
        agent.status === "awaiting_approval" ||
        agent.status === "awaiting_clarification",
    ),
);

/**
 * Select count of agents needing HITL input (memoized)
 */
export const selectAwaitingHitlCount = createSelector(
  [selectAwaitingHitlAgents],
  (hitlAgents): number => hitlAgents.length,
);

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
  // HITL actions
  setAgentAwaitingApproval,
  setAgentAwaitingClarification,
  clearAgentHitlStatus,
} = backgroundAgentSlice.actions;

export default backgroundAgentSlice.reducer;
