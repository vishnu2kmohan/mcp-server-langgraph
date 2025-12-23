/**
 * Health & Misc API Contract Tests
 *
 * Validates that the MSW handlers match the expected API contract for health,
 * user, agents config, and other miscellaneous endpoints.
 * Uses raw fetch() to test the actual response shapes without RTK Query transformation.
 *
 * These tests document the Health/Misc API contract and catch handler inconsistencies.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { server } from "../mocks/server";

describe("Health & Misc API Contract Tests", () => {
  beforeEach(() => {
    // Server is already started in setup.ts
  });

  afterEach(() => {
    server.resetHandlers();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("GET /api/v1/health", () => {
    it("should return health status", async () => {
      const response = await fetch("/api/v1/health");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      // Required health fields
      expect(data).toHaveProperty("status");
      expect(data).toHaveProperty("version");
      expect(data).toHaveProperty("uptime_seconds");
    });

    it("should return healthy status value", async () => {
      const response = await fetch("/api/v1/health");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(typeof data.status).toBe("string");
      expect(["healthy", "degraded", "unhealthy"]).toContain(data.status);
    });

    it("should return valid version string", async () => {
      const response = await fetch("/api/v1/health");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(typeof data.version).toBe("string");
      expect(data.version.length).toBeGreaterThan(0);
    });

    it("should return non-negative uptime", async () => {
      const response = await fetch("/api/v1/health");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(typeof data.uptime_seconds).toBe("number");
      expect(data.uptime_seconds).toBeGreaterThanOrEqual(0);
    });
  });

  describe("GET /api/v1/user/me", () => {
    it("should return current user info", async () => {
      const response = await fetch("/api/v1/user/me");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      // Required user fields
      expect(data).toHaveProperty("username");
      expect(data).toHaveProperty("email");
      expect(data).toHaveProperty("roles");
    });

    it("should return valid user field types", async () => {
      const response = await fetch("/api/v1/user/me");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(typeof data.username).toBe("string");
      expect(typeof data.email).toBe("string");
      expect(Array.isArray(data.roles)).toBe(true);
    });

    it("should return non-empty username and email", async () => {
      const response = await fetch("/api/v1/user/me");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.username.length).toBeGreaterThan(0);
      expect(data.email.length).toBeGreaterThan(0);
      expect(data.email).toContain("@");
    });

    it("should return at least one role", async () => {
      const response = await fetch("/api/v1/user/me");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.roles.length).toBeGreaterThan(0);
      for (const role of data.roles) {
        expect(typeof role).toBe("string");
      }
    });
  });

  describe("GET /api/v1/agents/config", () => {
    it("should return agent configuration", async () => {
      const response = await fetch("/api/v1/agents/config");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      // Required config fields
      expect(data).toHaveProperty("model");
      expect(data).toHaveProperty("provider");
      expect(data).toHaveProperty("temperature");
      expect(data).toHaveProperty("verification_enabled");
      expect(data).toHaveProperty("tools");
    });

    it("should return valid config field types", async () => {
      const response = await fetch("/api/v1/agents/config");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(typeof data.model).toBe("string");
      expect(typeof data.provider).toBe("string");
      expect(typeof data.temperature).toBe("number");
      expect(typeof data.verification_enabled).toBe("boolean");
      expect(Array.isArray(data.tools)).toBe(true);
    });

    it("should return valid temperature range", async () => {
      const response = await fetch("/api/v1/agents/config");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.temperature).toBeGreaterThanOrEqual(0);
      expect(data.temperature).toBeLessThanOrEqual(2);
    });

    it("should return tools with required fields", async () => {
      const response = await fetch("/api/v1/agents/config");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.tools.length).toBeGreaterThan(0);
      for (const tool of data.tools) {
        expect(tool).toHaveProperty("name");
        expect(tool).toHaveProperty("description");
        expect(typeof tool.name).toBe("string");
        expect(typeof tool.description).toBe("string");
      }
    });
  });

  describe("GET /api/v1/mcp/status", () => {
    it("should return MCP connection status", async () => {
      const response = await fetch("/api/v1/mcp/status");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      // Required status fields
      expect(data).toHaveProperty("connected");
      expect(data).toHaveProperty("server_name");
      expect(data).toHaveProperty("capabilities");
    });

    it("should return valid status field types", async () => {
      const response = await fetch("/api/v1/mcp/status");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(typeof data.connected).toBe("boolean");
      expect(typeof data.server_name).toBe("string");
      expect(Array.isArray(data.capabilities)).toBe(true);
    });

    it("should return valid capability values", async () => {
      const response = await fetch("/api/v1/mcp/status");
      expect(response.ok).toBe(true);

      const data = await response.json();

      const validCapabilities = [
        "tools",
        "resources",
        "prompts",
        "sampling",
        "elicitation",
      ];

      for (const capability of data.capabilities) {
        expect(typeof capability).toBe("string");
        expect(validCapabilities).toContain(capability);
      }
    });
  });

  describe("GET /api/v1/observability/ws/status", () => {
    it("should return observability WebSocket status", async () => {
      const response = await fetch("/api/v1/observability/ws/status");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      // Required status fields
      expect(data).toHaveProperty("connected");
      expect(data).toHaveProperty("active_subscriptions");
    });

    it("should return valid status field types", async () => {
      const response = await fetch("/api/v1/observability/ws/status");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(typeof data.connected).toBe("boolean");
      expect(typeof data.active_subscriptions).toBe("number");
    });

    it("should return non-negative subscription count", async () => {
      const response = await fetch("/api/v1/observability/ws/status");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.active_subscriptions).toBeGreaterThanOrEqual(0);
    });
  });

  describe("GET /api/v1/metrics/heart/aggregate", () => {
    it("should return HEART metrics aggregate", async () => {
      const response = await fetch("/api/v1/metrics/heart/aggregate");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);

      const data = await response.json();

      // Required HEART metrics fields
      expect(data).toHaveProperty("period");
      expect(data).toHaveProperty("nps_score_avg");
      expect(data).toHaveProperty("satisfaction_avg");
      expect(data).toHaveProperty("task_success_rate");
    });

    it("should return valid HEART metric types", async () => {
      const response = await fetch("/api/v1/metrics/heart/aggregate");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(typeof data.period).toBe("string");
      expect(typeof data.nps_score_avg).toBe("number");
      expect(typeof data.satisfaction_avg).toBe("number");
      expect(typeof data.task_success_rate).toBe("number");
    });

    it("should return valid metric ranges", async () => {
      const response = await fetch("/api/v1/metrics/heart/aggregate");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // NPS score: -100 to 100 typically, but avg could be 0-10
      expect(data.nps_score_avg).toBeGreaterThanOrEqual(0);
      expect(data.nps_score_avg).toBeLessThanOrEqual(10);

      // Satisfaction: typically 1-5 scale
      expect(data.satisfaction_avg).toBeGreaterThanOrEqual(0);
      expect(data.satisfaction_avg).toBeLessThanOrEqual(5);

      // Task success rate: 0-1 (percentage as decimal)
      expect(data.task_success_rate).toBeGreaterThanOrEqual(0);
      expect(data.task_success_rate).toBeLessThanOrEqual(1);
    });

    it("should return engagement metrics", async () => {
      const response = await fetch("/api/v1/metrics/heart/aggregate");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // Engagement metrics
      expect(data).toHaveProperty("total_tasks_started");
      expect(data).toHaveProperty("total_tasks_completed");
      expect(data).toHaveProperty("avg_session_duration_ms");

      expect(typeof data.total_tasks_started).toBe("number");
      expect(typeof data.total_tasks_completed).toBe("number");
      expect(typeof data.avg_session_duration_ms).toBe("number");
    });

    it("should return adoption metrics", async () => {
      const response = await fetch("/api/v1/metrics/heart/aggregate");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // Adoption metrics
      expect(data).toHaveProperty("new_users_count");
      expect(data).toHaveProperty("avg_return_visits");

      expect(typeof data.new_users_count).toBe("number");
      expect(typeof data.avg_return_visits).toBe("number");
    });
  });
});
