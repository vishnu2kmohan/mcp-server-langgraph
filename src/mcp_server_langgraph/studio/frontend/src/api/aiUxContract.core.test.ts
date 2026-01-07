/**
 * AI UX Core Endpoint Contract Tests
 *
 * TDD: Validates frontend request/response types match backend Pydantic models
 * using generated OpenAPI types as the source of truth.
 *
 * Endpoints covered:
 * - POST /api/v1/ai/nudges/recommend
 * - POST /api/v1/ai/onboarding/personalize
 * - POST /api/v1/ai/persona/analyze
 *
 * Reference: src/mcp_server_langgraph/api/v1/ai_ux.py
 */

import { describe, it, expect, afterEach, vi } from "vitest";

import type {
  NudgeRecommendRequest,
  OnboardingPersonalizeRequest,
  PersonaAnalyzeRequest,
} from "./aiUxContract.types.test-utils";

import {
  isValidNudgeRecommendRequest,
  isValidNudgeRecommendResponse,
  isValidOnboardingPersonalizeRequest,
  isValidOnboardingPersonalizeResponse,
  isValidPersonaAnalyzeRequest,
  isValidPersonaAnalyzeResponse,
} from "./aiUxContract.validators.test-utils";

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

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
