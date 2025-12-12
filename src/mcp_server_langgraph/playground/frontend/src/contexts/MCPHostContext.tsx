/**
 * MCP Host Context
 *
 * React context for managing multiple MCP server connections.
 * Acts as the MCP Host that coordinates between the frontend
 * and multiple MCP servers.
 */

import React, {
  createContext,
  useContext,
  useReducer,
  useCallback,
  useMemo,
  useEffect,
  useRef,
  ReactNode,
} from 'react';
import { createMCPClient, MCPClient } from '../api/mcp-client';
import type {
  MCPTool,
  MCPResource,
  MCPPrompt,
  MCPServerConnection,
  MCPConnectionStatus,
  PendingElicitation,
  PendingSamplingRequest,
  ElicitationAction,
} from '../api/mcp-types';

// =============================================================================
// Types
// =============================================================================

export interface MCPClientCapabilitiesConfig {
  elicitation: boolean;
  sampling: boolean;
  roots: { listChanged: boolean };
}

interface ServerEntry extends MCPServerConnection {
  client: MCPClient;
  tools: MCPTool[];
  resources: MCPResource[];
  prompts: MCPPrompt[];
}

interface AddServerOptions {
  primary?: boolean;
  authToken?: string;
}

export interface MCPHostContextValue {
  // Server management
  servers: Map<string, MCPServerConnection>;
  primaryServerId: string | null;
  addServer: (id: string, url: string, options?: AddServerOptions) => Promise<void>;
  removeServer: (id: string) => void;
  setPrimaryServer: (id: string) => void;

  // Aggregated capabilities from all servers
  allTools: MCPTool[];
  allResources: MCPResource[];
  allPrompts: MCPPrompt[];

  // Client capabilities (what this host supports)
  capabilities: MCPClientCapabilitiesConfig;

  // Pending requests from servers
  pendingElicitations: PendingElicitation[];
  pendingSamplingRequests: PendingSamplingRequest[];

  // Elicitation handlers
  addElicitation: (elicitation: PendingElicitation) => void;
  respondToElicitation: (
    id: string,
    action: ElicitationAction,
    content?: Record<string, unknown>
  ) => void;

  // Sampling handlers
  addSamplingRequest: (request: PendingSamplingRequest) => void;
  respondToSampling: (id: string, approved: boolean, result?: unknown) => void;

  // Get client for specific server
  getClient: (serverId: string) => MCPClient | null;
}

// =============================================================================
// State
// =============================================================================

interface MCPHostState {
  servers: Map<string, ServerEntry>;
  primaryServerId: string | null;
  pendingElicitations: PendingElicitation[];
  pendingSamplingRequests: PendingSamplingRequest[];
}

type MCPHostAction =
  | { type: 'ADD_SERVER'; payload: { id: string; entry: ServerEntry } }
  | { type: 'UPDATE_SERVER'; payload: { id: string; updates: Partial<ServerEntry> } }
  | { type: 'REMOVE_SERVER'; payload: { id: string } }
  | { type: 'SET_PRIMARY'; payload: { id: string } }
  | { type: 'ADD_ELICITATION'; payload: PendingElicitation }
  | { type: 'REMOVE_ELICITATION'; payload: { id: string } }
  | { type: 'ADD_SAMPLING_REQUEST'; payload: PendingSamplingRequest }
  | { type: 'REMOVE_SAMPLING_REQUEST'; payload: { id: string } };

function mcpHostReducer(state: MCPHostState, action: MCPHostAction): MCPHostState {
  switch (action.type) {
    case 'ADD_SERVER': {
      const newServers = new Map(state.servers);
      newServers.set(action.payload.id, action.payload.entry);
      return { ...state, servers: newServers };
    }

    case 'UPDATE_SERVER': {
      const server = state.servers.get(action.payload.id);
      if (!server) return state;

      const newServers = new Map(state.servers);
      newServers.set(action.payload.id, { ...server, ...action.payload.updates });
      return { ...state, servers: newServers };
    }

    case 'REMOVE_SERVER': {
      const newServers = new Map(state.servers);
      newServers.delete(action.payload.id);
      const newPrimaryId =
        state.primaryServerId === action.payload.id ? null : state.primaryServerId;
      return { ...state, servers: newServers, primaryServerId: newPrimaryId };
    }

    case 'SET_PRIMARY':
      return { ...state, primaryServerId: action.payload.id };

    case 'ADD_ELICITATION':
      return {
        ...state,
        pendingElicitations: [...state.pendingElicitations, action.payload],
      };

    case 'REMOVE_ELICITATION':
      return {
        ...state,
        pendingElicitations: state.pendingElicitations.filter(
          (e) => e.id !== action.payload.id
        ),
      };

    case 'ADD_SAMPLING_REQUEST':
      return {
        ...state,
        pendingSamplingRequests: [...state.pendingSamplingRequests, action.payload],
      };

    case 'REMOVE_SAMPLING_REQUEST':
      return {
        ...state,
        pendingSamplingRequests: state.pendingSamplingRequests.filter(
          (r) => r.id !== action.payload.id
        ),
      };

    default:
      return state;
  }
}

// =============================================================================
// Context
// =============================================================================

const MCPHostContext = createContext<MCPHostContextValue | null>(null);

// =============================================================================
// Provider
// =============================================================================

interface MCPHostProviderProps {
  children: ReactNode;
}

export function MCPHostProvider({ children }: MCPHostProviderProps): React.ReactElement {
  const [state, dispatch] = useReducer(mcpHostReducer, {
    servers: new Map(),
    primaryServerId: null,
    pendingElicitations: [],
    pendingSamplingRequests: [],
  });

  // Client capabilities this host supports
  const capabilities: MCPClientCapabilitiesConfig = useMemo(
    () => ({
      elicitation: true,
      sampling: true,
      roots: { listChanged: true },
    }),
    []
  );

  // Add a server and connect
  const addServer = useCallback(
    async (id: string, url: string, options?: AddServerOptions) => {
      const client = createMCPClient({
        baseUrl: url,
        authToken: options?.authToken,
      });

      // Add server with connecting status
      const initialEntry: ServerEntry = {
        id,
        url,
        status: 'connecting' as MCPConnectionStatus,
        client,
        tools: [],
        resources: [],
        prompts: [],
      };

      dispatch({ type: 'ADD_SERVER', payload: { id, entry: initialEntry } });

      if (options?.primary) {
        dispatch({ type: 'SET_PRIMARY', payload: { id } });
      }

      try {
        // Initialize connection
        const initResult = await client.initialize();

        // Fetch capabilities
        const [tools, resourcesResult, prompts] = await Promise.all([
          client.listTools().catch(() => []),
          client.listResources().catch(() => ({ resources: [] })),
          client.listPrompts().catch(() => []),
        ]);

        // Update with connected status and capabilities
        dispatch({
          type: 'UPDATE_SERVER',
          payload: {
            id,
            updates: {
              status: 'connected',
              serverInfo: initResult.serverInfo,
              capabilities: initResult.capabilities,
              tools,
              resources: resourcesResult.resources,
              prompts,
              lastConnected: new Date().toISOString(),
            },
          },
        });
      } catch (error) {
        // Update with error status
        dispatch({
          type: 'UPDATE_SERVER',
          payload: {
            id,
            updates: {
              status: 'error',
              error: error instanceof Error ? error.message : 'Connection failed',
            },
          },
        });
        throw error;
      }
    },
    []
  );

  // Remove a server
  const removeServer = useCallback((id: string) => {
    const server = state.servers.get(id);
    if (server) {
      server.client.disconnect();
    }
    dispatch({ type: 'REMOVE_SERVER', payload: { id } });
  }, [state.servers]);

  // Set primary server
  const setPrimaryServer = useCallback((id: string) => {
    if (state.servers.has(id)) {
      dispatch({ type: 'SET_PRIMARY', payload: { id } });
    }
  }, [state.servers]);

  // Get client for a specific server
  const getClient = useCallback(
    (serverId: string): MCPClient | null => {
      return state.servers.get(serverId)?.client || null;
    },
    [state.servers]
  );

  // Elicitation handlers
  const addElicitation = useCallback((elicitation: PendingElicitation) => {
    dispatch({ type: 'ADD_ELICITATION', payload: elicitation });
  }, []);

  const respondToElicitation = useCallback(
    (id: string, _action: ElicitationAction, _content?: Record<string, unknown>) => {
      // TODO: Send response to server (action and content will be used when implemented)
      dispatch({ type: 'REMOVE_ELICITATION', payload: { id } });
    },
    []
  );

  // Sampling handlers
  const addSamplingRequest = useCallback((request: PendingSamplingRequest) => {
    dispatch({ type: 'ADD_SAMPLING_REQUEST', payload: request });
  }, []);

  const respondToSampling = useCallback(
    (id: string, _approved: boolean, _result?: unknown) => {
      // TODO: Send response to server (approved and result will be used when implemented)
      dispatch({ type: 'REMOVE_SAMPLING_REQUEST', payload: { id } });
    },
    []
  );

  // Track if we've attempted auto-connect to avoid duplicate attempts
  const hasAttemptedAutoConnect = useRef(false);

  // Auto-connect to default MCP server on mount
  // Uses /mcp which routes to the MCP StreamableHTTP server via Traefik
  // Skipped in test environment to avoid interference with unit tests
  useEffect(() => {
    // Skip auto-connect in test environment
    if (import.meta.env.MODE === 'test') {
      return;
    }

    if (hasAttemptedAutoConnect.current) {
      return;
    }
    hasAttemptedAutoConnect.current = true;

    // Determine MCP server URL based on current location
    // In production (behind Traefik): use relative /mcp path
    // In development (Vite dev server): use absolute localhost:8001
    const mcpServerUrl =
      window.location.port === '5174'
        ? 'http://localhost:8001/mcp' // Vite dev server
        : '/mcp'; // Production (Traefik proxies /mcp to MCP server)

    // Auto-connect to default server, but don't fail if it's not available
    addServer('default', mcpServerUrl, { primary: true }).catch((error) => {
      console.warn('Auto-connect to default MCP server failed:', error.message);
      // Don't propagate - user can manually add servers
    });
  }, [addServer]);

  // Aggregate tools from all connected servers
  const allTools = useMemo(() => {
    const tools: MCPTool[] = [];
    for (const server of state.servers.values()) {
      if (server.status === 'connected') {
        tools.push(...server.tools);
      }
    }
    return tools;
  }, [state.servers]);

  // Aggregate resources from all connected servers
  const allResources = useMemo(() => {
    const resources: MCPResource[] = [];
    for (const server of state.servers.values()) {
      if (server.status === 'connected') {
        resources.push(...server.resources);
      }
    }
    return resources;
  }, [state.servers]);

  // Aggregate prompts from all connected servers
  const allPrompts = useMemo(() => {
    const prompts: MCPPrompt[] = [];
    for (const server of state.servers.values()) {
      if (server.status === 'connected') {
        prompts.push(...server.prompts);
      }
    }
    return prompts;
  }, [state.servers]);

  // Convert ServerEntry Map to MCPServerConnection Map for public API
  const servers = useMemo(() => {
    const publicServers = new Map<string, MCPServerConnection>();
    for (const [id, entry] of state.servers) {
      publicServers.set(id, {
        id: entry.id,
        url: entry.url,
        status: entry.status,
        serverInfo: entry.serverInfo,
        capabilities: entry.capabilities,
        error: entry.error,
        lastConnected: entry.lastConnected,
      });
    }
    return publicServers;
  }, [state.servers]);

  const value: MCPHostContextValue = useMemo(
    () => ({
      servers,
      primaryServerId: state.primaryServerId,
      addServer,
      removeServer,
      setPrimaryServer,
      allTools,
      allResources,
      allPrompts,
      capabilities,
      pendingElicitations: state.pendingElicitations,
      pendingSamplingRequests: state.pendingSamplingRequests,
      addElicitation,
      respondToElicitation,
      addSamplingRequest,
      respondToSampling,
      getClient,
    }),
    [
      servers,
      state.primaryServerId,
      state.pendingElicitations,
      state.pendingSamplingRequests,
      addServer,
      removeServer,
      setPrimaryServer,
      allTools,
      allResources,
      allPrompts,
      capabilities,
      addElicitation,
      respondToElicitation,
      addSamplingRequest,
      respondToSampling,
      getClient,
    ]
  );

  return <MCPHostContext.Provider value={value}>{children}</MCPHostContext.Provider>;
}

// =============================================================================
// Hook
// =============================================================================

export function useMCPHost(): MCPHostContextValue {
  const context = useContext(MCPHostContext);
  if (!context) {
    throw new Error('useMCPHost must be used within MCPHostProvider');
  }
  return context;
}

// =============================================================================
// Exports
// =============================================================================

export { MCPHostContext };
