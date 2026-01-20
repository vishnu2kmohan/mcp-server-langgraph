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
      // NOTE: gemini-3-flash-preview is the default model per .env.test MODEL_NAME
      const gemini3FlashPreview = data.find(
        (m: { id: string }) => m.id === "gemini-3-flash-preview",
      );
      expect(gemini3FlashPreview?.status).toBe("preview");

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

    it("should return default_reasoning_effort matching .env.test FF_MAX_THINKING_BUDGET", async () => {
      const response = await fetch("/api/v1/config/defaults");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // default_reasoning_effort should match FF_MAX_THINKING_BUDGET from .env.test
      expect(data).toHaveProperty("default_reasoning_effort");
      expect(typeof data.default_reasoning_effort).toBe("string");

      // Valid reasoning effort levels
      const validLevels = ["none", "low", "medium", "high", "ultra"];
      expect(validLevels).toContain(data.default_reasoning_effort);

      // Per .env.test: FF_MAX_THINKING_BUDGET=medium
      expect(data.default_reasoning_effort).toBe("medium");
    });

    it("should return model_name matching .env.test MODEL_NAME", async () => {
      const response = await fetch("/api/v1/config/defaults");
      expect(response.ok).toBe(true);

      const data = await response.json();

      // Per .env.test: MODEL_NAME=vertex_ai/gemini-3-flash-preview
      // The model_name should be the model ID (without provider prefix)
      expect(data.model_name).toBe("gemini-3-flash-preview");
      expect(data.model_provider).toBe("google");
    });

    it("should have default model_name present in /api/v1/config/models", async () => {
      // Fetch defaults to get the default model
      const defaultsResponse = await fetch("/api/v1/config/defaults");
      expect(defaultsResponse.ok).toBe(true);
      const defaults = await defaultsResponse.json();

      // Fetch available models
      const modelsResponse = await fetch("/api/v1/config/models");
      expect(modelsResponse.ok).toBe(true);
      const models = await modelsResponse.json();

      // The default model should exist in the models list
      const defaultModel = models.find(
        (m: { id: string }) => m.id === defaults.model_name,
      );
      expect(defaultModel).toBeDefined();
      expect(defaultModel.provider).toBe(defaults.model_provider);
    });
  });

  describe("Model-Defaults Consistency", () => {
    it("should mark exactly one model as is_default in /api/v1/config/models", async () => {
      const response = await fetch("/api/v1/config/models");
      expect(response.ok).toBe(true);

      const models = await response.json();

      const defaultModels = models.filter(
        (m: { is_default?: boolean }) => m.is_default === true,
      );
      expect(defaultModels.length).toBe(1);
    });

    it("should have is_default model matching /api/v1/config/defaults model_name", async () => {
      // Fetch defaults
      const defaultsResponse = await fetch("/api/v1/config/defaults");
      expect(defaultsResponse.ok).toBe(true);
      const defaults = await defaultsResponse.json();

      // Fetch models
      const modelsResponse = await fetch("/api/v1/config/models");
      expect(modelsResponse.ok).toBe(true);
      const models = await modelsResponse.json();

      // Find the model marked as default
      const isDefaultModel = models.find(
        (m: { is_default?: boolean }) => m.is_default === true,
      );
      expect(isDefaultModel).toBeDefined();

      // The is_default model ID should match defaults.model_name
      expect(isDefaultModel.id).toBe(defaults.model_name);
    });
  });
});
