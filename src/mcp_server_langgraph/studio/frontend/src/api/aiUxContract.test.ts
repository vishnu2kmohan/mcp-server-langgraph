/**
 * AI UX Endpoint Contract Tests
 *
 * TDD: Validates frontend request/response types match backend Pydantic models
 * using generated OpenAPI types as the source of truth.
 *
 * These tests:
 * 1. Verify generated types exist and have correct structure
 * 2. Validate RTK Query mutation types align with generated types
 * 3. Ensure snake_case contracts are enforced at the API boundary
 *
 * Reference: src/mcp_server_langgraph/api/v1/ai_ux.py
 * Generated: src/types/generated-api.ts
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import type { components } from "../types/generated-api";

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

// =============================================================================
// Generated Type Aliases (for readability)
// =============================================================================

type NudgeRecommendRequest = components["schemas"]["NudgeRecommendRequest"];
type NudgeRecommendResponse = components["schemas"]["NudgeRecommendResponse"];
type NudgeContext = components["schemas"]["NudgeContext"];
type NudgeHistoryItem = components["schemas"]["NudgeHistoryItem"];

type OnboardingPersonalizeRequest =
  components["schemas"]["OnboardingPersonalizeRequest"];
type OnboardingPersonalizeResponse =
  components["schemas"]["OnboardingPersonalizeResponse"];
type SignupContext = components["schemas"]["SignupContext"];

type PersonaAnalyzeRequest = components["schemas"]["PersonaAnalyzeRequest"];
type PersonaAnalyzeResponse = components["schemas"]["PersonaAnalyzeResponse"];

// =============================================================================
// Type Guard Functions (validate runtime objects match generated types)
// =============================================================================

/**
 * Validates NudgeContext structure
 */
function isValidNudgeContext(obj: unknown): obj is NudgeContext {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;

  // page is required
  if (!("page" in o) || typeof o.page !== "string") return false;

  // action has default "viewing" - optional in request
  if ("action" in o && typeof o.action !== "string") return false;

  // time_on_page has default 0 - optional in request
  if ("time_on_page" in o && typeof o.time_on_page !== "number") return false;

  return true;
}

/**
 * Validates NudgeHistoryItem structure
 */
function isValidNudgeHistoryItem(obj: unknown): obj is NudgeHistoryItem {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;

  // nudge_id is required
  if (!("nudge_id" in o) || typeof o.nudge_id !== "string") return false;

  // shown_at is required
  if (!("shown_at" in o) || typeof o.shown_at !== "string") return false;

  // action is optional
  if ("action" in o && o.action !== null && typeof o.action !== "string")
    return false;

  return true;
}

/**
 * Validates NudgeRecommendRequest structure
 * Backend: NudgeRecommendRequest (ai_ux.py:205)
 */
function isValidNudgeRecommendRequest(
  obj: unknown,
): obj is NudgeRecommendRequest {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;

  // user_id is required
  if (!("user_id" in o) || typeof o.user_id !== "string") return false;

  // current_context is required
  if (!("current_context" in o) || !isValidNudgeContext(o.current_context))
    return false;

  // nudge_history is optional array
  if ("nudge_history" in o) {
    if (!Array.isArray(o.nudge_history)) return false;
    for (const item of o.nudge_history) {
      if (!isValidNudgeHistoryItem(item)) return false;
    }
  }

  return true;
}

/**
 * Validates NudgeRecommendResponse structure
 */
function isValidNudgeRecommendResponse(
  obj: unknown,
): obj is NudgeRecommendResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;

  // should_show is required boolean
  if (!("should_show" in o) || typeof o.should_show !== "boolean") return false;

  // confidence is required number (default 0.5)
  if (!("confidence" in o) || typeof o.confidence !== "number") return false;

  // nudge is optional (can be null)
  // Note: We don't validate the full Nudge structure here for simplicity

  return true;
}

/**
 * Validates SignupContext structure
 */
function isValidSignupContext(obj: unknown): obj is SignupContext {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;

  // All fields are optional
  if ("referrer" in o && o.referrer !== null && typeof o.referrer !== "string")
    return false;
  if (
    "utm_source" in o &&
    o.utm_source !== null &&
    typeof o.utm_source !== "string"
  )
    return false;
  if (
    "utm_campaign" in o &&
    o.utm_campaign !== null &&
    typeof o.utm_campaign !== "string"
  )
    return false;
  if (
    "utm_medium" in o &&
    o.utm_medium !== null &&
    typeof o.utm_medium !== "string"
  )
    return false;

  return true;
}

/**
 * Validates OnboardingPersonalizeRequest structure
 * Backend: OnboardingPersonalizeRequest (ai_ux.py:307)
 */
function isValidOnboardingPersonalizeRequest(
  obj: unknown,
): obj is OnboardingPersonalizeRequest {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;

  // user_id is required
  if (!("user_id" in o) || typeof o.user_id !== "string") return false;

  // initial_actions is optional array of strings
  if ("initial_actions" in o) {
    if (!Array.isArray(o.initial_actions)) return false;
    for (const action of o.initial_actions) {
      if (typeof action !== "string") return false;
    }
  }

  // signup_context is optional (can be null)
  if ("signup_context" in o && o.signup_context !== null) {
    if (!isValidSignupContext(o.signup_context)) return false;
  }

  return true;
}

/**
 * Validates OnboardingPersonalizeResponse structure
 */
function isValidOnboardingPersonalizeResponse(
  obj: unknown,
): obj is OnboardingPersonalizeResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;

  // detected_intent is required
  if (!("detected_intent" in o) || typeof o.detected_intent !== "string")
    return false;

  // confidence is required number
  if (!("confidence" in o) || typeof o.confidence !== "number") return false;

  // recommended_path is required array
  if (!("recommended_path" in o) || !Array.isArray(o.recommended_path))
    return false;

  return true;
}

/**
 * Validates PersonaAnalyzeRequest structure
 * Backend: PersonaAnalyzeRequest (ai_ux.py:373)
 */
function isValidPersonaAnalyzeRequest(
  obj: unknown,
): obj is PersonaAnalyzeRequest {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;

  // user_id is required
  if (!("user_id" in o) || typeof o.user_id !== "string") return false;

  // assigned_persona is required
  if (!("assigned_persona" in o) || typeof o.assigned_persona !== "string")
    return false;

  // recent_actions is optional array of strings
  if ("recent_actions" in o) {
    if (!Array.isArray(o.recent_actions)) return false;
    for (const action of o.recent_actions) {
      if (typeof action !== "string") return false;
    }
  }

  // feature_usage is optional Record<string, number>
  if ("feature_usage" in o) {
    if (typeof o.feature_usage !== "object" || o.feature_usage === null)
      return false;
    for (const [key, value] of Object.entries(
      o.feature_usage as Record<string, unknown>,
    )) {
      if (typeof key !== "string" || typeof value !== "number") return false;
    }
  }

  return true;
}

/**
 * Validates PersonaAnalyzeResponse structure
 */
function isValidPersonaAnalyzeResponse(
  obj: unknown,
): obj is PersonaAnalyzeResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;

  // assigned_persona is required
  if (!("assigned_persona" in o) || typeof o.assigned_persona !== "string")
    return false;

  // detected_persona is required
  if (!("detected_persona" in o) || typeof o.detected_persona !== "string")
    return false;

  // confidence is required number
  if (!("confidence" in o) || typeof o.confidence !== "number") return false;

  // behavior_signals is required array
  if (!("behavior_signals" in o) || !Array.isArray(o.behavior_signals))
    return false;

  return true;
}

// =============================================================================
// POST /api/v1/ai/nudges/recommend Contract Tests
// =============================================================================

describe("POST /api/v1/ai/nudges/recommend", () => {
  describe("Request Contract (NudgeRecommendRequest)", () => {
    it("should require user_id field", () => {
      expect(isValidNudgeRecommendRequest({})).toBe(false);
      expect(
        isValidNudgeRecommendRequest({
          current_context: { page: "chat" },
        }),
      ).toBe(false);
    });

    it("should require current_context field", () => {
      expect(
        isValidNudgeRecommendRequest({
          user_id: "user-123",
        }),
      ).toBe(false);
    });

    it("should require current_context.page field", () => {
      expect(
        isValidNudgeRecommendRequest({
          user_id: "user-123",
          current_context: {},
        }),
      ).toBe(false);
    });

    it("should accept valid minimal request", () => {
      expect(
        isValidNudgeRecommendRequest({
          user_id: "user-123",
          current_context: {
            page: "chat",
          },
        }),
      ).toBe(true);
    });

    it("should accept request with optional action and time_on_page", () => {
      expect(
        isValidNudgeRecommendRequest({
          user_id: "user-123",
          current_context: {
            page: "chat",
            action: "viewing",
            time_on_page: 30,
          },
        }),
      ).toBe(true);
    });

    it("should accept request with nudge_history", () => {
      expect(
        isValidNudgeRecommendRequest({
          user_id: "user-123",
          current_context: {
            page: "chat",
          },
          nudge_history: [
            {
              nudge_id: "nudge-1",
              shown_at: "2024-01-01T00:00:00Z",
              action: "dismissed",
            },
          ],
        }),
      ).toBe(true);
    });

    it("should reject invalid nudge_history items", () => {
      expect(
        isValidNudgeRecommendRequest({
          user_id: "user-123",
          current_context: { page: "chat" },
          nudge_history: [
            {
              // Missing nudge_id
              shown_at: "2024-01-01T00:00:00Z",
            },
          ],
        }),
      ).toBe(false);
    });
  });

  describe("Response Contract (NudgeRecommendResponse)", () => {
    it("should require should_show field", () => {
      expect(isValidNudgeRecommendResponse({})).toBe(false);
      expect(
        isValidNudgeRecommendResponse({
          confidence: 0.5,
        }),
      ).toBe(false);
    });

    it("should require confidence field", () => {
      expect(
        isValidNudgeRecommendResponse({
          should_show: true,
        }),
      ).toBe(false);
    });

    it("should accept valid response", () => {
      expect(
        isValidNudgeRecommendResponse({
          should_show: true,
          confidence: 0.85,
          nudge: null,
        }),
      ).toBe(true);
    });
  });
});

// =============================================================================
// POST /api/v1/ai/onboarding/personalize Contract Tests
// =============================================================================

describe("POST /api/v1/ai/onboarding/personalize", () => {
  describe("Request Contract (OnboardingPersonalizeRequest)", () => {
    it("should require user_id field", () => {
      expect(isValidOnboardingPersonalizeRequest({})).toBe(false);
      expect(
        isValidOnboardingPersonalizeRequest({
          initial_actions: ["viewed_docs"],
        }),
      ).toBe(false);
    });

    it("should accept valid minimal request", () => {
      expect(
        isValidOnboardingPersonalizeRequest({
          user_id: "user-123",
        }),
      ).toBe(true);
    });

    it("should accept request with initial_actions", () => {
      expect(
        isValidOnboardingPersonalizeRequest({
          user_id: "user-123",
          initial_actions: ["viewed_docs", "clicked_template"],
        }),
      ).toBe(true);
    });

    it("should accept request with signup_context", () => {
      expect(
        isValidOnboardingPersonalizeRequest({
          user_id: "user-123",
          signup_context: {
            referrer: "github",
            utm_source: "docs",
          },
        }),
      ).toBe(true);
    });

    it("should accept null signup_context", () => {
      expect(
        isValidOnboardingPersonalizeRequest({
          user_id: "user-123",
          signup_context: null,
        }),
      ).toBe(true);
    });

    it("should reject invalid initial_actions (non-string items)", () => {
      expect(
        isValidOnboardingPersonalizeRequest({
          user_id: "user-123",
          initial_actions: [123, "valid"],
        }),
      ).toBe(false);
    });
  });

  describe("Response Contract (OnboardingPersonalizeResponse)", () => {
    it("should require detected_intent field", () => {
      expect(
        isValidOnboardingPersonalizeResponse({
          confidence: 0.85,
          recommended_path: [],
        }),
      ).toBe(false);
    });

    it("should require confidence field", () => {
      expect(
        isValidOnboardingPersonalizeResponse({
          detected_intent: "build_chatbot",
          recommended_path: [],
        }),
      ).toBe(false);
    });

    it("should require recommended_path field", () => {
      expect(
        isValidOnboardingPersonalizeResponse({
          detected_intent: "build_chatbot",
          confidence: 0.85,
        }),
      ).toBe(false);
    });

    it("should accept valid response", () => {
      expect(
        isValidOnboardingPersonalizeResponse({
          detected_intent: "build_chatbot",
          confidence: 0.85,
          recommended_path: [{ step: "template_selection", guided: true }],
        }),
      ).toBe(true);
    });
  });
});

// =============================================================================
// POST /api/v1/ai/persona/analyze Contract Tests
// =============================================================================

describe("POST /api/v1/ai/persona/analyze", () => {
  describe("Request Contract (PersonaAnalyzeRequest)", () => {
    it("should require user_id field", () => {
      expect(isValidPersonaAnalyzeRequest({})).toBe(false);
      expect(
        isValidPersonaAnalyzeRequest({
          assigned_persona: "admin",
        }),
      ).toBe(false);
    });

    it("should require assigned_persona field", () => {
      expect(
        isValidPersonaAnalyzeRequest({
          user_id: "user-123",
        }),
      ).toBe(false);
    });

    it("should accept valid minimal request", () => {
      expect(
        isValidPersonaAnalyzeRequest({
          user_id: "user-123",
          assigned_persona: "admin",
        }),
      ).toBe(true);
    });

    it("should accept request with recent_actions", () => {
      expect(
        isValidPersonaAnalyzeRequest({
          user_id: "user-123",
          assigned_persona: "admin",
          recent_actions: ["create_workflow", "edit_node", "run_test"],
        }),
      ).toBe(true);
    });

    it("should accept request with feature_usage", () => {
      expect(
        isValidPersonaAnalyzeRequest({
          user_id: "user-123",
          assigned_persona: "developer",
          feature_usage: {
            workflow_builder: 25,
            traces: 15,
            chat: 5,
          },
        }),
      ).toBe(true);
    });

    it("should reject invalid feature_usage (non-number values)", () => {
      expect(
        isValidPersonaAnalyzeRequest({
          user_id: "user-123",
          assigned_persona: "admin",
          feature_usage: {
            workflow_builder: "many", // Should be number
          },
        }),
      ).toBe(false);
    });
  });

  describe("Response Contract (PersonaAnalyzeResponse)", () => {
    it("should require assigned_persona field", () => {
      expect(
        isValidPersonaAnalyzeResponse({
          detected_persona: "developer",
          confidence: 0.9,
          behavior_signals: [],
        }),
      ).toBe(false);
    });

    it("should require detected_persona field", () => {
      expect(
        isValidPersonaAnalyzeResponse({
          assigned_persona: "admin",
          confidence: 0.9,
          behavior_signals: [],
        }),
      ).toBe(false);
    });

    it("should require confidence field", () => {
      expect(
        isValidPersonaAnalyzeResponse({
          assigned_persona: "admin",
          detected_persona: "developer",
          behavior_signals: [],
        }),
      ).toBe(false);
    });

    it("should require behavior_signals field", () => {
      expect(
        isValidPersonaAnalyzeResponse({
          assigned_persona: "admin",
          detected_persona: "developer",
          confidence: 0.9,
        }),
      ).toBe(false);
    });

    it("should accept valid response", () => {
      expect(
        isValidPersonaAnalyzeResponse({
          assigned_persona: "admin",
          detected_persona: "developer",
          confidence: 0.9,
          behavior_signals: ["high_api_usage", "workflow_creation"],
        }),
      ).toBe(true);
    });
  });
});

// =============================================================================
// ADR-0091 Phase 9: Aligned Schema Contract Tests
// These tests define the expected schema structure AFTER backend alignment.
// The backend Pydantic models should be updated to match these expectations.
// =============================================================================

// Type aliases for aligned schemas (to be added to generated-api.ts after backend update)
type DisclosureAnalyzeRequest =
  components["schemas"]["DisclosureAnalyzeRequest"];
type DisclosureAnalyzeResponse =
  components["schemas"]["DisclosureAnalyzeResponse"];
type EmptyStateSuggestionsRequest =
  components["schemas"]["EmptyStateSuggestionsRequest"];
type EmptyStateSuggestionsResponse =
  components["schemas"]["EmptyStateSuggestionsResponse"];
type ErrorAnalyzeRequest = components["schemas"]["ErrorAnalyzeRequest"];
type ErrorAnalyzeResponse = components["schemas"]["ErrorAnalyzeResponse"];
type MetricsInsightsResponse = components["schemas"]["MetricsInsightsResponse"];

/**
 * Validates DisclosureAnalyzeRequest structure (aligned with frontend)
 *
 * Expected request fields (matching frontend inline type):
 * - current_level: string (required)
 * - persona?: string (optional)
 * - context?: Record<string, unknown> (optional)
 * - user_behavior?: { feature_usage, session_count, avg_session_duration? } (optional)
 */
function isValidDisclosureAnalyzeRequest(
  obj: unknown,
): obj is DisclosureAnalyzeRequest {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;

  // current_level is required
  if (!("current_level" in o) || typeof o.current_level !== "string")
    return false;

  // persona is optional string
  if ("persona" in o && o.persona !== null && typeof o.persona !== "string")
    return false;

  // context is optional object
  if ("context" in o && o.context !== null && typeof o.context !== "object")
    return false;

  // user_behavior is optional object with specific fields
  if ("user_behavior" in o && o.user_behavior !== null) {
    if (typeof o.user_behavior !== "object") return false;
    const ub = o.user_behavior as Record<string, unknown>;
    // feature_usage is required in user_behavior
    if (!("feature_usage" in ub) || typeof ub.feature_usage !== "object")
      return false;
    // session_count is required in user_behavior
    if (!("session_count" in ub) || typeof ub.session_count !== "number")
      return false;
  }

  return true;
}

/**
 * Validates DisclosureAnalyzeResponse structure (aligned with frontend)
 *
 * Expected response fields (matching frontend inline type):
 * - current_level: string (required)
 * - recommended_level: string (required)
 * - confidence: number (required)
 * - unlock_features: string[] (required)
 * - personalized_message: string (required, not optional)
 * - reasoning?: string (optional - frontend extension)
 */
function isValidDisclosureAnalyzeResponse(
  obj: unknown,
): obj is DisclosureAnalyzeResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;

  if (!("current_level" in o) || typeof o.current_level !== "string")
    return false;
  if (!("recommended_level" in o) || typeof o.recommended_level !== "string")
    return false;
  if (!("confidence" in o) || typeof o.confidence !== "number") return false;
  if (!("unlock_features" in o) || !Array.isArray(o.unlock_features))
    return false;
  if (
    !("personalized_message" in o) ||
    typeof o.personalized_message !== "string"
  )
    return false;

  // reasoning is optional
  if (
    "reasoning" in o &&
    o.reasoning !== null &&
    typeof o.reasoning !== "string"
  )
    return false;

  return true;
}

/**
 * Validates EmptyStateSuggestionsRequest structure (aligned with frontend)
 *
 * Expected request fields (matching frontend inline type):
 * - context: string (required)
 * - persona?: string (optional)
 * - previous_actions?: string[] (optional)
 * - available_actions?: string[] (optional)
 */
function isValidEmptyStateSuggestionsRequest(
  obj: unknown,
): obj is EmptyStateSuggestionsRequest {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;

  // context is required
  if (!("context" in o) || typeof o.context !== "string") return false;

  // persona is optional string
  if ("persona" in o && o.persona !== null && typeof o.persona !== "string")
    return false;

  // previous_actions is optional array of strings
  if ("previous_actions" in o && o.previous_actions !== null) {
    if (!Array.isArray(o.previous_actions)) return false;
    for (const action of o.previous_actions) {
      if (typeof action !== "string") return false;
    }
  }

  // available_actions is optional array of strings
  if ("available_actions" in o && o.available_actions !== null) {
    if (!Array.isArray(o.available_actions)) return false;
    for (const action of o.available_actions) {
      if (typeof action !== "string") return false;
    }
  }

  return true;
}

/**
 * Validates EmptyStateSuggestionsResponse structure (aligned with frontend)
 *
 * Expected response fields (matching frontend inline type):
 * - suggestions: Array<{
 *     title: string,
 *     description: string,
 *     action_type: "navigate" | "create" | "learn" | "import",
 *     action_target: string,
 *     icon?: string,
 *     priority: number
 *   }>
 * - context_hint?: string
 */
function isValidEmptyStateSuggestionsResponse(
  obj: unknown,
): obj is EmptyStateSuggestionsResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;

  // suggestions is required array
  if (!("suggestions" in o) || !Array.isArray(o.suggestions)) return false;

  // Validate each suggestion
  for (const suggestion of o.suggestions) {
    if (typeof suggestion !== "object" || suggestion === null) return false;
    const s = suggestion as Record<string, unknown>;

    // title is required
    if (!("title" in s) || typeof s.title !== "string") return false;
    // description is required
    if (!("description" in s) || typeof s.description !== "string")
      return false;
    // action_type is required and must be one of the enum values
    if (!("action_type" in s) || typeof s.action_type !== "string")
      return false;
    if (
      !["navigate", "create", "learn", "import"].includes(
        s.action_type as string,
      )
    )
      return false;
    // action_target is required
    if (!("action_target" in s) || typeof s.action_target !== "string")
      return false;
    // priority is required
    if (!("priority" in s) || typeof s.priority !== "number") return false;
    // icon is optional
    if ("icon" in s && s.icon !== null && typeof s.icon !== "string")
      return false;
  }

  // context_hint is optional
  if (
    "context_hint" in o &&
    o.context_hint !== null &&
    typeof o.context_hint !== "string"
  )
    return false;

  return true;
}

/**
 * Validates ErrorAnalyzeRequest structure (aligned with frontend)
 *
 * Expected request fields (matching frontend inline type):
 * - error_code: string (required)
 * - error_message: string (required)
 * - context?: Record<string, unknown> (optional)
 * - stack_trace?: string (optional)
 */
function isValidErrorAnalyzeRequest(obj: unknown): obj is ErrorAnalyzeRequest {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;

  // error_code is required
  if (!("error_code" in o) || typeof o.error_code !== "string") return false;
  // error_message is required
  if (!("error_message" in o) || typeof o.error_message !== "string")
    return false;

  // context is optional object
  if ("context" in o && o.context !== null && typeof o.context !== "object")
    return false;

  // stack_trace is optional string
  if (
    "stack_trace" in o &&
    o.stack_trace !== null &&
    typeof o.stack_trace !== "string"
  )
    return false;

  return true;
}

/**
 * Validates ErrorAnalyzeResponse structure (aligned with frontend)
 *
 * Expected response fields (matching frontend inline type):
 * - error_type: string (required)
 * - recovery_steps: Array<{
 *     step_number: number,
 *     title: string,
 *     description: string,
 *     action_type: "automatic" | "manual" | "contact_support",
 *     action_target?: string
 *   }>
 * - auto_recoverable: boolean (required)
 * - suggested_action?: string (optional)
 * - confidence: number (required)
 */
function isValidErrorAnalyzeResponse(
  obj: unknown,
): obj is ErrorAnalyzeResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;

  // error_type is required
  if (!("error_type" in o) || typeof o.error_type !== "string") return false;
  // recovery_steps is required array
  if (!("recovery_steps" in o) || !Array.isArray(o.recovery_steps))
    return false;
  // auto_recoverable is required boolean
  if (!("auto_recoverable" in o) || typeof o.auto_recoverable !== "boolean")
    return false;
  // confidence is required number
  if (!("confidence" in o) || typeof o.confidence !== "number") return false;

  // Validate each recovery step
  for (const step of o.recovery_steps) {
    if (typeof step !== "object" || step === null) return false;
    const s = step as Record<string, unknown>;

    if (!("step_number" in s) || typeof s.step_number !== "number")
      return false;
    if (!("title" in s) || typeof s.title !== "string") return false;
    if (!("description" in s) || typeof s.description !== "string")
      return false;
    if (!("action_type" in s) || typeof s.action_type !== "string")
      return false;
    if (
      !["automatic", "manual", "contact_support"].includes(
        s.action_type as string,
      )
    )
      return false;
    // action_target is optional
    if (
      "action_target" in s &&
      s.action_target !== null &&
      typeof s.action_target !== "string"
    )
      return false;
  }

  // suggested_action is optional
  if (
    "suggested_action" in o &&
    o.suggested_action !== null &&
    typeof o.suggested_action !== "string"
  )
    return false;

  return true;
}

/**
 * Validates MetricsInsightsResponse structure (aligned with frontend)
 *
 * Expected response fields (matching frontend inline type):
 * - happiness_score: number (required)
 * - insights: Array<{
 *     category: "happiness" | "engagement" | "adoption" | "retention" | "task_success",
 *     title: string,
 *     description: string,
 *     trend: "improving" | "stable" | "declining",
 *     priority: "high" | "medium" | "low",
 *     suggested_action?: string
 *   }>
 * - overall_health: "excellent" | "good" | "needs_attention" | "critical" (required)
 * - recommendations: string[] (required)
 */
function isValidMetricsInsightsResponse(
  obj: unknown,
): obj is MetricsInsightsResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;

  // happiness_score is required number
  if (!("happiness_score" in o) || typeof o.happiness_score !== "number")
    return false;
  // insights is required array
  if (!("insights" in o) || !Array.isArray(o.insights)) return false;
  // overall_health is required
  if (!("overall_health" in o) || typeof o.overall_health !== "string")
    return false;
  if (
    !["excellent", "good", "needs_attention", "critical"].includes(
      o.overall_health as string,
    )
  )
    return false;
  // recommendations is required array
  if (!("recommendations" in o) || !Array.isArray(o.recommendations))
    return false;

  // Validate each insight
  for (const insight of o.insights) {
    if (typeof insight !== "object" || insight === null) return false;
    const i = insight as Record<string, unknown>;

    if (!("category" in i) || typeof i.category !== "string") return false;
    if (
      ![
        "happiness",
        "engagement",
        "adoption",
        "retention",
        "task_success",
      ].includes(i.category as string)
    )
      return false;
    if (!("title" in i) || typeof i.title !== "string") return false;
    if (!("description" in i) || typeof i.description !== "string")
      return false;
    if (!("trend" in i) || typeof i.trend !== "string") return false;
    if (!["improving", "stable", "declining"].includes(i.trend as string))
      return false;
    if (!("priority" in i) || typeof i.priority !== "string") return false;
    if (!["high", "medium", "low"].includes(i.priority as string)) return false;
    // suggested_action is optional
    if (
      "suggested_action" in i &&
      i.suggested_action !== null &&
      typeof i.suggested_action !== "string"
    )
      return false;
  }

  // Validate recommendations are strings
  for (const rec of o.recommendations) {
    if (typeof rec !== "string") return false;
  }

  return true;
}

// =============================================================================
// POST /api/v1/ai/disclosure/analyze Contract Tests (ADR-0091 Phase 9)
// =============================================================================

describe("POST /api/v1/ai/disclosure/analyze (aligned)", () => {
  describe("Request Contract (DisclosureAnalyzeRequest)", () => {
    it("should require current_level field", () => {
      expect(isValidDisclosureAnalyzeRequest({})).toBe(false);
      expect(
        isValidDisclosureAnalyzeRequest({
          persona: "admin",
        }),
      ).toBe(false);
    });

    it("should accept valid minimal request", () => {
      expect(
        isValidDisclosureAnalyzeRequest({
          current_level: "beginner",
        }),
      ).toBe(true);
    });

    it("should accept request with user_behavior", () => {
      expect(
        isValidDisclosureAnalyzeRequest({
          current_level: "intermediate",
          user_behavior: {
            feature_usage: { workflow_builder: 10 },
            session_count: 5,
          },
        }),
      ).toBe(true);
    });
  });

  describe("Response Contract (DisclosureAnalyzeResponse)", () => {
    it("should accept valid response with all required fields", () => {
      expect(
        isValidDisclosureAnalyzeResponse({
          current_level: "beginner",
          recommended_level: "intermediate",
          confidence: 0.85,
          unlock_features: ["advanced_settings"],
          personalized_message: "You're ready for more features!",
        }),
      ).toBe(true);
    });

    it("should accept response with optional reasoning", () => {
      expect(
        isValidDisclosureAnalyzeResponse({
          current_level: "beginner",
          recommended_level: "intermediate",
          confidence: 0.85,
          unlock_features: [],
          personalized_message: "Keep learning!",
          reasoning: "User has mastered basic features",
        }),
      ).toBe(true);
    });
  });
});

// =============================================================================
// POST /api/v1/ai/empty-state/suggestions Contract Tests (ADR-0091 Phase 9)
// =============================================================================

describe("POST /api/v1/ai/empty-state/suggestions (aligned)", () => {
  describe("Request Contract (EmptyStateSuggestionsRequest)", () => {
    it("should require context field", () => {
      expect(isValidEmptyStateSuggestionsRequest({})).toBe(false);
    });

    it("should accept valid minimal request", () => {
      expect(
        isValidEmptyStateSuggestionsRequest({
          context: "workflows",
        }),
      ).toBe(true);
    });

    it("should accept request with all optional fields", () => {
      expect(
        isValidEmptyStateSuggestionsRequest({
          context: "sessions",
          persona: "developer",
          previous_actions: ["viewed_docs"],
          available_actions: ["create_session", "import_template"],
        }),
      ).toBe(true);
    });
  });

  describe("Response Contract (EmptyStateSuggestionsResponse)", () => {
    it("should accept valid response with suggestions", () => {
      expect(
        isValidEmptyStateSuggestionsResponse({
          suggestions: [
            {
              title: "Create your first workflow",
              description: "Build an AI workflow with our visual editor",
              action_type: "create",
              action_target: "/studio/workflows/new",
              priority: 1,
            },
          ],
        }),
      ).toBe(true);
    });

    it("should accept response with context_hint", () => {
      expect(
        isValidEmptyStateSuggestionsResponse({
          suggestions: [],
          context_hint: "Try exploring the templates gallery",
        }),
      ).toBe(true);
    });

    it("should validate action_type enum values", () => {
      expect(
        isValidEmptyStateSuggestionsResponse({
          suggestions: [
            {
              title: "Test",
              description: "Test desc",
              action_type: "invalid_type", // Invalid!
              action_target: "/test",
              priority: 1,
            },
          ],
        }),
      ).toBe(false);
    });
  });
});

// =============================================================================
// POST /api/v1/ai/errors/analyze Contract Tests (ADR-0091 Phase 9)
// =============================================================================

describe("POST /api/v1/ai/errors/analyze (aligned)", () => {
  describe("Request Contract (ErrorAnalyzeRequest)", () => {
    it("should require error_code and error_message", () => {
      expect(isValidErrorAnalyzeRequest({})).toBe(false);
      expect(isValidErrorAnalyzeRequest({ error_code: "ERR_001" })).toBe(false);
      expect(
        isValidErrorAnalyzeRequest({ error_message: "Something failed" }),
      ).toBe(false);
    });

    it("should accept valid minimal request", () => {
      expect(
        isValidErrorAnalyzeRequest({
          error_code: "AUTH_FAILED",
          error_message: "Invalid credentials",
        }),
      ).toBe(true);
    });

    it("should accept request with optional fields", () => {
      expect(
        isValidErrorAnalyzeRequest({
          error_code: "NETWORK_ERROR",
          error_message: "Connection refused",
          context: { endpoint: "/api/v1/chat" },
          stack_trace: "Error at line 42...",
        }),
      ).toBe(true);
    });
  });

  describe("Response Contract (ErrorAnalyzeResponse)", () => {
    it("should accept valid response with recovery steps", () => {
      expect(
        isValidErrorAnalyzeResponse({
          error_type: "authentication",
          recovery_steps: [
            {
              step_number: 1,
              title: "Check credentials",
              description: "Verify your username and password are correct",
              action_type: "manual",
            },
            {
              step_number: 2,
              title: "Reset password",
              description: "Request a password reset if needed",
              action_type: "manual",
              action_target: "/reset-password",
            },
          ],
          auto_recoverable: false,
          confidence: 0.92,
        }),
      ).toBe(true);
    });

    it("should validate action_type enum values", () => {
      expect(
        isValidErrorAnalyzeResponse({
          error_type: "network",
          recovery_steps: [
            {
              step_number: 1,
              title: "Retry",
              description: "Try again",
              action_type: "invalid_action", // Invalid!
            },
          ],
          auto_recoverable: true,
          confidence: 0.8,
        }),
      ).toBe(false);
    });
  });
});

// =============================================================================
// GET /api/v1/ai/metrics/insights Contract Tests (ADR-0091 Phase 9)
// =============================================================================

describe("GET /api/v1/ai/metrics/insights (aligned)", () => {
  describe("Response Contract (MetricsInsightsResponse)", () => {
    it("should accept valid response with all fields", () => {
      expect(
        isValidMetricsInsightsResponse({
          happiness_score: 8.5,
          insights: [
            {
              category: "engagement",
              title: "Session duration increasing",
              description: "Users are spending more time in the app",
              trend: "improving",
              priority: "medium",
            },
          ],
          overall_health: "good",
          recommendations: ["Consider adding a feature tour"],
        }),
      ).toBe(true);
    });

    it("should validate category enum values", () => {
      expect(
        isValidMetricsInsightsResponse({
          happiness_score: 7.0,
          insights: [
            {
              category: "invalid_category", // Invalid!
              title: "Test",
              description: "Test desc",
              trend: "stable",
              priority: "low",
            },
          ],
          overall_health: "good",
          recommendations: [],
        }),
      ).toBe(false);
    });

    it("should validate overall_health enum values", () => {
      expect(
        isValidMetricsInsightsResponse({
          happiness_score: 5.0,
          insights: [],
          overall_health: "bad", // Invalid! Should be needs_attention or critical
          recommendations: [],
        }),
      ).toBe(false);
    });
  });
});

// =============================================================================
// Generated Types Smoke Tests
// =============================================================================

describe("Generated Types Smoke Tests", () => {
  it("should have NudgeRecommendRequest type with correct structure", () => {
    // This test validates the generated type exists and has expected shape
    // TypeScript compilation will fail if the type structure changes
    const validRequest: NudgeRecommendRequest = {
      user_id: "test-user",
      current_context: {
        page: "chat",
        action: "viewing",
        time_on_page: 0,
      },
    };
    expect(isValidNudgeRecommendRequest(validRequest)).toBe(true);
  });

  it("should have OnboardingPersonalizeRequest type with correct structure", () => {
    const validRequest: OnboardingPersonalizeRequest = {
      user_id: "test-user",
      initial_actions: ["action1"],
      signup_context: { referrer: "github" },
    };
    expect(isValidOnboardingPersonalizeRequest(validRequest)).toBe(true);
  });

  it("should have PersonaAnalyzeRequest type with correct structure", () => {
    const validRequest: PersonaAnalyzeRequest = {
      user_id: "test-user",
      assigned_persona: "admin",
      recent_actions: ["action1"],
      feature_usage: { feature1: 10 },
    };
    expect(isValidPersonaAnalyzeRequest(validRequest)).toBe(true);
  });
});
