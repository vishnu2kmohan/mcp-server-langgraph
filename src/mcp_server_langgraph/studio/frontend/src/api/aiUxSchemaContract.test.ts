/**
 * AI UX Schema Contract Tests
 *
 * TDD contract tests ensuring MSW handlers return data matching
 * RTK Query API schema definitions.
 *
 * These tests validate that mock responses match the expected API contract,
 * preventing schema drift between mocks and actual API expectations.
 */

import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from "vitest";
import { setupServer } from "msw/node";
import { aiHandlers } from "../mocks/handlers/aiHandlers";

// Set up MSW server with AI handlers
const server = setupServer(...aiHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});
afterAll(() => server.close());

/**
 * Schema definitions from RTK Query (api/index.ts)
 * These are the canonical schemas that MSW handlers must match.
 */

interface EmptyStateSuggestionSchema {
  title: string;
  description: string;
  action_type: "navigate" | "create" | "learn" | "import";
  action_target: string;
  icon?: string;
  priority: number;
}

interface EmptyStateSuggestionsResponse {
  suggestions: EmptyStateSuggestionSchema[];
  context_hint?: string;
}

interface DisclosureAnalyzeResponse {
  current_level: string;
  recommended_level: string;
  confidence: number;
  unlock_features: string[];
  personalized_message: string;
  reasoning?: string;
}

interface NudgeRecommendationResponse {
  nudge_type: string;
  message: string;
  confidence: number;
  action_cta?: string;
  action_target?: string;
  dismiss_duration_ms?: number;
}

interface ErrorAnalyzeResponse {
  error_type: string;
  recovery_steps: Array<{
    step_number: number;
    title: string;
    description: string;
    action_type: "automatic" | "manual" | "contact_support";
    action_target?: string;
  }>;
  auto_recoverable: boolean;
  suggested_action?: string;
  confidence: number;
}

interface OnboardingPersonalizeResponse {
  recommended_steps: string[];
  skip_steps: string[];
  estimated_duration_minutes: number;
  personalization_applied: boolean;
  reasoning?: string;
}

describe("AI UX API Schema Contract Tests", () => {
  describe("POST /api/v1/ai/empty-state/suggestions", () => {
    it("should return response matching EmptyStateSuggestionsResponse schema", async () => {
      const response = await fetch("/api/v1/ai/empty-state/suggestions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          context: "workflows",
          persona: "alice-builder",
        }),
      });

      expect(response.ok).toBe(true);
      const data: EmptyStateSuggestionsResponse = await response.json();

      // Validate response structure
      expect(data).toHaveProperty("suggestions");
      expect(Array.isArray(data.suggestions)).toBe(true);

      // Validate each suggestion matches schema
      for (const suggestion of data.suggestions) {
        expect(suggestion).toHaveProperty("title");
        expect(typeof suggestion.title).toBe("string");

        expect(suggestion).toHaveProperty("description");
        expect(typeof suggestion.description).toBe("string");

        expect(suggestion).toHaveProperty("action_type");
        expect(["navigate", "create", "learn", "import"]).toContain(
          suggestion.action_type,
        );

        expect(suggestion).toHaveProperty("action_target");
        expect(typeof suggestion.action_target).toBe("string");

        expect(suggestion).toHaveProperty("priority");
        expect(typeof suggestion.priority).toBe("number");

        // icon is optional
        if (suggestion.icon !== undefined) {
          expect(typeof suggestion.icon).toBe("string");
        }
      }

      // context_hint is optional
      if (data.context_hint !== undefined) {
        expect(typeof data.context_hint).toBe("string");
      }
    });

    it("should return valid suggestions for different contexts", async () => {
      const contexts = ["workflows", "sessions", "projects", "chat"];

      for (const context of contexts) {
        const response = await fetch("/api/v1/ai/empty-state/suggestions", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ context }),
        });

        expect(response.ok).toBe(true);
        const data: EmptyStateSuggestionsResponse = await response.json();
        expect(data.suggestions).toBeDefined();
      }
    });
  });

  describe("POST /api/v1/ai/disclosure/analyze", () => {
    it("should return response matching DisclosureAnalyzeResponse schema", async () => {
      const response = await fetch("/api/v1/ai/disclosure/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_level: "basic",
          persona: "alice-builder",
        }),
      });

      expect(response.ok).toBe(true);
      const data: DisclosureAnalyzeResponse = await response.json();

      expect(data).toHaveProperty("current_level");
      expect(typeof data.current_level).toBe("string");

      expect(data).toHaveProperty("recommended_level");
      expect(typeof data.recommended_level).toBe("string");

      expect(data).toHaveProperty("confidence");
      expect(typeof data.confidence).toBe("number");
      expect(data.confidence).toBeGreaterThanOrEqual(0);
      expect(data.confidence).toBeLessThanOrEqual(1);

      expect(data).toHaveProperty("unlock_features");
      expect(Array.isArray(data.unlock_features)).toBe(true);

      expect(data).toHaveProperty("personalized_message");
      expect(typeof data.personalized_message).toBe("string");

      if (data.reasoning !== undefined) {
        expect(typeof data.reasoning).toBe("string");
      }
    });
  });

  describe("POST /api/v1/ai/nudges/recommend", () => {
    it("should return response matching NudgeRecommendationResponse schema", async () => {
      const response = await fetch("/api/v1/ai/nudges/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          context: "chat",
          current_feature: "chat-input",
        }),
      });

      expect(response.ok).toBe(true);
      const data: NudgeRecommendationResponse = await response.json();

      expect(data).toHaveProperty("nudge_type");
      expect(typeof data.nudge_type).toBe("string");

      expect(data).toHaveProperty("message");
      expect(typeof data.message).toBe("string");

      expect(data).toHaveProperty("confidence");
      expect(typeof data.confidence).toBe("number");

      if (data.action_cta !== undefined) {
        expect(typeof data.action_cta).toBe("string");
      }

      if (data.action_target !== undefined) {
        expect(typeof data.action_target).toBe("string");
      }

      if (data.dismiss_duration_ms !== undefined) {
        expect(typeof data.dismiss_duration_ms).toBe("number");
      }
    });
  });

  describe("POST /api/v1/ai/errors/analyze", () => {
    it("should return response matching ErrorAnalyzeResponse schema", async () => {
      const response = await fetch("/api/v1/ai/errors/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          error_code: "AUTH_001",
          error_message: "Session expired",
        }),
      });

      expect(response.ok).toBe(true);
      const data: ErrorAnalyzeResponse = await response.json();

      expect(data).toHaveProperty("error_type");
      expect(typeof data.error_type).toBe("string");

      expect(data).toHaveProperty("recovery_steps");
      expect(Array.isArray(data.recovery_steps)).toBe(true);

      for (const step of data.recovery_steps) {
        expect(step).toHaveProperty("step_number");
        expect(typeof step.step_number).toBe("number");

        expect(step).toHaveProperty("title");
        expect(typeof step.title).toBe("string");

        expect(step).toHaveProperty("description");
        expect(typeof step.description).toBe("string");

        expect(step).toHaveProperty("action_type");
        expect(["automatic", "manual", "contact_support"]).toContain(
          step.action_type,
        );

        if (step.action_target !== undefined) {
          expect(typeof step.action_target).toBe("string");
        }
      }

      expect(data).toHaveProperty("auto_recoverable");
      expect(typeof data.auto_recoverable).toBe("boolean");

      expect(data).toHaveProperty("confidence");
      expect(typeof data.confidence).toBe("number");

      if (data.suggested_action !== undefined) {
        expect(typeof data.suggested_action).toBe("string");
      }
    });
  });

  describe("POST /api/v1/ai/onboarding/personalize", () => {
    it("should return response matching OnboardingPersonalizeResponse schema", async () => {
      const response = await fetch("/api/v1/ai/onboarding/personalize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          detected_persona: "developer",
          experience_level: "intermediate",
        }),
      });

      expect(response.ok).toBe(true);
      const data: OnboardingPersonalizeResponse = await response.json();

      expect(data).toHaveProperty("recommended_steps");
      expect(Array.isArray(data.recommended_steps)).toBe(true);

      expect(data).toHaveProperty("skip_steps");
      expect(Array.isArray(data.skip_steps)).toBe(true);

      expect(data).toHaveProperty("estimated_duration_minutes");
      expect(typeof data.estimated_duration_minutes).toBe("number");

      expect(data).toHaveProperty("personalization_applied");
      expect(typeof data.personalization_applied).toBe("boolean");

      if (data.reasoning !== undefined) {
        expect(typeof data.reasoning).toBe("string");
      }
    });
  });
});
