/**
 * AI UX Schema Contract Tests
 *
 * TDD contract tests ensuring MSW handlers return data matching
 * generated OpenAPI types (ADR-0091).
 *
 * These tests validate that mock responses match the expected API contract,
 * preventing schema drift between mocks and actual API expectations.
 *
 * IMPORTANT: All types imported from generated-api.ts to ensure contract alignment.
 */

import {
  describe,
  it,
  expect,
  beforeAll,
  afterAll,
  afterEach,
  vi,
} from "vitest";
import { setupServer } from "msw/node";
import { aiHandlers } from "../mocks/handlers/aiHandlers";
import type { components } from "../types/generated-api";

// Set up MSW server with AI handlers
const server = setupServer(...aiHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});
afterAll(() => server.close());

/**
 * Generated schema types from OpenAPI spec (ADR-0091)
 * Using generated types ensures tests break if backend contract changes.
 */

// Nudge types
type Nudge = components["schemas"]["Nudge"];
type NudgeRecommendResponse = components["schemas"]["NudgeRecommendResponse"];

// Onboarding types
type OnboardingStep = components["schemas"]["OnboardingStep"];
type OnboardingPersonalizeResponse =
  components["schemas"]["OnboardingPersonalizeResponse"];

// Persona types
type PersonaAnalyzeResponse = components["schemas"]["PersonaAnalyzeResponse"];
type UIAdaptation = components["schemas"]["UIAdaptation"];

// Empty state suggestion types (not in generated types, kept as local interface)
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

// Disclosure types (not in generated types, kept as local interface)
interface DisclosureAnalyzeResponse {
  current_level: string;
  recommended_level: string;
  confidence: number;
  unlock_features: string[];
  personalized_message: string;
  reasoning?: string;
}

// Error analysis types (not in generated types, kept as local interface)
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
    it("should return response matching generated NudgeRecommendResponse schema", async () => {
      const response = await fetch("/api/v1/ai/nudges/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "test-user",
          current_context: {
            page: "chat",
            action: "viewing",
          },
        }),
      });

      expect(response.ok).toBe(true);
      const data: NudgeRecommendResponse = await response.json();

      // Validate required fields from generated schema
      expect(data).toHaveProperty("should_show");
      expect(typeof data.should_show).toBe("boolean");

      expect(data).toHaveProperty("confidence");
      expect(typeof data.confidence).toBe("number");
      expect(data.confidence).toBeGreaterThanOrEqual(0);
      expect(data.confidence).toBeLessThanOrEqual(1);

      // Validate nudge object when present
      if (data.nudge !== null && data.nudge !== undefined) {
        const nudge: Nudge = data.nudge;

        expect(nudge).toHaveProperty("id");
        expect(typeof nudge.id).toBe("string");

        expect(nudge).toHaveProperty("type");
        expect(typeof nudge.type).toBe("string");

        expect(nudge).toHaveProperty("message");
        expect(typeof nudge.message).toBe("string");

        expect(nudge).toHaveProperty("priority");
        expect(typeof nudge.priority).toBe("string");

        expect(nudge).toHaveProperty("show_after_ms");
        expect(typeof nudge.show_after_ms).toBe("number");

        // target_element is optional
        if (
          nudge.target_element !== undefined &&
          nudge.target_element !== null
        ) {
          expect(typeof nudge.target_element).toBe("string");
        }
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
    it("should return response matching generated OnboardingPersonalizeResponse schema", async () => {
      const response = await fetch("/api/v1/ai/onboarding/personalize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "test-user",
          initial_actions: ["viewed_workflows", "clicked_templates"],
        }),
      });

      expect(response.ok).toBe(true);
      const data: OnboardingPersonalizeResponse = await response.json();

      // Validate required fields from generated schema
      expect(data).toHaveProperty("detected_intent");
      expect(typeof data.detected_intent).toBe("string");

      expect(data).toHaveProperty("confidence");
      expect(typeof data.confidence).toBe("number");
      expect(data.confidence).toBeGreaterThanOrEqual(0);
      expect(data.confidence).toBeLessThanOrEqual(1);

      expect(data).toHaveProperty("recommended_path");
      expect(Array.isArray(data.recommended_path)).toBe(true);

      // Validate each step in recommended_path
      for (const step of data.recommended_path) {
        const typedStep: OnboardingStep = step;

        expect(typedStep).toHaveProperty("step");
        expect(typeof typedStep.step).toBe("string");

        expect(typedStep).toHaveProperty("guided");
        expect(typeof typedStep.guided).toBe("boolean");

        // focus is optional
        if (typedStep.focus !== undefined && typedStep.focus !== null) {
          expect(typeof typedStep.focus).toBe("string");
        }

        // template is optional
        if (typedStep.template !== undefined && typedStep.template !== null) {
          expect(typeof typedStep.template).toBe("string");
        }
      }

      // skip_steps is optional
      if (data.skip_steps !== undefined) {
        expect(Array.isArray(data.skip_steps)).toBe(true);
      }

      // persona_prediction is optional
      if (
        data.persona_prediction !== undefined &&
        data.persona_prediction !== null
      ) {
        expect(typeof data.persona_prediction).toBe("string");
      }
    });
  });

  describe("POST /api/v1/ai/persona/analyze", () => {
    it("should return response matching generated PersonaAnalyzeResponse schema", async () => {
      const response = await fetch("/api/v1/ai/persona/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "test-user",
          assigned_persona: "bob",
          recent_actions: ["viewed_workflows", "edited_workflow"],
          feature_usage: { workflow_builder: 25, traces: 10 },
        }),
      });

      expect(response.ok).toBe(true);
      const data: PersonaAnalyzeResponse = await response.json();

      // Validate required fields from generated schema
      expect(data).toHaveProperty("assigned_persona");
      expect(typeof data.assigned_persona).toBe("string");

      expect(data).toHaveProperty("detected_persona");
      expect(typeof data.detected_persona).toBe("string");

      expect(data).toHaveProperty("confidence");
      expect(typeof data.confidence).toBe("number");
      expect(data.confidence).toBeGreaterThanOrEqual(0);
      expect(data.confidence).toBeLessThanOrEqual(1);

      expect(data).toHaveProperty("behavior_signals");
      expect(Array.isArray(data.behavior_signals)).toBe(true);

      // recommendation is optional
      if (data.recommendation !== undefined && data.recommendation !== null) {
        expect(typeof data.recommendation).toBe("string");
      }

      // ui_adaptations is optional
      if (data.ui_adaptations !== undefined) {
        expect(Array.isArray(data.ui_adaptations)).toBe(true);
        for (const adaptation of data.ui_adaptations) {
          const typedAdaptation: UIAdaptation = adaptation;
          expect(typedAdaptation).toHaveProperty("feature");
          expect(typeof typedAdaptation.feature).toBe("string");
          expect(typedAdaptation).toHaveProperty("action");
          expect(typeof typedAdaptation.action).toBe("string");
        }
      }
    });
  });
});
