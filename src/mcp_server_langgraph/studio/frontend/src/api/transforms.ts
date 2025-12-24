/**
 * API Response Transform Helpers
 *
 * Provides reusable transformation functions for converting backend API responses
 * to frontend-friendly formats.
 *
 * Key transformations:
 * - Cursor pagination: Backend `{data, pagination}` → Frontend `{items, pagination, ...}`
 */

import type {
  BackendCursorPaginatedResponse,
  CursorPaginatedFrontendResponse,
  CursorPaginationMetadata,
  PaginatedResponse,
} from "../types/api";

/**
 * Transform cursor-paginated backend response to frontend format.
 *
 * IMPORTANT: `count` is the number of items in the CURRENT page, NOT total.
 * Cursor pagination deliberately omits total for efficiency.
 *
 * Preserves raw `pagination` object for components needing direct cursor access.
 *
 * @param response - Raw backend response with `{data, pagination}` structure
 * @returns Transformed response with `{items, pagination, count, hasNext, ...}`
 *
 * @example
 * ```typescript
 * // In RTK Query endpoint
 * listSessions: builder.query({
 *   query: (params) => ({ url: '/sessions', params }),
 *   transformResponse: (response: BackendCursorPaginatedResponse<Session>) =>
 *     transformCursorPaginatedResponse(response),
 * }),
 * ```
 */
export function transformCursorPaginatedResponse<T>(
  response: BackendCursorPaginatedResponse<T>,
): CursorPaginatedFrontendResponse<T> {
  const { data, pagination } = response;

  return {
    items: data,
    pagination,
    count: pagination.count,
    hasNext: pagination.has_next,
    hasPrev: pagination.has_prev,
    nextCursor: pagination.next_cursor ?? undefined,
    prevCursor: pagination.prev_cursor ?? undefined,
  };
}

/**
 * Transform cursor-paginated backend response to legacy PaginatedResponse format.
 *
 * This is for backward compatibility with components still using the old
 * `{items, total, limit, next_cursor}` format.
 *
 * @deprecated Use `transformCursorPaginatedResponse` for new code.
 * @param response - Raw backend response with `{data, pagination}` structure
 * @param limit - The limit used in the query (for backward compatibility)
 * @returns Legacy paginated response format
 */
export function transformToLegacyPaginatedResponse<T>(
  response: BackendCursorPaginatedResponse<T>,
  limit: number = 20,
): PaginatedResponse<T> {
  const { data, pagination } = response;

  return {
    items: data,
    // Note: Cursor pagination does NOT provide total count
    // Components relying on total need to be refactored
    total: undefined,
    limit,
    next_cursor: pagination.next_cursor ?? undefined,
  };
}

/**
 * Type guard to check if a response is a cursor-paginated backend response.
 *
 * Useful when handling endpoints that may return different response formats.
 *
 * @param response - Unknown response object to check
 * @returns True if the response matches BackendCursorPaginatedResponse structure
 */
export function isCursorPaginatedResponse<T = unknown>(
  response: unknown,
): response is BackendCursorPaginatedResponse<T> {
  return (
    typeof response === "object" &&
    response !== null &&
    "data" in response &&
    "pagination" in response &&
    Array.isArray((response as BackendCursorPaginatedResponse<T>).data) &&
    typeof (response as BackendCursorPaginatedResponse<T>).pagination ===
      "object"
  );
}

/**
 * Extract pagination metadata from various response formats.
 *
 * Handles both backend format and already-transformed frontend format.
 *
 * @param response - Response that may contain pagination in different locations
 * @returns Pagination metadata or undefined if not found
 */
export function extractPaginationMetadata(
  response: unknown,
): CursorPaginationMetadata | undefined {
  if (!response || typeof response !== "object") {
    return undefined;
  }

  // Check for backend format: {data, pagination}
  if ("pagination" in response && typeof response.pagination === "object") {
    return response.pagination as CursorPaginationMetadata;
  }

  // Check for already transformed format with raw has_next/has_prev
  if ("has_next" in response && "has_prev" in response) {
    return {
      count: (response as { count?: number }).count ?? 0,
      has_next: (response as { has_next: boolean }).has_next,
      has_prev: (response as { has_prev: boolean }).has_prev,
      next_cursor: (response as { next_cursor?: string }).next_cursor,
      prev_cursor: (response as { prev_cursor?: string }).prev_cursor,
    };
  }

  return undefined;
}
