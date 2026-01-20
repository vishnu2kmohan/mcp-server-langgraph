/**
 * AI Suggestions MSW Handlers
 *
 * HTTP fallback endpoints for AI suggestions when WebSocket is unavailable.
 * These handlers mirror the WebSocket message protocol for consistency.
 *
 * Endpoints:
 * - GET /api/v1/ai/suggestions - Poll for current suggestions
 * - POST /api/v1/ai/suggestions/request - Request new suggestions with context
 * - POST /api/v1/ai/suggestions/dismiss - Dismiss a specific suggestion
 * - GET /api/v1/ai/suggestions/health - Health check for fallback mode
 */

import { http } from "msw";
import { apiJsonResponse, apiErrorResponse } from "../utils/apiResponse";

// =============================================================================
// Types
// =============================================================================

export interface MockSuggestion {
  id: string;
  type: "tooltip" | "spotlight" | "banner" | "modal";
  message: string;
  priority: "low" | "medium" | "high";
  target_element?: string;
  show_after_ms?: number;
}

interface SuggestionRequestContext {
  page?: string;
  action?: string;
  sessionId?: string;
  [key: string]: unknown;
}

interface SuggestionRequestBody {
  context?: SuggestionRequestContext;
}

interface DismissRequestBody {
  id?: string;
}

// =============================================================================
// State Management
// =============================================================================

let suggestions: MockSuggestion[] = [];
let suggestionCounter = 0;

/**
 * Get current mock suggestions (for testing)
 */
export function mockSuggestions(): MockSuggestion[] {
  return [...suggestions];
}

/**
 * Reset mock suggestions (call between tests)
 */
export function resetMockSuggestions(): void {
  suggestions = [];
  suggestionCounter = 0;
}

/**
 * Add a mock suggestion (for test setup)
 */
export function addMockSuggestion(suggestion: MockSuggestion): void {
  suggestions.push(suggestion);
}

// =============================================================================
// Context-Based Suggestion Generation
// =============================================================================

/**
 * Generate suggestions based on page context
 */
function generateContextSuggestions(
  context: SuggestionRequestContext,
): MockSuggestion[] {
  const page = context.page || "default";
  const generated: MockSuggestion[] = [];

  switch (page) {
    case "chat":
      generated.push({
        id: `suggestion-chat-${++suggestionCounter}`,
        type: "tooltip",
        message: "Use keyboard shortcuts for faster navigation",
        priority: "medium",
        target_element: "#chat-input",
        show_after_ms: 3000,
      });
      break;

    case "workflows":
      generated.push({
        id: `suggestion-workflow-${++suggestionCounter}`,
        type: "spotlight",
        message: "Create your first workflow from a template",
        priority: "high",
        target_element: "#new-workflow-button",
        show_after_ms: 5000,
      });
      break;

    case "observability":
      generated.push({
        id: `suggestion-obs-${++suggestionCounter}`,
        type: "banner",
        message: "Set up alerts for critical metrics",
        priority: "medium",
      });
      break;

    case "connections":
      generated.push({
        id: `suggestion-conn-${++suggestionCounter}`,
        type: "tooltip",
        message: "Connect your first MCP server to get started",
        priority: "high",
        target_element: "#add-connection-button",
      });
      break;

    default:
      generated.push({
        id: `suggestion-default-${++suggestionCounter}`,
        type: "tooltip",
        message: "Explore the help section for tips and tutorials",
        priority: "low",
        target_element: "#help-button",
        show_after_ms: 10000,
      });
  }

  return generated;
}

// =============================================================================
// HTTP Handlers
// =============================================================================

export const aiSuggestionsHandlers = [
  // NOTE: More specific paths MUST come before less specific ones

  /**
   * GET /api/v1/ai/suggestions/health
   * Health check for suggestions service
   */
  http.get("/api/v1/ai/suggestions/health", () => {
    return apiJsonResponse({
      status: "healthy",
      websocketAvailable: false,
      fallbackActive: true,
      timestamp: Date.now(),
    });
  }),

  /**
   * POST /api/v1/ai/suggestions/request
   * Request new suggestions with context
   */
  http.post("/api/v1/ai/suggestions/request", async ({ request }) => {
    const body = (await request.json()) as SuggestionRequestBody;

    if (!body.context) {
      return apiErrorResponse("Missing context in request body", 400);
    }

    // Generate context-aware suggestions
    const newSuggestions = generateContextSuggestions(body.context);

    // Add to current suggestions (avoiding duplicates)
    for (const suggestion of newSuggestions) {
      if (!suggestions.find((s) => s.id === suggestion.id)) {
        suggestions.push(suggestion);
      }
    }

    return apiJsonResponse({
      type: "suggestions",
      data: newSuggestions,
      timestamp: Date.now(),
    });
  }),

  /**
   * POST /api/v1/ai/suggestions/dismiss
   * Dismiss a specific suggestion
   */
  http.post("/api/v1/ai/suggestions/dismiss", async ({ request }) => {
    const body = (await request.json()) as DismissRequestBody;

    if (!body.id) {
      return apiErrorResponse("Missing suggestion ID", 400);
    }

    const index = suggestions.findIndex((s) => s.id === body.id);

    if (index === -1) {
      return apiErrorResponse(`Suggestion not found: ${body.id}`, 404);
    }

    suggestions.splice(index, 1);

    return apiJsonResponse({
      type: "dismissed",
      id: body.id,
      timestamp: Date.now(),
    });
  }),

  /**
   * GET /api/v1/ai/suggestions
   * Returns current suggestions (polling endpoint)
   * NOTE: Must be LAST to not match sub-paths
   */
  http.get("/api/v1/ai/suggestions", () => {
    return apiJsonResponse({
      type: "suggestions",
      data: suggestions,
      timestamp: Date.now(),
    });
  }),
];

export default aiSuggestionsHandlers;
