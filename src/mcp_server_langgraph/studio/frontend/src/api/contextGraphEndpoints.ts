/**
 * Context Graph RTK Query Endpoints (ADR-0101)
 *
 * Provides endpoints for decision trace retrieval and precedent search.
 * These endpoints integrate with the backend context-graph API.
 * Transforms snake_case backend responses to camelCase per ADR-0091.
 */

import { api } from "./index";
import type {
  DecisionTrace,
  DecisionTraceSummary,
  PrecedentSearchRequest,
  PrecedentSearchResult,
} from "../types/contextGraph";

// =============================================================================
// Request/Response Types (snake_case from backend)
// =============================================================================

interface DecisionTraceBackend {
  trace_id: string;
  run_id: string;
  session_id: string;
  workflow_id?: string;
  project_id?: string;
  timestamp: string;
  decision_type: string;
  decision_stage: string;
  chosen_action: string;
  confidence: number;
  rationale: string;
  outcome: string | null;
  requires_approval: boolean;
  approval_status?: string;
}

interface DecisionTraceSummaryBackend {
  trace_id: string;
  timestamp: string;
  decision_type: string;
  chosen_action: string;
  confidence: number;
  outcome: string | null;
}

interface PrecedentSearchResultBackend {
  trace: DecisionTraceBackend;
  similarity_score: number;
}

interface SessionTracesParams {
  sessionId: string;
  limit?: number;
  offset?: number;
}

// =============================================================================
// Transform Functions (snake_case backend -> camelCase frontend)
// These functions intentionally access snake_case backend properties
// =============================================================================

/* eslint-disable no-restricted-syntax -- Accessing snake_case backend API */
function transformDecisionTrace(backend: DecisionTraceBackend): DecisionTrace {
  return {
    traceId: backend.trace_id,
    runId: backend.run_id,
    sessionId: backend.session_id,
    workflowId: backend.workflow_id,
    projectId: backend.project_id,
    timestamp: backend.timestamp,
    decisionType: backend.decision_type as DecisionTrace["decisionType"],
    chosenAction: backend.chosen_action,
    confidence: backend.confidence,
    rationale: backend.rationale,
    outcome: backend.outcome as DecisionTrace["outcome"],
    requiresApproval: backend.requires_approval,
    approvalStatus: backend.approval_status,
  };
}

function transformDecisionTraceSummary(
  backend: DecisionTraceSummaryBackend,
): DecisionTraceSummary {
  return {
    traceId: backend.trace_id,
    timestamp: backend.timestamp,
    decisionType: backend.decision_type as DecisionTraceSummary["decisionType"],
    chosenAction: backend.chosen_action,
    confidence: backend.confidence,
    outcome: backend.outcome as DecisionTraceSummary["outcome"],
  };
}

function transformPrecedentResult(
  backend: PrecedentSearchResultBackend,
): PrecedentSearchResult {
  return {
    trace: transformDecisionTrace(backend.trace),
    similarityScore: backend.similarity_score,
  };
}
/* eslint-enable no-restricted-syntax */

// =============================================================================
// RTK Query Endpoints
// =============================================================================

export const contextGraphApi = api.injectEndpoints({
  endpoints: (builder) => ({
    /**
     * Get a specific decision trace by ID
     */
    getDecisionTrace: builder.query<DecisionTrace, string>({
      query: (traceId) => `/context-graph/traces/${traceId}`,
      transformResponse: (response: DecisionTraceBackend) =>
        transformDecisionTrace(response),
      providesTags: (_result, _error, traceId) => [
        { type: "DecisionTrace" as const, id: traceId },
      ],
    }),

    /**
     * Get decision traces for a session
     */
    getSessionTraces: builder.query<
      DecisionTraceSummary[],
      SessionTracesParams
    >({
      query: ({ sessionId, limit = 100, offset = 0 }) =>
        `/context-graph/sessions/${sessionId}/traces?limit=${limit}&offset=${offset}`,
      transformResponse: (response: DecisionTraceSummaryBackend[]) =>
        response.map(transformDecisionTraceSummary),
      providesTags: (_result, _error, { sessionId }) => [
        { type: "SessionTraces" as const, id: sessionId },
      ],
    }),

    /**
     * Search for similar past decisions (precedents)
     */
    searchPrecedents: builder.mutation<
      PrecedentSearchResult[],
      PrecedentSearchRequest
    >({
      query: (body) => ({
        url: "/context-graph/precedents/search",
        method: "POST",
        body: {
          query: body.query,
          decision_type: body.decisionType,
          outcome: body.outcome,
          limit: body.limit ?? 10,
        },
      }),
      transformResponse: (response: PrecedentSearchResultBackend[]) =>
        response.map(transformPrecedentResult),
    }),
  }),
  overrideExisting: false,
});

// Export hooks for use in components
export const {
  useGetDecisionTraceQuery,
  useGetSessionTracesQuery,
  useSearchPrecedentsMutation,
} = contextGraphApi;

// Export endpoint definitions for testing
export const { getDecisionTrace, getSessionTraces, searchPrecedents } =
  contextGraphApi.endpoints;
