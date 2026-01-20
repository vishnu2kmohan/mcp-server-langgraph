/**
 * MSW API Response Utilities
 *
 * Provides helpers for creating API-compliant mock responses.
 * Converts frontend camelCase types to backend snake_case format.
 *
 * Usage:
 * ```typescript
 * // In MSW handler
 * http.get('/api/v1/sessions', () => {
 *   const sessions = [createMockSession(), createMockSession()];
 *   return apiJsonResponse(sessions);
 * });
 * ```
 */
import { HttpResponse } from "msw";
import { transformCamelToSnake } from "../../api/transforms";

/**
 * Create an HTTP JSON response with snake_case keys.
 *
 * MSW handlers should use this instead of HttpResponse.json() directly
 * to ensure mock responses match the real backend API format.
 *
 * @param data - Frontend-typed data (camelCase)
 * @param init - Optional response init (status, headers, etc.)
 * @returns HttpResponse with snake_case JSON body
 *
 * @example
 * ```typescript
 * // Handler returns snake_case to match real API
 * http.get('/api/v1/sessions/:id', ({ params }) => {
 *   const session = createMockSession({ id: params.id });
 *   return apiJsonResponse(session);
 *   // Returns: { "session_id": "...", "created_at": "..." }
 * });
 * ```
 */
export function apiJsonResponse<T>(
  data: T,
  init?: ResponseInit,
): ReturnType<typeof HttpResponse.json> {
  const snakeCaseData = transformCamelToSnake(data);
  // Type assertion needed for MSW's JsonBodyType compatibility
  return HttpResponse.json(snakeCaseData as Record<string, unknown>, init);
}

/**
 * Create an HTTP JSON response with pagination (snake_case).
 *
 * For paginated endpoints that return { data, pagination } format.
 *
 * @param items - Array of items (camelCase frontend types)
 * @param pagination - Pagination metadata
 * @param init - Optional response init
 * @returns HttpResponse with snake_case paginated response
 *
 * @example
 * ```typescript
 * http.get('/api/v1/sessions', ({ request }) => {
 *   const sessions = mockSessions.slice(0, 10);
 *   return apiPaginatedResponse(sessions, {
 *     count: sessions.length,
 *     hasNext: true,
 *     hasPrev: false,
 *     nextCursor: 'cursor-abc',
 *   });
 * });
 * ```
 */
export function apiPaginatedResponse<T>(
  items: T[],
  pagination: {
    count: number;
    hasNext: boolean;
    hasPrev: boolean;
    nextCursor?: string | null;
    prevCursor?: string | null;
  },
  init?: ResponseInit,
): ReturnType<typeof HttpResponse.json> {
  const response = {
    data: items,
    pagination: {
      count: pagination.count,
      has_next: pagination.hasNext,
      has_prev: pagination.hasPrev,
      next_cursor: pagination.nextCursor ?? null,
      prev_cursor: pagination.prevCursor ?? null,
    },
  };
  // Transform the data array items, but keep pagination as-is (already snake_case)
  const snakeCaseData = transformCamelToSnake(items);
  return HttpResponse.json(
    {
      data: snakeCaseData,
      pagination: response.pagination,
    },
    init,
  );
}

/**
 * Create an error response matching backend error format.
 *
 * @param message - Error message
 * @param status - HTTP status code (default: 400)
 * @param code - Optional error code
 * @returns HttpResponse with error body
 */
export function apiErrorResponse(
  message: string,
  status: number = 400,
  code?: string,
): ReturnType<typeof HttpResponse.json> {
  return HttpResponse.json(
    {
      detail: message,
      error_code: code,
    },
    { status },
  );
}
