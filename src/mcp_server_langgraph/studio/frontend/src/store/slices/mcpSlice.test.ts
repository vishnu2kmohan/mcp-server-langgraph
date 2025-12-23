/**
 * MCP Slice Tests
 *
 * TDD tests for MCP Redux slice.
 */

import { describe, it, expect, beforeEach, vi, afterEach } from "vitest";
import { configureStore } from "@reduxjs/toolkit";
import mcpReducer, {
  initialMCPState,
  addServer,
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
  selectServers,
  selectServerList,
  selectPrimaryServerId,
  selectIsConnecting,
  selectMCPError,
  selectAllTools,
  selectAllResources,
  selectAllPrompts,
  selectIsConnected,
  selectMCPCapabilities,
  selectPendingElicitations,
  selectPendingSamplingRequests,
  selectServerById,
} from "./mcpSlice";
import type { MCPSliceState } from "./mcpSlice";
import type {
  ServerEntry,
  MCPTool,
  MCPResource,
  MCPPrompt,
} from "../../types/mcp";

// Helper to create a test store
const createTestStore = (preloadedState?: Partial<MCPSliceState>) => {
  return configureStore({
    reducer: { mcp: mcpReducer },
    preloadedState: preloadedState
      ? { mcp: { ...initialMCPState, ...preloadedState } }
      : undefined,
  });
};

// Mock server entry
const mockServer: ServerEntry = {
  id: "server-1",
  url: "http://localhost:3000",
  status: "connected",
  tools: [],
  resources: [],
  prompts: [],
};

describe("mcpSlice", () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    mockFetch.mockReset();
    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.clearAllMocks();
  });

  describe("Initial State", () => {
    it("should have empty servers", () => {
      const store = createTestStore();
      expect(selectServers(store.getState())).toEqual({});
    });

    it("should have no primary server", () => {
      const store = createTestStore();
      expect(selectPrimaryServerId(store.getState())).toBeNull();
    });

    it("should not be connecting", () => {
      const store = createTestStore();
      expect(selectIsConnecting(store.getState())).toBe(false);
    });

    it("should have no error", () => {
      const store = createTestStore();
      expect(selectMCPError(store.getState())).toBeNull();
    });
  });

  describe("removeServer", () => {
    it("should remove server by id", () => {
      const store = createTestStore({ servers: { "server-1": mockServer } });
      store.dispatch(removeServer("server-1"));

      expect(selectServers(store.getState())).toEqual({});
    });

    it("should clear primary server if removing primary", () => {
      const store = createTestStore({
        servers: { "server-1": mockServer },
        primaryServerId: "server-1",
      });
      store.dispatch(removeServer("server-1"));

      expect(selectPrimaryServerId(store.getState())).toBeNull();
    });
  });

  describe("setPrimaryServer", () => {
    it("should set primary server id", () => {
      const store = createTestStore({ servers: { "server-1": mockServer } });
      store.dispatch(setPrimaryServer("server-1"));

      expect(selectPrimaryServerId(store.getState())).toBe("server-1");
    });
  });

  describe("updateServerStatus", () => {
    it("should update server status", () => {
      const store = createTestStore({ servers: { "server-1": mockServer } });
      store.dispatch(
        updateServerStatus({
          id: "server-1",
          status: "error",
          error: "Connection lost",
        }),
      );

      const server = selectServers(store.getState())["server-1"];
      expect(server.status).toBe("error");
      expect(server.error).toBe("Connection lost");
    });

    it("should set lastConnected when status is connected", () => {
      const disconnectedServer = {
        ...mockServer,
        status: "disconnected" as const,
      };
      const store = createTestStore({
        servers: { "server-1": disconnectedServer },
      });

      const beforeTime = Date.now();
      store.dispatch(
        updateServerStatus({
          id: "server-1",
          status: "connected",
        }),
      );

      const server = selectServers(store.getState())["server-1"];
      expect(server.status).toBe("connected");
      expect(server.lastConnected).toBeGreaterThanOrEqual(beforeTime);
    });

    it("should not update non-existent server", () => {
      const store = createTestStore({ servers: {} });
      store.dispatch(
        updateServerStatus({
          id: "non-existent",
          status: "connected",
        }),
      );

      expect(selectServers(store.getState())).toEqual({});
    });
  });

  describe("setServerTools", () => {
    it("should set server tools", () => {
      const tools: MCPTool[] = [
        { name: "test-tool", description: "A test tool", inputSchema: {} },
      ];

      const store = createTestStore({ servers: { "server-1": mockServer } });
      store.dispatch(setServerTools({ id: "server-1", tools }));

      const server = selectServers(store.getState())["server-1"];
      expect(server.tools).toHaveLength(1);
      expect(server.tools[0].name).toBe("test-tool");
    });

    it("should do nothing when server does not exist", () => {
      const tools: MCPTool[] = [
        { name: "test-tool", description: "A test tool", inputSchema: {} },
      ];

      const store = createTestStore({ servers: {} });
      store.dispatch(setServerTools({ id: "non-existent", tools }));

      expect(selectServers(store.getState())).toEqual({});
    });
  });

  describe("setServerResources", () => {
    it("should set server resources", () => {
      const resources: MCPResource[] = [
        { uri: "file://test.txt", name: "test.txt" },
      ];

      const store = createTestStore({ servers: { "server-1": mockServer } });
      store.dispatch(setServerResources({ id: "server-1", resources }));

      const server = selectServers(store.getState())["server-1"];
      expect(server.resources).toHaveLength(1);
      expect(server.resources[0].name).toBe("test.txt");
    });

    it("should do nothing when server does not exist", () => {
      const resources: MCPResource[] = [
        { uri: "file://test.txt", name: "test.txt" },
      ];

      const store = createTestStore({ servers: {} });
      store.dispatch(setServerResources({ id: "non-existent", resources }));

      expect(selectServers(store.getState())).toEqual({});
    });
  });

  describe("setServerPrompts", () => {
    it("should set server prompts", () => {
      const prompts: MCPPrompt[] = [
        { name: "test-prompt", description: "A test prompt" },
      ];

      const store = createTestStore({ servers: { "server-1": mockServer } });
      store.dispatch(setServerPrompts({ id: "server-1", prompts }));

      const server = selectServers(store.getState())["server-1"];
      expect(server.prompts).toHaveLength(1);
      expect(server.prompts[0].name).toBe("test-prompt");
    });

    it("should do nothing when server does not exist", () => {
      const prompts: MCPPrompt[] = [
        { name: "test-prompt", description: "A test prompt" },
      ];

      const store = createTestStore({ servers: {} });
      store.dispatch(setServerPrompts({ id: "non-existent", prompts }));

      expect(selectServers(store.getState())).toEqual({});
    });
  });

  describe("Elicitation", () => {
    it("should add elicitation", () => {
      const store = createTestStore();
      store.dispatch(
        addElicitation({
          id: "elicit-1",
          serverId: "server-1",
          type: "confirm",
          message: "Are you sure?",
          timestamp: Date.now(),
        }),
      );

      expect(store.getState().mcp.pendingElicitations).toHaveLength(1);
    });

    it("should remove elicitation when responded", () => {
      const store = createTestStore({
        pendingElicitations: [
          {
            id: "elicit-1",
            serverId: "server-1",
            type: "confirm",
            message: "Are you sure?",
            timestamp: Date.now(),
          },
        ],
      });

      store.dispatch(respondToElicitation("elicit-1"));
      expect(store.getState().mcp.pendingElicitations).toHaveLength(0);
    });
  });

  describe("Sampling", () => {
    it("should add sampling request", () => {
      const store = createTestStore();
      store.dispatch(
        addSamplingRequest({
          id: "sample-1",
          serverId: "server-1",
          messages: [],
          timestamp: Date.now(),
        }),
      );

      expect(store.getState().mcp.pendingSamplingRequests).toHaveLength(1);
    });

    it("should remove sampling request when responded", () => {
      const store = createTestStore({
        pendingSamplingRequests: [
          {
            id: "sample-1",
            serverId: "server-1",
            messages: [],
            timestamp: Date.now(),
          },
        ],
      });

      store.dispatch(respondToSampling("sample-1"));
      expect(store.getState().mcp.pendingSamplingRequests).toHaveLength(0);
    });
  });

  describe("clearMCPError", () => {
    it("should clear error", () => {
      const store = createTestStore({ error: "Some error" });
      store.dispatch(clearMCPError());

      expect(selectMCPError(store.getState())).toBeNull();
    });
  });

  describe("resetMCP", () => {
    it("should reset to initial state", () => {
      const store = createTestStore({
        servers: { "server-1": mockServer },
        primaryServerId: "server-1",
        error: "Some error",
      });
      store.dispatch(resetMCP());

      expect(selectServers(store.getState())).toEqual({});
      expect(selectPrimaryServerId(store.getState())).toBeNull();
      expect(selectMCPError(store.getState())).toBeNull();
    });
  });

  describe("Selectors", () => {
    describe("selectServerList", () => {
      it("should return array of servers", () => {
        const store = createTestStore({
          servers: {
            "server-1": mockServer,
            "server-2": { ...mockServer, id: "server-2" },
          },
        });

        const serverList = selectServerList(store.getState());
        expect(serverList).toHaveLength(2);
      });
    });

    describe("selectAllTools", () => {
      it("should return tools from all servers", () => {
        const server1: ServerEntry = {
          ...mockServer,
          id: "server-1",
          tools: [{ name: "tool1", description: "Tool 1", inputSchema: {} }],
        };
        const server2: ServerEntry = {
          ...mockServer,
          id: "server-2",
          tools: [{ name: "tool2", description: "Tool 2", inputSchema: {} }],
        };

        const store = createTestStore({
          servers: { "server-1": server1, "server-2": server2 },
        });

        const tools = selectAllTools(store.getState());
        expect(tools).toHaveLength(2);
      });
    });

    describe("selectAllResources", () => {
      it("should return resources from all servers", () => {
        const server1: ServerEntry = {
          ...mockServer,
          id: "server-1",
          resources: [{ uri: "file://a.txt", name: "a.txt" }],
        };
        const server2: ServerEntry = {
          ...mockServer,
          id: "server-2",
          resources: [{ uri: "file://b.txt", name: "b.txt" }],
        };

        const store = createTestStore({
          servers: { "server-1": server1, "server-2": server2 },
        });

        const resources = selectAllResources(store.getState());
        expect(resources).toHaveLength(2);
      });
    });

    describe("selectAllPrompts", () => {
      it("should return prompts from all servers", () => {
        const server1: ServerEntry = {
          ...mockServer,
          id: "server-1",
          prompts: [{ name: "prompt1", description: "Prompt 1" }],
        };
        const server2: ServerEntry = {
          ...mockServer,
          id: "server-2",
          prompts: [{ name: "prompt2", description: "Prompt 2" }],
        };

        const store = createTestStore({
          servers: { "server-1": server1, "server-2": server2 },
        });

        const prompts = selectAllPrompts(store.getState());
        expect(prompts).toHaveLength(2);
      });
    });

    describe("selectIsConnected", () => {
      it("should return true if any server is connected", () => {
        const store = createTestStore({
          servers: { "server-1": mockServer },
        });

        expect(selectIsConnected(store.getState())).toBe(true);
      });

      it("should return false if no servers are connected", () => {
        const store = createTestStore({
          servers: { "server-1": { ...mockServer, status: "error" } },
        });

        expect(selectIsConnected(store.getState())).toBe(false);
      });
    });

    describe("selectMCPCapabilities", () => {
      it("should return capabilities", () => {
        const capabilities = { tools: true, resources: true, prompts: false };
        const store = createTestStore({ capabilities });
        expect(selectMCPCapabilities(store.getState())).toEqual(capabilities);
      });
    });

    describe("selectPendingElicitations", () => {
      it("should return pending elicitations", () => {
        const elicitation = {
          id: "elicit-1",
          serverId: "server-1",
          message: "Choose an option",
          schema: {},
          requestId: "req-1",
        };
        const store = createTestStore({ pendingElicitations: [elicitation] });
        expect(selectPendingElicitations(store.getState())).toEqual([
          elicitation,
        ]);
      });
    });

    describe("selectPendingSamplingRequests", () => {
      it("should return pending sampling requests", () => {
        const sampling = {
          id: "sample-1",
          serverId: "server-1",
          messages: [],
          requestId: "req-1",
        };
        const store = createTestStore({ pendingSamplingRequests: [sampling] });
        expect(selectPendingSamplingRequests(store.getState())).toEqual([
          sampling,
        ]);
      });
    });

    describe("selectServerById", () => {
      it("should return server by id", () => {
        const store = createTestStore({
          servers: { "server-1": mockServer },
        });
        expect(selectServerById("server-1")(store.getState())).toEqual(
          mockServer,
        );
      });

      it("should return undefined for non-existent server", () => {
        const store = createTestStore();
        expect(
          selectServerById("non-existent")(store.getState()),
        ).toBeUndefined();
      });
    });
  });

  describe("addServer async thunk", () => {
    it("should add server entry in pending state", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ serverInfo: { name: "test" } }),
      });

      const store = createTestStore();
      const promise = store.dispatch(
        addServer({ id: "server-1", url: "http://localhost:3000" }),
      );

      // Check pending state is set
      expect(selectIsConnecting(store.getState())).toBe(true);

      await promise;

      // Check fulfilled state
      expect(selectIsConnecting(store.getState())).toBe(false);
      const server = selectServers(store.getState())["server-1"];
      expect(server.status).toBe("connected");
    });

    it("should set error state on failure", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      const store = createTestStore();
      await store.dispatch(
        addServer({ id: "server-1", url: "http://localhost:3000" }),
      );

      const server = selectServers(store.getState())["server-1"];
      expect(server.status).toBe("error");
      expect(server.error).toBe("HTTP 500");
    });

    it("should set as primary if first server", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ serverInfo: {} }),
      });

      const store = createTestStore();
      await store.dispatch(
        addServer({ id: "server-1", url: "http://localhost:3000" }),
      );

      expect(selectPrimaryServerId(store.getState())).toBe("server-1");
    });

    it("should not change primary when adding second server without primary flag", async () => {
      mockFetch
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ serverInfo: {} }),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve({ serverInfo: {} }),
        });

      const store = createTestStore();
      // Add first server - becomes primary
      await store.dispatch(
        addServer({ id: "server-1", url: "http://localhost:3000" }),
      );
      expect(selectPrimaryServerId(store.getState())).toBe("server-1");

      // Add second server without primary flag - should NOT change primary
      await store.dispatch(
        addServer({ id: "server-2", url: "http://localhost:3001" }),
      );
      expect(selectPrimaryServerId(store.getState())).toBe("server-1");
    });

    it("should include auth token in headers when provided", async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ serverInfo: { name: "test" } }),
      });

      const store = createTestStore();
      await store.dispatch(
        addServer({
          id: "server-1",
          url: "http://localhost:3000",
          authToken: "test-auth-token",
        }),
      );

      expect(mockFetch).toHaveBeenCalledWith(
        "http://localhost:3000/mcp/initialize",
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer test-auth-token",
          }),
        }),
      );
    });

    it("should handle non-Error rejection", async () => {
      mockFetch.mockRejectedValueOnce("String error");

      const store = createTestStore();
      await store.dispatch(
        addServer({ id: "server-1", url: "http://localhost:3000" }),
      );

      const server = selectServers(store.getState())["server-1"];
      expect(server.status).toBe("error");
      expect(server.error).toBe("Connection failed");
    });

    it("should handle network error", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));

      const store = createTestStore();
      await store.dispatch(
        addServer({ id: "server-1", url: "http://localhost:3000" }),
      );

      const server = selectServers(store.getState())["server-1"];
      expect(server.status).toBe("error");
      expect(server.error).toBe("Network error");
    });

    it("should handle fulfilled when server was removed before completion", () => {
      // Directly test reducer with server not in state
      const state = mcpReducer(
        { ...initialMCPState, isConnecting: true },
        {
          type: addServer.fulfilled.type,
          payload: {
            id: "non-existent-server",
            serverInfo: { name: "Test", version: "1.0" },
            capabilities: {},
          },
        },
      );
      // Should not throw, just set isConnecting to false
      expect(state.isConnecting).toBe(false);
      expect(state.servers["non-existent-server"]).toBeUndefined();
    });

    it("should handle rejected with undefined payload", () => {
      // Directly test reducer with undefined payload
      const state = mcpReducer(
        { ...initialMCPState, isConnecting: true },
        { type: addServer.rejected.type, payload: undefined },
      );
      // Should not throw, just set isConnecting to false
      expect(state.isConnecting).toBe(false);
    });

    it("should handle rejected when server was removed before completion", () => {
      // Directly test reducer with server not in state
      const state = mcpReducer(
        { ...initialMCPState, isConnecting: true },
        {
          type: addServer.rejected.type,
          payload: { id: "non-existent-server", error: "Connection failed" },
        },
      );
      // Should not throw, just set isConnecting to false
      expect(state.isConnecting).toBe(false);
      expect(state.servers["non-existent-server"]).toBeUndefined();
    });
  });
});
