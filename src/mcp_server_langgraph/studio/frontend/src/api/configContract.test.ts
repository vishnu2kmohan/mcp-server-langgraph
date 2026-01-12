/**
 * Config API Contract Tests
 *
 * Validates that the MSW handlers match the expected API contract for
 * configuration endpoints (/config/models).
 * Uses raw fetch() to test the actual response shapes without RTK Query transformation.
 *
 * These tests document the Config API contract and catch handler inconsistencies.
 */

import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { server } from "../mocks/server";

describe("Config API Contract Tests", () => {
  beforeEach(() => {
    // Server is already started in setup.ts
  });

  afterEach(() => {
    server.resetHandlers();
    vi.clearAllMocks();
    vi.restoreAllMocks();
  });

  describe("GET /api/v1/config/models", () => {
    it("should return 200 status", async () => {
      const response = await fetch("/api/v1/config/models");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);
    });

    it("should return an array of models", async () => {
      const response = await fetch("/api/v1/config/models");
      expect(response.ok).toBe(true);

      const data = await response.json();
      expect(Array.isArray(data)).toBe(true);
      expect(data.length).toBeGreaterThan(0);
    });

    it("should return models with required fields", async () => {
      const response = await fetch("/api/v1/config/models");
      expect(response.ok).toBe(true);

      const data = await response.json();

      for (const model of data) {
        expect(model).toHaveProperty("id");
        expect(model).toHaveProperty("name");
        expect(model).toHaveProperty("provider");
        expect(model).toHaveProperty("supports_thinking");
        // Sprint 1: Enhanced Model Selector - capability badges require these fields
        expect(model).toHaveProperty("supports_vision");
        expect(model).toHaveProperty("supports_tools");
      }
    });

    it("should return valid field types for each model", async () => {
      const response = await fetch("/api/v1/config/models");
      expect(response.ok).toBe(true);

      const data = await response.json();

      for (const model of data) {
        expect(typeof model.id).toBe("string");
        expect(typeof model.name).toBe("string");
        expect(typeof model.provider).toBe("string");
        expect(typeof model.supports_thinking).toBe("boolean");
        // Sprint 1: Enhanced Model Selector - capability badges
        expect(typeof model.supports_vision).toBe("boolean");
        expect(typeof model.supports_tools).toBe("boolean");
      }
    });

    it("should include Anthropic models", async () => {
      const response = await fetch("/api/v1/config/models");
      expect(response.ok).toBe(true);

      const data = await response.json();
      const providers = data.map((m: { provider: string }) => m.provider);

      expect(providers).toContain("anthropic");
    });

    it("should include OpenAI models", async () => {
      const response = await fetch("/api/v1/config/models");
      expect(response.ok).toBe(true);

      const data = await response.json();
      const providers = data.map((m: { provider: string }) => m.provider);

      expect(providers).toContain("openai");
    });

    it("should include Google models", async () => {
      const response = await fetch("/api/v1/config/models");
      expect(response.ok).toBe(true);

      const data = await response.json();
      const providers = data.map((m: { provider: string }) => m.provider);

      expect(providers).toContain("google");
    });

    it("should correctly identify thinking-capable models", async () => {
      const response = await fetch("/api/v1/config/models");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // Claude Opus 4.5 and Claude Sonnet 4.5 support extended thinking
      const claudeOpus = data.find(
        (m: { id: string }) => m.id === "claude-opus-4-5",
      );
      const claudeSonnet = data.find(
        (m: { id: string }) => m.id === "claude-sonnet-4-5",
      );

      expect(claudeOpus?.supports_thinking).toBe(true);
      expect(claudeSonnet?.supports_thinking).toBe(true);
    });

    it("should correctly identify non-thinking models", async () => {
      const response = await fetch("/api/v1/config/models");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // Claude Haiku 4.5 does not support extended thinking
      const claudeHaiku = data.find(
        (m: { id: string }) => m.id === "claude-haiku-4-5",
      );

      expect(claudeHaiku?.supports_thinking).toBe(false);
    });

    // =========================================================================
    // Vision & Tools Capability Tests (Sprint 1 - Enhanced Model Selector)
    // =========================================================================

    it("should correctly identify vision-capable models", async () => {
      const response = await fetch("/api/v1/config/models");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // Current Claude models support vision
      const claudeOpus = data.find(
        (m: { id: string }) => m.id === "claude-opus-4-5",
      );
      const claudeSonnet = data.find(
        (m: { id: string }) => m.id === "claude-sonnet-4-5",
      );
      const gpt52 = data.find((m: { id: string }) => m.id === "gpt-5.2");

      expect(claudeOpus?.supports_vision).toBe(true);
      expect(claudeSonnet?.supports_vision).toBe(true);
      expect(gpt52?.supports_vision).toBe(true);
    });

    it("should correctly identify tools-capable models", async () => {
      const response = await fetch("/api/v1/config/models");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // Most modern models support tools
      const claudeOpus = data.find(
        (m: { id: string }) => m.id === "claude-opus-4-5",
      );
      const gpt52 = data.find((m: { id: string }) => m.id === "gpt-5.2");
      const gemini = data.find(
        (m: { id: string }) => m.id === "gemini-2.5-flash",
      );

      expect(claudeOpus?.supports_tools).toBe(true);
      expect(gpt52?.supports_tools).toBe(true);
      expect(gemini?.supports_tools).toBe(true);
    });

    // =========================================================================
    // Model Status Tests (Sprint 1 - Enhanced Model Selector)
    // =========================================================================

    it("should include status field for lifecycle management", async () => {
      const response = await fetch("/api/v1/config/models");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // All models should have a status field
      for (const model of data) {
        expect(model).toHaveProperty("status");
        expect(["current", "preview", "legacy", "deprecated"]).toContain(
          model.status,
        );
      }
    });

    it("should correctly categorize model statuses", async () => {
      const response = await fetch("/api/v1/config/models");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // Current models (recommended for production)
      const claudeOpus = data.find(
        (m: { id: string }) => m.id === "claude-opus-4-5",
      );
      expect(claudeOpus?.status).toBe("current");

      // Preview models (not yet GA)
      const gemini3Flash = data.find(
        (m: { id: string }) => m.id === "gemini-3-flash",
      );
      expect(gemini3Flash?.status).toBe("preview");

      // Legacy models (still supported but superseded)
      const gpt4o = data.find((m: { id: string }) => m.id === "gpt-4o");
      expect(gpt4o?.status).toBe("legacy");

      // Deprecated models (scheduled for retirement)
      const claude35Sonnet = data.find(
        (m: { id: string }) => m.id === "claude-3-5-sonnet",
      );
      expect(claude35Sonnet?.status).toBe("deprecated");
    });

    it("should include sunset_date for deprecated models", async () => {
      const response = await fetch("/api/v1/config/models");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // Deprecated models should have sunset_date
      const deprecatedModels = data.filter(
        (m: { status: string }) => m.status === "deprecated",
      );

      expect(deprecatedModels.length).toBeGreaterThan(0);

      for (const model of deprecatedModels) {
        expect(model).toHaveProperty("sunset_date");
        expect(typeof model.sunset_date).toBe("string");
        // Validate ISO 8601 date format (YYYY-MM-DD)
        expect(model.sunset_date).toMatch(/^\d{4}-\d{2}-\d{2}$/);
      }
    });

    it("should NOT include sunset_date for non-deprecated models", async () => {
      const response = await fetch("/api/v1/config/models");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // Non-deprecated models should NOT have sunset_date
      const nonDeprecatedModels = data.filter(
        (m: { status: string }) => m.status !== "deprecated",
      );

      for (const model of nonDeprecatedModels) {
        expect(model.sunset_date).toBeUndefined();
      }
    });

    it("should have consistent required fields across all models", async () => {
      const response = await fetch("/api/v1/config/models");
      expect(response.ok).toBe(true);

      const data = await response.json();

      for (const model of data) {
        // All fields are now required (Sprint 1 - Enhanced Model Selector)
        expect(model.id).toBeDefined();
        expect(model.name).toBeDefined();
        expect(model.provider).toBeDefined();
        expect(model.supports_thinking).toBeDefined();
        expect(model.supports_vision).toBeDefined();
        expect(model.supports_tools).toBeDefined();

        // Type validation
        expect(typeof model.id).toBe("string");
        expect(typeof model.name).toBe("string");
        expect(typeof model.provider).toBe("string");
        expect(typeof model.supports_thinking).toBe("boolean");
        expect(typeof model.supports_vision).toBe("boolean");
        expect(typeof model.supports_tools).toBe("boolean");
      }
    });
  });

  describe("GET /api/v1/config/defaults", () => {
    it("should return 200 status", async () => {
      const response = await fetch("/api/v1/config/defaults");
      expect(response.ok).toBe(true);
      expect(response.status).toBe(200);
    });

    it("should return required server config fields", async () => {
      const response = await fetch("/api/v1/config/defaults");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data).toHaveProperty("model_name");
      expect(data).toHaveProperty("model_provider");
      expect(data).toHaveProperty("max_tokens");
      expect(data).toHaveProperty("temperature");
    });

    it("should return valid field types", async () => {
      const response = await fetch("/api/v1/config/defaults");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(typeof data.model_name).toBe("string");
      expect(typeof data.model_provider).toBe("string");
      expect(typeof data.max_tokens).toBe("number");
      expect(typeof data.temperature).toBe("number");
    });

    it("should return valid temperature range", async () => {
      const response = await fetch("/api/v1/config/defaults");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.temperature).toBeGreaterThanOrEqual(0);
      expect(data.temperature).toBeLessThanOrEqual(2);
    });

    it("should return positive max_tokens", async () => {
      const response = await fetch("/api/v1/config/defaults");
      expect(response.ok).toBe(true);

      const data = await response.json();

      expect(data.max_tokens).toBeGreaterThan(0);
    });

    it("should return a known model provider", async () => {
      const response = await fetch("/api/v1/config/defaults");
      expect(response.ok).toBe(true);

      const data = await response.json();

      const knownProviders = [
        "anthropic",
        "openai",
        "google",
        "azure",
        "unknown",
      ];
      expect(knownProviders).toContain(data.model_provider);
    });
  });
});
