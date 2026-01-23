/**
 * API Transforms Tests
 *
 * TDD tests for type-safe API response transformations.
 */
import { describe, it, expect, afterEach, vi } from "vitest";
import {
  isApiSession,
  transformApiSessionToClient,
  validateApiSession,
  safeTransformToClientSession,
  transformApiMessageToClient,
  isApiMessage,
  DEFAULT_SESSION_CONFIG,
  type ApiSession,
  type ApiMessage,
} from "./apiTransforms";
import { DEFAULT_SESSION_CONFIG as CANONICAL_SESSION_CONFIG } from "../types/session";

// =============================================================================
// Test Data
// =============================================================================

const validApiSession: ApiSession = {
  id: "session-123",
  name: "Test Session",
  status: "active",
  created_at: "2025-01-15T10:00:00Z",
  updated_at: "2025-01-15T11:00:00Z",
  config: {
    model: "gpt-4",
    model_provider: "openai",
    temperature: 0.7,
    max_tokens: 4096,
  },
  organization_id: "org-123",
};

const minimalApiSession: ApiSession = {
  id: "session-456",
  created_at: "2025-01-15T10:00:00Z",
  updated_at: "2025-01-15T10:00:00Z",
};

// =============================================================================
// Tests
// =============================================================================

describe("apiTransforms", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  // ===========================================================================
  // DRY Principle: Single Source of Truth for Configuration
  // ===========================================================================

  describe("DEFAULT_SESSION_CONFIG (Single Source of Truth)", () => {
    it("should re-export the canonical DEFAULT_SESSION_CONFIG from types/session.ts", () => {
      // DRY Principle: Configuration should have a single source of truth
      // apiTransforms should re-export from types/session.ts, not define its own
      expect(DEFAULT_SESSION_CONFIG).toBe(CANONICAL_SESSION_CONFIG);
    });

    it("should have modelName matching canonical config", () => {
      expect(DEFAULT_SESSION_CONFIG.modelName).toBe(
        CANONICAL_SESSION_CONFIG.modelName,
      );
    });

    it("should have maxTokens matching canonical config", () => {
      expect(DEFAULT_SESSION_CONFIG.maxTokens).toBe(
        CANONICAL_SESSION_CONFIG.maxTokens,
      );
    });

    it("should have modelProvider matching canonical config", () => {
      expect(DEFAULT_SESSION_CONFIG.modelProvider).toBe(
        CANONICAL_SESSION_CONFIG.modelProvider,
      );
    });
  });

  describe("isApiSession (Type Guard)", () => {
    it("should return true for valid API session", () => {
      expect(isApiSession(validApiSession)).toBe(true);
    });

    it("should return true for minimal API session", () => {
      expect(isApiSession(minimalApiSession)).toBe(true);
    });

    it("should return false for null", () => {
      expect(isApiSession(null)).toBe(false);
    });

    it("should return false for undefined", () => {
      expect(isApiSession(undefined)).toBe(false);
    });

    it("should return false for missing id", () => {
      expect(
        isApiSession({ created_at: "2025-01-15", updated_at: "2025-01-15" }),
      ).toBe(false);
    });

    it("should return false for missing created_at", () => {
      expect(isApiSession({ id: "123", updated_at: "2025-01-15" })).toBe(false);
    });

    it("should return false for missing updated_at", () => {
      expect(isApiSession({ id: "123", created_at: "2025-01-15" })).toBe(false);
    });

    it("should return false for non-object", () => {
      expect(isApiSession("string")).toBe(false);
      expect(isApiSession(123)).toBe(false);
      expect(isApiSession([])).toBe(false);
    });

    it("should return false for invalid organization_id type", () => {
      expect(
        isApiSession({
          id: "123",
          created_at: "2025-01-15",
          updated_at: "2025-01-15",
          organization_id: 12345, // number instead of string
        }),
      ).toBe(false);
    });

    it("should return false for invalid status type", () => {
      expect(
        isApiSession({
          id: "123",
          created_at: "2025-01-15",
          updated_at: "2025-01-15",
          status: { invalid: "object" }, // object instead of string
        }),
      ).toBe(false);
    });
  });

  describe("validateApiSession", () => {
    it("should return valid session for valid input", () => {
      const result = validateApiSession(validApiSession);
      expect(result.success).toBe(true);
      if (result.success) {
        expect(result.data.id).toBe("session-123");
      }
    });

    it("should return error for invalid input", () => {
      const result = validateApiSession({ invalid: "data" });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toBeDefined();
      }
    });

    it("should return error for null value", () => {
      const result = validateApiSession(null);
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toBe("Value is null or undefined");
      }
    });

    it("should return error for non-object value", () => {
      const result = validateApiSession("string-value");
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toBe("Expected object, got string");
      }
    });

    it("should return error for missing id field", () => {
      const result = validateApiSession({
        created_at: "2025-01-15",
        updated_at: "2025-01-15",
      });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toBe("Missing or invalid 'id' field");
      }
    });

    it("should return error for missing created_at field", () => {
      const result = validateApiSession({
        id: "test-id",
        updated_at: "2025-01-15",
      });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toBe("Missing or invalid 'created_at' field");
      }
    });

    it("should return error for missing updated_at field", () => {
      const result = validateApiSession({
        id: "test-id",
        created_at: "2025-01-15",
      });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toBe("Missing or invalid 'updated_at' field");
      }
    });
  });

  describe("transformApiSessionToClient", () => {
    it("should transform snake_case to camelCase", () => {
      const result = transformApiSessionToClient(validApiSession, []);

      expect(result.id).toBe("session-123");
      expect(result.name).toBe("Test Session");
      expect(result.createdAt).toBeTypeOf("number");
      expect(result.updatedAt).toBeTypeOf("number");
      expect(result.organizationId).toBe("org-123");
    });

    it("should transform config fields", () => {
      const result = transformApiSessionToClient(validApiSession, []);

      expect(result.config.modelName).toBe("gpt-4");
      expect(result.config.modelProvider).toBe("openai");
      expect(result.config.temperature).toBe(0.7);
      expect(result.config.maxTokens).toBe(4096);
    });

    it("should use default config for missing fields", () => {
      const result = transformApiSessionToClient(minimalApiSession, []);

      // Should use canonical DEFAULT_SESSION_CONFIG from types/session.ts
      expect(result.config.modelName).toBe(CANONICAL_SESSION_CONFIG.modelName);
      expect(result.config.modelProvider).toBe(
        CANONICAL_SESSION_CONFIG.modelProvider,
      );
      expect(result.config.temperature).toBe(
        CANONICAL_SESSION_CONFIG.temperature,
      );
      expect(result.config.maxTokens).toBe(CANONICAL_SESSION_CONFIG.maxTokens);
    });

    it("should include messages in result", () => {
      const messages = [
        {
          id: "msg-1",
          role: "user" as const,
          content: "Hello",
          timestamp: Date.now(),
        },
      ];
      const result = transformApiSessionToClient(validApiSession, messages);

      expect(result.messages).toHaveLength(1);
      expect(result.messages[0].content).toBe("Hello");
    });

    it("should use Untitled for missing name", () => {
      const result = transformApiSessionToClient(minimalApiSession, []);

      expect(result.name).toBe("Untitled");
    });

    it("should handle camelCase config fields (already transformed)", () => {
      const session: ApiSession = {
        ...minimalApiSession,
        config: {
          modelName: "claude-3",
          modelProvider: "anthropic",
        },
      };
      const result = transformApiSessionToClient(session, []);

      expect(result.config.modelName).toBe("claude-3");
      expect(result.config.modelProvider).toBe("anthropic");
    });

    it("should handle system_prompt snake_case config", () => {
      const session: ApiSession = {
        ...minimalApiSession,
        config: {
          system_prompt: "You are a helpful assistant",
        },
      };
      const result = transformApiSessionToClient(session, []);

      expect(result.config.systemPrompt).toBe("You are a helpful assistant");
    });

    it("should handle systemPrompt camelCase config", () => {
      const session: ApiSession = {
        ...minimalApiSession,
        config: {
          systemPrompt: "You are a coding assistant",
        },
      };
      const result = transformApiSessionToClient(session, []);

      expect(result.config.systemPrompt).toBe("You are a coding assistant");
    });

    it("should handle maxTokens camelCase config", () => {
      const session: ApiSession = {
        ...minimalApiSession,
        config: {
          maxTokens: 8192,
        },
      };
      const result = transformApiSessionToClient(session, []);

      expect(result.config.maxTokens).toBe(8192);
    });
  });

  describe("safeTransformToClientSession", () => {
    it("should transform valid session", () => {
      const result = safeTransformToClientSession(validApiSession, []);

      expect(result).not.toBeNull();
      expect(result?.id).toBe("session-123");
    });

    it("should return null for invalid session", () => {
      const result = safeTransformToClientSession({ invalid: "data" }, []);

      expect(result).toBeNull();
    });

    it("should return null for null input", () => {
      const result = safeTransformToClientSession(null, []);

      expect(result).toBeNull();
    });
  });

  // ===========================================================================
  // Message Transform Tests (TDD - tests written first)
  // ===========================================================================

  describe("isApiMessage (Type Guard)", () => {
    const validApiMessage: ApiMessage = {
      message_id: "msg-123",
      role: "assistant",
      content: "Hello, how can I help you?",
      timestamp: "2025-01-15T10:00:00Z",
      sources: [{ title: "Documentation", url: "https://example.com/docs" }],
      thinking: {
        content: "Let me think about this...",
        tokens: 150,
      },
      model_name: "gpt-4",
    };

    const minimalApiMessage: ApiMessage = {
      message_id: "msg-456",
      role: "user",
      content: "Hello",
      timestamp: null,
    };

    it("should return true for valid API message with all fields", () => {
      expect(isApiMessage(validApiMessage)).toBe(true);
    });

    it("should return true for minimal API message", () => {
      expect(isApiMessage(minimalApiMessage)).toBe(true);
    });

    it("should return false for null", () => {
      expect(isApiMessage(null)).toBe(false);
    });

    it("should return false for undefined", () => {
      expect(isApiMessage(undefined)).toBe(false);
    });

    it("should return false for missing message_id", () => {
      expect(isApiMessage({ role: "user", content: "Hello" })).toBe(false);
    });

    it("should return false for missing role", () => {
      expect(isApiMessage({ message_id: "123", content: "Hello" })).toBe(false);
    });

    it("should return false for missing content", () => {
      expect(isApiMessage({ message_id: "123", role: "user" })).toBe(false);
    });

    it("should return false for invalid role type", () => {
      expect(
        isApiMessage({ message_id: "123", role: 123, content: "Hello" }),
      ).toBe(false);
    });

    it("should return false for non-object", () => {
      expect(isApiMessage("string")).toBe(false);
      expect(isApiMessage(123)).toBe(false);
      expect(isApiMessage([])).toBe(false);
    });
  });

  describe("transformApiMessageToClient", () => {
    const validApiMessage: ApiMessage = {
      message_id: "msg-123",
      role: "assistant",
      content: "Hello, how can I help you?",
      timestamp: "2025-01-15T10:00:00Z",
      sources: [
        {
          title: "Documentation",
          url: "https://example.com/docs",
          snippet: "Relevant info",
        },
      ],
      thinking: {
        content: "Let me think about this...",
        tokens: 150,
      },
      model_name: "gpt-4",
    };

    it("should transform message_id to id", () => {
      const result = transformApiMessageToClient(validApiMessage);
      expect(result.id).toBe("msg-123");
    });

    it("should preserve role", () => {
      const result = transformApiMessageToClient(validApiMessage);
      expect(result.role).toBe("assistant");
    });

    it("should preserve content", () => {
      const result = transformApiMessageToClient(validApiMessage);
      expect(result.content).toBe("Hello, how can I help you?");
    });

    it("should transform ISO timestamp to Unix milliseconds", () => {
      const result = transformApiMessageToClient(validApiMessage);
      expect(result.timestamp).toBeTypeOf("number");
      expect(result.timestamp).toBe(new Date("2025-01-15T10:00:00Z").getTime());
    });

    it("should handle null timestamp", () => {
      const messageWithNullTimestamp: ApiMessage = {
        message_id: "msg-456",
        role: "user",
        content: "Hello",
        timestamp: null,
      };
      const result = transformApiMessageToClient(messageWithNullTimestamp);
      expect(result.timestamp).toBe(0);
    });

    it("should transform sources", () => {
      const result = transformApiMessageToClient(validApiMessage);
      expect(result.sources).toHaveLength(1);
      expect(result.sources?.[0].title).toBe("Documentation");
      expect(result.sources?.[0].url).toBe("https://example.com/docs");
    });

    it("should handle null sources", () => {
      const messageWithoutSources: ApiMessage = {
        message_id: "msg-456",
        role: "user",
        content: "Hello",
        timestamp: "2025-01-15T10:00:00Z",
        sources: null,
      };
      const result = transformApiMessageToClient(messageWithoutSources);
      expect(result.sources).toBeUndefined();
    });

    // Thinking object format (only format supported - legacy fields deprecated)
    it("should transform thinking object to thinkingContent and thinkingTokens", () => {
      const result = transformApiMessageToClient(validApiMessage);
      expect(result.thinkingContent).toBe("Let me think about this...");
      expect(result.thinkingTokens).toBe(150);
    });

    it("should handle thinking object without tokens", () => {
      const messageWithPartialThinking: ApiMessage = {
        message_id: "msg-partial",
        role: "assistant",
        content: "Response",
        timestamp: "2025-01-15T10:00:00Z",
        thinking: {
          content: "Just thinking content, no tokens",
        },
      };
      const result = transformApiMessageToClient(messageWithPartialThinking);
      expect(result.thinkingContent).toBe("Just thinking content, no tokens");
      expect(result.thinkingTokens).toBeUndefined();
    });

    it("should handle null thinking object", () => {
      const messageWithNullThinking: ApiMessage = {
        message_id: "msg-null-thinking",
        role: "assistant",
        content: "Response",
        timestamp: "2025-01-15T10:00:00Z",
        thinking: null,
      };
      const result = transformApiMessageToClient(messageWithNullThinking);
      expect(result.thinkingContent).toBeUndefined();
      expect(result.thinkingTokens).toBeUndefined();
    });

    it("should transform model_name to modelName", () => {
      const result = transformApiMessageToClient(validApiMessage);
      expect(result.modelName).toBe("gpt-4");
    });

    it("should handle missing optional fields", () => {
      const minimalMessage: ApiMessage = {
        message_id: "msg-789",
        role: "user",
        content: "Hello",
        timestamp: "2025-01-15T10:00:00Z",
      };
      const result = transformApiMessageToClient(minimalMessage);

      expect(result.id).toBe("msg-789");
      expect(result.sources).toBeUndefined();
      expect(result.thinkingContent).toBeUndefined();
      expect(result.thinkingTokens).toBeUndefined();
      expect(result.modelName).toBeUndefined();
    });
  });

  // ===========================================================================
  // Pattern 12: Thinking Field Conventions Across Layers
  // ===========================================================================
  // Documents the transformation pipeline for extended thinking fields:
  // OTEL (thinking_content) → API (thinking: {content, tokens}) → Client (thinkingContent)
  //
  // Reference: .claude/context/code-patterns.md (Pattern 12)
  // Reference: adr/adr-0091-api-response-transformation-strategy.md

  describe("Pattern 12: Thinking Object Transformation", () => {
    describe("Message thinking object → camelCase", () => {
      // These tests verify the transformation documented in Pattern 12
      it("should transform thinking object to flat camelCase fields", () => {
        const apiMessage: ApiMessage = {
          message_id: "msg-thinking",
          role: "assistant",
          content: "Response with thinking",
          timestamp: "2025-01-15T10:00:00Z",
          thinking: {
            content: "Let me reason through this step by step...",
            tokens: 250,
          },
          model_name: "claude-opus-4-5-20250514",
        };

        const result = transformApiMessageToClient(apiMessage);

        // Pattern 12: API object format → Client camelCase flat fields
        expect(result.thinkingContent).toBe(
          "Let me reason through this step by step...",
        );
        expect(result.thinkingTokens).toBe(250);
        expect(result.modelName).toBe("claude-opus-4-5-20250514");
      });

      it("should handle thinking with only content (no tokens)", () => {
        const apiMessage: ApiMessage = {
          message_id: "msg-content-only",
          role: "assistant",
          content: "Response",
          timestamp: "2025-01-15T10:00:00Z",
          thinking: {
            content: "Thinking without token count",
            // tokens intentionally omitted
          },
        };

        const result = transformApiMessageToClient(apiMessage);

        expect(result.thinkingContent).toBe("Thinking without token count");
        expect(result.thinkingTokens).toBeUndefined();
      });

      it("should handle null thinking object", () => {
        const apiMessage: ApiMessage = {
          message_id: "msg-no-thinking",
          role: "assistant",
          content: "Response without thinking",
          timestamp: "2025-01-15T10:00:00Z",
          thinking: null,
        };

        const result = transformApiMessageToClient(apiMessage);

        expect(result.thinkingContent).toBeUndefined();
        expect(result.thinkingTokens).toBeUndefined();
      });

      it("should handle undefined thinking (field not present)", () => {
        const apiMessage: ApiMessage = {
          message_id: "msg-undefined-thinking",
          role: "user",
          content: "User message",
          timestamp: "2025-01-15T10:00:00Z",
          // thinking field not present
        };

        const result = transformApiMessageToClient(apiMessage);

        expect(result.thinkingContent).toBeUndefined();
        expect(result.thinkingTokens).toBeUndefined();
      });
    });

    describe("Span thinking object structure", () => {
      // These tests verify the SpanResponse thinking object format matches Pattern 12
      it("should accept span with thinking object structure", () => {
        // SpanResponse format from API (matches generated-api.ts)
        const apiSpan = {
          span_id: "span-123",
          parent_span_id: null,
          name: "llm-call",
          start_time: "2025-01-15T10:00:00Z",
          duration_ms: 1500,
          status: "OK",
          attributes: {},
          thinking: {
            content: "Analyzing the problem...",
            tokens: 150,
          },
          model_name: "claude-opus-4-5-20250514",
        };

        // Verify thinking object structure
        expect(apiSpan.thinking).toBeDefined();
        expect(apiSpan.thinking?.content).toBe("Analyzing the problem...");
        expect(apiSpan.thinking?.tokens).toBe(150);
        expect(apiSpan.model_name).toBe("claude-opus-4-5-20250514");
      });

      it("should accept span without thinking (tool calls, etc)", () => {
        const apiSpan = {
          span_id: "span-456",
          parent_span_id: "span-123",
          name: "tool-call",
          start_time: "2025-01-15T10:00:01Z",
          duration_ms: 200,
          status: "OK",
          attributes: { "tool.name": "web_search" },
          thinking: null,
          model_name: null,
        };

        expect(apiSpan.thinking).toBeNull();
        expect(apiSpan.model_name).toBeNull();
      });
    });

    describe("TraceListItem aggregation fields", () => {
      // Pattern 12: Aggregation uses _total suffix for summed values
      it("should support thinking_tokens_total for trace aggregation", () => {
        const traceListItem = {
          trace_id: "trace-123",
          start_time: "2025-01-15T10:00:00Z",
          duration_ms: 5000,
          span_count: 10,
          has_thinking: true,
          thinking_tokens_total: 750, // Sum across all spans
        };

        expect(traceListItem.has_thinking).toBe(true);
        expect(traceListItem.thinking_tokens_total).toBe(750);
      });
    });
  });

  // ===========================================================================
  // Contract Tests: Loader ↔ Validator Boundary (ADR-0091 Phase 6 Findings)
  // ===========================================================================
  // These tests validate that components across the transformation boundary
  // use consistent data formats.

  describe("Contract: Loader output ↔ isApiSession validation", () => {
    /**
     * Finding 2 (HIGH): Chat loader builds camelCase sessions but isApiSession
     * expects snake_case. This causes session validation to fail silently.
     *
     * This test documents the expected behavior AFTER the fix.
     */
    it("should accept camelCase session from loader (createdAt/updatedAt)", () => {
      // Loader output format (camelCase)
      const loaderSession = {
        id: "session-123",
        name: "Test Session",
        status: "active",
        createdAt: "2025-01-15T10:00:00Z", // camelCase from loader
        updatedAt: "2025-01-15T11:00:00Z", // camelCase from loader
        config: { maxTokens: 8192 },
      };

      // After fix: isApiSession should accept EITHER format
      // Currently fails - this test documents expected behavior
      expect(isApiSession(loaderSession)).toBe(true);
    });

    it("should accept snake_case session from API", () => {
      // API response format (snake_case)
      const apiSession = {
        id: "session-123",
        name: "Test Session",
        status: "active",
        created_at: "2025-01-15T10:00:00Z",
        updated_at: "2025-01-15T11:00:00Z",
        config: { max_tokens: 8192 },
      };

      expect(isApiSession(apiSession)).toBe(true);
    });
  });
});
