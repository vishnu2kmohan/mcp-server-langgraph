import { describe, it, expect, vi, afterEach } from "vitest";
import { formatProviderDisplay } from "./modelDisplay";
import type { ModelOption } from "@/types/api";

afterEach(() => {
  vi.clearAllMocks();
  vi.restoreAllMocks();
});

describe("formatProviderDisplay", () => {
  it("returns capitalized provider when no vendor specified", () => {
    const model: ModelOption = {
      id: "gpt-4o",
      name: "GPT-4o",
      provider: "openai",
    };
    expect(formatProviderDisplay(model)).toBe("OpenAI");
  });

  it("returns 'Google (Vertex AI)' for Vertex AI Google models", () => {
    const model: ModelOption = {
      id: "gemini-2.0-flash",
      name: "Gemini 2.0 Flash",
      provider: "google",
      vendor: "vertex_ai",
    };
    expect(formatProviderDisplay(model)).toBe("Google (Vertex AI)");
  });

  it("returns 'Anthropic (Vertex AI)' for Vertex AI Anthropic models", () => {
    const model: ModelOption = {
      id: "claude-sonnet-4",
      name: "Claude Sonnet 4",
      provider: "anthropic",
      vendor: "vertex_ai_anthropic",
    };
    expect(formatProviderDisplay(model)).toBe("Anthropic (Vertex AI)");
  });

  it("returns 'OpenAI (Azure)' for Azure OpenAI models", () => {
    const model: ModelOption = {
      id: "gpt-4o-azure",
      name: "GPT-4o (Azure)",
      provider: "openai",
      vendor: "azure",
    };
    expect(formatProviderDisplay(model)).toBe("OpenAI (Azure)");
  });

  it("returns capitalized provider for unknown vendor", () => {
    const model: ModelOption = {
      id: "custom-model",
      name: "Custom Model",
      provider: "custom",
      vendor: "unknown_vendor",
    };
    expect(formatProviderDisplay(model)).toBe("Custom");
  });
});
