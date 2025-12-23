/**
 * Handlers Ordering Validation Tests
 *
 * Validates that MSW handlers in handlers.ts are correctly ordered.
 * Static paths MUST be defined BEFORE parameterized paths to avoid conflicts.
 *
 * Example issue: /connections/:id defined before /connections/templates
 * would cause /connections/templates to match :id handler with id="templates"
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { server } from "../server";

// These tests use the default handlers from handlers.ts via the server

describe("handlers.ts Ordering Validation", () => {
  beforeEach(() => {
    // Server is already started in setup.ts
  });

  afterEach(() => {
    server.resetHandlers();
    vi.clearAllMocks();
  });

  describe("Connection Handlers Ordering", () => {
    it("should match /connections/templates as templates handler, not :id", async () => {
      const response = await fetch("/api/v1/connections/templates");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // If ordering is correct, we should get templates array
      // If ordering is wrong, we'd get a single connection with id="templates"
      expect(data).toHaveProperty("templates");
      expect(Array.isArray(data.templates)).toBe(true);
    });

    it("should match /connections/audit/logs as audit handler, not :id", async () => {
      const response = await fetch("/api/v1/connections/audit/logs");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // If ordering is correct, we should get audit logs array
      expect(data).toHaveProperty("items");
      expect(Array.isArray(data.items)).toBe(true);
    });

    it("should match /connections/bulk/test as bulk handler, not :id", async () => {
      const response = await fetch("/api/v1/connections/bulk/test", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ connection_ids: ["conn-1"] }),
      });
      expect(response.ok).toBe(true);

      const data = await response.json();

      // If ordering is correct, we should get bulk test results
      expect(data).toHaveProperty("results");
      expect(Array.isArray(data.results)).toBe(true);
    });

    it("should still match /connections/:id for actual IDs", async () => {
      const response = await fetch("/api/v1/connections/conn-1");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // Should get a single connection object with id
      expect(data).toHaveProperty("id");
      expect(data).toHaveProperty("name");
      expect(data).toHaveProperty("status");
    });
  });

  describe("Workflow Handlers Ordering", () => {
    it("should match /workflows/shared-with-me as static handler, not :id", async () => {
      const response = await fetch("/api/v1/workflows/shared-with-me");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // If ordering is correct, we should get an array of shared workflows
      // If ordering is wrong, we'd get a 404 because :id handler wouldn't find id="shared-with-me"
      expect(Array.isArray(data)).toBe(true);
      expect(data.length).toBeGreaterThan(0);
      expect(data[0]).toHaveProperty("id");
      expect(data[0]).toHaveProperty("name");
    });

    it("should still match /workflows/:id for actual IDs", async () => {
      const response = await fetch("/api/v1/workflows/wf-1");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data).toHaveProperty("id");
      expect(data).toHaveProperty("name");
    });
  });

  describe("Session Handlers Ordering", () => {
    it("should match /sessions/generate-title as static handler, not :id", async () => {
      const response = await fetch("/api/v1/sessions/generate-title", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          messages: [{ role: "user", content: "Hello world" }],
        }),
      });
      expect(response.ok).toBe(true);

      const data = await response.json();

      // If ordering is correct, we should get generated title
      // If ordering is wrong, we'd get a 404 because :sessionId handler wouldn't find id="generate-title"
      expect(data).toHaveProperty("title");
      expect(typeof data.title).toBe("string");
      expect(data.title.length).toBeGreaterThan(0);
    });

    it("should still match /sessions/:id for actual IDs", async () => {
      const response = await fetch("/api/v1/sessions/session-1");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data).toHaveProperty("id");
      expect(data).toHaveProperty("name");
    });
  });
});
