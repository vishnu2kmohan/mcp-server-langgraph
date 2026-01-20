/**
 * MSW Test Helpers
 *
 * Utilities for testing MSW handlers that return snake_case responses.
 */
import { transformSnakeToCamel } from "../../api/transforms";

/**
 * Fetch and transform API response from snake_case to camelCase.
 *
 * Use this in tests to get camelCase data from snake_case API responses.
 * This simulates what the frontend hooks do when consuming API data.
 *
 * @param url - URL to fetch
 * @param options - Fetch options
 * @returns Transformed camelCase response data
 *
 * @example
 * ```typescript
 * it('fetches an artifact', async () => {
 *   const data = await fetchAndTransform('/api/v1/artifacts/art-1');
 *   expect(data.sessionId).toBe('session-1'); // camelCase!
 * });
 * ```
 */
export async function fetchAndTransform<T>(
  url: string,
  options?: RequestInit,
): Promise<T> {
  const response = await fetch(url, options);
  const rawData = await response.json();
  return transformSnakeToCamel(rawData) as T;
}

/**
 * Transform a raw API response to camelCase.
 *
 * Use this when you already have the response and just need to transform it.
 *
 * @param data - Raw snake_case API response
 * @returns Transformed camelCase data
 */
export function transformApiResponse<T>(data: unknown): T {
  return transformSnakeToCamel(data) as T;
}
