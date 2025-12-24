/**
 * HITL Types Tests
 *
 * Tests for Human-in-the-Loop (HITL) type definitions and utilities.
 * Ensures type safety and conversion functions work correctly.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import {
  convertUIResponseToAPIResponse,
  convertAPIResponseToUIResponse,
  convertApprovalPayloadToRequest,
  type ClarificationUIResponse,
  type ClarificationAPIResponse,
  type ConfidenceFactor,
  type AlternativeSuggestion,
  type AIExplanation,
  type AgentApprovalRequest,
  type ApprovalRequiredPayload,
} from "./hitl";

describe("HITL Types", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("convertUIResponseToAPIResponse", () => {
    it("should convert text response correctly", () => {
      const uiResponse: ClarificationUIResponse = {
        request_id: "req-123",
        value: "My text answer",
        responded_by: "user@example.com",
      };

      const apiResponse = convertUIResponseToAPIResponse(uiResponse);

      expect(apiResponse).toEqual({
        request_id: "req-123",
        responded_by: "user@example.com",
        response_type: "text",
        value: "My text answer",
      });
    });

    it("should convert choice response correctly", () => {
      const uiResponse: ClarificationUIResponse = {
        request_id: "req-456",
        selected_option_id: "option-2",
        responded_by: "user@example.com",
      };

      const apiResponse = convertUIResponseToAPIResponse(uiResponse);

      expect(apiResponse).toEqual({
        request_id: "req-456",
        responded_by: "user@example.com",
        response_type: "choice",
        selected_option_id: "option-2",
      });
    });

    it("should convert confirmation response (true) correctly", () => {
      const uiResponse: ClarificationUIResponse = {
        request_id: "req-789",
        confirmed: true,
        responded_by: "user@example.com",
      };

      const apiResponse = convertUIResponseToAPIResponse(uiResponse);

      expect(apiResponse).toEqual({
        request_id: "req-789",
        responded_by: "user@example.com",
        response_type: "confirm",
        confirmed: true,
      });
    });

    it("should convert confirmation response (false) correctly", () => {
      const uiResponse: ClarificationUIResponse = {
        request_id: "req-999",
        confirmed: false,
        responded_by: "user@example.com",
      };

      const apiResponse = convertUIResponseToAPIResponse(uiResponse);

      expect(apiResponse).toEqual({
        request_id: "req-999",
        responded_by: "user@example.com",
        response_type: "confirm",
        confirmed: false,
      });
    });

    it("should prioritize confirmed over other fields", () => {
      const uiResponse: ClarificationUIResponse = {
        request_id: "req-mixed",
        value: "some text",
        selected_option_id: "option-1",
        confirmed: true,
        responded_by: "user@example.com",
      };

      const apiResponse = convertUIResponseToAPIResponse(uiResponse);

      expect(apiResponse.response_type).toBe("confirm");
      expect(apiResponse.confirmed).toBe(true);
    });

    it("should prioritize choice over text", () => {
      const uiResponse: ClarificationUIResponse = {
        request_id: "req-choice-text",
        value: "some text",
        selected_option_id: "option-1",
        responded_by: "user@example.com",
      };

      const apiResponse = convertUIResponseToAPIResponse(uiResponse);

      expect(apiResponse.response_type).toBe("choice");
      expect(apiResponse.selected_option_id).toBe("option-1");
    });
  });

  describe("convertAPIResponseToUIResponse", () => {
    it("should convert text API response to UI response", () => {
      const apiResponse: ClarificationAPIResponse = {
        request_id: "req-123",
        responded_by: "user@example.com",
        response_type: "text",
        value: "My answer",
      };

      const uiResponse = convertAPIResponseToUIResponse(
        apiResponse,
        "user@test.com",
      );

      expect(uiResponse).toEqual({
        request_id: "req-123",
        value: "My answer",
        responded_by: "user@test.com",
      });
    });

    it("should convert choice API response to UI response", () => {
      const apiResponse: ClarificationAPIResponse = {
        request_id: "req-456",
        responded_by: "admin@example.com",
        response_type: "choice",
        selected_option_id: "opt-3",
      };

      const uiResponse = convertAPIResponseToUIResponse(
        apiResponse,
        "admin@test.com",
      );

      expect(uiResponse).toEqual({
        request_id: "req-456",
        selected_option_id: "opt-3",
        responded_by: "admin@test.com",
      });
    });

    it("should convert confirm API response to UI response", () => {
      const apiResponse: ClarificationAPIResponse = {
        request_id: "req-789",
        responded_by: "user@example.com",
        response_type: "confirm",
        confirmed: false,
      };

      const uiResponse = convertAPIResponseToUIResponse(
        apiResponse,
        "user@test.com",
      );

      expect(uiResponse).toEqual({
        request_id: "req-789",
        confirmed: false,
        responded_by: "user@test.com",
      });
    });

    it("should use API responded_by if no override provided", () => {
      const apiResponse: ClarificationAPIResponse = {
        request_id: "req-999",
        responded_by: "original@example.com",
        response_type: "text",
        value: "My answer",
      };

      const uiResponse = convertAPIResponseToUIResponse(apiResponse);

      expect(uiResponse).toEqual({
        request_id: "req-999",
        value: "My answer",
        responded_by: "original@example.com",
      });
    });
  });

  describe("Type exports", () => {
    it("should export all required HITL types", async () => {
      // Dynamic import to verify all exports exist
      const hitlModule = await import("./hitl");

      // Type exports (these are compile-time checks, but we verify the module structure)
      expect(hitlModule).toHaveProperty("convertUIResponseToAPIResponse");
      expect(hitlModule).toHaveProperty("convertAPIResponseToUIResponse");
    });
  });

  // =============================================================================
  // AI Explanation Types Tests (AI-Native HITL Enhancements Phase 1)
  // =============================================================================

  describe("ConfidenceFactor type", () => {
    it("should create a valid ConfidenceFactor object", () => {
      const factor: ConfidenceFactor = {
        factor: "ambiguous_input",
        weight: -0.2,
        evidence: "User query contains ambiguous terms",
      };

      expect(factor.factor).toBe("ambiguous_input");
      expect(factor.weight).toBe(-0.2);
      expect(factor.evidence).toBe("User query contains ambiguous terms");
    });

    it("should accept positive and negative weights", () => {
      const negativeFactor: ConfidenceFactor = {
        factor: "uncertainty",
        weight: -1.0,
        evidence: "Maximum uncertainty",
      };

      const positiveFactor: ConfidenceFactor = {
        factor: "strong_match",
        weight: 1.0,
        evidence: "Strong pattern match",
      };

      expect(negativeFactor.weight).toBe(-1.0);
      expect(positiveFactor.weight).toBe(1.0);
    });
  });

  describe("AlternativeSuggestion type", () => {
    it("should create a valid AlternativeSuggestion object", () => {
      const alternative: AlternativeSuggestion = {
        action: "Use read-only mode instead",
        confidence: 0.92,
        trade_off: "Cannot make changes, only view data",
      };

      expect(alternative.action).toBe("Use read-only mode instead");
      expect(alternative.confidence).toBe(0.92);
      expect(alternative.trade_off).toBe("Cannot make changes, only view data");
    });

    it("should accept confidence values from 0 to 1", () => {
      const lowConfidence: AlternativeSuggestion = {
        action: "Risky alternative",
        confidence: 0.0,
        trade_off: "Completely uncertain",
      };

      const highConfidence: AlternativeSuggestion = {
        action: "Safe alternative",
        confidence: 1.0,
        trade_off: "Full guarantee",
      };

      expect(lowConfidence.confidence).toBe(0.0);
      expect(highConfidence.confidence).toBe(1.0);
    });
  });

  describe("AIExplanation type", () => {
    it("should create a minimal AIExplanation object", () => {
      const explanation: AIExplanation = {
        why_uncertain: "The input is ambiguous.",
        what_could_go_wrong: "May perform wrong action.",
      };

      expect(explanation.why_uncertain).toBe("The input is ambiguous.");
      expect(explanation.what_could_go_wrong).toBe("May perform wrong action.");
    });

    it("should create AIExplanation with optional fields", () => {
      const explanation: AIExplanation = {
        why_uncertain: "Multiple interpretations possible",
        what_could_go_wrong: "May delete important files",
        safer_alternatives: [
          {
            action: "Preview files first",
            confidence: 0.95,
            trade_off: "Adds one extra step",
          },
        ],
        confidence_factors: [
          {
            factor: "ambiguous_threshold",
            weight: -0.25,
            evidence: "'Old' not defined precisely",
          },
        ],
        reasoning_trace: ["Step 1: Parsed query", "Step 2: Found ambiguity"],
        model_used: "gpt-4o-mini",
        generated_at: "2024-01-15T10:30:00Z",
        generation_latency_ms: 150.5,
        cached: false,
      };

      expect(explanation.safer_alternatives).toHaveLength(1);
      expect(explanation.safer_alternatives?.[0].action).toBe(
        "Preview files first",
      );
      expect(explanation.confidence_factors).toHaveLength(1);
      expect(explanation.confidence_factors?.[0].factor).toBe(
        "ambiguous_threshold",
      );
      expect(explanation.reasoning_trace).toHaveLength(2);
      expect(explanation.model_used).toBe("gpt-4o-mini");
      expect(explanation.generated_at).toBe("2024-01-15T10:30:00Z");
      expect(explanation.generation_latency_ms).toBe(150.5);
      expect(explanation.cached).toBe(false);
    });

    it("should allow cached explanations", () => {
      const cachedExplanation: AIExplanation = {
        why_uncertain: "Cached explanation",
        what_could_go_wrong: "Previously analyzed risk",
        cached: true,
        generation_latency_ms: 5.0,
      };

      expect(cachedExplanation.cached).toBe(true);
      expect(cachedExplanation.generation_latency_ms).toBe(5.0);
    });
  });

  describe("AgentApprovalRequest with ai_explanation", () => {
    it("should accept AgentApprovalRequest without ai_explanation", () => {
      const request: AgentApprovalRequest = {
        request_id: "req-123",
        session_id: "sess-456",
        task_id: "task-789",
        agent_name: "FileAgent",
        confidence: 0.65,
        threshold: 0.7,
        proposed_action: "Delete temporary files",
        trigger_reason: "low_confidence",
        context: {},
        requested_at: "2024-01-15T10:00:00Z",
      };

      expect(request.ai_explanation).toBeUndefined();
    });

    it("should accept AgentApprovalRequest with ai_explanation", () => {
      const explanation: AIExplanation = {
        why_uncertain: "The input contains ambiguous terms.",
        what_could_go_wrong: "May delete wrong files.",
        safer_alternatives: [
          {
            action: "List files before deleting",
            confidence: 0.92,
            trade_off: "Extra confirmation step",
          },
        ],
      };

      const request: AgentApprovalRequest = {
        request_id: "req-123",
        session_id: "sess-456",
        task_id: "task-789",
        agent_name: "FileAgent",
        confidence: 0.65,
        threshold: 0.7,
        proposed_action: "Delete temporary files",
        trigger_reason: "low_confidence",
        context: {},
        requested_at: "2024-01-15T10:00:00Z",
        ai_explanation: explanation,
      };

      expect(request.ai_explanation).toBeDefined();
      expect(request.ai_explanation?.why_uncertain).toBe(
        "The input contains ambiguous terms.",
      );
      expect(request.ai_explanation?.safer_alternatives).toHaveLength(1);
    });
  });

  describe("ApprovalRequiredPayload with ai_explanation", () => {
    it("should accept ApprovalRequiredPayload without ai_explanation", () => {
      const payload: ApprovalRequiredPayload = {
        request_id: "req-123",
        session_id: "sess-456",
        task_id: "task-789",
        agent_name: "FileAgent",
        confidence: 0.65,
        threshold: 0.7,
        proposed_action: "Delete temporary files",
        trigger_reason: "low_confidence",
        context: {},
        requested_at: "2024-01-15T10:00:00Z",
      };

      expect(payload.ai_explanation).toBeUndefined();
    });

    it("should accept ApprovalRequiredPayload with ai_explanation", () => {
      const payload: ApprovalRequiredPayload = {
        request_id: "req-123",
        session_id: "sess-456",
        task_id: "task-789",
        agent_name: "FileAgent",
        confidence: 0.65,
        threshold: 0.7,
        proposed_action: "Delete temporary files",
        trigger_reason: "low_confidence",
        context: {},
        requested_at: "2024-01-15T10:00:00Z",
        ai_explanation: {
          why_uncertain: "Ambiguous input detected",
          what_could_go_wrong: "Could affect wrong files",
        },
      };

      expect(payload.ai_explanation).toBeDefined();
      expect(payload.ai_explanation?.why_uncertain).toBe(
        "Ambiguous input detected",
      );
    });

    it("should convert payload with ai_explanation to request", () => {
      const payload: ApprovalRequiredPayload = {
        request_id: "req-convert-123",
        session_id: "sess-456",
        task_id: "task-789",
        agent_name: "ConvertAgent",
        confidence: 0.55,
        threshold: 0.8,
        proposed_action: "Run migration",
        trigger_reason: "high_risk_action",
        context: { database: "production" },
        requested_at: "2024-01-15T11:00:00Z",
        ai_explanation: {
          why_uncertain: "Production database operation",
          what_could_go_wrong: "Data loss if migration fails",
          safer_alternatives: [
            {
              action: "Run on staging first",
              confidence: 0.95,
              trade_off: "Delays production deployment",
            },
          ],
        },
      };

      const request = convertApprovalPayloadToRequest(payload);

      expect(request.request_id).toBe("req-convert-123");
      expect(request.ai_explanation).toBeDefined();
      expect(request.ai_explanation?.why_uncertain).toBe(
        "Production database operation",
      );
      expect(request.ai_explanation?.safer_alternatives).toHaveLength(1);
    });
  });
});
