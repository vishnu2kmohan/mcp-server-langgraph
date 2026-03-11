/**
 * MCP API Contract Tests
 *
 * Validates that the MSW handlers match the expected API contract for MCP endpoints.
 * Uses raw fetch() to test the actual response shapes without RTK Query transformation.
 *
 * These tests document the MCP protocol API contract and catch handler inconsistencies.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { server } from "../mocks/server";

describe("MCP API Contract Tests", () => {
  beforeEach(() => {
    // Server is already started in setup.ts
  });

  afterEach(() => {
    server.resetHandlers();
    vi.clearAllMocks();
  });

  describe("GET /api/v1/mcp/resources", () => {
    it("should return resources array", async () => {
      const response = await fetch("/api/v1/mcp/resources");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty("resources");
      expect(Array.isArray(data.resources)).toBe(true);
    });

    it("should return resources with required MCP fields (snake_case from API)", async () => {
      const response = await fetch("/api/v1/mcp/resources");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.resources.length).toBeGreaterThan(0);
      const resource = data.resources[0];

      // Required MCP resource fields (snake_case from apiJsonResponse transform)
      expect(resource).toHaveProperty("uri");
      expect(resource).toHaveProperty("name");
      expect(resource).toHaveProperty("mime_type");

      // Type validation
      expect(typeof resource.uri).toBe("string");
      expect(typeof resource.name).toBe("string");
      expect(typeof resource.mime_type).toBe("string");
    });
  });

  describe("GET /api/v1/mcp/resources/content", () => {
    it("should return resource content", async () => {
      const uri = encodeURIComponent("file:///project/README.md");
      const response = await fetch(`/api/v1/mcp/resources/content?uri=${uri}`);
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty("contents");
      expect(Array.isArray(data.contents)).toBe(true);
      expect(data.contents.length).toBeGreaterThan(0);

      const content = data.contents[0];
      expect(content).toHaveProperty("uri");
      expect(content).toHaveProperty("text");
      expect(content).toHaveProperty("mime_type");
    });

    it("should return 400 when uri is missing", async () => {
      const response = await fetch("/api/v1/mcp/resources/content");
      expect(response.status).toBe(400);

      const data = await response.json();
      expect(data).toHaveProperty("error");
    });

    it("should return 404 when resource not found", async () => {
      const uri = encodeURIComponent("file:///nonexistent.txt");
      const response = await fetch(`/api/v1/mcp/resources/content?uri=${uri}`);
      expect(response.status).toBe(404);

      const data = await response.json();
      expect(data).toHaveProperty("error");
    });
  });

  describe("GET /api/v1/mcp/tools", () => {
    it("should return tools array", async () => {
      const response = await fetch("/api/v1/mcp/tools");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty("tools");
      expect(Array.isArray(data.tools)).toBe(true);
    });

    it("should return tools with required MCP fields", async () => {
      const response = await fetch("/api/v1/mcp/tools");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.tools.length).toBeGreaterThan(0);
      const tool = data.tools[0];

      // Required MCP tool fields (snake_case from apiJsonResponse transform)
      expect(tool).toHaveProperty("name");
      expect(tool).toHaveProperty("description");
      expect(tool).toHaveProperty("input_schema");

      // Type validation
      expect(typeof tool.name).toBe("string");
      expect(typeof tool.description).toBe("string");
      expect(typeof tool.input_schema).toBe("object");
    });
  });

  describe("POST /api/v1/mcp/tools/call", () => {
    it("should invoke tool and return result", async () => {
      const response = await fetch("/api/v1/mcp/tools/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "read_file",
          arguments: { path: "/test.txt" },
        }),
      });
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty("content");
      expect(data).toHaveProperty("is_error");
      expect(Array.isArray(data.content)).toBe(true);
      expect(typeof data.is_error).toBe("boolean");
    });

    it("should return 404 for unknown tool", async () => {
      const response = await fetch("/api/v1/mcp/tools/call", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "nonexistent_tool",
          arguments: {},
        }),
      });
      expect(response.status).toBe(404);

      const data = await response.json();
      expect(data).toHaveProperty("error");
    });
  });

  describe("POST /api/v1/mcp/sampling", () => {
    it("should return sampling response", async () => {
      const response = await fetch("/api/v1/mcp/sampling", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content: "Hello" }],
          maxTokens: 100,
        }),
      });
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty("role");
      expect(data).toHaveProperty("content");
      expect(data).toHaveProperty("model");
      expect(data).toHaveProperty("stop_reason");

      expect(data.role).toBe("assistant");
      expect(typeof data.content).toBe("object");
      expect(typeof data.model).toBe("string");
    });

    it("should respect model hints", async () => {
      const response = await fetch("/api/v1/mcp/sampling", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content: "Hello" }],
          maxTokens: 100,
          modelPreferences: { hints: [{ name: "gpt-4" }] },
        }),
      });
      expect(response.ok).toBe(true);

      const data = await response.json();
      expect(data.model).toBe("gpt-4");
    });
  });

  describe("POST /api/v1/mcp/elicitation", () => {
    it("should return elicitation response", async () => {
      const response = await fetch("/api/v1/mcp/elicitation", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          schema: {
            type: "object",
            properties: {
              name: { type: "string" },
              email: { type: "string" },
            },
          },
        }),
      });
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty("action");
      expect(data).toHaveProperty("content");

      expect(data.action).toBe("accept");
      expect(typeof data.content).toBe("object");
    });
  });

  describe("GET /api/v1/mcp/prompts", () => {
    it("should return prompts array", async () => {
      const response = await fetch("/api/v1/mcp/prompts");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty("prompts");
      expect(Array.isArray(data.prompts)).toBe(true);
    });

    it("should return prompts with required MCP fields", async () => {
      const response = await fetch("/api/v1/mcp/prompts");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.prompts.length).toBeGreaterThan(0);
      const prompt = data.prompts[0];

      // Required MCP prompt fields
      expect(prompt).toHaveProperty("name");
      expect(prompt).toHaveProperty("description");

      // Type validation
      expect(typeof prompt.name).toBe("string");
      expect(typeof prompt.description).toBe("string");

      // Arguments are optional but if present should be an array
      if (prompt.arguments) {
        expect(Array.isArray(prompt.arguments)).toBe(true);
      }
    });
  });

  describe("POST /api/v1/mcp/prompts/get", () => {
    it("should return prompt with messages", async () => {
      const response = await fetch("/api/v1/mcp/prompts/get", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "summarize",
          arguments: { text: "This is some text to summarize" },
        }),
      });
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty("description");
      expect(data).toHaveProperty("messages");

      expect(typeof data.description).toBe("string");
      expect(Array.isArray(data.messages)).toBe(true);
    });

    it("should return 404 for unknown prompt", async () => {
      const response = await fetch("/api/v1/mcp/prompts/get", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: "nonexistent_prompt",
          arguments: {},
        }),
      });
      expect(response.status).toBe(404);

      const data = await response.json();
      expect(data).toHaveProperty("error");
    });
  });

  describe("GET /api/v1/mcp/tasks", () => {
    it("should return tasks array", async () => {
      const response = await fetch("/api/v1/mcp/tasks");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty("tasks");
      expect(Array.isArray(data.tasks)).toBe(true);
    });

    it("should return tasks with required fields", async () => {
      const response = await fetch("/api/v1/mcp/tasks");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.tasks.length).toBeGreaterThan(0);
      const task = data.tasks[0];

      // Required task fields (snake_case from apiJsonResponse transform)
      expect(task).toHaveProperty("id");
      expect(task).toHaveProperty("status");
      expect(task).toHaveProperty("created_at");

      // Type validation
      expect(typeof task.id).toBe("string");
      expect(typeof task.status).toBe("string");
      expect(typeof task.created_at).toBe("string");

      // Status should be one of valid values
      expect([
        "pending",
        "running",
        "completed",
        "cancelled",
        "failed",
      ]).toContain(task.status);
    });
  });

  describe("GET /api/v1/mcp/tasks/:id", () => {
    it("should return task by ID", async () => {
      const response = await fetch("/api/v1/mcp/tasks/task-1");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty("id");
      expect(data).toHaveProperty("status");
      expect(data.id).toBe("task-1");
    });

    it("should return 404 for unknown task", async () => {
      const response = await fetch("/api/v1/mcp/tasks/nonexistent-task");
      expect(response.status).toBe(404);

      const data = await response.json();
      expect(data).toHaveProperty("error");
    });
  });

  describe("POST /api/v1/mcp/tasks/:id/cancel", () => {
    it("should cancel task and return updated status", async () => {
      const response = await fetch("/api/v1/mcp/tasks/task-1/cancel", {
        method: "POST",
      });
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      expect(data).toHaveProperty("id");
      expect(data).toHaveProperty("status");
      expect(data.status).toBe("cancelled");
      expect(data).toHaveProperty("updated_at");
    });

    it("should return 404 for unknown task", async () => {
      const response = await fetch(
        "/api/v1/mcp/tasks/nonexistent-task/cancel",
        {
          method: "POST",
        },
      );
      expect(response.status).toBe(404);

      const data = await response.json();
      expect(data).toHaveProperty("error");
    });
  });
});
