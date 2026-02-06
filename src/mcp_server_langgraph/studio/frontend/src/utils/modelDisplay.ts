/**
 * Model Display Utilities
 *
 * Shared utilities for formatting model provider/vendor information
 * for consistent display across the application.
 */

import type { ModelOption } from "@/types/api";

/**
 * Proper brand casing for known providers
 */
const PROVIDER_LABELS: Record<string, string> = {
  openai: "OpenAI",
  anthropic: "Anthropic",
  google: "Google",
  meta: "Meta",
  mistral: "Mistral",
  cohere: "Cohere",
  deepseek: "DeepSeek",
};

/**
 * Capitalize first letter of a string (fallback for unknown providers)
 */
function capitalize(s: string): string {
  return s.charAt(0).toUpperCase() + s.slice(1);
}

/**
 * Get properly cased provider name
 */
function getProviderLabel(provider: string): string {
  return PROVIDER_LABELS[provider.toLowerCase()] ?? capitalize(provider);
}

/**
 * Format provider display string with vendor distinction.
 *
 * LLM Gateway (LiteLLM Router) returns simplified providers like "google", "anthropic"
 * but the actual vendor may differ (e.g., Vertex AI vs native API).
 *
 * This function shows the distinction for clarity:
 * - "Google (Vertex AI)" when using Vertex AI instead of native API
 * - "Anthropic (Vertex AI)" for Anthropic models on Vertex
 * - "OpenAI (Azure)" for Azure-hosted OpenAI models
 *
 * @param model - The model option containing provider and vendor info
 * @returns Formatted provider display string
 */
export function formatProviderDisplay(model: ModelOption): string {
  const { provider, vendor } = model;

  // No vendor specified - return properly cased provider
  if (!vendor) return getProviderLabel(provider);

  // Show vendor distinction when it differs from simplified provider
  if (vendor === "vertex_ai" && provider === "google") {
    return "Google (Vertex AI)";
  }
  if (vendor === "vertex_ai_anthropic" && provider === "anthropic") {
    return "Anthropic (Vertex AI)";
  }
  if (vendor === "azure" && provider === "openai") {
    return "OpenAI (Azure)";
  }

  // Default: return properly cased provider
  return getProviderLabel(provider);
}
