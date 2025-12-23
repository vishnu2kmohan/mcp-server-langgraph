/**
 * AI API Contract Tests
 *
 * Validates that frontend expectations align with backend API contracts.
 * These tests serve as a contract between frontend and backend teams.
 *
 * Contract Documentation:
 * - POST /api/v1/ai/interpret-command - Natural language command interpretation
 * - GET /api/v1/ai/suggestions - AI suggestions for artifact
 * - POST /api/v1/ai/fetch-url - Fetch and extract content from URL
 */
import {
  describe,
  it,
  expect,
  beforeAll,
  afterAll,
  afterEach,
  vi,
} from "vitest";
import { setupServer } from "msw/node";
import { aiHandlers } from "../mocks/handlers/aiHandlers";
import type { AIInterpretation, Suggestion } from "../ai";

// Setup MSW server with AI handlers
const server = setupServer(...aiHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});
afterAll(() => server.close());

describe("AI API Contract", () => {
  describe("POST /api/v1/ai/interpret-command", () => {
    describe("Request Contract", () => {
      it("accepts JSON body with query field", async () => {
        const response = await fetch("/api/v1/ai/interpret-command", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: "test query" }),
        });

        expect(response.ok).toBe(true);
        expect(response.headers.get("Content-Type")).toContain(
          "application/json",
        );
      });

      it("returns 400 when query field is missing", async () => {
        const response = await fetch("/api/v1/ai/interpret-command", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });

        expect(response.status).toBe(400);
        const data = await response.json();
        expect(data).toHaveProperty("error");
      });
    });

    describe("Response Contract - AIInterpretation", () => {
      it("returns action field (required, string)", async () => {
        const response = await fetch("/api/v1/ai/interpret-command", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: "go to settings" }),
        });

        const data: AIInterpretation = await response.json();
        expect(typeof data.action).toBe("string");
        expect(data.action.length).toBeGreaterThan(0);
      });

      it("returns params field (required, object)", async () => {
        const response = await fetch("/api/v1/ai/interpret-command", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: "navigate to compliance" }),
        });

        const data: AIInterpretation = await response.json();
        expect(typeof data.params).toBe("object");
        expect(data.params).not.toBeNull();
      });

      it("returns confidence field (required, number between 0 and 1)", async () => {
        const response = await fetch("/api/v1/ai/interpret-command", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query: "do something" }),
        });

        const data: AIInterpretation = await response.json();
        expect(typeof data.confidence).toBe("number");
        expect(data.confidence).toBeGreaterThanOrEqual(0);
        expect(data.confidence).toBeLessThanOrEqual(1);
      });

      it("returns valid action types", async () => {
        const queries = [
          "go to compliance", // navigate
          "find workflows", // search
          "toggle canvas", // toggle-panel
          "new chat", // new-chat
        ];

        const validActions = ["navigate", "search", "toggle-panel", "new-chat"];

        for (const query of queries) {
          const response = await fetch("/api/v1/ai/interpret-command", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query }),
          });

          const data: AIInterpretation = await response.json();
          expect(validActions).toContain(data.action);
        }
      });
    });
  });

  describe("GET /api/v1/ai/suggestions", () => {
    describe("Request Contract", () => {
      it("requires artifactId query parameter", async () => {
        const response = await fetch(
          "/api/v1/ai/suggestions?artifactId=test-123",
        );

        expect(response.ok).toBe(true);
        expect(response.headers.get("Content-Type")).toContain(
          "application/json",
        );
      });

      it("returns 400 when artifactId is missing", async () => {
        const response = await fetch("/api/v1/ai/suggestions");

        expect(response.status).toBe(400);
        const data = await response.json();
        expect(data).toHaveProperty("error");
      });
    });

    describe("Response Contract - Suggestion[]", () => {
      it("returns suggestions array", async () => {
        const response = await fetch(
          "/api/v1/ai/suggestions?artifactId=test-123",
        );

        const data = await response.json();
        expect(data).toHaveProperty("suggestions");
        expect(Array.isArray(data.suggestions)).toBe(true);
      });

      it("each suggestion has required fields", async () => {
        const response = await fetch(
          "/api/v1/ai/suggestions?artifactId=test-123",
        );

        const data = await response.json();
        const suggestions: Suggestion[] = data.suggestions;

        suggestions.forEach((suggestion) => {
          // Required fields
          expect(typeof suggestion.id).toBe("string");
          expect(typeof suggestion.type).toBe("string");
          expect(typeof suggestion.content).toBe("string");
          expect(typeof suggestion.confidence).toBe("number");

          // Type must be one of the valid types
          expect(["completion", "refactor", "fix", "explain"]).toContain(
            suggestion.type,
          );

          // Confidence must be between 0 and 1
          expect(suggestion.confidence).toBeGreaterThanOrEqual(0);
          expect(suggestion.confidence).toBeLessThanOrEqual(1);
        });
      });

      it("suggestion.position is optional object", async () => {
        const response = await fetch(
          "/api/v1/ai/suggestions?artifactId=test-123",
        );

        const data = await response.json();
        const suggestions: Suggestion[] = data.suggestions;

        suggestions.forEach((suggestion) => {
          if (suggestion.position !== undefined) {
            expect(typeof suggestion.position.line).toBe("number");
            expect(typeof suggestion.position.column).toBe("number");
          }
        });
      });
    });
  });

  describe("POST /api/v1/ai/fetch-url", () => {
    describe("Request Contract", () => {
      it("accepts JSON body with url field", async () => {
        const response = await fetch("/api/v1/ai/fetch-url", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: "https://example.com" }),
        });

        expect(response.ok).toBe(true);
        expect(response.headers.get("Content-Type")).toContain(
          "application/json",
        );
      });

      it("returns 400 when url field is missing", async () => {
        const response = await fetch("/api/v1/ai/fetch-url", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({}),
        });

        expect(response.status).toBe(400);
      });

      it("returns 422 for invalid URL format", async () => {
        const response = await fetch("/api/v1/ai/fetch-url", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: "not-a-url" }),
        });

        expect(response.status).toBe(422);
      });
    });

    describe("Response Contract - FetchUrlResponse", () => {
      it("returns content field (required, string)", async () => {
        const response = await fetch("/api/v1/ai/fetch-url", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: "https://example.com" }),
        });

        const data = await response.json();
        expect(typeof data.content).toBe("string");
      });

      it("returns title field (required, string)", async () => {
        const response = await fetch("/api/v1/ai/fetch-url", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: "https://example.com" }),
        });

        const data = await response.json();
        expect(typeof data.title).toBe("string");
      });

      it("returns url field (required, string, same as input)", async () => {
        const inputUrl = "https://example.com/page";
        const response = await fetch("/api/v1/ai/fetch-url", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: inputUrl }),
        });

        const data = await response.json();
        expect(data.url).toBe(inputUrl);
      });

      it("returns fetchedAt field (required, ISO 8601 date string)", async () => {
        const response = await fetch("/api/v1/ai/fetch-url", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ url: "https://example.com" }),
        });

        const data = await response.json();
        expect(typeof data.fetchedAt).toBe("string");
        // Validate ISO 8601 format
        expect(() => new Date(data.fetchedAt)).not.toThrow();
        expect(new Date(data.fetchedAt).toISOString()).toBe(data.fetchedAt);
      });
    });
  });

  describe("Error Response Contract", () => {
    it("400 errors return error field with message", async () => {
      const response = await fetch("/api/v1/ai/interpret-command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      expect(response.status).toBe(400);
      const data = await response.json();
      expect(typeof data.error).toBe("string");
      expect(data.error.length).toBeGreaterThan(0);
    });

    it("422 errors return error field with message", async () => {
      const response = await fetch("/api/v1/ai/fetch-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: "invalid-url" }),
      });

      expect(response.status).toBe(422);
      const data = await response.json();
      expect(typeof data.error).toBe("string");
    });
  });
});
