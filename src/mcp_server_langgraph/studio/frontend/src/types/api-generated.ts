/**
 * API Generated Type Re-exports
 *
 * Re-exports from generated OpenAPI types for use in the application.
 * These types represent the API contract (snake_case) before transformation
 * to client-side types (camelCase).
 *
 * Usage:
 * ```tsx
 * import type { ApiMessageResponse, ApiSessionResponse } from "../types/api-generated";
 * import { transformApiMessageToClient } from "../utils/apiTransforms";
 *
 * // Use generated types for API responses
 * const message: ApiMessageResponse = await fetchMessage(id);
 * // Transform to client format
 * const clientMessage = transformApiMessageToClient(message);
 * ```
 */
import type { components, operations } from "./generated-api";

// =============================================================================
// Schema Type Aliases
// =============================================================================

/**
 * Message response from API (snake_case)
 * GET /api/v1/sessions/{session_id}/messages
 */
export type ApiMessageResponse = components["schemas"]["MessageResponse"];

/**
 * Source citation for a message
 */
export type ApiSourceCitation = components["schemas"]["SourceCitation"];

/**
 * Session response from API (snake_case)
 * GET /api/v1/sessions, GET /api/v1/sessions/{session_id}
 */
export type ApiSessionResponse = components["schemas"]["SessionResponse"];

/**
 * Session configuration response
 */
export type ApiSessionConfigResponse =
  components["schemas"]["SessionConfigResponse"];

/**
 * Span response from observability API (snake_case)
 * GET /api/v1/observability/traces/{id}
 */
export type ApiSpanResponse = components["schemas"]["SpanResponse"];

/**
 * Trace response from observability API
 */
export type ApiTraceResponse = components["schemas"]["TraceResponse"];

/**
 * Artifact content type enum
 */
export type ApiContentType = components["schemas"]["ContentType"];

/**
 * Artifact response from API
 * GET /api/v1/artifacts, GET /api/v1/artifacts/{id}
 */
export type ApiArtifactResponse = components["schemas"]["ArtifactResponse"];

/**
 * Artifact version response
 * GET /api/v1/artifacts/{id}/versions
 */
export type ApiArtifactVersionResponse =
  components["schemas"]["ArtifactVersionResponse"];

// =============================================================================
// Operation Response Types
// =============================================================================

/**
 * List sessions response
 */
export type ListSessionsResponse =
  operations["list_sessions_api_v1_sessions_get"]["responses"]["200"]["content"]["application/json"];

/**
 * Get session messages response
 */
export type GetSessionMessagesResponse =
  operations["get_session_messages_api_v1_sessions__session_id__messages_get"]["responses"]["200"]["content"]["application/json"];

/**
 * List traces response
 */
export type ListTracesResponse =
  operations["list_traces_api_v1_observability_traces_get"]["responses"]["200"]["content"]["application/json"];

/**
 * Get trace response
 */
export type GetTraceResponse =
  operations["get_trace_api_v1_observability_traces__trace_id__get"]["responses"]["200"]["content"]["application/json"];
