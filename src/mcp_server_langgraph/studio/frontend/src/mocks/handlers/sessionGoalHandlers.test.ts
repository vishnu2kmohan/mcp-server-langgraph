/**
 * Session Goal Handlers Tests
 *
 * TDD tests for MSW handlers that mock session goal API endpoints.
 * These handlers support dynamic session IDs for E2E and integration tests.
 *
 * Written FIRST per TDD methodology (RED phase).
 */

import { describe, it, expect, afterEach, beforeAll, afterAll } from "vitest";
import { setupServer } from "msw/node";
import { sessionGoalHandlers, createMockGoal } from "./sessionGoalHandlers";
import { transformSnakeToCamel } from "../../api/transforms";

const server = setupServer(...sessionGoalHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("sessionGoalHandlers", () => {
  describe("GET /api/v1/sessions/:session_id/goals", () => {
    it("returns goal history for any session ID", async () => {
      const response = await fetch(
        "/api/v1/sessions/dynamic-session-123/goals?limit=50&offset=0",
      );

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data).toHaveProperty("session_id", "dynamic-session-123");
      expect(data).toHaveProperty("goals");
      expect(data).toHaveProperty("total");
    });

    it("supports e2e-prefixed session IDs", async () => {
      const response = await fetch(
        "/api/v1/sessions/e2e-rollback-test/goals?limit=50&offset=0",
      );

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.session_id).toBe("e2e-rollback-test");
    });

    it("supports pagination parameters", async () => {
      const response = await fetch(
        "/api/v1/sessions/session-123/goals?limit=10&offset=5",
      );

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data).toHaveProperty("goals");
      expect(Array.isArray(data.goals)).toBe(true);
    });
  });

  describe("POST /api/v1/sessions/:session_id/goal", () => {
    it("creates a new goal for any session ID", async () => {
      const response = await fetch("/api/v1/sessions/dynamic-session-456/goal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          goal: "Test goal",
          set_at: Date.now(),
        }),
      });

      expect(response.status).toBe(201);
      const data = await response.json();
      expect(data.session_id).toBe("dynamic-session-456");
      expect(data.goal).toBe("Test goal");
    });
  });

  describe("POST /api/v1/sessions/:session_id/goal/complete", () => {
    it("completes a goal for any session ID", async () => {
      const response = await fetch(
        "/api/v1/sessions/dynamic-session-789/goal/complete",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            goal: "Completed goal",
            achieved: true,
            feedback: "Done!",
            completed_at: Date.now(),
          }),
        },
      );

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.session_id).toBe("dynamic-session-789");
      expect(data.achieved).toBe(true);
    });

    it("supports partial achievement status", async () => {
      const response = await fetch(
        "/api/v1/sessions/session-123/goal/complete",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            goal: "Partial goal",
            achieved: "partial",
            feedback: "Partially done",
            completed_at: Date.now(),
          }),
        },
      );

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.achieved).toBe("partial");
    });
  });

  describe("DELETE /api/v1/sessions/:session_id/goals/:goal_id", () => {
    it("deletes a goal for any session and goal ID", async () => {
      const response = await fetch(
        "/api/v1/sessions/dynamic-session-123/goals/goal-abc",
        {
          method: "DELETE",
        },
      );

      expect(response.status).toBe(204);
    });

    it("supports e2e-prefixed session IDs", async () => {
      const response = await fetch(
        "/api/v1/sessions/e2e-rollback-test/goals/goal-1",
        {
          method: "DELETE",
        },
      );

      expect(response.status).toBe(204);
    });
  });

  describe("createMockGoal helper", () => {
    it("creates a goal with default values", () => {
      const goal = createMockGoal();

      expect(goal).toHaveProperty("id");
      expect(goal).toHaveProperty("goal");
      expect(goal).toHaveProperty("achieved");
      expect(goal).toHaveProperty("set_at");
      expect(goal).toHaveProperty("completed_at");
    });

    it("allows overriding default values", () => {
      const goal = createMockGoal({
        id: "custom-id",
        goal: "Custom goal text",
        achieved: "partial",
      });

      expect(goal.id).toBe("custom-id");
      expect(goal.goal).toBe("Custom goal text");
      expect(goal.achieved).toBe("partial");
    });
  });

  describe("API Contract Transformation", () => {
    it("should return goal in snake_case and transform to camelCase", async () => {
      const response = await fetch("/api/v1/sessions/test-session/goal", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ goal: "Complete the implementation", set_at: Date.now() }),
      });
      expect(response.status).toBe(201);
      const rawData = await response.json();

      // Verify snake_case in raw response (backend format)
      expect(rawData).toHaveProperty("session_id");
      expect(rawData).toHaveProperty("set_at");

      // Verify transformation works (frontend format)
      const transformedData = transformSnakeToCamel(rawData);
      expect(transformedData).toHaveProperty("sessionId");
      expect(transformedData).toHaveProperty("setAt");
    });
  });
});
