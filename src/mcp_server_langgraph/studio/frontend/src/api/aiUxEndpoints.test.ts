/**
 * AI UX RTK Query Endpoints - Contract Tests
 *
 * TDD tests for AI UX endpoints (Phase 2.1).
 * Tests cover all 9 AI UX API endpoints that power the AI-augmented UX features.
 *
 * Backend Endpoints (from ai_ux.py):
 * - POST /ai/disclosure/analyze - Progressive disclosure analysis
 * - POST /ai/empty-state/suggestions - Empty state suggestions
 * - POST /ai/nudges/recommend - Smart nudge recommendations
 * - POST /ai/errors/analyze - Error recovery analysis
 * - POST /ai/onboarding/personalize - Onboarding personalization
 * - GET /ai/metrics/insights - HEART metrics insights
 * - POST /ai/persona/analyze - Persona behavior analysis
 * - POST /ai/composite/analyze - Composite analysis
 * - POST /ai/composite/batch - Batch composite analysis
 */

import { describe, it, expect, afterEach, vi } from "vitest";

// Import the RTK Query hooks to verify they exist
import {
  useAnalyzeDisclosureMutation,
  useGetEmptyStateSuggestionsMutation,
  useGetNudgeRecommendationMutation,
  useAnalyzeErrorMutation,
  usePersonalizeOnboardingMutation,
  useGetMetricsInsightsQuery,
  useAnalyzePersonaMutation,
  useAnalyzeCompositeMutation,
  useBatchCompositeAnalysisMutation,
} from "./index";

// ============================================================================
// Type Definitions for AI UX API
// These match the backend response types from ai_ux.py
// ============================================================================

/**
 * Disclosure level enum
 */
export type DisclosureLevel = "beginner" | "intermediate" | "advanced";

/**
 * Request for disclosure analysis
 */
export interface DisclosureAnalyzeRequest {
  current_level: DisclosureLevel;
  session_id?: string;
  behavior_data?: Record<string, unknown>;
}

/**
 * Response from disclosure analysis
 */
export interface DisclosureAnalyzeResponse {
  current_level: DisclosureLevel;
  recommended_level: DisclosureLevel;
  confidence: number;
  unlock_features: string[];
  personalized_message: string;
  reasoning?: string;
}

/**
 * Request for empty state suggestions
 */
export interface EmptyStateSuggestionsRequest {
  context: string;
  persona?: string;
  session_id?: string;
}

/**
 * Single suggestion item
 */
export interface EmptyStateSuggestion {
  action: string;
  label: string;
  priority: number;
  description?: string;
}

/**
 * Response from empty state suggestions
 */
export interface EmptyStateSuggestionsResponse {
  suggestions: EmptyStateSuggestion[];
  personalized_greeting: string;
  context_hints: string[];
}

/**
 * Request for nudge recommendation
 */
export interface NudgeRecommendRequest {
  context: string;
  user_actions?: string[];
  session_id?: string;
}

/**
 * Response from nudge recommendation
 */
export interface NudgeRecommendResponse {
  nudge_type: string;
  message: string;
  action: string;
  priority: "low" | "medium" | "high";
  confidence: number;
  dismiss_duration_hours: number;
}

/**
 * Request for error analysis
 */
export interface ErrorAnalyzeRequest {
  error_code: string;
  error_message: string;
  context?: string;
  stack_trace?: string;
}

/**
 * Recovery step in error analysis
 */
export interface RecoveryStep {
  step: number;
  action: string;
  label: string;
}

/**
 * Response from error analysis
 */
export interface ErrorAnalyzeResponse {
  error_type: string;
  severity: "info" | "warning" | "error" | "critical";
  recovery_steps: RecoveryStep[];
  personalized_message: string;
  auto_recoverable: boolean;
}

/**
 * Request for onboarding personalization
 */
export interface OnboardingPersonalizeRequest {
  detected_persona?: string;
  prior_experience?: string;
  preferences?: Record<string, unknown>;
}

/**
 * Response from onboarding personalization
 */
export interface OnboardingPersonalizeResponse {
  recommended_steps: string[];
  skip_steps: string[];
  personalized_flow: boolean;
  estimated_minutes: number;
  persona_detected: string;
}

/**
 * Request params for metrics insights query
 */
export interface MetricsInsightsParams {
  session_id?: string;
  period?: string;
}

/**
 * Single metric insight
 */
export interface MetricInsight {
  metric: string;
  trend: "improving" | "stable" | "declining";
  delta: number;
}

/**
 * Response from metrics insights
 */
export interface MetricsInsightsResponse {
  session_id?: string;
  happiness_score: number;
  engagement_rate: number;
  adoption_rate: number;
  retention_rate: number;
  task_success_rate: number;
  insights: MetricInsight[];
  recommendations: string[];
}

/**
 * Request for persona analysis
 */
export interface PersonaAnalyzeRequest {
  behavior_data: Record<string, unknown>;
  current_persona?: string;
}

/**
 * Response from persona analysis
 */
export interface PersonaAnalyzeResponse {
  detected_persona: string;
  confidence: number;
  behavior_patterns: string[];
  recommended_features: string[];
  mismatch_warning: string | null;
}

/**
 * Request for composite analysis
 */
export interface CompositeAnalyzeRequest {
  session_id?: string;
  include_disclosure?: boolean;
  include_nudges?: boolean;
  include_persona?: boolean;
}

/**
 * Response from composite analysis
 */
export interface CompositeAnalyzeResponse {
  analysis_id: string;
  timestamp: string;
  disclosure?: DisclosureAnalyzeResponse;
  nudges?: NudgeRecommendResponse[];
  persona?: PersonaAnalyzeResponse;
}

/**
 * Request for batch composite analysis
 */
export interface BatchCompositeRequest {
  requests: CompositeAnalyzeRequest[];
}

/**
 * Response from batch composite analysis
 */
export interface BatchCompositeResponse {
  results: CompositeAnalyzeResponse[];
  processed: number;
  failed: number;
  errors: string[];
}

// ============================================================================
// Type Guards for Runtime Validation
// ============================================================================

function isDisclosureAnalyzeResponse(
  obj: unknown,
): obj is DisclosureAnalyzeResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.current_level === "string" &&
    typeof o.recommended_level === "string" &&
    typeof o.confidence === "number" &&
    Array.isArray(o.unlock_features) &&
    typeof o.personalized_message === "string"
  );
}

function isEmptyStateSuggestionsResponse(
  obj: unknown,
): obj is EmptyStateSuggestionsResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    Array.isArray(o.suggestions) &&
    typeof o.personalized_greeting === "string" &&
    Array.isArray(o.context_hints)
  );
}

function isNudgeRecommendResponse(obj: unknown): obj is NudgeRecommendResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.nudge_type === "string" &&
    typeof o.message === "string" &&
    typeof o.action === "string" &&
    typeof o.confidence === "number" &&
    typeof o.dismiss_duration_hours === "number"
  );
}

function isErrorAnalyzeResponse(obj: unknown): obj is ErrorAnalyzeResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.error_type === "string" &&
    typeof o.severity === "string" &&
    Array.isArray(o.recovery_steps) &&
    typeof o.personalized_message === "string" &&
    typeof o.auto_recoverable === "boolean"
  );
}

function isOnboardingPersonalizeResponse(
  obj: unknown,
): obj is OnboardingPersonalizeResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    Array.isArray(o.recommended_steps) &&
    Array.isArray(o.skip_steps) &&
    typeof o.personalized_flow === "boolean" &&
    typeof o.estimated_minutes === "number" &&
    typeof o.persona_detected === "string"
  );
}

function isMetricsInsightsResponse(
  obj: unknown,
): obj is MetricsInsightsResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.happiness_score === "number" &&
    typeof o.engagement_rate === "number" &&
    typeof o.task_success_rate === "number" &&
    Array.isArray(o.insights) &&
    Array.isArray(o.recommendations)
  );
}

function isPersonaAnalyzeResponse(obj: unknown): obj is PersonaAnalyzeResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.detected_persona === "string" &&
    typeof o.confidence === "number" &&
    Array.isArray(o.behavior_patterns) &&
    Array.isArray(o.recommended_features)
  );
}

function isCompositeAnalyzeResponse(
  obj: unknown,
): obj is CompositeAnalyzeResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return typeof o.analysis_id === "string" && typeof o.timestamp === "string";
}

function isBatchCompositeResponse(obj: unknown): obj is BatchCompositeResponse {
  if (typeof obj !== "object" || obj === null) return false;
  const o = obj as Record<string, unknown>;
  return (
    Array.isArray(o.results) &&
    typeof o.processed === "number" &&
    typeof o.failed === "number" &&
    Array.isArray(o.errors)
  );
}

// ============================================================================
// Hook Existence Tests (TDD RED Phase - verify hooks exist)
// ============================================================================

describe("AI UX RTK Query Endpoints - Hook Existence", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it("should export useAnalyzeDisclosureMutation hook", () => {
    expect(useAnalyzeDisclosureMutation).toBeDefined();
    expect(typeof useAnalyzeDisclosureMutation).toBe("function");
  });

  it("should export useGetEmptyStateSuggestionsMutation hook", () => {
    expect(useGetEmptyStateSuggestionsMutation).toBeDefined();
    expect(typeof useGetEmptyStateSuggestionsMutation).toBe("function");
  });

  it("should export useGetNudgeRecommendationMutation hook", () => {
    expect(useGetNudgeRecommendationMutation).toBeDefined();
    expect(typeof useGetNudgeRecommendationMutation).toBe("function");
  });

  it("should export useAnalyzeErrorMutation hook", () => {
    expect(useAnalyzeErrorMutation).toBeDefined();
    expect(typeof useAnalyzeErrorMutation).toBe("function");
  });

  it("should export usePersonalizeOnboardingMutation hook", () => {
    expect(usePersonalizeOnboardingMutation).toBeDefined();
    expect(typeof usePersonalizeOnboardingMutation).toBe("function");
  });

  it("should export useGetMetricsInsightsQuery hook", () => {
    expect(useGetMetricsInsightsQuery).toBeDefined();
    expect(typeof useGetMetricsInsightsQuery).toBe("function");
  });

  it("should export useAnalyzePersonaMutation hook", () => {
    expect(useAnalyzePersonaMutation).toBeDefined();
    expect(typeof useAnalyzePersonaMutation).toBe("function");
  });

  it("should export useAnalyzeCompositeMutation hook", () => {
    expect(useAnalyzeCompositeMutation).toBeDefined();
    expect(typeof useAnalyzeCompositeMutation).toBe("function");
  });

  it("should export useBatchCompositeAnalysisMutation hook", () => {
    expect(useBatchCompositeAnalysisMutation).toBeDefined();
    expect(typeof useBatchCompositeAnalysisMutation).toBe("function");
  });
});

// ============================================================================
// Type Guard Tests (validate response type checking)
// ============================================================================

describe("AI UX API Type Guards", () => {
  describe("isDisclosureAnalyzeResponse", () => {
    it("should return true for valid disclosure response", () => {
      const valid = {
        current_level: "beginner",
        recommended_level: "intermediate",
        confidence: 0.85,
        unlock_features: ["feature1", "feature2"],
        personalized_message: "Great progress!",
      };
      expect(isDisclosureAnalyzeResponse(valid)).toBe(true);
    });

    it("should return false for invalid disclosure response", () => {
      expect(isDisclosureAnalyzeResponse(null)).toBe(false);
      expect(isDisclosureAnalyzeResponse({})).toBe(false);
      expect(isDisclosureAnalyzeResponse({ current_level: "beginner" })).toBe(
        false,
      );
    });
  });

  describe("isEmptyStateSuggestionsResponse", () => {
    it("should return true for valid empty state response", () => {
      const valid = {
        suggestions: [{ action: "create", label: "Create New", priority: 1 }],
        personalized_greeting: "Welcome!",
        context_hints: ["hint1"],
      };
      expect(isEmptyStateSuggestionsResponse(valid)).toBe(true);
    });

    it("should return false for invalid empty state response", () => {
      expect(isEmptyStateSuggestionsResponse(null)).toBe(false);
      expect(isEmptyStateSuggestionsResponse({ suggestions: [] })).toBe(false);
    });
  });

  describe("isNudgeRecommendResponse", () => {
    it("should return true for valid nudge response", () => {
      const valid = {
        nudge_type: "feature_discovery",
        message: "Try this!",
        action: "show_feature",
        priority: "low",
        confidence: 0.72,
        dismiss_duration_hours: 24,
      };
      expect(isNudgeRecommendResponse(valid)).toBe(true);
    });

    it("should return false for invalid nudge response", () => {
      expect(isNudgeRecommendResponse(null)).toBe(false);
      expect(isNudgeRecommendResponse({ nudge_type: "tip" })).toBe(false);
    });
  });

  describe("isErrorAnalyzeResponse", () => {
    it("should return true for valid error analysis response", () => {
      const valid = {
        error_type: "authentication",
        severity: "warning",
        recovery_steps: [{ step: 1, action: "retry", label: "Retry" }],
        personalized_message: "Let's fix this",
        auto_recoverable: true,
      };
      expect(isErrorAnalyzeResponse(valid)).toBe(true);
    });

    it("should return false for invalid error analysis response", () => {
      expect(isErrorAnalyzeResponse(null)).toBe(false);
      expect(isErrorAnalyzeResponse({ error_type: "auth" })).toBe(false);
    });
  });

  describe("isOnboardingPersonalizeResponse", () => {
    it("should return true for valid onboarding response", () => {
      const valid = {
        recommended_steps: ["step1", "step2"],
        skip_steps: ["step3"],
        personalized_flow: true,
        estimated_minutes: 5,
        persona_detected: "developer",
      };
      expect(isOnboardingPersonalizeResponse(valid)).toBe(true);
    });

    it("should return false for invalid onboarding response", () => {
      expect(isOnboardingPersonalizeResponse(null)).toBe(false);
      expect(isOnboardingPersonalizeResponse({ recommended_steps: [] })).toBe(
        false,
      );
    });
  });

  describe("isMetricsInsightsResponse", () => {
    it("should return true for valid metrics insights response", () => {
      const valid = {
        happiness_score: 4.2,
        engagement_rate: 0.78,
        adoption_rate: 0.65,
        retention_rate: 0.82,
        task_success_rate: 0.91,
        insights: [{ metric: "engagement", trend: "improving", delta: 0.1 }],
        recommendations: ["Enable shortcuts"],
      };
      expect(isMetricsInsightsResponse(valid)).toBe(true);
    });

    it("should return false for invalid metrics insights response", () => {
      expect(isMetricsInsightsResponse(null)).toBe(false);
      expect(isMetricsInsightsResponse({ happiness_score: 4.2 })).toBe(false);
    });
  });

  describe("isPersonaAnalyzeResponse", () => {
    it("should return true for valid persona analysis response", () => {
      const valid = {
        detected_persona: "alice-builder",
        confidence: 0.88,
        behavior_patterns: ["frequent_chat", "workflow_creation"],
        recommended_features: ["background_agents"],
        mismatch_warning: null,
      };
      expect(isPersonaAnalyzeResponse(valid)).toBe(true);
    });

    it("should return false for invalid persona analysis response", () => {
      expect(isPersonaAnalyzeResponse(null)).toBe(false);
      expect(isPersonaAnalyzeResponse({ detected_persona: "admin" })).toBe(
        false,
      );
    });
  });

  describe("isCompositeAnalyzeResponse", () => {
    it("should return true for valid composite analysis response", () => {
      const valid = {
        analysis_id: "analysis-001",
        timestamp: new Date().toISOString(),
      };
      expect(isCompositeAnalyzeResponse(valid)).toBe(true);
    });

    it("should return false for invalid composite analysis response", () => {
      expect(isCompositeAnalyzeResponse(null)).toBe(false);
      expect(isCompositeAnalyzeResponse({ analysis_id: "001" })).toBe(false);
    });
  });

  describe("isBatchCompositeResponse", () => {
    it("should return true for valid batch composite response", () => {
      const valid = {
        results: [],
        processed: 0,
        failed: 0,
        errors: [],
      };
      expect(isBatchCompositeResponse(valid)).toBe(true);
    });

    it("should return false for invalid batch composite response", () => {
      expect(isBatchCompositeResponse(null)).toBe(false);
      expect(isBatchCompositeResponse({ results: [] })).toBe(false);
    });
  });
});

// ============================================================================
// Request Type Tests (validate request structure)
// ============================================================================

describe("AI UX API Request Types", () => {
  it("should have valid DisclosureAnalyzeRequest structure", () => {
    const request: DisclosureAnalyzeRequest = {
      current_level: "beginner",
      session_id: "session-123",
    };
    expect(request.current_level).toBe("beginner");
  });

  it("should have valid EmptyStateSuggestionsRequest structure", () => {
    const request: EmptyStateSuggestionsRequest = {
      context: "chat_page",
      persona: "alice-builder",
    };
    expect(request.context).toBe("chat_page");
  });

  it("should have valid NudgeRecommendRequest structure", () => {
    const request: NudgeRecommendRequest = {
      context: "workflow_page",
      user_actions: ["viewed_flow", "clicked_node"],
    };
    expect(request.user_actions).toHaveLength(2);
  });

  it("should have valid ErrorAnalyzeRequest structure", () => {
    const request: ErrorAnalyzeRequest = {
      error_code: "401",
      error_message: "Unauthorized",
      context: "api_call",
    };
    expect(request.error_code).toBe("401");
  });

  it("should have valid OnboardingPersonalizeRequest structure", () => {
    const request: OnboardingPersonalizeRequest = {
      detected_persona: "developer",
      prior_experience: "some",
    };
    expect(request.detected_persona).toBe("developer");
  });

  it("should have valid PersonaAnalyzeRequest structure", () => {
    const request: PersonaAnalyzeRequest = {
      behavior_data: { pages_visited: ["chat", "workflows"] },
      current_persona: "admin",
    };
    expect(request.current_persona).toBe("admin");
  });

  it("should have valid CompositeAnalyzeRequest structure", () => {
    const request: CompositeAnalyzeRequest = {
      session_id: "session-123",
      include_disclosure: true,
      include_nudges: true,
      include_persona: true,
    };
    expect(request.include_disclosure).toBe(true);
  });

  it("should have valid BatchCompositeRequest structure", () => {
    const request: BatchCompositeRequest = {
      requests: [
        { session_id: "session-1", include_disclosure: true },
        { session_id: "session-2", include_nudges: true },
      ],
    };
    expect(request.requests).toHaveLength(2);
  });
});
