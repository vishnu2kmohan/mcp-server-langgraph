/**
 * MCP Handlers Tests (TDD)
 *
 * Tests for MSW handlers covering MCP (Model Context Protocol) endpoints.
 *
 * Endpoints covered:
 * - GET /api/v1/mcp/resources - List resources
 * - GET /api/v1/mcp/resources/content - Read resource content
 * - GET /api/v1/mcp/tools - List tools
 * - POST /api/v1/mcp/tools/call - Invoke tool
 * - POST /api/v1/mcp/sampling - Request sampling
 * - POST /api/v1/mcp/elicitation - Request elicitation
 * - GET /api/v1/mcp/prompts - List prompts
 * - POST /api/v1/mcp/prompts/get - Get prompt with arguments
 * - GET /api/v1/mcp/tasks - List tasks
 * - GET /api/v1/mcp/tasks/:id - Get task by ID
 * - POST /api/v1/mcp/tasks/:id/cancel - Cancel task
 *
 * Following TDD: RED phase - write failing tests first
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { http as _http, HttpResponse as _HttpResponse } from "msw";
import { server } from "../server";
import { transformSnakeToCamel } from "../../api/transforms";
import {
  mcpHandlers as _mcpHandlers,
  createMockResource,
  createMockTool,
  createMockPrompt,
  createMockTask,
  createErrorHandler,
  createNetworkErrorHandler,
  createDelayedHandler,
  MOCK_RESOURCES,
  MOCK_TOOLS,
  MOCK_PROMPTS,
} from "./mcpHandlers";

// =============================================================================
// Test Setup
// =============================================================================

// Use the global server from ../server (started in test/setup.ts)
// The global server includes mcpHandlers, so we just need to reset after each test
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});

// =============================================================================
// Tests
// =============================================================================

describe("MCP Handlers", () => {
  describe("Mock Data Factories", () => {
    it("creates mock resource with default values", () => {
      const resource = createMockResource();

      expect(resource).toHaveProperty("uri");
      expect(resource).toHaveProperty("name");
      expect(resource).toHaveProperty("mimeType");
    });

    it("creates mock resource with overrides", () => {
      const resource = createMockResource({
        uri: "file:///custom/path.txt",
        name: "custom.txt",
      });

      expect(resource.uri).toBe("file:///custom/path.txt");
      expect(resource.name).toBe("custom.txt");
    });

    it("creates mock tool with default values", () => {
      const tool = createMockTool();

      expect(tool).toHaveProperty("name");
      expect(tool).toHaveProperty("description");
      expect(tool).toHaveProperty("inputSchema");
    });

    it("creates mock tool with overrides", () => {
      const tool = createMockTool({
        name: "custom_tool",
        description: "A custom tool",
      });

      expect(tool.name).toBe("custom_tool");
      expect(tool.description).toBe("A custom tool");
    });

    it("creates mock prompt with default values", () => {
      const prompt = createMockPrompt();

      expect(prompt).toHaveProperty("name");
      expect(prompt).toHaveProperty("description");
    });

    it("creates mock task with default values", () => {
      const task = createMockTask();

      expect(task).toHaveProperty("id");
      expect(task).toHaveProperty("status");
      expect(task).toHaveProperty("createdAt");
    });
  });

  describe("GET /api/v1/mcp/resources", () => {
    it("returns list of resources", async () => {
      const response = await fetch("/api/v1/mcp/resources");
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data).toHaveProperty("resources");
      expect(Array.isArray(data.resources)).toBe(true);
    });

    it("returns resources with expected structure", async () => {
      const response = await fetch("/api/v1/mcp/resources");
      const data = await response.json();

      expect(data.resources.length).toBeGreaterThan(0);
      const resource = data.resources[0];
      expect(resource).toHaveProperty("uri");
      expect(resource).toHaveProperty("name");
    });
  });

  describe("GET /api/v1/mcp/resources/content", () => {
    it("returns resource content for valid URI", async () => {
      const uri = encodeURIComponent("file:///project/README.md");
      const response = await fetch(`/api/v1/mcp/resources/content?uri=${uri}`);
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data).toHaveProperty("contents");
      expect(Array.isArray(data.contents)).toBe(true);
    });

    it("returns 404 for unknown resource URI", async () => {
      const uri = encodeURIComponent("file:///nonexistent/file.txt");
      const response = await fetch(`/api/v1/mcp/resources/content?uri=${uri}`);

      expect(response.status).toBe(404);
    });

    it("returns text content for text resources", async () => {
      const uri = encodeURIComponent("file:///project/README.md");
      const response = await fetch(`/api/v1/mcp/resources/content?uri=${uri}`);
      const rawData = await response.json();
      // Transform snake_case API response to camelCase
      const data = transformSnakeToCamel(rawData);

      expect(data.contents[0]).toHaveProperty("text");
      expect(data.contents[0].mimeType).toMatch(/^text\//);
    });
  });

  describe("GET /api/v1/mcp/tools", () => {
    it("returns list of tools", async () => {
      const response = await fetch("/api/v1/mcp/tools");
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data).toHaveProperty("tools");
      expect(Array.isArray(data.tools)).toBe(true);
    });

    it("returns tools with input schema", async () => {
      const response = await fetch("/api/v1/mcp/tools");
      const rawData = await response.json();
      // Transform snake_case API response to camelCase
      const data = transformSnakeToCamel(rawData);

      expect(data.tools.length).toBeGreaterThan(0);
      const tool = data.tools[0];
      expect(tool).toHaveProperty("name");
      expect(tool).toHaveProperty("inputSchema");
    });
  });

  describe("POST /api/v1/mcp/tools/call", () => {
    it("invokes tool and returns result", async () => {
      const response = await fetch("/api/v1/mcp/tools/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "read_file",
          arguments: { path: "/test/file.txt" },
        }),
      });
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data).toHaveProperty("content");
    });

    it("returns error for unknown tool", async () => {
      const response = await fetch("/api/v1/mcp/tools/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "nonexistent_tool",
          arguments: {},
        }),
      });

      expect(response.status).toBe(404);
    });
  });

  describe("POST /api/v1/mcp/sampling", () => {
    it("returns sampling completion", async () => {
      const response = await fetch("/api/v1/mcp/sampling", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [
            { role: "user", content: { type: "text", text: "Hello" } },
          ],
          maxTokens: 100,
        }),
      });
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data).toHaveProperty("role");
      expect(data).toHaveProperty("content");
      expect(data.role).toBe("assistant");
    });

    it("respects model parameter", async () => {
      const response = await fetch("/api/v1/mcp/sampling", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content: { type: "text", text: "Hi" } }],
          maxTokens: 50,
          modelPreferences: { hints: [{ name: "claude-3" }] },
        }),
      });
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data).toHaveProperty("model");
    });
  });

  describe("POST /api/v1/mcp/elicitation", () => {
    it("returns elicitation response with accept action", async () => {
      const response = await fetch("/api/v1/mcp/elicitation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: "Please enter your name",
          schema: { type: "object", properties: { name: { type: "string" } } },
        }),
      });
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data).toHaveProperty("action");
      expect(["accept", "decline"]).toContain(data.action);
    });

    it("returns content when action is accept", async () => {
      const response = await fetch("/api/v1/mcp/elicitation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: "Enter details",
          schema: null,
        }),
      });
      const data = await response.json();

      if (data.action === "accept") {
        expect(data).toHaveProperty("content");
      }
    });
  });

  describe("GET /api/v1/mcp/prompts", () => {
    it("returns list of prompts", async () => {
      const response = await fetch("/api/v1/mcp/prompts");
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data).toHaveProperty("prompts");
      expect(Array.isArray(data.prompts)).toBe(true);
    });

    it("returns prompts with arguments schema", async () => {
      const response = await fetch("/api/v1/mcp/prompts");
      const data = await response.json();

      expect(data.prompts.length).toBeGreaterThan(0);
      const prompt = data.prompts[0];
      expect(prompt).toHaveProperty("name");
      expect(prompt).toHaveProperty("description");
    });
  });

  describe("POST /api/v1/mcp/prompts/get", () => {
    it("returns prompt messages", async () => {
      const response = await fetch("/api/v1/mcp/prompts/get", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "summarize",
          arguments: { text: "Some text to summarize" },
        }),
      });
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data).toHaveProperty("messages");
      expect(Array.isArray(data.messages)).toBe(true);
    });

    it("returns 404 for unknown prompt", async () => {
      const response = await fetch("/api/v1/mcp/prompts/get", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "nonexistent_prompt",
          arguments: {},
        }),
      });

      expect(response.status).toBe(404);
    });
  });

  describe("GET /api/v1/mcp/tasks", () => {
    it("returns list of tasks", async () => {
      const response = await fetch("/api/v1/mcp/tasks");
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data).toHaveProperty("tasks");
      expect(Array.isArray(data.tasks)).toBe(true);
    });
  });

  describe("GET /api/v1/mcp/tasks/:id", () => {
    it("returns task by ID", async () => {
      const response = await fetch("/api/v1/mcp/tasks/task-1");
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data).toHaveProperty("id");
      expect(data).toHaveProperty("status");
    });

    it("returns 404 for unknown task", async () => {
      const response = await fetch("/api/v1/mcp/tasks/nonexistent-task");

      expect(response.status).toBe(404);
    });
  });

  describe("POST /api/v1/mcp/tasks/:id/cancel", () => {
    it("cancels task and returns updated task", async () => {
      const response = await fetch("/api/v1/mcp/tasks/task-1/cancel", {
        method: "POST",
      });
      const data = await response.json();

      expect(response.status).toBe(200);
      expect(data).toHaveProperty("id");
      expect(data.status).toBe("cancelled");
    });

    it("returns 404 for unknown task", async () => {
      const response = await fetch(
        "/api/v1/mcp/tasks/nonexistent-task/cancel",
        {
          method: "POST",
        },
      );

      expect(response.status).toBe(404);
    });
  });

  describe("Default Mock Data", () => {
    it("MOCK_RESOURCES contains expected resources", () => {
      expect(MOCK_RESOURCES.length).toBeGreaterThan(0);
      expect(MOCK_RESOURCES.some((r) => r.uri.includes("README"))).toBe(true);
    });

    it("MOCK_TOOLS contains expected tools", () => {
      expect(MOCK_TOOLS.length).toBeGreaterThan(0);
      expect(MOCK_TOOLS.some((t) => t.name === "read_file")).toBe(true);
    });

    it("MOCK_PROMPTS contains expected prompts", () => {
      expect(MOCK_PROMPTS.length).toBeGreaterThan(0);
      expect(MOCK_PROMPTS.some((p) => p.name === "summarize")).toBe(true);
    });
  });

  // ===========================================================================
  // Error Scenario Factories
  // ===========================================================================

  describe("Error Scenario Factories", () => {
    describe("createErrorHandler", () => {
      it("creates handler that returns specified error", async () => {
        const errorHandler = createErrorHandler(
          "get",
          "/api/v1/mcp/resources",
          500,
          "Internal server error",
        );
        server.use(errorHandler);

        const response = await fetch("/api/v1/mcp/resources");
        const data = await response.json();

        expect(response.status).toBe(500);
        expect(data.error).toBe("Internal server error");
      });

      it("creates handler for POST methods", async () => {
        const errorHandler = createErrorHandler(
          "post",
          "/api/v1/mcp/tools/call",
          503,
          "Service unavailable",
        );
        server.use(errorHandler);

        const response = await fetch("/api/v1/mcp/tools/call", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: "read_file", arguments: {} }),
        });
        const data = await response.json();

        expect(response.status).toBe(503);
        expect(data.error).toBe("Service unavailable");
      });

      it("supports custom error details", async () => {
        const errorHandler = createErrorHandler(
          "get",
          "/api/v1/mcp/tasks",
          400,
          "Validation error",
          { field: "session_id", issue: "required" },
        );
        server.use(errorHandler);

        const response = await fetch("/api/v1/mcp/tasks");
        const data = await response.json();

        expect(response.status).toBe(400);
        expect(data.error).toBe("Validation error");
        expect(data.details).toEqual({
          field: "session_id",
          issue: "required",
        });
      });
    });

    describe("createNetworkErrorHandler", () => {
      it("creates handler that simulates network failure", async () => {
        const networkErrorHandler = createNetworkErrorHandler(
          "get",
          "/api/v1/mcp/resources",
        );
        server.use(networkErrorHandler);

        await expect(fetch("/api/v1/mcp/resources")).rejects.toThrow();
      });

      it("works for POST requests", async () => {
        const networkErrorHandler = createNetworkErrorHandler(
          "post",
          "/api/v1/mcp/sampling",
        );
        server.use(networkErrorHandler);

        await expect(
          fetch("/api/v1/mcp/sampling", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ messages: [], maxTokens: 100 }),
          }),
        ).rejects.toThrow();
      });
    });

    describe("createDelayedHandler", () => {
      it("creates handler that delays response", async () => {
        const delayedHandler = createDelayedHandler(
          "get",
          "/api/v1/mcp/resources",
          50, // 50ms delay
          { resources: [] },
        );
        server.use(delayedHandler);

        const start = Date.now();
        const response = await fetch("/api/v1/mcp/resources");
        const elapsed = Date.now() - start;
        const data = await response.json();

        expect(response.status).toBe(200);
        expect(elapsed).toBeGreaterThanOrEqual(45); // Allow some timing variance
        expect(data.resources).toEqual([]);
      });

      it("works for POST requests with custom response", async () => {
        const delayedHandler = createDelayedHandler(
          "post",
          "/api/v1/mcp/tools/call",
          30,
          {
            content: [{ type: "text", text: "Delayed result" }],
            isError: false,
          },
        );
        server.use(delayedHandler);

        const response = await fetch("/api/v1/mcp/tools/call", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ name: "read_file", arguments: {} }),
        });
        const data = await response.json();

        expect(response.status).toBe(200);
        expect(data.content[0].text).toBe("Delayed result");
      });
    });
  });
});
