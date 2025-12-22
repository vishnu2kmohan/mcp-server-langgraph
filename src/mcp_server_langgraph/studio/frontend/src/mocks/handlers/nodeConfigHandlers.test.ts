/**
 * Node Config Handlers Tests
 *
 * TDD tests for Node Config Assistant MSW handlers.
 * Tests cover:
 * - POST /api/v1/ai/node-config/help - Node configuration help
 * - Request validation
 * - Response formatting
 * - Error scenarios
 */

import { describe, it, expect, beforeAll, afterAll, afterEach } from "vitest";
import { setupServer } from "msw/node";
import { nodeConfigHandlers, mockNodeConfigHelpResponse } from "./nodeConfigHandlers";
import type { NodeConfigHelpRequest, NodeConfigHelpResponse } from "../../types/api";

// Setup MSW server with handlers
const server = setupServer(...nodeConfigHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("nodeConfigHandlers", () => {
  describe("POST /api/v1/ai/node-config/help", () => {
    const endpoint = "/api/v1/ai/node-config/help";

    it("returns help response for valid request", async () => {
      const request: NodeConfigHelpRequest = {
        node_type: "llm",
        node_config: { model: "gpt-4", temperature: 0.7 },
        question: "How do I configure the model temperature?",
      };

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data: NodeConfigHelpResponse = await response.json();
      expect(data.answer).toBeDefined();
      expect(typeof data.answer).toBe("string");
    });

    it("includes suggested_config in response for config questions", async () => {
      const request: NodeConfigHelpRequest = {
        node_type: "llm",
        node_config: { model: "gpt-4" },
        question: "What is the optimal configuration for code generation?",
      };

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      const data: NodeConfigHelpResponse = await response.json();
      expect(data.suggested_config).toBeDefined();
      expect(typeof data.suggested_config).toBe("object");
    });

    it("includes examples in response for how-to questions", async () => {
      const request: NodeConfigHelpRequest = {
        node_type: "prompt",
        node_config: { template: "Hello {name}" },
        question: "How do I use template variables?",
      };

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      const data: NodeConfigHelpResponse = await response.json();
      expect(data.examples).toBeDefined();
      expect(Array.isArray(data.examples)).toBe(true);
      expect(data.examples!.length).toBeGreaterThan(0);
    });

    it("returns 400 when node_type is missing", async () => {
      const request = {
        node_config: { model: "gpt-4" },
        question: "How do I configure this?",
      };

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      expect(response.ok).toBe(false);
      expect(response.status).toBe(400);

      const error = await response.json();
      expect(error.error).toContain("node_type");
    });

    it("returns 400 when question is missing", async () => {
      const request = {
        node_type: "llm",
        node_config: { model: "gpt-4" },
      };

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      expect(response.ok).toBe(false);
      expect(response.status).toBe(400);

      const error = await response.json();
      expect(error.error).toContain("question");
    });

    it("returns 400 when node_config is missing", async () => {
      const request = {
        node_type: "llm",
        question: "How do I configure this?",
      };

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      expect(response.ok).toBe(false);
      expect(response.status).toBe(400);

      const error = await response.json();
      expect(error.error).toContain("node_config");
    });

    it("accepts optional context field", async () => {
      const request: NodeConfigHelpRequest = {
        node_type: "llm",
        node_config: { model: "gpt-4" },
        question: "Why is my prompt not working?",
        context: "I'm building a code review agent",
      };

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);
    });

    it("handles different node types", async () => {
      const nodeTypes = ["llm", "prompt", "tool", "memory", "router", "retriever"];

      for (const nodeType of nodeTypes) {
        const request: NodeConfigHelpRequest = {
          node_type: nodeType,
          node_config: {},
          question: `How do I configure a ${nodeType} node?`,
        };

        const response = await fetch(endpoint, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(request),
        });

        expect(response.ok).toBe(true);

        const data: NodeConfigHelpResponse = await response.json();
        expect(data.answer).toBeDefined();
      }
    });

    it("returns context-aware response for complex config", async () => {
      const request: NodeConfigHelpRequest = {
        node_type: "llm",
        node_config: {
          model: "gpt-4",
          temperature: 0.7,
          max_tokens: 1000,
          top_p: 0.9,
          frequency_penalty: 0.5,
        },
        question: "Should I adjust my temperature setting?",
      };

      const response = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(request),
      });

      const data: NodeConfigHelpResponse = await response.json();
      expect(data.answer).toBeDefined();
      // The response should be contextual based on the existing config
      expect(data.answer.length).toBeGreaterThan(0);
    });
  });

  describe("Mock Data Exports", () => {
    it("exports mockNodeConfigHelpResponse with required fields", () => {
      expect(mockNodeConfigHelpResponse).toBeDefined();
      expect(mockNodeConfigHelpResponse.answer).toBeDefined();
      expect(typeof mockNodeConfigHelpResponse.answer).toBe("string");
    });
  });
});
