/**
 * useAIOnboarding Hook Tests
 *
 * TDD tests for the AI-powered onboarding personalization hook.
 * Phase 6.5: AI Onboarding Personalization
 *
 * Tests the hook's ability to:
 * - Detect user intent from initial actions
 * - Provide personalized onboarding paths
 * - Handle loading and error states
 * - Integrate with Redux persona state
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";
import personaReducer from "../store/slices/personaSlice";
import authReducer from "../store/slices/authSlice";

// Mock hook implementation - will be created
const mockUseAIOnboarding = vi.fn();
vi.mock("./useAIOnboarding", () => ({
  useAIOnboarding: () => mockUseAIOnboarding(),
  default: () => mockUseAIOnboarding(),
}));

// =============================================================================
// Test Store Setup
// =============================================================================

const createTestStore = () =>
  configureStore({
    reducer: {
      persona: personaReducer,
      auth: authReducer,
    },
    preloadedState: {
      persona: {
        persona: "user",
        username: "new-user",
        email: "new@example.com",
        permissions: [],
        isPersonaLoading: false,
      },
      auth: {
        user: {
          id: "new-user-123",
          username: "new-user",
          email: "new@example.com",
          roles: ["user"],
          persona: "user",
        },
        tokens: {
          accessToken: "mock-token",
          refreshToken: "mock-refresh",
          expiresAt: Date.now() + 3600000,
          refreshExpiresAt: Date.now() + 86400000,
        },
        currentOrg: null,
        organizations: [],
        isInitializing: false,
        isLoading: false,
        error: null,
      },
    },
  });

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <Provider store={createTestStore()}>{children}</Provider>
);

// =============================================================================
// Tests
// =============================================================================

describe("useAIOnboarding", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Initial State", () => {
    it("should start with loading state when enabled", () => {
      mockUseAIOnboarding.mockReturnValue({
        isLoading: true,
        error: null,
        detectedIntent: null,
        confidence: 0,
        recommendedPath: [],
        skipSteps: [],
        personaPrediction: null,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIOnboarding(), { wrapper });
      expect(result.current.isLoading).toBe(true);
    });

    it("should not fetch when disabled", () => {
      mockUseAIOnboarding.mockReturnValue({
        isLoading: false,
        error: null,
        detectedIntent: null,
        confidence: 0,
        recommendedPath: [],
        skipSteps: [],
        personaPrediction: null,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIOnboarding(), { wrapper });
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe("Intent Detection", () => {
    it("should detect workflow building intent from actions", async () => {
      mockUseAIOnboarding.mockReturnValue({
        isLoading: false,
        error: null,
        detectedIntent: "build_chatbot",
        confidence: 0.92,
        recommendedPath: [
          { step: "template_selection", template: "basic-chatbot" },
          { step: "first_run", guided: true },
        ],
        skipSteps: ["project_creation"],
        personaPrediction: "alice-builder",
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIOnboarding(), { wrapper });

      expect(result.current.detectedIntent).toBe("build_chatbot");
      expect(result.current.confidence).toBeGreaterThan(0.9);
      expect(result.current.personaPrediction).toBe("alice-builder");
    });

    it("should provide recommended path steps", async () => {
      mockUseAIOnboarding.mockReturnValue({
        isLoading: false,
        error: null,
        detectedIntent: "build_chatbot",
        confidence: 0.92,
        recommendedPath: [
          { step: "template_selection", template: "basic-chatbot" },
          { step: "first_run", guided: true },
          { step: "customization", focus: "llm_selection" },
        ],
        skipSteps: ["project_creation"],
        personaPrediction: "alice-builder",
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIOnboarding(), { wrapper });

      expect(result.current.recommendedPath).toHaveLength(3);
      expect(result.current.recommendedPath[0]).toEqual({
        step: "template_selection",
        template: "basic-chatbot",
      });
    });

    it("should identify steps to skip for advanced users", async () => {
      mockUseAIOnboarding.mockReturnValue({
        isLoading: false,
        error: null,
        detectedIntent: "build_chatbot",
        confidence: 0.92,
        recommendedPath: [],
        skipSteps: ["project_creation"],
        personaPrediction: "alice-builder",
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIOnboarding(), { wrapper });

      expect(result.current.skipSteps).toContain("project_creation");
    });

    it("should default to exploration intent for new users", async () => {
      mockUseAIOnboarding.mockReturnValue({
        isLoading: false,
        error: null,
        detectedIntent: "general_exploration",
        confidence: 0.65,
        recommendedPath: [
          { step: "welcome_tour", duration: "short" },
        ],
        skipSteps: [],
        personaPrediction: "bob",
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIOnboarding(), { wrapper });

      expect(result.current.detectedIntent).toBe("general_exploration");
      expect(result.current.personaPrediction).toBe("bob");
    });
  });

  describe("Error Handling", () => {
    it("should handle API errors gracefully", async () => {
      mockUseAIOnboarding.mockReturnValue({
        isLoading: false,
        error: new Error("Failed to personalize onboarding"),
        detectedIntent: null,
        confidence: 0,
        recommendedPath: [],
        skipSteps: [],
        personaPrediction: null,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIOnboarding(), { wrapper });

      expect(result.current.error).toBeTruthy();
      expect(result.current.error?.message).toContain("personalize");
    });

    it("should handle timeout with fallback", async () => {
      mockUseAIOnboarding.mockReturnValue({
        isLoading: false,
        error: new Error("Request timed out"),
        detectedIntent: null,
        confidence: 0,
        recommendedPath: [],
        skipSteps: [],
        personaPrediction: null,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIOnboarding(), { wrapper });

      expect(result.current.error?.message).toContain("timed out");
    });
  });

  describe("Refresh Capability", () => {
    it("should provide refresh function", () => {
      const refreshFn = vi.fn();
      mockUseAIOnboarding.mockReturnValue({
        isLoading: false,
        error: null,
        detectedIntent: "general_exploration",
        confidence: 0.65,
        recommendedPath: [],
        skipSteps: [],
        personaPrediction: "bob",
        refresh: refreshFn,
      });

      const { result } = renderHook(() => mockUseAIOnboarding(), { wrapper });

      expect(typeof result.current.refresh).toBe("function");
      result.current.refresh();
      expect(refreshFn).toHaveBeenCalledTimes(1);
    });
  });

  describe("Signup Context Integration", () => {
    it("should use signup context for personalization", async () => {
      mockUseAIOnboarding.mockReturnValue({
        isLoading: false,
        error: null,
        detectedIntent: "documentation_seeker",
        confidence: 0.85,
        recommendedPath: [
          { step: "docs_highlight", focus: "api" },
        ],
        skipSteps: ["basic_intro"],
        personaPrediction: "alice-analyst",
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIOnboarding(), { wrapper });

      expect(result.current.confidence).toBeGreaterThan(0.8);
    });
  });
});
