/**
 * AI Handlers Tests - Phase 4
 *
 * Tests for AI API mock handlers.
 * Validates the contract between frontend and backend for AI endpoints.
 *
 * API Contract Testing:
 * - Handlers return snake_case responses (via apiJsonResponse)
 * - Tests use transformSnakeToCamel to validate transformation
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
import { transformSnakeToCamel } from "../../api/transforms";
import {
  aiHandlers,
  mockAIInterpretation,
  mockSuggestions,
} from "./aiHandlers";

// Setup MSW server with AI handlers
const server = setupServer(...aiHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});
afterAll(() => server.close());

describe("aiHandlers", () => {
  describe("POST /api/v1/ai/interpret-command", () => {
    it("returns AI interpretation for valid query", async () => {
      const response = await fetch("/api/v1/ai/interpret-command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "show me compliance" }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data).toHaveProperty("action");
      expect(data).toHaveProperty("params");
      expect(data).toHaveProperty("confidence");
      expect(typeof data.confidence).toBe("number");
      expect(data.confidence).toBeGreaterThanOrEqual(0);
      expect(data.confidence).toBeLessThanOrEqual(1);
    });

    it("returns navigate action for navigation queries", async () => {
      const response = await fetch("/api/v1/ai/interpret-command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "go to compliance dashboard" }),
      });

      const data = await response.json();
      expect(data.action).toBe("navigate");
      expect(data.params).toHaveProperty("path");
    });

    it("returns search action for search-like queries", async () => {
      const response = await fetch("/api/v1/ai/interpret-command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: "find all workflows" }),
      });

      const data = await response.json();
      expect(data.action).toBe("search");
      expect(data.params).toHaveProperty("query");
    });

    it("returns 400 for missing query", async () => {
      const response = await fetch("/api/v1/ai/interpret-command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      expect(response.status).toBe(400);
    });
  });

  describe("GET /api/v1/ai/suggestions", () => {
    it("returns suggestions for artifact", async () => {
      const response = await fetch(
        "/api/v1/ai/suggestions?artifactId=artifact-1",
      );

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data).toHaveProperty("suggestions");
      expect(Array.isArray(data.suggestions)).toBe(true);
    });

    it("returns suggestions with required fields", async () => {
      const response = await fetch(
        "/api/v1/ai/suggestions?artifactId=artifact-1",
      );

      const data = await response.json();

      if (data.suggestions.length > 0) {
        const suggestion = data.suggestions[0];
        expect(suggestion).toHaveProperty("id");
        expect(suggestion).toHaveProperty("type");
        expect(suggestion).toHaveProperty("content");
        expect(suggestion).toHaveProperty("confidence");
        expect(["completion", "refactor", "fix", "explain"]).toContain(
          suggestion.type,
        );
      }
    });

    it("returns 400 for missing artifactId", async () => {
      const response = await fetch("/api/v1/ai/suggestions");

      expect(response.status).toBe(400);
    });
  });

  describe("POST /api/v1/ai/fetch-url", () => {
    it("returns fetched content for valid URL", async () => {
      const response = await fetch("/api/v1/ai/fetch-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: "https://example.com/page" }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data).toHaveProperty("content");
      expect(data).toHaveProperty("title");
      expect(data).toHaveProperty("url");
    });

    it("returns 400 for missing URL", async () => {
      const response = await fetch("/api/v1/ai/fetch-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });

      expect(response.status).toBe(400);
    });

    it("returns 422 for invalid URL format", async () => {
      const response = await fetch("/api/v1/ai/fetch-url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: "not-a-valid-url" }),
      });

      expect(response.status).toBe(422);
    });
  });

  describe("POST /api/v1/ai/empty-state/suggestions", () => {
    it("returns suggestions for empty state context", async () => {
      const response = await fetch("/api/v1/ai/empty-state/suggestions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          context: "workflows",
          persona: "alice-builder",
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data).toHaveProperty("suggestions");
      expect(Array.isArray(data.suggestions)).toBe(true);
    });

    it("returns suggestions with required fields (RTK Query schema)", async () => {
      const response = await fetch("/api/v1/ai/empty-state/suggestions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ context: "sessions" }),
      });

      const data = await response.json();

      if (data.suggestions.length > 0) {
        const suggestion = data.suggestions[0];
        // RTK Query schema: title, description, action_type, action_target, priority, icon?
        expect(suggestion).toHaveProperty("title");
        expect(suggestion).toHaveProperty("description");
        expect(suggestion).toHaveProperty("action_type");
        expect(suggestion).toHaveProperty("action_target");
        expect(suggestion).toHaveProperty("priority");
        expect(["navigate", "create", "learn", "import"]).toContain(
          suggestion.action_type,
        );
      }
    });

    it("returns persona-aware suggestions", async () => {
      const response = await fetch("/api/v1/ai/empty-state/suggestions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          context: "workflows",
          persona: "alice-analyst",
        }),
      });

      const data = await response.json();
      expect(data.suggestions.length).toBeGreaterThan(0);
    });

    it("returns context-specific suggestions", async () => {
      const workflowsResponse = await fetch(
        "/api/v1/ai/empty-state/suggestions",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ context: "workflows" }),
        },
      );

      const sessionsResponse = await fetch(
        "/api/v1/ai/empty-state/suggestions",
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ context: "sessions" }),
        },
      );

      const workflowsData = await workflowsResponse.json();
      const sessionsData = await sessionsResponse.json();

      // Suggestions should be different for different contexts
      expect(workflowsData.suggestions[0].title).not.toBe(
        sessionsData.suggestions[0].title,
      );
    });

    it("includes session context when provided", async () => {
      const response = await fetch("/api/v1/ai/empty-state/suggestions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          context: "workflows",
          session_id: "test-session-123",
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.suggestions.length).toBeGreaterThan(0);
    });
  });

  describe("POST /api/v1/ai/errors/analyze (Phase 6.4 - RTK Query schema)", () => {
    it("returns analysis for timeout errors", async () => {
      const response = await fetch("/api/v1/ai/errors/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          error_code: "TIMEOUT_001",
          error_message: "Request timeout",
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();

      // RTK Query schema: error_type, recovery_steps, auto_recoverable, confidence
      expect(data).toHaveProperty("error_type");
      expect(data.error_type).toBe("network_timeout");
      expect(data).toHaveProperty("recovery_steps");
      expect(data).toHaveProperty("auto_recoverable");
      expect(data).toHaveProperty("confidence");
      expect(data.confidence).toBeGreaterThan(0.7);
    });

    it("returns analysis for authentication errors", async () => {
      const response = await fetch("/api/v1/ai/errors/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          error_code: "AUTH_001",
          error_message: "Session expired",
        }),
      });

      const data = await response.json();

      expect(data.error_type).toBe("authentication");
      expect(
        data.recovery_steps.some(
          (s: { action_type: string }) => s.action_type === "manual",
        ),
      ).toBe(true);
    });

    it("returns analysis for validation errors", async () => {
      const response = await fetch("/api/v1/ai/errors/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          error_code: "VALIDATION_001",
          error_message: "Invalid workflow name",
        }),
      });

      const data = await response.json();

      expect(data.error_type).toBe("validation");
      expect(
        data.recovery_steps.some(
          (s: { action_type: string }) => s.action_type === "manual",
        ),
      ).toBe(true);
    });

    it("returns recovery_steps with required fields", async () => {
      const response = await fetch("/api/v1/ai/errors/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          error_code: "NETWORK_001",
          error_message: "Connection refused",
        }),
      });

      const data = await response.json();

      // RTK Query schema
      expect(data).toHaveProperty("error_type");
      expect(data).toHaveProperty("recovery_steps");
      expect(Array.isArray(data.recovery_steps)).toBe(true);

      if (data.recovery_steps.length > 0) {
        const step = data.recovery_steps[0];
        expect(step).toHaveProperty("step_number");
        expect(step).toHaveProperty("title");
        expect(step).toHaveProperty("description");
        expect(step).toHaveProperty("action_type");
        expect(["automatic", "manual", "contact_support"]).toContain(
          step.action_type,
        );
      }
    });

    it("returns auto_recoverable flag", async () => {
      const response = await fetch("/api/v1/ai/errors/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          error_code: "TIMEOUT_001",
          error_message: "Request timed out",
        }),
      });

      const data = await response.json();

      expect(data).toHaveProperty("auto_recoverable");
      expect(typeof data.auto_recoverable).toBe("boolean");
    });

    it("handles unknown errors with default error_type", async () => {
      const response = await fetch("/api/v1/ai/errors/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          error_code: "UNKNOWN_999",
          error_message: "Something unexpected happened",
        }),
      });

      const data = await response.json();

      expect(data.error_type).toBe("unknown");
      expect(data.recovery_steps.length).toBeGreaterThan(0);
    });

    it("returns 400 for missing error_message field", async () => {
      const response = await fetch("/api/v1/ai/errors/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ error_code: "TEST" }),
      });

      expect(response.status).toBe(400);
    });

    it("includes context in analysis when provided", async () => {
      const response = await fetch("/api/v1/ai/errors/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          error_code: "RATE_LIMIT_001",
          error_message: "Rate limit exceeded",
          context: {
            page: "chat",
            sessionId: "sess-123",
          },
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();
      expect(data.error_type).toBe("rate_limit");
    });
  });

  describe("POST /api/v1/ai/disclosure/analyze (Phase 6.1)", () => {
    it("returns disclosure level recommendation", async () => {
      const response = await fetch("/api/v1/ai/disclosure/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_level: "beginner",
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data).toHaveProperty("current_level");
      expect(data).toHaveProperty("recommended_level");
      expect(data).toHaveProperty("confidence");
      expect(data).toHaveProperty("unlock_features");
      expect(data).toHaveProperty("personalized_message");
      expect(Array.isArray(data.unlock_features)).toBe(true);
    });

    it("recommends higher level for beginner users", async () => {
      const response = await fetch("/api/v1/ai/disclosure/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_level: "beginner",
        }),
      });

      const data = await response.json();

      expect(data.current_level).toBe("beginner");
      expect(["intermediate", "advanced", "expert"]).toContain(
        data.recommended_level,
      );
    });

    it("returns personalized message based on level", async () => {
      const response = await fetch("/api/v1/ai/disclosure/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_level: "intermediate",
        }),
      });

      const data = await response.json();

      expect(data.personalized_message).toBeTruthy();
      expect(typeof data.personalized_message).toBe("string");
    });

    it("includes confidence score", async () => {
      const response = await fetch("/api/v1/ai/disclosure/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          current_level: "beginner",
        }),
      });

      const data = await response.json();

      expect(data.confidence).toBeGreaterThan(0);
      expect(data.confidence).toBeLessThanOrEqual(1);
    });
  });

  describe("POST /api/v1/ai/nudges/recommend (Phase 6.3 - RTK Query schema)", () => {
    it("returns nudge recommendation with required fields", async () => {
      const response = await fetch("/api/v1/ai/nudges/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          context: "chat",
          current_feature: "chat-input",
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();

      // NudgeRecommendResponse schema: should_show, confidence, nudge?
      expect(data).toHaveProperty("should_show");
      expect(typeof data.should_show).toBe("boolean");
      expect(data).toHaveProperty("confidence");
      expect(typeof data.confidence).toBe("number");
      // Nudge object contains type and message
      expect(data).toHaveProperty("nudge");
      expect(data.nudge).toHaveProperty("type");
      expect(typeof data.nudge.type).toBe("string");
      expect(data.nudge).toHaveProperty("message");
      expect(typeof data.nudge.message).toBe("string");
    });

    it("returns optional nudge fields when present", async () => {
      const response = await fetch("/api/v1/ai/nudges/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          context: "chat",
          current_feature: "chat-input",
        }),
      });

      const data = await response.json();

      // Optional nudge fields from NudgeRecommendResponse schema
      if (data.nudge) {
        if (data.nudge.priority !== undefined) {
          expect(typeof data.nudge.priority).toBe("string");
        }
        if (data.nudge.show_after_ms !== undefined) {
          expect(typeof data.nudge.show_after_ms).toBe("number");
        }
        // target_element can be string or null
        if (data.nudge.target_element !== undefined) {
          expect(
            data.nudge.target_element === null ||
              typeof data.nudge.target_element === "string",
          ).toBe(true);
        }
      }
    });

    it("returns context-aware nudges", async () => {
      const response = await fetch("/api/v1/ai/nudges/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          context: "workflows",
          current_feature: "workflow-editor",
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();

      // NudgeRecommendResponse schema: should_show, confidence, nudge
      expect(data).toHaveProperty("should_show");
      expect(data).toHaveProperty("nudge");
      expect(data.nudge).toHaveProperty("type");
      expect(data.nudge).toHaveProperty("message");
    });

    it("includes confidence score", async () => {
      const response = await fetch("/api/v1/ai/nudges/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          context: "chat",
          current_feature: "chat-input",
        }),
      });

      const data = await response.json();

      expect(data).toHaveProperty("confidence");
      expect(data.confidence).toBeGreaterThan(0);
      expect(data.confidence).toBeLessThanOrEqual(1);
    });
  });

  describe("POST /api/v1/ai/composite/batch (Batch Composite Analysis)", () => {
    it("returns batch composite analysis results", async () => {
      const response = await fetch("/api/v1/ai/composite/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "user-123",
          session_id: "session-456",
          include_persona: true,
          include_disclosure: true,
          include_error: false,
          persona_data: { assigned_persona: "bob" },
          disclosure_data: { feature_usage: { chat: 10 } },
        }),
      });

      expect(response.ok).toBe(true);
      const data = await response.json();

      expect(data).toHaveProperty("user_id");
      expect(data).toHaveProperty("session_id");
      expect(data).toHaveProperty("confidence");
      expect(typeof data.confidence).toBe("number");
    });

    it("returns persona_result when include_persona is true", async () => {
      const response = await fetch("/api/v1/ai/composite/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "user-123",
          session_id: "session-456",
          include_persona: true,
          include_disclosure: false,
          include_error: false,
          persona_data: { assigned_persona: "alice-builder" },
        }),
      });

      const data = await response.json();

      expect(data).toHaveProperty("persona_result");
      expect(data.persona_result).not.toBeNull();
      expect(data.persona_result).toHaveProperty("detected_persona");
      expect(data.persona_result).toHaveProperty("confidence");
    });

    it("returns disclosure_result when include_disclosure is true", async () => {
      const response = await fetch("/api/v1/ai/composite/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "user-123",
          session_id: "session-456",
          include_persona: false,
          include_disclosure: true,
          include_error: false,
          disclosure_data: { current_level: "intermediate" },
        }),
      });

      const data = await response.json();

      expect(data).toHaveProperty("disclosure_result");
      expect(data.disclosure_result).not.toBeNull();
      expect(data.disclosure_result).toHaveProperty("current_level");
      expect(data.disclosure_result).toHaveProperty("recommended_level");
    });

    it("returns error_result when include_error is true (RTK Query schema)", async () => {
      const response = await fetch("/api/v1/ai/composite/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "user-123",
          session_id: "session-456",
          include_persona: false,
          include_disclosure: false,
          include_error: true,
          error_data: {
            error_code: "TIMEOUT_001",
            error_message: "Connection timeout",
          },
        }),
      });

      const data = await response.json();

      expect(data).toHaveProperty("error_result");
      expect(data.error_result).not.toBeNull();
      // RTK Query schema: error_type, recovery_steps, auto_recoverable, confidence
      expect(data.error_result).toHaveProperty("error_type");
      expect(data.error_result).toHaveProperty("recovery_steps");
      expect(data.error_result).toHaveProperty("auto_recoverable");
      expect(data.error_result).toHaveProperty("confidence");
    });

    it("returns null for analyses not requested", async () => {
      const response = await fetch("/api/v1/ai/composite/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "user-123",
          session_id: "session-456",
          include_persona: true,
          include_disclosure: false,
          include_error: false,
          persona_data: { assigned_persona: "bob" },
        }),
      });

      const data = await response.json();

      expect(data.persona_result).not.toBeNull();
      expect(data.disclosure_result).toBeNull();
      expect(data.error_result).toBeNull();
    });

    it("returns cross_insights when multiple analyses are requested", async () => {
      const response = await fetch("/api/v1/ai/composite/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "user-123",
          session_id: "session-456",
          include_persona: true,
          include_disclosure: true,
          include_error: false,
          persona_data: { assigned_persona: "bob" },
          disclosure_data: { current_level: "beginner" },
        }),
      });

      const data = await response.json();

      expect(data).toHaveProperty("cross_insights");
      expect(Array.isArray(data.cross_insights)).toBe(true);
    });

    it("returns 400 when user_id is missing", async () => {
      const response = await fetch("/api/v1/ai/composite/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          session_id: "session-456",
          include_persona: true,
        }),
      });

      expect(response.status).toBe(400);
    });

    it("returns 400 when session_id is missing", async () => {
      const response = await fetch("/api/v1/ai/composite/batch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "user-123",
          include_persona: true,
        }),
      });

      expect(response.status).toBe(400);
    });
  });

  describe("mock data factories", () => {
    it("mockAIInterpretation has correct structure", () => {
      expect(mockAIInterpretation).toHaveProperty("action");
      expect(mockAIInterpretation).toHaveProperty("params");
      expect(mockAIInterpretation).toHaveProperty("confidence");
    });

    it("mockSuggestions is an array of valid suggestions", () => {
      expect(Array.isArray(mockSuggestions)).toBe(true);
      mockSuggestions.forEach((suggestion) => {
        expect(suggestion).toHaveProperty("id");
        expect(suggestion).toHaveProperty("type");
        expect(suggestion).toHaveProperty("content");
        expect(suggestion).toHaveProperty("confidence");
      });
    });
  });

  describe("API Contract Transformation", () => {
    it("should return disclosure response in snake_case and transform to camelCase", async () => {
      const response = await fetch("/api/v1/ai/disclosure/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_level: "beginner" }),
      });

      const rawData = await response.json();

      // Verify raw response is in snake_case (backend format)
      expect(rawData).toHaveProperty("current_level");
      expect(rawData).toHaveProperty("recommended_level");
      expect(rawData).toHaveProperty("unlock_features");
      expect(rawData).toHaveProperty("personalized_message");

      // Transform and verify camelCase (frontend format)
      const transformedData = transformSnakeToCamel(rawData);
      expect(transformedData).toHaveProperty("currentLevel");
      expect(transformedData).toHaveProperty("recommendedLevel");
      expect(transformedData).toHaveProperty("unlockFeatures");
      expect(transformedData).toHaveProperty("personalizedMessage");
    });

    it("should return nudge response in snake_case and transform to camelCase", async () => {
      const response = await fetch("/api/v1/ai/nudges/recommend", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "user-123",
          current_context: { page: "chat" },
        }),
      });

      const rawData = await response.json();

      // Verify raw response is in snake_case (backend format)
      expect(rawData).toHaveProperty("should_show");
      expect(rawData.nudge).toHaveProperty("show_after_ms");
      expect(rawData.nudge).toHaveProperty("target_element");

      // Transform and verify camelCase (frontend format)
      const transformedData = transformSnakeToCamel(rawData);
      expect(transformedData).toHaveProperty("shouldShow");
      expect(transformedData.nudge).toHaveProperty("showAfterMs");
      expect(transformedData.nudge).toHaveProperty("targetElement");
    });

    it("should return onboarding response in snake_case and transform to camelCase", async () => {
      const response = await fetch("/api/v1/ai/onboarding/personalize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user_id: "user-123" }),
      });

      const rawData = await response.json();

      // Verify raw response is in snake_case (backend format)
      expect(rawData).toHaveProperty("detected_intent");
      expect(rawData).toHaveProperty("recommended_path");
      expect(rawData).toHaveProperty("skip_steps");
      expect(rawData).toHaveProperty("persona_prediction");

      // Transform and verify camelCase (frontend format)
      const transformedData = transformSnakeToCamel(rawData);
      expect(transformedData).toHaveProperty("detectedIntent");
      expect(transformedData).toHaveProperty("recommendedPath");
      expect(transformedData).toHaveProperty("skipSteps");
      expect(transformedData).toHaveProperty("personaPrediction");
    });

    it("should return persona response in snake_case and transform to camelCase", async () => {
      const response = await fetch("/api/v1/ai/persona/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "user-123",
          assigned_persona: "bob",
        }),
      });

      const rawData = await response.json();

      // Verify raw response is in snake_case (backend format)
      expect(rawData).toHaveProperty("assigned_persona");
      expect(rawData).toHaveProperty("detected_persona");
      expect(rawData).toHaveProperty("behavior_signals");
      expect(rawData).toHaveProperty("ui_adaptations");

      // Transform and verify camelCase (frontend format)
      const transformedData = transformSnakeToCamel(rawData);
      expect(transformedData).toHaveProperty("assignedPersona");
      expect(transformedData).toHaveProperty("detectedPersona");
      expect(transformedData).toHaveProperty("behaviorSignals");
      expect(transformedData).toHaveProperty("uiAdaptations");
    });

    it("should return composite response in snake_case and transform to camelCase", async () => {
      const response = await fetch("/api/v1/ai/composite/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: "user-123",
          session_id: "session-456",
          include_persona: true,
          include_disclosure: true,
        }),
      });

      const rawData = await response.json();

      // Verify raw response is in snake_case (backend format)
      expect(rawData).toHaveProperty("user_id");
      expect(rawData).toHaveProperty("session_id");
      expect(rawData).toHaveProperty("persona_result");
      expect(rawData).toHaveProperty("disclosure_result");
      expect(rawData).toHaveProperty("cross_insights");

      // Transform and verify camelCase (frontend format)
      const transformedData = transformSnakeToCamel(rawData);
      expect(transformedData).toHaveProperty("userId");
      expect(transformedData).toHaveProperty("sessionId");
      expect(transformedData).toHaveProperty("personaResult");
      expect(transformedData).toHaveProperty("disclosureResult");
      expect(transformedData).toHaveProperty("crossInsights");
    });

    it("should return metrics insights in snake_case and transform to camelCase", async () => {
      const response = await fetch("/api/v1/ai/metrics/insights");

      const rawData = await response.json();

      // Verify raw response contains snake_case nested fields
      const anomalyInsight = rawData.insights.find(
        (i: { type: string }) => i.type === "anomaly",
      );
      expect(anomalyInsight).toHaveProperty("suggested_actions");
      expect(anomalyInsight).toHaveProperty("detected_at");

      // Transform and verify camelCase
      const transformedData = transformSnakeToCamel(rawData);
      const transformedAnomaly = transformedData.insights.find(
        (i: { type: string }) => i.type === "anomaly",
      );
      expect(transformedAnomaly).toHaveProperty("suggestedActions");
      expect(transformedAnomaly).toHaveProperty("detectedAt");
    });
  });
});
