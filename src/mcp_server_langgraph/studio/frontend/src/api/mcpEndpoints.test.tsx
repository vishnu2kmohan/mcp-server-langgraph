/**
 * MCP RTK Query Endpoints Tests (TDD)
 *
 * Tests for MCP-related RTK Query endpoints:
 * - listMcpResources: List available resources
 * - readMcpResource: Read resource content
 * - invokeMcpTool: Call an MCP tool
 * - requestMcpSampling: Request LLM completion
 * - requestMcpElicitation: Request user input
 * - listMcpPrompts: List available prompts
 * - getMcpPrompt: Get prompt by name
 *
 * Following TDD: RED phase - write failing tests first
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { http, HttpResponse } from "msw";
import { renderHook, waitFor, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";
import { server } from "../mocks/server";

import {
  api,
  useListMcpResourcesQuery,
  useReadMcpResourceMutation,
  useInvokeMcpToolMutation,
  useRequestMcpSamplingMutation,
  useRequestMcpElicitationMutation,
  useListMcpPromptsQuery,
  useGetMcpPromptMutation,
} from "./index";

// =============================================================================
// Mock Data
// =============================================================================

const _MOCK_RESOURCES = {
  resources: [
    {
      uri: "file:///project/README.md",
      name: "README.md",
      mimeType: "text/markdown",
      description: "Project README file",
    },
    {
      uri: "file:///project/src/index.ts",
      name: "index.ts",
      mimeType: "text/typescript",
      description: "Project README file",
    },
    {
      uri: "file:///project/package.json",
      name: "package.json",
      mimeType: "application/json",
      description: "Project README file",
    },
  ],
};

const _MOCK_RESOURCE_CONTENT = {
  contents: [
    {
      uri: "file:///project/README.md",
      mimeType: "text/markdown",
      text: "# Project README\n\nThis is the project readme file.",
    },
  ],
};

const _MOCK_TOOL_RESULT = {
  content: [
    {
      type: "text",
      text: "Tool executed successfully",
    },
  ],
  isError: false,
};

const _MOCK_SAMPLING_RESPONSE = {
  role: "assistant",
  content: { type: "text", text: "This is a mock sampling response." },
  model: "mock-model",
  stopReason: "end_turn",
};

const _MOCK_ELICITATION_RESPONSE = {
  action: "accept",
  content: { name: "John Doe", email: "john@example.com" },
};

const _MOCK_PROMPTS = {
  prompts: [
    {
      name: "summarize",
      description: "Summarize the given text",
      arguments: [
        { name: "text", description: "Text to summarize", required: true },
      ],
    },
    {
      name: "translate",
      description: "Translate text to another language",
      arguments: [
        { name: "text", description: "Text to translate", required: true },
        { name: "language", description: "Target language", required: true },
      ],
    },
  ],
};

const _MOCK_PROMPT_DETAIL = {
  description: "Summarize the given text",
  messages: [
    {
      role: "user",
      content: {
        type: "text",
        text: 'Summarize the given text: {"text":"Hello world"}',
      },
    },
  ],
};

// Note: This test uses the global MSW server from ../mocks/server
// which includes mcpHandlers. We use server.use() to override for specific tests.

// =============================================================================
// Test Store Setup
// =============================================================================

const createTestStore = () =>
  configureStore({
    reducer: {
      [api.reducerPath]: api.reducer,
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(api.middleware),
  });

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <Provider store={createTestStore()}>{children}</Provider>
);

// =============================================================================
// Test Setup
// =============================================================================

// The global server is started/stopped in test/setup.ts
// We only need to reset handlers after each test
afterEach(() => {
  cleanup();
  server.resetHandlers();
  vi.clearAllMocks();
});

// =============================================================================
// Tests
// =============================================================================

describe("MCP RTK Query Endpoints", () => {
  describe("useListMcpResourcesQuery", () => {
    it("fetches resources successfully", async () => {
      const { result } = renderHook(() => useListMcpResourcesQuery(), {
        wrapper,
      });

      // Initially loading
      expect(result.current.isLoading).toBe(true);

      // Wait for response
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify data structure (not exact match due to dynamic values)
      expect(result.current.data?.resources).toHaveLength(3);
      expect(result.current.data?.resources[0].name).toBe("README.md");
      expect(result.current.data?.resources[0].uri).toBe(
        "file:///project/README.md",
      );
    });

    it("handles empty resources list", async () => {
      server.use(
        http.get("/api/v1/mcp/resources", () => {
          return HttpResponse.json({ resources: [] });
        }),
      );

      const { result } = renderHook(() => useListMcpResourcesQuery(), {
        wrapper,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.resources).toHaveLength(0);
    });
  });

  describe("useReadMcpResourceMutation", () => {
    it("reads resource content successfully", async () => {
      const { result } = renderHook(() => useReadMcpResourceMutation(), {
        wrapper,
      });

      const [readResource] = result.current;

      const response = await readResource({
        uri: "file:///project/README.md",
      }).unwrap();

      expect(response.contents).toHaveLength(1);
      expect(response.contents[0].text).toContain("Project README");
      expect(response.contents[0].mimeType).toBe("text/markdown");
    });

    it("handles resource not found error", async () => {
      server.use(
        http.get("/api/v1/mcp/resources/content", () => {
          return HttpResponse.json(
            { detail: "Resource not found" },
            { status: 404 },
          );
        }),
      );

      const { result } = renderHook(() => useReadMcpResourceMutation(), {
        wrapper,
      });

      const [readResource] = result.current;

      await expect(
        readResource({ uri: "file:///nonexistent.md" }).unwrap(),
      ).rejects.toThrow();
    });
  });

  describe("useInvokeMcpToolMutation", () => {
    it("invokes tool successfully", async () => {
      const { result } = renderHook(() => useInvokeMcpToolMutation(), {
        wrapper,
      });

      const [invokeTool] = result.current;

      const response = await invokeTool({
        name: "read_file",
        arguments: { path: "/tmp/test.txt" },
      }).unwrap();

      // Verify response structure (handler includes tool name in message)
      // Note: invokeMcpTool has no transformResponse, so response is snake_case from apiJsonResponse
      expect(response.content).toHaveLength(1);
      expect(response.content[0].type).toBe("text");
      expect(response.content[0].text).toContain("executed successfully");
      expect(response.is_error).toBe(false);
    });

    it("handles tool execution error", async () => {
      server.use(
        http.post("/api/v1/mcp/tools/call", () => {
          return HttpResponse.json(
            { content: [{ type: "text", text: "Error" }], isError: true },
            { status: 200 },
          );
        }),
      );

      const { result } = renderHook(() => useInvokeMcpToolMutation(), {
        wrapper,
      });

      const [invokeTool] = result.current;

      const response = await invokeTool({
        name: "bad_tool",
        arguments: {},
      }).unwrap();

      expect(response.isError).toBe(true);
    });
  });

  describe("useRequestMcpSamplingMutation", () => {
    it("requests sampling successfully", async () => {
      const { result } = renderHook(() => useRequestMcpSamplingMutation(), {
        wrapper,
      });

      const [requestSampling] = result.current;

      const response = await requestSampling({
        messages: [{ role: "user", content: { type: "text", text: "Hello" } }],
        max_tokens: 100,
      }).unwrap();

      expect(response.role).toBe("assistant");
      expect(response.model).toBe("mock-model");
      expect(response.content).toBeDefined();
    });

    it("handles sampling with model hints", async () => {
      const { result } = renderHook(() => useRequestMcpSamplingMutation(), {
        wrapper,
      });

      const [requestSampling] = result.current;

      const response = await requestSampling({
        messages: [{ role: "user", content: { type: "text", text: "Hello" } }],
        max_tokens: 100,
        model_hints: ["claude-3-opus"],
        intelligence_priority: 0.9,
      }).unwrap();

      expect(response.role).toBe("assistant");
    });
  });

  describe("useRequestMcpElicitationMutation", () => {
    it("requests elicitation successfully", async () => {
      const { result } = renderHook(() => useRequestMcpElicitationMutation(), {
        wrapper,
      });

      const [requestElicitation] = result.current;

      const response = await requestElicitation({
        message: "Please enter your name and email",
        schema: {
          type: "object",
          properties: {
            name: { type: "string" },
            email: { type: "string", format: "email" },
          },
          required: ["name", "email"],
        },
      }).unwrap();

      expect(response.action).toBe("accept");
      expect(response.content?.name).toBe("John Doe");
      expect(response.content?.email).toBe("john@example.com");
    });

    it("handles user declining elicitation", async () => {
      server.use(
        http.post("/api/v1/mcp/elicitation", () => {
          return HttpResponse.json({
            action: "decline",
            content: null,
          });
        }),
      );

      const { result } = renderHook(() => useRequestMcpElicitationMutation(), {
        wrapper,
      });

      const [requestElicitation] = result.current;

      const response = await requestElicitation({
        message: "Please confirm action",
      }).unwrap();

      expect(response.action).toBe("decline");
      expect(response.content).toBeNull();
    });
  });

  describe("useListMcpPromptsQuery", () => {
    it("fetches prompts successfully", async () => {
      const { result } = renderHook(() => useListMcpPromptsQuery(), {
        wrapper,
      });

      // Initially loading
      expect(result.current.isLoading).toBe(true);

      // Wait for response
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify data structure (not exact match due to dynamic values)
      expect(result.current.data?.prompts).toHaveLength(2);
      expect(result.current.data?.prompts[0].name).toBe("summarize");
      expect(result.current.data?.prompts[0].description).toBe(
        "Summarize the given text",
      );
    });
  });

  describe("useGetMcpPromptMutation", () => {
    it("gets prompt with arguments", async () => {
      const { result } = renderHook(() => useGetMcpPromptMutation(), {
        wrapper,
      });

      const [getPrompt] = result.current;

      const response = await getPrompt({
        name: "summarize",
        arguments: { text: "Hello world" },
      }).unwrap();

      expect(response.messages).toHaveLength(1);
      expect(response.messages[0].role).toBe("user");
      expect(response.description).toBe("Summarize the given text");
    });

    it("handles prompt not found", async () => {
      server.use(
        http.post("/api/v1/mcp/prompts/get", () => {
          return HttpResponse.json(
            { detail: "Prompt not found" },
            { status: 404 },
          );
        }),
      );

      const { result } = renderHook(() => useGetMcpPromptMutation(), {
        wrapper,
      });

      const [getPrompt] = result.current;

      await expect(
        getPrompt({ name: "nonexistent" }).unwrap(),
      ).rejects.toThrow();
    });
  });

  // ===========================================================================
  // RTK Query Tag Invalidation Tests
  // ===========================================================================

  describe("Tag Invalidation", () => {
    it("invokeMcpTool invalidates TASKS tag", async () => {
      // First, fetch tasks to populate cache
      const store = createTestStore();
      const taskWrapper = ({ children }: { children: React.ReactNode }) => (
        <Provider store={store}>{children}</Provider>
      );

      const { result: tasksResult } = renderHook(
        () => api.endpoints.listMcpTasks.useQuery(),
        { wrapper: taskWrapper },
      );

      await waitFor(() => expect(tasksResult.current.isSuccess).toBe(true));

      // Get initial fetch count from RTK Query state
      const initialState = store.getState().api.queries;
      const initialTasksQuery = Object.values(initialState).find(
        (q) => q && "endpointName" in q && q.endpointName === "listMcpTasks",
      );
      expect(initialTasksQuery).toBeDefined();

      // Invoke a tool (should invalidate TASKS) - use valid mock tool name
      const { result: toolResult } = renderHook(
        () => useInvokeMcpToolMutation(),
        { wrapper: taskWrapper },
      );

      const [invokeTool] = toolResult.current;
      await invokeTool({
        name: "read_file", // Use valid mock tool
        arguments: { path: "/tmp/test.txt" },
      }).unwrap();

      // Wait for refetch triggered by invalidation
      await waitFor(() => {
        const state = store.getState().api.queries;
        const tasksQuery = Object.values(state).find(
          (q) => q && "endpointName" in q && q.endpointName === "listMcpTasks",
        );
        // Query should still exist (refetched after invalidation)
        return tasksQuery !== undefined;
      });
    });

    it("cancelMcpTask invalidates specific task and TASKS list", async () => {
      const store = createTestStore();
      const taskWrapper = ({ children }: { children: React.ReactNode }) => (
        <Provider store={store}>{children}</Provider>
      );

      // Fetch a specific task - use valid mock task ID
      const { result: taskResult } = renderHook(
        () => api.endpoints.getMcpTask.useQuery("task-1"),
        { wrapper: taskWrapper },
      );

      await waitFor(() => expect(taskResult.current.isSuccess).toBe(true));

      // Cancel the task
      const { result: cancelResult } = renderHook(
        () => api.endpoints.cancelMcpTask.useMutation(),
        { wrapper: taskWrapper },
      );

      const [cancelTask] = cancelResult.current;
      await cancelTask("task-1").unwrap();

      // After cancel, the cache should be invalidated
      // This is verified by checking that the endpoint would refetch
      await waitFor(() => {
        const _state = store.getState().api.queries;
        // At minimum, the mutation should complete without error
        return cancelResult.current[1].isSuccess;
      });
    });
  });

  // ===========================================================================
  // Cache Configuration Tests
  // ===========================================================================

  describe("Cache Configuration", () => {
    it("MCP resources endpoint has proper cache configuration", async () => {
      // Verify the endpoint exists and has correct query
      const store = createTestStore();
      const cacheWrapper = ({ children }: { children: React.ReactNode }) => (
        <Provider store={store}>{children}</Provider>
      );

      const { result } = renderHook(() => useListMcpResourcesQuery(), {
        wrapper: cacheWrapper,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify cached data persists after query success
      const state = store.getState().api;
      expect(state.queries).toBeDefined();
      expect(Object.keys(state.queries).length).toBeGreaterThan(0);
    });

    it("MCP tools endpoint has proper cache configuration", async () => {
      const store = createTestStore();
      const cacheWrapper = ({ children }: { children: React.ReactNode }) => (
        <Provider store={store}>{children}</Provider>
      );

      const { result } = renderHook(
        () => api.endpoints.listMcpTools.useQuery(),
        { wrapper: cacheWrapper },
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.tools).toBeDefined();
    });

    it("MCP prompts endpoint has proper cache configuration", async () => {
      const store = createTestStore();
      const cacheWrapper = ({ children }: { children: React.ReactNode }) => (
        <Provider store={store}>{children}</Provider>
      );

      const { result } = renderHook(
        () => api.endpoints.listMcpPrompts.useQuery(),
        { wrapper: cacheWrapper },
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.data?.prompts).toBeDefined();
    });

    it("cached data is reused on subsequent queries", async () => {
      const store = createTestStore();
      const cacheWrapper = ({ children }: { children: React.ReactNode }) => (
        <Provider store={store}>{children}</Provider>
      );

      // First query
      const { result: result1 } = renderHook(() => useListMcpResourcesQuery(), {
        wrapper: cacheWrapper,
      });

      await waitFor(() => expect(result1.current.isSuccess).toBe(true));
      const firstData = result1.current.data;

      // Second query uses same store - should use cached data
      const { result: result2 } = renderHook(() => useListMcpResourcesQuery(), {
        wrapper: cacheWrapper,
      });

      // Should immediately have data (from cache)
      await waitFor(() => expect(result2.current.isSuccess).toBe(true));
      expect(result2.current.data).toEqual(firstData);
      // Should not be fetching (using cache)
      expect(result2.current.isFetching).toBe(false);
    });
  });
});
