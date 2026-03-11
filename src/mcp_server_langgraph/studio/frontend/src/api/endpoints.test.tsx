/**
 * RTK Query Endpoints Tests
 *
 * Tests for the predictions and session goal API endpoints.
 * These endpoints are documented in docs-internal/frontend/PENDING-BACKEND-APIS.md
 *
 * Following TDD: Tests verify endpoint behavior before backend implementation.
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { http, HttpResponse } from "msw";
import React from "react";

import { server } from "../mocks/server";

import {
  api,
  useGetPredictionsQuery,
  useSetSessionGoalMutation,
  useCompleteSessionGoalMutation,
  useGetSessionGoalHistoryQuery,
} from "./index";

// =============================================================================
// MSW Setup
// =============================================================================

const handlers = [
  // GET /api/v1/ai/predictions
  http.get("/api/v1/ai/predictions", ({ request }) => {
    const url = new URL(request.url);
    const _sessionId = url.searchParams.get("session_id");
    const type = url.searchParams.get("type");
    const minConfidence = url.searchParams.get("min_confidence");

    const predictions = [
      {
        id: "pred-1",
        type: "churn_risk",
        metric: "user_engagement",
        predicted_value: 0.75,
        confidence: 0.85,
        timeframe: "7d",
        factors: [
          { name: "session_frequency", impact: 0.3 },
          { name: "task_completion_rate", impact: 0.25 },
        ],
        created_at: 1705123456789,
      },
      {
        id: "pred-2",
        type: "adoption_forecast",
        metric: "feature_adoption",
        predicted_value: 0.6,
        confidence: 0.72,
        timeframe: "30d",
        factors: [{ name: "feature_discovery", impact: 0.4 }],
        created_at: 1705123456790,
      },
    ];

    // Filter by type if specified
    let filtered = predictions;
    if (type) {
      filtered = filtered.filter((p) => p.type === type);
    }
    if (minConfidence) {
      const threshold = parseFloat(minConfidence);
      filtered = filtered.filter((p) => p.confidence >= threshold);
    }

    return HttpResponse.json({ predictions: filtered });
  }),

  // POST /api/v1/sessions/{session_id}/goal
  http.post(
    "/api/v1/sessions/:session_id/goal",
    async ({ params, request }) => {
      const { session_id } = params;
      const body = (await request.json()) as { goal: string; set_at: number };

      return HttpResponse.json(
        {
          session_id,
          goal: body.goal,
          set_at: body.set_at,
        },
        { status: 201 },
      );
    },
  ),

  // POST /api/v1/sessions/{session_id}/goal/complete
  http.post(
    "/api/v1/sessions/:session_id/goal/complete",
    async ({ params, request }) => {
      const { session_id } = params;
      const body = (await request.json()) as {
        goal: string;
        achieved: boolean | "partial";
        feedback?: string;
        completed_at: number;
      };

      return HttpResponse.json({
        session_id,
        goal: body.goal,
        achieved: body.achieved,
        feedback: body.feedback ?? null,
        set_at: 1705123456789,
        completed_at: body.completed_at,
      });
    },
  ),

  // GET /api/v1/sessions/{session_id}/goals
  http.get("/api/v1/sessions/:session_id/goals", ({ params, request }) => {
    const { session_id } = params;
    const url = new URL(request.url);
    const limit = parseInt(url.searchParams.get("limit") || "50", 10);
    const offset = parseInt(url.searchParams.get("offset") || "0", 10);

    // Mock goal history data
    const allGoals = [
      {
        id: "goal-1",
        goal: "Complete the data analysis",
        achieved: true,
        feedback: "All analysis done successfully",
        set_at: 1705123456789,
        completed_at: 1705127056789,
      },
      {
        id: "goal-2",
        goal: "Implement new feature",
        achieved: "partial",
        feedback: "Completed 80%",
        set_at: 1705130000000,
        completed_at: 1705133600000,
      },
      {
        id: "goal-3",
        goal: "Fix critical bug",
        achieved: false,
        feedback: "Blocked by dependencies",
        set_at: 1705137200000,
        completed_at: 1705140800000,
      },
    ];

    const goals = allGoals.slice(offset, offset + limit);

    return HttpResponse.json({
      session_id,
      goals,
      total: allGoals.length,
    });
  }),
];

// Handlers array for use with server.use()
const endpointHandlers = handlers;

// =============================================================================
// Test Setup
// =============================================================================

// Use the global server from test/setup.ts with our handlers prepended
// This ensures our handlers take priority over the default ones

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
// Tests
// =============================================================================

describe("Predictions API", () => {
  // Prepend our handlers before each test
  beforeEach(() => {
    server.use(...endpointHandlers);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    server.resetHandlers();
  });

  describe("useGetPredictionsQuery", () => {
    it("fetches predictions successfully", async () => {
      const { result } = renderHook(() => useGetPredictionsQuery({}), {
        wrapper,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.predictions).toHaveLength(2);
      expect(result.current.data?.predictions[0].id).toBe("pred-1");
      expect(result.current.data?.predictions[0].type).toBe("churn_risk");
    });

    it("filters predictions by type", async () => {
      const { result } = renderHook(
        () => useGetPredictionsQuery({ type: "churn_risk" }),
        { wrapper },
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.predictions).toHaveLength(1);
      expect(result.current.data?.predictions[0].type).toBe("churn_risk");
    });

    it("filters predictions by minimum confidence", async () => {
      const { result } = renderHook(
        () => useGetPredictionsQuery({ min_confidence: 0.8 }),
        { wrapper },
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.predictions).toHaveLength(1);
      expect(
        result.current.data?.predictions[0].confidence,
      ).toBeGreaterThanOrEqual(0.8);
    });

    it("returns prediction with factors array", async () => {
      const { result } = renderHook(() => useGetPredictionsQuery({}), {
        wrapper,
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const prediction = result.current.data?.predictions[0];
      expect(prediction?.factors).toHaveLength(2);
      expect(prediction?.factors[0]).toHaveProperty("name");
      expect(prediction?.factors[0]).toHaveProperty("impact");
    });
  });
});

describe("Session Goal API", () => {
  // Prepend our handlers before each test
  beforeEach(() => {
    server.use(...endpointHandlers);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    server.resetHandlers();
  });

  describe("useSetSessionGoalMutation", () => {
    it("sets session goal successfully", async () => {
      const { result } = renderHook(() => useSetSessionGoalMutation(), {
        wrapper,
      });

      const [setGoal] = result.current;
      const timestamp = Date.now();

      const response = await setGoal({
        sessionId: "session-123",
        goal: "Complete the data analysis",
        setAt: timestamp,
      }).unwrap();

      expect(response.sessionId).toBe("session-123");
      expect(response.goal).toBe("Complete the data analysis");
      expect(response.setAt).toBe(timestamp);
    });

    it("provides isSuccess state after mutation", async () => {
      const { result } = renderHook(() => useSetSessionGoalMutation(), {
        wrapper,
      });

      const [setGoal] = result.current;

      await setGoal({
        sessionId: "session-123",
        goal: "Test goal",
        setAt: Date.now(),
      }).unwrap();

      // After successful request
      await waitFor(() => expect(result.current[1].isSuccess).toBe(true));
    });
  });

  describe("useCompleteSessionGoalMutation", () => {
    it("completes session goal with achieved=true", async () => {
      const { result } = renderHook(() => useCompleteSessionGoalMutation(), {
        wrapper,
      });

      const [completeGoal] = result.current;
      const completedAt = Date.now();

      const response = await completeGoal({
        sessionId: "session-123",
        goal: "Complete the data analysis",
        achieved: true,
        completedAt: completedAt,
      }).unwrap();

      expect(response.sessionId).toBe("session-123");
      expect(response.achieved).toBe(true);
      expect(response.completedAt).toBe(completedAt);
    });

    it("completes session goal with achieved=partial", async () => {
      const { result } = renderHook(() => useCompleteSessionGoalMutation(), {
        wrapper,
      });

      const [completeGoal] = result.current;

      const response = await completeGoal({
        sessionId: "session-123",
        goal: "Complete the data analysis",
        achieved: "partial",
        feedback: "Completed 80% of the analysis",
        completedAt: Date.now(),
      }).unwrap();

      expect(response.achieved).toBe("partial");
      expect(response.feedback).toBe("Completed 80% of the analysis");
    });

    it("completes session goal with achieved=false", async () => {
      const { result } = renderHook(() => useCompleteSessionGoalMutation(), {
        wrapper,
      });

      const [completeGoal] = result.current;

      const response = await completeGoal({
        sessionId: "session-123",
        goal: "Complete the data analysis",
        achieved: false,
        feedback: "Could not complete due to data issues",
        completedAt: Date.now(),
      }).unwrap();

      expect(response.achieved).toBe(false);
      expect(response.feedback).toBe("Could not complete due to data issues");
    });
  });

  describe("useGetSessionGoalHistoryQuery", () => {
    it("fetches goal history successfully", async () => {
      const { result } = renderHook(
        () => useGetSessionGoalHistoryQuery({ sessionId: "session-123" }),
        { wrapper },
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.goals).toHaveLength(3);
      expect(result.current.data?.total).toBe(3);
      expect(result.current.data?.sessionId).toBe("session-123");
    });

    it("returns goals with correct structure", async () => {
      const { result } = renderHook(
        () => useGetSessionGoalHistoryQuery({ sessionId: "session-123" }),
        { wrapper },
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const goal = result.current.data?.goals[0];
      expect(goal).toHaveProperty("id");
      expect(goal).toHaveProperty("goal");
      expect(goal).toHaveProperty("achieved");
      expect(goal).toHaveProperty("feedback");
      expect(goal).toHaveProperty("setAt");
      expect(goal).toHaveProperty("completedAt");
    });

    it("supports different achievement statuses", async () => {
      const { result } = renderHook(
        () => useGetSessionGoalHistoryQuery({ sessionId: "session-123" }),
        { wrapper },
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const goals = result.current.data?.goals;
      expect(goals?.[0].achieved).toBe(true);
      expect(goals?.[1].achieved).toBe("partial");
      expect(goals?.[2].achieved).toBe(false);
    });

    it("supports pagination with limit and offset", async () => {
      const { result } = renderHook(
        () =>
          useGetSessionGoalHistoryQuery({
            sessionId: "session-123",
            limit: 2,
            offset: 1,
          }),
        { wrapper },
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.goals).toHaveLength(2);
      expect(result.current.data?.goals[0].id).toBe("goal-2");
    });
  });
});

// =============================================================================
// Error Response Tests
// =============================================================================

describe("Error Response Handling", () => {
  // Prepend our handlers before each test
  beforeEach(() => {
    server.use(...endpointHandlers);
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
    server.resetHandlers();
  });

  describe("Predictions API errors", () => {
    it("handles 401 Unauthorized error", async () => {
      server.use(
        http.get("/api/v1/ai/predictions", () => {
          return HttpResponse.json(
            { detail: "Not authenticated" },
            { status: 401 },
          );
        }),
      );

      const { result } = renderHook(() => useGetPredictionsQuery({}), {
        wrapper,
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeDefined();
    });

    it("handles 400 Bad Request error", async () => {
      server.use(
        http.get("/api/v1/ai/predictions", () => {
          return HttpResponse.json(
            { detail: "Invalid min_confidence value" },
            { status: 400 },
          );
        }),
      );

      const { result } = renderHook(
        () => useGetPredictionsQuery({ min_confidence: -1 }),
        { wrapper },
      );

      await waitFor(() => expect(result.current.isError).toBe(true));
    });

    it("handles 500 Internal Server Error", async () => {
      server.use(
        http.get("/api/v1/ai/predictions", () => {
          return HttpResponse.json(
            { detail: "Internal server error" },
            { status: 500 },
          );
        }),
      );

      const { result } = renderHook(() => useGetPredictionsQuery({}), {
        wrapper,
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
    });
  });

  describe("Session Goal API errors", () => {
    it("handles 404 Not Found for set goal", async () => {
      server.use(
        http.post("/api/v1/sessions/:session_id/goal", () => {
          return HttpResponse.json(
            { detail: "Session not found" },
            { status: 404 },
          );
        }),
      );

      const { result } = renderHook(() => useSetSessionGoalMutation(), {
        wrapper,
      });

      const [setGoal] = result.current;

      await expect(
        setGoal({
          sessionId: "nonexistent-session",
          goal: "Test goal",
          setAt: Date.now(),
        }).unwrap(),
      ).rejects.toMatchObject({
        status: 404,
      });
    });

    it("handles 400 Bad Request for invalid goal data", async () => {
      server.use(
        http.post("/api/v1/sessions/:session_id/goal", () => {
          return HttpResponse.json(
            { detail: "Goal text is required" },
            { status: 400 },
          );
        }),
      );

      const { result } = renderHook(() => useSetSessionGoalMutation(), {
        wrapper,
      });

      const [setGoal] = result.current;

      await expect(
        setGoal({
          sessionId: "session-123",
          goal: "",
          setAt: Date.now(),
        }).unwrap(),
      ).rejects.toMatchObject({
        status: 400,
      });
    });

    it("handles 404 Not Found for complete goal", async () => {
      server.use(
        http.post("/api/v1/sessions/:session_id/goal/complete", () => {
          return HttpResponse.json(
            { detail: "Session or goal not found" },
            { status: 404 },
          );
        }),
      );

      const { result } = renderHook(() => useCompleteSessionGoalMutation(), {
        wrapper,
      });

      const [completeGoal] = result.current;

      await expect(
        completeGoal({
          sessionId: "nonexistent-session",
          goal: "Test goal",
          achieved: true,
          completedAt: Date.now(),
        }).unwrap(),
      ).rejects.toMatchObject({
        status: 404,
      });
    });

    it("handles 409 Conflict for duplicate goal", async () => {
      server.use(
        http.post("/api/v1/sessions/:session_id/goal", () => {
          return HttpResponse.json(
            { detail: "Goal already exists for this session" },
            { status: 409 },
          );
        }),
      );

      const { result } = renderHook(() => useSetSessionGoalMutation(), {
        wrapper,
      });

      const [setGoal] = result.current;

      await expect(
        setGoal({
          sessionId: "session-123",
          goal: "Duplicate goal",
          setAt: Date.now(),
        }).unwrap(),
      ).rejects.toMatchObject({
        status: 409,
      });
    });
  });

  describe("Network errors", () => {
    it("handles network failure for predictions", async () => {
      server.use(
        http.get("/api/v1/ai/predictions", () => {
          return HttpResponse.error();
        }),
      );

      const { result } = renderHook(() => useGetPredictionsQuery({}), {
        wrapper,
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
    });

    it("handles network failure for set goal", async () => {
      server.use(
        http.post("/api/v1/sessions/:session_id/goal", () => {
          return HttpResponse.error();
        }),
      );

      const { result } = renderHook(() => useSetSessionGoalMutation(), {
        wrapper,
      });

      const [setGoal] = result.current;

      await expect(
        setGoal({
          sessionId: "session-123",
          goal: "Test goal",
          setAt: Date.now(),
        }).unwrap(),
      ).rejects.toBeDefined();
    });
  });
});
