/**
 * MSW Handlers Tests
 *
 * These tests verify that MSW handlers work correctly
 * and demonstrate how to use MSW in tests.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { http, HttpResponse } from "msw";
import {
  server,
  mockWorkflows,
  mockConnections,
  mockHealthStatus,
  createServerErrorHandler,
} from "./server";

describe("MSW Handlers", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("Health Endpoint", () => {
    it("should return healthy status", async () => {
      const response = await fetch("/api/v1/health");
      const data = await response.json();

      expect(response.ok).toBe(true);
      expect(data.status).toBe("healthy");
    });

    it("should allow overriding health status", async () => {
      // Override the default handler for this test
      server.use(
        http.get("/api/v1/health", () =>
          HttpResponse.json({ status: "unhealthy", version: "1.0.0" }),
        ),
      );

      const response = await fetch("/api/v1/health");
      const data = await response.json();

      expect(data.status).toBe("unhealthy");
    });
  });

  describe("Workflows Endpoint", () => {
    it("should return mock workflows", async () => {
      const response = await fetch("/api/v1/workflows");
      const data = await response.json();

      expect(response.ok).toBe(true);
      expect(data.items).toHaveLength(mockWorkflows.length);
    });

    it("should filter workflows by search", async () => {
      const response = await fetch("/api/v1/workflows?search=Data");
      const data = await response.json();

      expect(response.ok).toBe(true);
      expect(
        data.items.every((w: { name: string }) => w.name.includes("Data")),
      ).toBe(true);
    });

    it("should return 404 for non-existent workflow", async () => {
      const response = await fetch("/api/v1/workflows/non-existent");

      expect(response.status).toBe(404);
    });
  });

  describe("Connections Endpoint", () => {
    it("should return mock connections", async () => {
      const response = await fetch("/api/v1/connections");
      const data = await response.json();

      expect(response.ok).toBe(true);
      expect(data.items).toHaveLength(mockConnections.length);
    });

    it("should filter connections by status", async () => {
      const response = await fetch("/api/v1/connections?status=connected");
      const data = await response.json();

      expect(response.ok).toBe(true);
      expect(
        data.items.every((c: { status: string }) => c.status === "connected"),
      ).toBe(true);
    });
  });

  describe("Cost Endpoints", () => {
    it("should return cost summary", async () => {
      const response = await fetch("/api/v1/cost/summary");
      const data = await response.json();

      expect(response.ok).toBe(true);
      expect(typeof data.total_cost).toBe("number");
      expect(typeof data.total_tokens).toBe("number");
    });

    it("should return cost by model", async () => {
      const response = await fetch("/api/v1/cost/by-model");
      const data = await response.json();

      expect(response.ok).toBe(true);
      expect(Array.isArray(data)).toBe(true);
      expect(data[0]).toHaveProperty("model");
      expect(data[0]).toHaveProperty("cost");
      expect(data[0]).toHaveProperty("requests");
    });

    it("should return cost history", async () => {
      const response = await fetch("/api/v1/cost/history");
      const data = await response.json();

      expect(response.ok).toBe(true);
      expect(Array.isArray(data)).toBe(true);
      expect(data[0]).toHaveProperty("date");
      expect(data[0]).toHaveProperty("cost");
    });
  });

  describe("OAuth2 Callback", () => {
    it("should handle successful callback", async () => {
      const response = await fetch("/api/v1/connections/oauth/callback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: "test-code", state: "test-state" }),
      });
      const data = await response.json();

      expect(response.ok).toBe(true);
      expect(data.success).toBe(true);
      expect(data.connection_id).toBeDefined();
    });

    it("should return 400 for missing code", async () => {
      const response = await fetch("/api/v1/connections/oauth/callback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state: "test-state" }),
      });

      expect(response.status).toBe(400);
    });

    it("should return 400 for missing state", async () => {
      const response = await fetch("/api/v1/connections/oauth/callback", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code: "test-code" }),
      });

      expect(response.status).toBe(400);
    });
  });

  describe("Error Handler Factories", () => {
    it("should create server error handler", async () => {
      server.use(createServerErrorHandler("/api/v1/test-error"));

      const response = await fetch("/api/v1/test-error");

      expect(response.status).toBe(500);
    });
  });

  describe("Mock Data Verification", () => {
    it("should have correct mock health status", () => {
      expect(mockHealthStatus.status).toBe("healthy");
      expect(mockHealthStatus.version).toBeDefined();
    });

    it("should have mock workflows with required fields", () => {
      mockWorkflows.forEach((workflow) => {
        expect(workflow.id).toBeDefined();
        expect(workflow.name).toBeDefined();
        expect(workflow.created_at).toBeDefined();
      });
    });

    it("should have mock connections with required fields", () => {
      mockConnections.forEach((connection) => {
        expect(connection.id).toBeDefined();
        expect(connection.name).toBeDefined();
        expect(connection.url).toBeDefined();
        expect(connection.auth_type).toBeDefined();
        expect(connection.status).toBeDefined();
      });
    });
  });
});
