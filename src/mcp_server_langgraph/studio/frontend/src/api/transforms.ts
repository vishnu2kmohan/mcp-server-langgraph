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
): CursorPaginatedFrontendResponse<SnakeToCamelCaseDeep<T>> {
  const { data, pagination } = response;

  return {
    // Transform each item's keys from snake_case to camelCase
    items: data.map((item) =>
      transformSnakeToCamel(item),
    ) as SnakeToCamelCaseDeep<T>[],
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

// =============================================================================
// ADR-0091 Phase 5: Case Transformation Utilities
// =============================================================================

// -----------------------------------------------------------------------------
// Type-Level Transformations (for TypeScript compile-time)
// -----------------------------------------------------------------------------

/**
 * Convert a snake_case string literal type to camelCase.
 *
 * If the string contains no underscore, it's preserved as-is (matches runtime behavior).
 * This allows the type to work correctly with already-camelCase strings.
 *
 * @example
 * type Result = SnakeToCamelCase<"alert_id">; // "alertId"
 * type Result2 = SnakeToCamelCase<"user_first_name">; // "userFirstName"
 * type Result3 = SnakeToCamelCase<"alertId">; // "alertId" (preserved)
 */
export type SnakeToCamelCase<S extends string> =
  S extends `${infer Head}_${infer Tail}`
    ? `${Lowercase<Head>}${Capitalize<SnakeToCamelCase<Tail>>}`
    : S;

/**
 * Convert a camelCase string literal type to snake_case.
 *
 * @example
 * type Result = CamelToSnakeCase<"alertId">; // "alert_id"
 * type Result2 = CamelToSnakeCase<"userFirstName">; // "user_first_name"
 */
export type CamelToSnakeCase<S extends string> =
  S extends `${infer Head}${infer Tail}`
    ? Head extends Uppercase<Head>
      ? Head extends Lowercase<Head>
        ? `${Head}${CamelToSnakeCase<Tail>}`
        : `_${Lowercase<Head>}${CamelToSnakeCase<Tail>}`
      : `${Head}${CamelToSnakeCase<Tail>}`
    : S;

/**
 * Recursively convert all keys of an object type from snake_case to camelCase.
 *
 * Use this to derive frontend-friendly types from backend API types.
 *
 * @example
 * ```typescript
 * // Backend API type (snake_case)
 * interface SessionSnake {
 *   session_id: string;
 *   created_at: string;
 *   user_data: { first_name: string };
 * }
 *
 * // Frontend type (camelCase) - derived automatically
 * type SessionCamel = SnakeToCamelCaseDeep<SessionSnake>;
 * // Result: { sessionId: string; createdAt: string; userData: { firstName: string } }
 * ```
 */
export type SnakeToCamelCaseDeep<T> = T extends (infer U)[]
  ? SnakeToCamelCaseDeep<U>[]
  : T extends object
    ? {
        [K in keyof T as K extends string
          ? SnakeToCamelCase<K>
          : K]: SnakeToCamelCaseDeep<T[K]>;
      }
    : T;

/**
 * Recursively convert all keys of an object type from camelCase to snake_case.
 *
 * Use this for request body types sent to the backend.
 *
 * @example
 * ```typescript
 * // Frontend type (camelCase)
 * interface CreateSessionRequest {
 *   sessionName: string;
 *   workflowId: string;
 * }
 *
 * // Backend-compatible type - derived automatically
 * type CreateSessionRequestSnake = CamelToSnakeCaseDeep<CreateSessionRequest>;
 * // Result: { session_name: string; workflow_id: string }
 * ```
 */
export type CamelToSnakeCaseDeep<T> = T extends (infer U)[]
  ? CamelToSnakeCaseDeep<U>[]
  : T extends object
    ? {
        [K in keyof T as K extends string
          ? CamelToSnakeCase<K>
          : K]: CamelToSnakeCaseDeep<T[K]>;
      }
    : T;

// -----------------------------------------------------------------------------
// Runtime Transformations
// -----------------------------------------------------------------------------

/**
 * Convert a snake_case string to camelCase.
 *
 * @param str - The snake_case string to convert
 * @returns The camelCase version of the string
 *
 * @example
 * toCamelCase("alert_id") // "alertId"
 * toCamelCase("user_first_name") // "userFirstName"
 */
export function toCamelCase(str: string): string {
  // Handle already camelCase or single word
  if (!str.includes("_")) {
    return str;
  }

  return str
    .toLowerCase()
    .replace(/_+([a-z0-9])/g, (_, char: string) => char.toUpperCase());
}

/**
 * Recursively transform all object keys from snake_case to camelCase.
 *
 * This is the core transformation function for ADR-0091 Phase 5.
 * Use this in RTK Query's transformResponse to convert backend responses.
 *
 * Features:
 * - Recursively processes nested objects
 * - Transforms arrays of objects
 * - Preserves primitive values (strings, numbers, booleans, null)
 * - Handles Date objects and other special types
 * - Preserves already-camelCase keys
 *
 * **ADR-0091 Phase 6 Update**: Return type is now `SnakeToCamelCaseDeep<T>`
 * to properly reflect the runtime transformation, enabling type-safe
 * property access without manual casts.
 *
 * @param obj - The object with snake_case keys to transform
 * @returns A new object with all keys converted to camelCase (typed as SnakeToCamelCaseDeep<T>)
 *
 * @example
 * ```typescript
 * // In RTK Query endpoint - no cast needed!
 * listAlerts: builder.query<AlertCamelCase[], void>({
 *   query: (params) => ({ url: '/alerts', params }),
 *   transformResponse: (response: BackendAlertResponse) =>
 *     transformSnakeToCamel(response), // Returns SnakeToCamelCaseDeep<BackendAlertResponse>
 * }),
 * ```
 */
export function transformSnakeToCamel<T>(obj: T): SnakeToCamelCaseDeep<T> {
  // Handle null and undefined
  if (obj === null || obj === undefined) {
    return obj as SnakeToCamelCaseDeep<T>;
  }

  // Handle arrays - recursively transform each element
  if (Array.isArray(obj)) {
    return obj.map((item) =>
      transformSnakeToCamel(item),
    ) as SnakeToCamelCaseDeep<T>;
  }

  // Handle Date objects - preserve as-is
  if (obj instanceof Date) {
    return obj as SnakeToCamelCaseDeep<T>;
  }

  // Handle plain objects
  if (typeof obj === "object") {
    const result: Record<string, unknown> = {};

    for (const [key, value] of Object.entries(obj)) {
      const camelKey = toCamelCase(key);
      result[camelKey] = transformSnakeToCamel(value);
    }

    return result as SnakeToCamelCaseDeep<T>;
  }

  // Handle primitives (string, number, boolean) - return as-is
  return obj as SnakeToCamelCaseDeep<T>;
}

/**
 * Convert a camelCase string to snake_case.
 *
 * @param str - The camelCase string to convert
 * @returns The snake_case version of the string
 *
 * @example
 * toSnakeCase("alertId") // "alert_id"
 * toSnakeCase("userFirstName") // "user_first_name"
 */
export function toSnakeCase(str: string): string {
  // Handle already snake_case (contains underscore) or all lowercase
  if (str.includes("_") || str === str.toLowerCase()) {
    return str;
  }

  return str
    .replace(/([A-Z])/g, "_$1")
    .toLowerCase()
    .replace(/^_/, ""); // Remove leading underscore if first char was uppercase
}

/**
 * Recursively transform all object keys from camelCase to snake_case.
 *
 * This is the request transformation function for ADR-0091 Phase 5.
 * Use this for mutation request bodies before sending to the backend.
 *
 * Features:
 * - Recursively processes nested objects
 * - Transforms arrays of objects
 * - Preserves primitive values (strings, numbers, booleans, null)
 * - Handles Date objects and other special types
 * - Preserves already-snake_case keys
 *
 * @param obj - The object with camelCase keys to transform
 * @returns A new object with all keys converted to snake_case
 *
 * @example
 * ```typescript
 * // In RTK Query mutation
 * createWorkflow: builder.mutation({
 *   query: (body) => ({
 *     url: '/workflows',
 *     method: 'POST',
 *     body: transformCamelToSnake(body),
 *   }),
 * }),
 * ```
 */
export function transformCamelToSnake<T>(obj: T): CamelToSnakeCaseDeep<T> {
  // Handle null and undefined
  if (obj === null || obj === undefined) {
    return obj as CamelToSnakeCaseDeep<T>;
  }

  // Handle arrays - recursively transform each element
  if (Array.isArray(obj)) {
    return obj.map((item) =>
      transformCamelToSnake(item),
    ) as CamelToSnakeCaseDeep<T>;
  }

  // Handle Date objects - preserve as-is
  if (obj instanceof Date) {
    return obj as CamelToSnakeCaseDeep<T>;
  }

  // Handle plain objects
  if (typeof obj === "object") {
    const result: Record<string, unknown> = {};

    for (const [key, value] of Object.entries(obj)) {
      const snakeKey = toSnakeCase(key);
      result[snakeKey] = transformCamelToSnake(value);
    }

    return result as CamelToSnakeCaseDeep<T>;
  }

  // Handle primitives (string, number, boolean) - return as-is
  return obj as CamelToSnakeCaseDeep<T>;
}
