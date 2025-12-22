/**
 * HEART Metrics MSW Handlers
 *
 * Mock Service Worker handlers for HEART metrics API endpoints.
 * These handlers prevent "unhandled request" warnings during tests
 * and provide realistic mock responses for HEART tracking.
 *
 * Endpoints:
 * - POST /api/v1/metrics/heart/event - Single HEART event
 * - POST /api/v1/metrics/heart/batch - Batch HEART events
 */

import { http, HttpResponse } from "msw";

/**
 * HEART event request body
 */
interface HeartEventRequest {
  event_type: string;
  persona?: string;
  username?: string;
  timestamp: number;
  [key: string]: unknown;
}

/**
 * HEART batch request body
 */
interface HeartBatchRequest {
  events: Array<{
    event_type: string;
    payload: Record<string, unknown>;
    timestamp: number;
  }>;
  session_duration: number;
}

/**
 * Generate a unique ID for mock responses
 */
function generateId(): string {
  return `mock-${Date.now()}-${Math.random().toString(36).slice(2, 11)}`;
}

/**
 * Create a custom HEART event handler with callback
 */
export function createHeartEventHandler(
  callback?: (body: HeartEventRequest) => Record<string, unknown>
) {
  return http.post("/api/v1/metrics/heart/event", async ({ request }) => {
    const body = (await request.json()) as HeartEventRequest;

    if (callback) {
      const customResponse = callback(body);
      return HttpResponse.json({
        success: true,
        event_id: generateId(),
        ...customResponse,
      });
    }

    return HttpResponse.json({
      success: true,
      event_id: generateId(),
      event_type: body.event_type,
      persona_received: body.persona || null,
      timestamp_received: body.timestamp,
    });
  });
}

/**
 * Create a custom HEART batch handler with callback
 */
export function createHeartBatchHandler(
  callback?: (
    events: HeartBatchRequest["events"],
    sessionDuration: number
  ) => Record<string, unknown>
) {
  return http.post("/api/v1/metrics/heart/batch", async ({ request }) => {
    const body = (await request.json()) as HeartBatchRequest;

    if (callback) {
      const customResponse = callback(body.events, body.session_duration);
      return HttpResponse.json({
        success: true,
        batch_id: generateId(),
        ...customResponse,
      });
    }

    return HttpResponse.json({
      success: true,
      batch_id: generateId(),
      events_received: body.events.length,
      session_duration_received: body.session_duration,
    });
  });
}

/**
 * Default HEART metrics handlers
 */
export const heartHandlers = [
  // Single event endpoint
  createHeartEventHandler(),

  // Batch events endpoint
  createHeartBatchHandler(),
];

export default heartHandlers;
