/**
 * Studio Handlers Tests - TDD
 *
 * Tests for MSW handlers supporting StudioOrchestrator integration.
 *
 * Endpoints:
 * - POST /api/v1/studio/analyze - Unified analysis endpoint for all intelligence types
 * - GET /api/v1/studio/templates - List available templates
 * - POST /api/v1/studio/suggestions - Studio suggestions
 */

import { describe, it, expect, beforeAll, afterAll, afterEach, vi } from "vitest";
import { setupServer } from "msw/node";
import { studioHandlers, createStudioAnalyzeResponse } from "./studioHandlers";

// =============================================================================
// Test Server Setup
// =============================================================================

const server = setupServer(...studioHandlers);

beforeAll(() => server.listen({ onUnhandledRequest: "error" }));
afterEach(() => {
  server.resetHandlers();
  vi.clearAllMocks();
});
afterAll(() => server.close());

// =============================================================================
// Helper Functions
// =============================================================================

async function fetchStudioAnalyze(body: unknown): Promise<Response> {
  return fetch("/api/v1/studio/analyze", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

// =============================================================================
// POST /api/v1/studio/analyze Tests
// =============================================================================

describe("POST /api/v1/studio/analyze", () => {
  describe("Session Intelligence Tasks", () => {
    it("should return session summary for session_summarize task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        session_id: "session-456",
        tasks: [{ category: "session", type: "session_summarize", data: {} }],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.user_id).toBe("user-123");
      expect(result.session_id).toBe("session-456");
      expect(result.analyses.session_summarize).toBeDefined();
      expect(result.analyses.session_summarize.summary).toBeDefined();
      expect(result.analyses.session_summarize.key_topics).toBeInstanceOf(
        Array,
      );
    });

    it("should return session groups for session_group task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        session_id: "session-456",
        tasks: [{ category: "session", type: "session_group", data: {} }],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.session_group).toBeDefined();
      expect(result.analyses.session_group.groups).toBeInstanceOf(Array);
    });

    it("should return similar sessions for session_similarity task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        session_id: "session-456",
        tasks: [{ category: "session", type: "session_similarity", data: {} }],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.session_similarity).toBeDefined();
      expect(
        result.analyses.session_similarity.similar_sessions,
      ).toBeInstanceOf(Array);
    });
  });

  describe("Conversation Intelligence Tasks", () => {
    it("should return intent detection for intent_detect task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [
          {
            category: "conversation",
            type: "intent_detect",
            data: { query: "create a new file" },
          },
        ],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.intent_detect).toBeDefined();
      expect(result.analyses.intent_detect.intent).toBeDefined();
      expect(result.analyses.intent_detect.confidence).toBeGreaterThan(0);
    });

    it("should return context optimization for context_optimize task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [
          { category: "conversation", type: "context_optimize", data: {} },
        ],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.context_optimize).toBeDefined();
      expect(result.analyses.context_optimize.suggestions).toBeInstanceOf(
        Array,
      );
    });

    it("should return goal tracking for goal_track task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [{ category: "conversation", type: "goal_track", data: {} }],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.goal_track).toBeDefined();
      expect(result.analyses.goal_track.primary_goal).toBeDefined();
    });
  });

  describe("Canvas Intelligence Tasks", () => {
    it("should return artifact type suggestion for artifact_suggest_type task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [
          {
            category: "canvas",
            type: "artifact_suggest_type",
            data: { content: "graph TD; A-->B" },
          },
        ],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.artifact_suggest_type).toBeDefined();
      expect(
        result.analyses.artifact_suggest_type.suggested_type,
      ).toBeDefined();
    });

    it("should return code analysis for code_analyze task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [
          {
            category: "canvas",
            type: "code_analyze",
            data: { code: "def hello(): pass" },
          },
        ],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.code_analyze).toBeDefined();
      expect(result.analyses.code_analyze.quality_score).toBeDefined();
    });

    it("should return diff explanation for diff_explain task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [
          {
            category: "canvas",
            type: "diff_explain",
            data: { old_content: "a", new_content: "b" },
          },
        ],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.diff_explain).toBeDefined();
      expect(result.analyses.diff_explain.summary).toBeDefined();
    });
  });

  describe("Diagram Intelligence Tasks", () => {
    it("should return diagram analysis for diagram_analyze task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [
          {
            category: "diagram",
            type: "diagram_analyze",
            data: { diagram: "graph TD; A-->B" },
          },
        ],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.diagram_analyze).toBeDefined();
      expect(result.analyses.diagram_analyze.diagram_type).toBeDefined();
    });

    it("should return generated code for diagram_to_code task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [
          {
            category: "diagram",
            type: "diagram_to_code",
            data: { diagram: "flowchart TD; A-->B" },
          },
        ],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.diagram_to_code).toBeDefined();
      expect(result.analyses.diagram_to_code.code).toBeDefined();
      expect(result.analyses.diagram_to_code.language).toBeDefined();
    });
  });

  describe("Trace Intelligence Tasks", () => {
    it("should return trace summary for trace_summarize task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [
          {
            category: "trace",
            type: "trace_summarize",
            data: { trace_id: "t1" },
          },
        ],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.trace_summarize).toBeDefined();
      expect(result.analyses.trace_summarize.summary).toBeDefined();
    });

    it("should return anomalies for trace_anomaly task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [
          {
            category: "trace",
            type: "trace_anomaly",
            data: { trace_id: "t1" },
          },
        ],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.trace_anomaly).toBeDefined();
      expect(result.analyses.trace_anomaly.anomalies).toBeInstanceOf(Array);
    });

    it("should return cost projection for cost_project task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [{ category: "trace", type: "cost_project", data: {} }],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.cost_project).toBeDefined();
      expect(result.analyses.cost_project.current_cost).toBeDefined();
    });

    it("should return token prediction for token_predict task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [{ category: "trace", type: "token_predict", data: {} }],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.token_predict).toBeDefined();
      expect(result.analyses.token_predict.current_tokens).toBeDefined();
    });
  });

  describe("HITL Intelligence Tasks", () => {
    it("should return risk assessment for risk_assess task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [
          {
            category: "hitl",
            type: "risk_assess",
            data: { action_type: "file_write" },
          },
        ],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.risk_assess).toBeDefined();
      expect(result.analyses.risk_assess.risk_score).toBeDefined();
      expect(result.analyses.risk_assess.risk_level).toBeDefined();
    });

    it("should return decision history for decision_history task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [{ category: "hitl", type: "decision_history", data: {} }],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.decision_history).toBeDefined();
      expect(result.analyses.decision_history.similar_decisions).toBeInstanceOf(
        Array,
      );
    });
  });

  describe("Command Intelligence Tasks", () => {
    it("should return interpreted command for command_interpret task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [
          {
            category: "command",
            type: "command_interpret",
            data: { query: "create a Python file" },
          },
        ],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.command_interpret).toBeDefined();
      expect(
        result.analyses.command_interpret.interpreted_command,
      ).toBeDefined();
    });

    it("should return inline suggestions for inline_suggest task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [
          {
            category: "command",
            type: "inline_suggest",
            data: { code: "def ", cursor_position: 4, language: "python" },
          },
        ],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.inline_suggest).toBeDefined();
      expect(result.analyses.inline_suggest.suggestions).toBeInstanceOf(Array);
    });

    it("should return AI edit for ai_edit_generate task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [
          {
            category: "command",
            type: "ai_edit_generate",
            data: {
              content: "def hello():\n  pass",
              instruction: "add docstring",
            },
          },
        ],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.ai_edit_generate).toBeDefined();
      expect(result.analyses.ai_edit_generate.edited_content).toBeDefined();
    });
  });

  describe("UX Intelligence Tasks", () => {
    it("should return nav prediction for nav_prediction task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [{ category: "ux", type: "nav_prediction", data: {} }],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.nav_prediction).toBeDefined();
      expect(result.analyses.nav_prediction.predicted_items).toBeInstanceOf(
        Array,
      );
    });

    it("should return contextual help for contextual_help task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [
          {
            category: "ux",
            type: "contextual_help",
            data: { context: "chat" },
          },
        ],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.contextual_help).toBeDefined();
      expect(result.analyses.contextual_help.help_topics).toBeInstanceOf(Array);
    });

    it("should return learning path for learning_path task", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [{ category: "ux", type: "learning_path", data: {} }],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.analyses.learning_path).toBeDefined();
      expect(result.analyses.learning_path.current_level).toBeDefined();
    });
  });

  describe("Multiple Tasks", () => {
    it("should handle multiple tasks in single request", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        session_id: "session-456",
        tasks: [
          { category: "session", type: "session_summarize", data: {} },
          {
            category: "conversation",
            type: "intent_detect",
            data: { query: "help" },
          },
          { category: "ux", type: "nav_prediction", data: {} },
        ],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(Object.keys(result.analyses)).toHaveLength(3);
      expect(result.analyses.session_summarize).toBeDefined();
      expect(result.analyses.intent_detect).toBeDefined();
      expect(result.analyses.nav_prediction).toBeDefined();
    });

    it("should generate cross-insights for multiple tasks", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [
          { category: "session", type: "session_summarize", data: {} },
          { category: "conversation", type: "goal_track", data: {} },
        ],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.cross_insights).toBeInstanceOf(Array);
      expect(result.cross_insights.length).toBeGreaterThan(0);
    });
  });

  describe("Response Structure", () => {
    it("should include total_cost in response", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [{ category: "session", type: "session_summarize", data: {} }],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.total_cost).toBeDefined();
      expect(typeof result.total_cost).toBe("string"); // Decimal as string
    });

    it("should include failed_analyses array", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [{ category: "session", type: "session_summarize", data: {} }],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.failed_analyses).toBeInstanceOf(Array);
    });
  });

  describe("Error Handling", () => {
    it("should return 400 for missing user_id", async () => {
      const response = await fetchStudioAnalyze({
        tasks: [{ category: "session", type: "session_summarize", data: {} }],
      });

      expect(response.status).toBe(400);
      const result = await response.json();
      expect(result.detail).toContain("user_id");
    });

    it("should return 400 for empty tasks array", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [],
      });

      expect(response.status).toBe(400);
      const result = await response.json();
      expect(result.detail).toContain("tasks");
    });

    it("should mark unknown task types as failed", async () => {
      const response = await fetchStudioAnalyze({
        user_id: "user-123",
        tasks: [{ category: "unknown", type: "unknown_type", data: {} }],
      });

      expect(response.status).toBe(200);
      const result = await response.json();
      expect(result.failed_analyses).toContain("unknown:unknown_type");
    });
  });
});

// =============================================================================
// GET /api/v1/studio/templates Tests
// =============================================================================

describe("GET /api/v1/studio/templates", () => {
  it("should return list of templates", async () => {
    const response = await fetch("/api/v1/studio/templates");

    expect(response.status).toBe(200);
    const result = await response.json();
    expect(result.templates).toBeInstanceOf(Array);
    expect(result.templates.length).toBeGreaterThan(0);
  });

  it("should include template metadata", async () => {
    const response = await fetch("/api/v1/studio/templates");

    expect(response.status).toBe(200);
    const result = await response.json();
    const template = result.templates[0];
    expect(template.id).toBeDefined();
    expect(template.name).toBeDefined();
    expect(template.category).toBeDefined();
  });
});

// =============================================================================
// POST /api/v1/studio/suggestions Tests
// =============================================================================

describe("POST /api/v1/studio/suggestions", () => {
  it("should return suggestions for context", async () => {
    const response = await fetch("/api/v1/studio/suggestions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        context: "chat",
        user_id: "user-123",
      }),
    });

    expect(response.status).toBe(200);
    const result = await response.json();
    expect(result.suggestions).toBeInstanceOf(Array);
  });
});

// =============================================================================
// Helper Function Tests
// =============================================================================

describe("createStudioAnalyzeResponse", () => {
  it("should create valid response structure", () => {
    const response = createStudioAnalyzeResponse({
      user_id: "user-123",
      session_id: "session-456",
      tasks: [{ category: "session", type: "session_summarize", data: {} }],
    });

    expect(response.user_id).toBe("user-123");
    expect(response.session_id).toBe("session-456");
    expect(response.analyses).toBeDefined();
    expect(response.cross_insights).toBeInstanceOf(Array);
    expect(response.failed_analyses).toBeInstanceOf(Array);
    expect(response.total_cost).toBeDefined();
  });
});
