/**
 * Session Goal Handlers - MSW Support for Session Goals API
 *
 * MSW handlers for session goal API endpoints, supporting dynamic
 * session IDs for E2E and integration tests.
 *
 * Endpoints:
 * - GET /api/v1/sessions/:session_id/goals - Get goal history
 * - POST /api/v1/sessions/:session_id/goal - Set a new goal
 * - POST /api/v1/sessions/:session_id/goal/complete - Complete a goal
 * - DELETE /api/v1/sessions/:session_id/goals/:goal_id - Delete a goal
 */

import { http, delay, HttpResponse } from "msw";
import { apiJsonResponse } from "../utils/apiResponse";

// =============================================================================
// Types
// =============================================================================

export interface MockGoal {
  id: string;
  goal: string;
  achieved: boolean | "partial";
  feedback: string | null;
  set_at: number;
  completed_at: number;
}

// =============================================================================
// Mock Data Factory
// =============================================================================

let goalIdCounter = 0;

/**
 * Create a mock goal with default values
 */
export const createMockGoal = (
  overrides: Partial<MockGoal> = {},
): MockGoal => ({
  id: `goal-${++goalIdCounter}`,
  goal: "Complete the task",
  achieved: true,
  feedback: "Completed successfully",
  set_at: Date.now() - 120000,
  completed_at: Date.now() - 60000,
  ...overrides,
});

// =============================================================================
// Default Mock Goals for Various Session IDs
// =============================================================================

const defaultGoals: MockGoal[] = [
  createMockGoal({
    id: "goal-1",
    goal: "Complete the data analysis",
    achieved: true,
    feedback: "All analysis done successfully",
    set_at: 1705123456789,
    completed_at: 1705127056789,
  }),
  createMockGoal({
    id: "goal-2",
    goal: "Implement new feature",
    achieved: "partial",
    feedback: "Completed 80%",
    set_at: 1705130000000,
    completed_at: 1705133600000,
  }),
  createMockGoal({
    id: "goal-3",
    goal: "Fix critical bug",
    achieved: false,
    feedback: "Blocked by dependencies",
    set_at: 1705137200000,
    completed_at: 1705140800000,
  }),
];

// =============================================================================
// MSW Handlers
// =============================================================================

export const sessionGoalHandlers = [
  // GET /api/v1/sessions/:session_id/goals - Get goal history
  // Supports any session ID (dynamic matching with :session_id param)
  http.get(
    "/api/v1/sessions/:session_id/goals",
    async ({ params, request }) => {
      await delay(50);

      const { session_id } = params as { session_id: string };
      const url = new URL(request.url);
      const limit = parseInt(url.searchParams.get("limit") ?? "50", 10);
      const offset = parseInt(url.searchParams.get("offset") ?? "0", 10);

      // Return default goals paginated
      const paginatedGoals = defaultGoals.slice(offset, offset + limit);

      return apiJsonResponse({
        session_id,
        goals: paginatedGoals,
        total: defaultGoals.length,
      });
    },
  ),

  // POST /api/v1/sessions/:session_id/goal - Set a new goal
  http.post(
    "/api/v1/sessions/:session_id/goal",
    async ({ params, request }) => {
      await delay(50);

      const { session_id } = params as { session_id: string };
      const body = (await request.json()) as { goal: string; set_at: number };

      return apiJsonResponse(
        {
          session_id,
          goal: body.goal,
          set_at: body.set_at,
        },
        { status: 201 },
      );
    },
  ),

  // POST /api/v1/sessions/:session_id/goal/complete - Complete a goal
  http.post(
    "/api/v1/sessions/:session_id/goal/complete",
    async ({ params, request }) => {
      await delay(50);

      const { session_id } = params as { session_id: string };
      const body = (await request.json()) as {
        goal: string;
        achieved: boolean | "partial";
        feedback?: string;
        completed_at: number;
      };

      return apiJsonResponse({
        session_id,
        goal: body.goal,
        achieved: body.achieved,
        feedback: body.feedback ?? null,
        set_at: Date.now() - 60000, // Mock a set_at time
        completed_at: body.completed_at,
      });
    },
  ),

  // DELETE /api/v1/sessions/:session_id/goals/:goal_id - Delete a goal
  http.delete("/api/v1/sessions/:session_id/goals/:goal_id", async () => {
    await delay(50);
    return new HttpResponse(null, { status: 204 });
  }),
];

export default sessionGoalHandlers;
