/**
 * AI UX Aligned Schema Contract Tests
 *
 * ADR-0091 Phase 9: Aligned Schema Contract Tests
 * These tests define the expected schema structure AFTER backend alignment.
 * The backend Pydantic models should be updated to match these expectations.
 *
 * Endpoints covered:
 * - POST /api/v1/ai/disclosure/analyze
 * - POST /api/v1/ai/empty-state/suggestions
 * - POST /api/v1/ai/errors/analyze
 * - GET /api/v1/ai/metrics/insights
 */

import { describe, it, expect, afterEach, vi } from "vitest";

import {
  isValidDisclosureAnalyzeRequest,
  isValidDisclosureAnalyzeResponse,
  isValidEmptyStateSuggestionsRequest,
  isValidEmptyStateSuggestionsResponse,
  isValidErrorAnalyzeRequest,
  isValidErrorAnalyzeResponse,
  isValidMetricsInsightsResponse,
} from "./aiUxContract.validators.test-utils";

// Clean up after each test
afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

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
