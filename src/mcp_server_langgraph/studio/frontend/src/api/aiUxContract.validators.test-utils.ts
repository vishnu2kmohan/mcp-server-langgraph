/**
 * Type Guard Validators for AI UX Contract Tests
 *
 * Runtime validators that match generated OpenAPI types.
 * These validators check wire format (snake_case) before RTK Query transforms.
 */
/* eslint-disable no-restricted-syntax */

import type {
  NudgeContext,
  NudgeHistoryItem,
  NudgeRecommendRequest,
  NudgeRecommendResponse,
  SignupContext,
  OnboardingPersonalizeRequest,
  OnboardingPersonalizeResponse,
  PersonaAnalyzeRequest,
  PersonaAnalyzeResponse,
  DisclosureAnalyzeRequest,
  DisclosureAnalyzeResponse,
  EmptyStateSuggestionsRequest,
  EmptyStateSuggestionsResponse,
  ErrorAnalyzeRequest,
  ErrorAnalyzeResponse,
  MetricsInsightsResponse,
} from "./aiUxContract.types.test-utils";

// =============================================================================
// Core AI UX Validators
// =============================================================================

/**
 * Validates NudgeContext structure
 */
export function isValidNudgeContext(obj: unknown): obj is NudgeContext {
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
export function isValidNudgeHistoryItem(obj: unknown): obj is NudgeHistoryItem {
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
export function isValidNudgeRecommendRequest(
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
export function isValidNudgeRecommendResponse(
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
export function isValidSignupContext(obj: unknown): obj is SignupContext {
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
export function isValidOnboardingPersonalizeRequest(
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
export function isValidOnboardingPersonalizeResponse(
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
export function isValidPersonaAnalyzeRequest(
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
export function isValidPersonaAnalyzeResponse(
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
// ADR-0091 Phase 9: Aligned Schema Validators
// =============================================================================

/**
 * Validates DisclosureAnalyzeRequest structure (aligned with frontend)
 */
export function isValidDisclosureAnalyzeRequest(
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
 */
export function isValidDisclosureAnalyzeResponse(
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
 */
export function isValidEmptyStateSuggestionsRequest(
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
 */
export function isValidEmptyStateSuggestionsResponse(
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
 */
export function isValidErrorAnalyzeRequest(
  obj: unknown,
): obj is ErrorAnalyzeRequest {
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
 */
export function isValidErrorAnalyzeResponse(
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
 */
export function isValidMetricsInsightsResponse(
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
