/**
 * API Transforms Tests
 *
 * TDD tests for type-safe API response transformations.
 */
import { describe, it, expect } from "vitest";
import {
  isApiSession,
  transformApiSessionToClient,
  validateApiSession,
  safeTransformToClientSession,
  type ApiSession,
} from "./apiTransforms";

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
      expect(isApiSession({ created_at: "2025-01-15", updated_at: "2025-01-15" })).toBe(false);
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
        })
      ).toBe(false);
    });

    it("should return false for invalid status type", () => {
      expect(
        isApiSession({
          id: "123",
          created_at: "2025-01-15",
          updated_at: "2025-01-15",
          status: { invalid: "object" }, // object instead of string
        })
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
      const result = validateApiSession({ created_at: "2025-01-15", updated_at: "2025-01-15" });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toBe("Missing or invalid 'id' field");
      }
    });

    it("should return error for missing created_at field", () => {
      const result = validateApiSession({ id: "test-id", updated_at: "2025-01-15" });
      expect(result.success).toBe(false);
      if (!result.success) {
        expect(result.error).toBe("Missing or invalid 'created_at' field");
      }
    });

    it("should return error for missing updated_at field", () => {
      const result = validateApiSession({ id: "test-id", created_at: "2025-01-15" });
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

      expect(result.config.modelName).toBe("gpt-4");
      expect(result.config.modelProvider).toBe("openai");
      expect(result.config.temperature).toBe(0.7);
      expect(result.config.maxTokens).toBe(4096);
    });

    it("should include messages in result", () => {
      const messages = [
        { id: "msg-1", role: "user" as const, content: "Hello", timestamp: Date.now() },
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
});
