/**
 * MCP Store
 *
 * Zustand store for managing MCP (Model Context Protocol) state including:
 * - Server connections lifecycle
 * - Tool/resource/prompt aggregation
 * - Elicitation handling
 * - Sampling handling
 *
 * This replaces the MCPHostContext useReducer pattern with Zustand.
 */

import { create, StateCreator } from 'zustand';
import type {
  MCPStore,
  MCPState,
  ServerEntry,
  MCPServerConnection,
  MCPConnectionStatus,
  MCPTool,
  MCPResource,
  MCPPrompt,
  PendingElicitation,
  PendingSamplingRequest,
  ElicitationAction,
  AddServerOptions,
  MCPClientCapabilities,
} from '../types/mcp';

/** Default client capabilities */
const DEFAULT_CAPABILITIES: MCPClientCapabilities = {
  elicitation: true,
  sampling: true,
  roots: { listChanged: true },
};

/**
 * Initial MCP state
 */
export const initialMCPState: MCPState = {
  servers: new Map(),
  primaryServerId: null,
  capabilities: DEFAULT_CAPABILITIES,
  pendingElicitations: [],
  pendingSamplingRequests: [],
  isConnecting: false,
  error: null,
};

/**
 * Create the MCP store state and actions
 */
const createMCPStore: StateCreator<MCPStore> = (set, get) => ({
  ...initialMCPState,

  /**
   * Add a server connection
   */
  addServer: async (id: string, url: string, options?: AddServerOptions) => {
    // Create initial server entry
    const serverEntry: ServerEntry = {
      id,
      url,
      status: 'connecting',
      tools: [],
      resources: [],
      prompts: [],
    };

    // Add to map
    set((state) => {
      const newServers = new Map(state.servers);
      newServers.set(id, serverEntry);
      return {
        servers: newServers,
        isConnecting: true,
      };
    });

    try {
      // Initialize connection with server
      const response = await fetch(`${url}/mcp/initialize`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(options?.authToken && { Authorization: `Bearer ${options.authToken}` }),
        },
        body: JSON.stringify({
          protocolVersion: '2025-11-25',
          capabilities: get().capabilities,
          clientInfo: {
            name: 'mcp-server-langgraph-studio',
            version: '1.0.0',
          },
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const data = await response.json();

      // Update server with connection info
      set((state) => {
        const newServers = new Map(state.servers);
        const existing = newServers.get(id);
        if (existing) {
          newServers.set(id, {
            ...existing,
            status: 'connected',
            serverInfo: data.serverInfo,
            capabilities: data.capabilities,
            lastConnected: Date.now(),
          });
        }

        // Set as primary if requested or if first server
        const shouldBePrimary = options?.primary || state.primaryServerId === null;

        return {
          servers: newServers,
          primaryServerId: shouldBePrimary ? id : state.primaryServerId,
          isConnecting: false,
        };
      });
    } catch (error) {
      // Set error status
      set((state) => {
        const newServers = new Map(state.servers);
        const existing = newServers.get(id);
        if (existing) {
          newServers.set(id, {
            ...existing,
            status: 'error',
            error: error instanceof Error ? error.message : 'Connection failed',
          });
        }
        return {
          servers: newServers,
          isConnecting: false,
        };
      });
    }
  },

  /**
   * Remove a server connection
   */
  removeServer: (id: string) => {
    set((state) => {
      const newServers = new Map(state.servers);
      newServers.delete(id);

      return {
        servers: newServers,
        primaryServerId: state.primaryServerId === id ? null : state.primaryServerId,
      };
    });
  },

  /**
   * Set primary server
   */
  setPrimaryServer: (id: string) => {
    set({ primaryServerId: id });
  },

  /**
   * Update server status
   */
  updateServerStatus: (id: string, status: MCPConnectionStatus, error?: string) => {
    set((state) => {
      const server = state.servers.get(id);
      if (!server) return state;

      const newServers = new Map(state.servers);
      newServers.set(id, {
        ...server,
        status,
        error,
        lastConnected: status === 'connected' ? Date.now() : server.lastConnected,
      });

      return { servers: newServers };
    });
  },

  /**
   * Set server tools
   */
  setServerTools: (id: string, tools: MCPTool[]) => {
    set((state) => {
      const server = state.servers.get(id);
      if (!server) return state;

      const newServers = new Map(state.servers);
      newServers.set(id, { ...server, tools });

      return { servers: newServers };
    });
  },

  /**
   * Set server resources
   */
  setServerResources: (id: string, resources: MCPResource[]) => {
    set((state) => {
      const server = state.servers.get(id);
      if (!server) return state;

      const newServers = new Map(state.servers);
      newServers.set(id, { ...server, resources });

      return { servers: newServers };
    });
  },

  /**
   * Set server prompts
   */
  setServerPrompts: (id: string, prompts: MCPPrompt[]) => {
    set((state) => {
      const server = state.servers.get(id);
      if (!server) return state;

      const newServers = new Map(state.servers);
      newServers.set(id, { ...server, prompts });

      return { servers: newServers };
    });
  },

  /**
   * Add elicitation request
   */
  addElicitation: (elicitation: PendingElicitation) => {
    set((state) => ({
      pendingElicitations: [...state.pendingElicitations, elicitation],
    }));
  },

  /**
   * Respond to elicitation
   */
  respondToElicitation: (id: string, action: ElicitationAction, content?: Record<string, unknown>) => {
    // In a real implementation, this would send the response to the server
    // For now, just remove from pending
    set((state) => ({
      pendingElicitations: state.pendingElicitations.filter((e) => e.id !== id),
    }));
  },

  /**
   * Add sampling request
   */
  addSamplingRequest: (request: PendingSamplingRequest) => {
    set((state) => ({
      pendingSamplingRequests: [...state.pendingSamplingRequests, request],
    }));
  },

  /**
   * Respond to sampling
   */
  respondToSampling: (id: string, approved: boolean, result?: unknown) => {
    // In a real implementation, this would send the response to the server
    // For now, just remove from pending
    set((state) => ({
      pendingSamplingRequests: state.pendingSamplingRequests.filter((r) => r.id !== id),
    }));
  },

  /**
   * Get all tools from all servers
   */
  getAllTools: (): MCPTool[] => {
    const { servers } = get();
    const tools: MCPTool[] = [];
    servers.forEach((server) => {
      tools.push(...server.tools);
    });
    return tools;
  },

  /**
   * Get all resources from all servers
   */
  getAllResources: (): MCPResource[] => {
    const { servers } = get();
    const resources: MCPResource[] = [];
    servers.forEach((server) => {
      resources.push(...server.resources);
    });
    return resources;
  },

  /**
   * Get all prompts from all servers
   */
  getAllPrompts: (): MCPPrompt[] => {
    const { servers } = get();
    const prompts: MCPPrompt[] = [];
    servers.forEach((server) => {
      prompts.push(...server.prompts);
    });
    return prompts;
  },

  /**
   * Clear error
   */
  clearError: () => {
    set({ error: null });
  },

  /**
   * Reset state
   */
  reset: () => {
    set({
      servers: new Map(),
      primaryServerId: null,
      pendingElicitations: [],
      pendingSamplingRequests: [],
      isConnecting: false,
      error: null,
    });
  },
});

/**
 * MCP store with Zustand
 */
export const useMCPStore = create<MCPStore>()(createMCPStore);

/**
 * Create a test store without persistence
 */
export const createTestMCPStore = () => create<MCPStore>()(createMCPStore);
