/**
 * Feedback Handlers - MSW Handlers for Feedback API
 *
 * Mock Service Worker handlers for feedback API endpoints.
 * These handlers prevent "unhandled request" warnings during tests
 * and provide realistic mock responses for feedback metrics.
 *
 * Endpoints:
 * - GET /api/v1/feedback/summary - Aggregated feedback metrics
 */

import { http, delay } from "msw";
import { apiJsonResponse } from "../utils/apiResponse";
import type {
  FeedbackSummaryResponse,
  HallucinationCategoryCounts,
} from "../../types/api";

// =============================================================================
// Types
// =============================================================================

/**
 * Options for creating mock feedback summary
 */
export type MockFeedbackSummaryOptions = Partial<FeedbackSummaryResponse>;

// =============================================================================
// Mock Data Factories
// =============================================================================

/**
 * Create a mock HallucinationCategoryCounts object
 */
export function createMockHallucinationCategories(
  overrides: Partial<HallucinationCategoryCounts> = {},
): HallucinationCategoryCounts {
  return {
    factual_error: 5,
    outdated_info: 3,
    made_up_source: 2,
    other: 2,
    ...overrides,
  };
}

/**
 * Create a mock FeedbackSummaryResponse object
 */
export function createMockFeedbackSummary(
  overrides: MockFeedbackSummaryOptions = {},
): FeedbackSummaryResponse {
  const total_feedback = overrides.total_feedback ?? 100;
  const positive_count = overrides.positive_count ?? 80;
  const negative_count = overrides.negative_count ?? 20;

  // Calculate positive_rate if not provided
  const positive_rate =
    overrides.positive_rate ??
    (total_feedback > 0 ? positive_count / total_feedback : 0);

  return {
    timeframe: overrides.timeframe ?? "7d",
    total_feedback,
    positive_count,
    negative_count,
    positive_rate,
    hallucination_reports: overrides.hallucination_reports ?? 12,
    hallucination_categories:
      overrides.hallucination_categories ?? createMockHallucinationCategories(),
  };
}

// =============================================================================
// Handler Factories
// =============================================================================

/**
 * Create a custom feedback summary handler with callback
 *
 * @param callback - Optional callback to customize response based on timeframe
 */
export function createFeedbackSummaryHandler(
  callback?: (timeframe: string) => FeedbackSummaryResponse,
) {
  return http.get("/api/v1/feedback/summary", async ({ request }) => {
    await delay(50);

    const url = new URL(request.url);
    const timeframe = url.searchParams.get("timeframe") ?? "7d";

    if (callback) {
      const customResponse = callback(timeframe);
      return apiJsonResponse(customResponse);
    }

    return apiJsonResponse(createMockFeedbackSummary({ timeframe }));
  });
}

// =============================================================================
// Default Handlers
// =============================================================================

/**
 * Default feedback handlers for MSW
 */
export const feedbackHandlers = [
  // Feedback summary endpoint
  createFeedbackSummaryHandler(),
];

export default feedbackHandlers;
