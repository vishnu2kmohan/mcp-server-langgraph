/**
 * MCP Slice
 *
 * Redux slice for managing MCP (Model Context Protocol) state including:
 * - Server connections lifecycle
 * - Tool/resource/prompt aggregation
 * - Elicitation handling
 * - Sampling handling
 */

import {
  createSlice,
  createAsyncThunk,
  createSelector,
  PayloadAction,
} from "@reduxjs/toolkit";
import type { RootState } from "../index";
import type {
  ServerEntry,
  MCPConnectionStatus,
  MCPTool,
  MCPResource,
  MCPPrompt,
  PendingElicitation,
  PendingSamplingRequest,
  MCPClientCapabilities,
  MCPServerInfo,
  MCPServerCapabilities,
  JSONRPCId,
} from "../../types/mcp";

// ============================================================================
// Constants
// ============================================================================

/** Default client capabilities */
const DEFAULT_CAPABILITIES: MCPClientCapabilities = {
  elicitation: true,
  sampling: true,
  roots: { listChanged: true },
};

// ============================================================================
// State Type (Redux-compatible - using Record instead of Map)
// ============================================================================

export interface MCPSliceState {
  /** Connected servers (Record instead of Map for serialization) */
  servers: Record<string, ServerEntry>;

  /** Primary server ID */
  primaryServerId: string | null;

  /** Client capabilities */
  capabilities: MCPClientCapabilities;

  /** Pending elicitation requests */
  pendingElicitations: PendingElicitation[];

  /** Pending sampling requests */
  pendingSamplingRequests: PendingSamplingRequest[];

  /** Whether initial connection is in progress */
  isConnecting: boolean;

  /** Global error */
  error: string | null;
}

// ============================================================================
// Initial State
// ============================================================================

export const initialMCPState: MCPSliceState = {
  servers: {},
  primaryServerId: null,
  capabilities: DEFAULT_CAPABILITIES,
  pendingElicitations: [],
  pendingSamplingRequests: [],
  isConnecting: false,
  error: null,
};

// ============================================================================
// Async Thunks
// ============================================================================

export const addServer = createAsyncThunk<
  { id: string; serverInfo?: unknown; capabilities?: unknown },
  { id: string; url: string; primary?: boolean; authToken?: string },
  { state: RootState; rejectValue: { id: string; error: string } }
>(
  "mcp/addServer",
  async ({ id, url, authToken }, { getState, rejectWithValue }) => {
    try {
      const response = await fetch(`${url}/mcp/initialize`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(authToken && { Authorization: `Bearer ${authToken}` }),
        },
        body: JSON.stringify({
          protocolVersion: "2025-11-25",
          capabilities: getState().mcp.capabilities,
          clientInfo: {
            name: "agent-studio",
            version: "1.0.0",
          },
        }),
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      return {
        id,
        serverInfo: data.serverInfo,
        capabilities: data.capabilities,
      };
    } catch (error) {
      return rejectWithValue({
        id,
        error: error instanceof Error ? error.message : "Connection failed",
      });
    }
  },
);

// ============================================================================
// Slice
// ============================================================================

export const mcpSlice = createSlice({
  name: "mcp",
  initialState: initialMCPState,
  reducers: {
    removeServer: (state, action: PayloadAction<string>) => {
      const id = action.payload;
      delete state.servers[id];
      if (state.primaryServerId === id) {
        state.primaryServerId = null;
      }
    },

    setPrimaryServer: (state, action: PayloadAction<string>) => {
      state.primaryServerId = action.payload;
    },

    updateServerStatus: (
      state,
      action: PayloadAction<{
        id: string;
        status: MCPConnectionStatus;
        error?: string;
      }>,
    ) => {
      const { id, status, error } = action.payload;
      const server = state.servers[id];
      if (server) {
        server.status = status;
        server.error = error;
        if (status === "connected") {
          server.lastConnected = Date.now();
        }
      }
    },

    setServerTools: (
      state,
      action: PayloadAction<{ id: string; tools: MCPTool[] }>,
    ) => {
      const { id, tools } = action.payload;
      const server = state.servers[id];
      if (server) {
        server.tools = tools;
      }
    },

    setServerResources: (
      state,
      action: PayloadAction<{ id: string; resources: MCPResource[] }>,
    ) => {
      const { id, resources } = action.payload;
      const server = state.servers[id];
      if (server) {
        server.resources = resources;
      }
    },

    setServerPrompts: (
      state,
      action: PayloadAction<{ id: string; prompts: MCPPrompt[] }>,
    ) => {
      const { id, prompts } = action.payload;
      const server = state.servers[id];
      if (server) {
        server.prompts = prompts;
      }
    },

    addElicitation: (state, action: PayloadAction<PendingElicitation>) => {
      state.pendingElicitations.push(action.payload);
    },

    respondToElicitation: (state, action: PayloadAction<JSONRPCId>) => {
      const id = action.payload;
      state.pendingElicitations = state.pendingElicitations.filter(
        (e) => e.id !== id,
      );
    },

    addSamplingRequest: (
      state,
      action: PayloadAction<PendingSamplingRequest>,
    ) => {
      state.pendingSamplingRequests.push(action.payload);
    },

    respondToSampling: (state, action: PayloadAction<JSONRPCId>) => {
      const id = action.payload;
      state.pendingSamplingRequests = state.pendingSamplingRequests.filter(
        (r) => r.id !== id,
      );
    },

    clearMCPError: (state) => {
      state.error = null;
    },

    resetMCP: (state) => {
      state.servers = {};
      state.primaryServerId = null;
      state.pendingElicitations = [];
      state.pendingSamplingRequests = [];
      state.isConnecting = false;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(addServer.pending, (state, action) => {
        const { id, url, primary } = action.meta.arg;
        // Create initial server entry
        state.servers[id] = {
          id,
          url,
          status: "connecting",
          tools: [],
          resources: [],
          prompts: [],
        };
        state.isConnecting = true;

        // Set as primary if requested or if first server
        if (primary || state.primaryServerId === null) {
          state.primaryServerId = id;
        }
      })
      .addCase(addServer.fulfilled, (state, action) => {
        const { id, serverInfo, capabilities } = action.payload;
        const server = state.servers[id];
        if (server) {
          server.status = "connected";
          server.serverInfo = serverInfo as MCPServerInfo | undefined;
          server.capabilities = capabilities as
            | MCPServerCapabilities
            | undefined;
          server.lastConnected = Date.now();
        }
        state.isConnecting = false;
      })
      .addCase(addServer.rejected, (state, action) => {
        if (action.payload) {
          const { id, error } = action.payload;
          const server = state.servers[id];
          if (server) {
            server.status = "error";
            server.error = error;
          }
        }
        state.isConnecting = false;
      });
  },
});

// ============================================================================
// Actions
// ============================================================================

export const {
  removeServer,
  setPrimaryServer,
  updateServerStatus,
  setServerTools,
  setServerResources,
  setServerPrompts,
  addElicitation,
  respondToElicitation,
  addSamplingRequest,
  respondToSampling,
  clearMCPError,
  resetMCP,
} = mcpSlice.actions;

// ============================================================================
// Selectors
// ============================================================================

export const selectServers = (state: RootState) => state.mcp.servers;
export const selectPrimaryServerId = (state: RootState) =>
  state.mcp.primaryServerId;
export const selectMCPCapabilities = (state: RootState) =>
  state.mcp.capabilities;
export const selectPendingElicitations = (state: RootState) =>
  state.mcp.pendingElicitations;
export const selectPendingSamplingRequests = (state: RootState) =>
  state.mcp.pendingSamplingRequests;
export const selectIsConnecting = (state: RootState) => state.mcp.isConnecting;
export const selectMCPError = (state: RootState) => state.mcp.error;

export const selectServerById = (id: string) => (state: RootState) =>
  state.mcp.servers[id];

// Memoized selectors to prevent unnecessary re-renders
export const selectServerList = createSelector(
  [selectServers],
  (servers): ServerEntry[] => Object.values(servers),
);

export const selectAllTools = createSelector(
  [selectServers],
  (servers): MCPTool[] => {
    const tools: MCPTool[] = [];
    Object.values(servers).forEach((server) => {
      tools.push(...server.tools);
    });
    return tools;
  },
);

export const selectAllResources = createSelector(
  [selectServers],
  (servers): MCPResource[] => {
    const resources: MCPResource[] = [];
    Object.values(servers).forEach((server) => {
      resources.push(...server.resources);
    });
    return resources;
  },
);

export const selectAllPrompts = createSelector(
  [selectServers],
  (servers): MCPPrompt[] => {
    const prompts: MCPPrompt[] = [];
    Object.values(servers).forEach((server) => {
      prompts.push(...server.prompts);
    });
    return prompts;
  },
);

export const selectIsConnected = createSelector(
  [selectServers],
  (servers): boolean => {
    return Object.values(servers).some((s) => s.status === "connected");
  },
);

// ============================================================================
// Export
// ============================================================================

export default mcpSlice.reducer;
