/**
 * LLMProvidersCard Tests
 *
 * TDD tests for the LLMProvidersCard component.
 * Tests cover:
 * - Display of LLM provider registry
 * - Provider details (name, description, model types)
 * - API key requirements
 * - Persona-based visibility (only admin, developer)
 */

import { describe, it, expect, vi, afterEach } from "vitest";
import { render, screen, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import { LLMProvidersCard } from "./LLMProvidersCard";
import personaReducer from "../../store/slices/personaSlice";
import type { ProviderInfo } from "../../types/api";

// Helper to create a test store with specific persona
function createTestStoreWithPersona(persona: "admin" | "developer" | "user") {
  return configureStore({
    reducer: {
      persona: personaReducer,
    },
    preloadedState: {
      persona: {
        persona,
        subPersona: null,
        username: "testuser",
        email: "test@example.com",
        permissions: [],
        isPersonaLoading: false,
        visibleModules: [],
        featureFlags: {},
        apiVersion: null,
      },
    },
  });
}

// Mock providers data (camelCase per ADR-0091)
const mockProviders: ProviderInfo[] = [
  {
    name: "google",
    displayName: "Google Gemini",
    description: "Google's Gemini AI models",
    supportedModelTypes: ["primary", "summarization", "verification"],
    requiresApiKey: true,
    apiKeyEnvVar: "GOOGLE_API_KEY",
  },
  {
    name: "anthropic",
    displayName: "Anthropic Claude",
    description: "Anthropic's Claude AI models",
    supportedModelTypes: ["primary", "summarization", "verification"],
    requiresApiKey: true,
    apiKeyEnvVar: "ANTHROPIC_API_KEY",
  },
  {
    name: "ollama",
    displayName: "Ollama (Local)",
    description: "Local LLM inference via Ollama",
    supportedModelTypes: ["primary"],
    requiresApiKey: false,
    apiKeyEnvVar: null,
  },
];

describe("LLMProvidersCard", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Admin Persona", () => {
    it("should render card for admin persona", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <LLMProvidersCard providers={mockProviders} />
        </Provider>,
      );

      expect(screen.getAllByText(/Providers/i).length).toBeGreaterThan(0);
    });

    it("should display provider count", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <LLMProvidersCard providers={mockProviders} />
        </Provider>,
      );

      expect(screen.getByText(/3 providers/i)).toBeInTheDocument();
    });

    it("should display provider names", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <LLMProvidersCard providers={mockProviders} />
        </Provider>,
      );

      expect(screen.getByText("Google Gemini")).toBeInTheDocument();
      expect(screen.getByText("Anthropic Claude")).toBeInTheDocument();
      expect(screen.getByText("Ollama (Local)")).toBeInTheDocument();
    });

    it("should display supported model types", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <LLMProvidersCard providers={mockProviders} />
        </Provider>,
      );

      // Check model types are shown
      expect(screen.getAllByText("primary").length).toBeGreaterThan(0);
      expect(screen.getAllByText("summarization").length).toBeGreaterThan(0);
      expect(screen.getAllByText("verification").length).toBeGreaterThan(0);
    });

    it("should display API key requirements", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <LLMProvidersCard providers={mockProviders} />
        </Provider>,
      );

      // 2 providers require API key, 1 doesn't
      expect(screen.getAllByText("API Key Required").length).toBe(2);
      expect(screen.getByText("No API Key")).toBeInTheDocument();
    });
  });

  describe("Developer Persona", () => {
    it("should render card for developer persona", () => {
      const store = createTestStoreWithPersona("developer");

      render(
        <Provider store={store}>
          <LLMProvidersCard providers={mockProviders} />
        </Provider>,
      );

      expect(screen.getAllByText(/Providers/i).length).toBeGreaterThan(0);
    });
  });

  describe("User Persona", () => {
    it("should NOT render card for user persona", () => {
      const store = createTestStoreWithPersona("user");

      render(
        <Provider store={store}>
          <LLMProvidersCard providers={mockProviders} />
        </Provider>,
      );

      expect(screen.queryByText(/Providers/i)).not.toBeInTheDocument();
    });
  });

  describe("Empty Data Handling", () => {
    it("should render nothing when providers is empty", () => {
      const store = createTestStoreWithPersona("admin");

      render(
        <Provider store={store}>
          <LLMProvidersCard providers={[]} />
        </Provider>,
      );

      expect(screen.queryByText(/Providers/i)).not.toBeInTheDocument();
    });
  });
});
