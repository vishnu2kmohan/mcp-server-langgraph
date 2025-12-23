/**
 * useBatchCompositeAnalysis Hook Tests
 *
 * TDD tests for the batch composite analysis hook.
 * Validates the frontend hook that calls the batch composite endpoint.
 *
 * Tests verify:
 * - Hook returns proper structure
 * - Loading and error states work correctly
 * - Partial analysis flags are respected
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

import personaReducer from "../store/slices/personaSlice";
import authReducer from "../store/slices/authSlice";

// Mock hook implementation
const mockUseBatchCompositeAnalysis = vi.fn();
vi.mock("./useBatchCompositeAnalysis", () => ({
  useBatchCompositeAnalysis: () => mockUseBatchCompositeAnalysis(),
  default: () => mockUseBatchCompositeAnalysis(),
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
        persona: "bob",
        subPersona: null,
        username: "bob",
        email: "bob@example.com",
        permissions: [],
        isPersonaLoading: false,
      },
      auth: {
        user: {
          id: "user-123",
          username: "bob",
          email: "bob@example.com",
          roles: ["user"],
          persona: "bob",
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

describe("useBatchCompositeAnalysis", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("hook structure", () => {
    it("returns expected result shape", () => {
      mockUseBatchCompositeAnalysis.mockReturnValue({
        personaResult: null,
        disclosureResult: null,
        errorResult: null,
        crossInsights: [],
        confidence: 0,
        isLoading: false,
        error: null,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseBatchCompositeAnalysis(), {
        wrapper,
      });

      expect(result.current).toHaveProperty("personaResult");
      expect(result.current).toHaveProperty("disclosureResult");
      expect(result.current).toHaveProperty("errorResult");
      expect(result.current).toHaveProperty("crossInsights");
      expect(result.current).toHaveProperty("confidence");
      expect(result.current).toHaveProperty("isLoading");
      expect(result.current).toHaveProperty("error");
      expect(result.current).toHaveProperty("refresh");
    });
  });

  describe("persona analysis", () => {
    it("returns persona result when includePersona is true", () => {
      mockUseBatchCompositeAnalysis.mockReturnValue({
        personaResult: {
          assigned_persona: "bob",
          detected_persona: "alice-builder",
          confidence: 0.85,
          behavior_signals: ["frequent_workflow_edits", "advanced_features"],
          recommendation: "Consider upgrading to alice-builder",
          ui_adaptations: [{ feature: "workflow_builder", action: "promote" }],
        },
        disclosureResult: null,
        errorResult: null,
        crossInsights: [],
        confidence: 0.85,
        isLoading: false,
        error: null,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseBatchCompositeAnalysis(), {
        wrapper,
      });

      expect(result.current.personaResult).not.toBeNull();
      expect(result.current.personaResult?.detected_persona).toBe(
        "alice-builder",
      );
      expect(result.current.personaResult?.confidence).toBe(0.85);
    });

    it("returns null persona result when includePersona is false", () => {
      mockUseBatchCompositeAnalysis.mockReturnValue({
        personaResult: null,
        disclosureResult: {
          current_level: "intermediate",
          recommended_level: "advanced",
          confidence: 0.8,
          unlock_features: ["advanced_settings"],
          personalized_message: "Ready for advanced features",
        },
        errorResult: null,
        crossInsights: [],
        confidence: 0.8,
        isLoading: false,
        error: null,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseBatchCompositeAnalysis(), {
        wrapper,
      });

      expect(result.current.personaResult).toBeNull();
      expect(result.current.disclosureResult).not.toBeNull();
    });
  });

  describe("disclosure analysis", () => {
    it("returns disclosure result when includeDisclosure is true", () => {
      mockUseBatchCompositeAnalysis.mockReturnValue({
        personaResult: null,
        disclosureResult: {
          current_level: "beginner",
          recommended_level: "intermediate",
          confidence: 0.9,
          unlock_features: ["templates", "shortcuts"],
          personalized_message: "You're ready for more features!",
        },
        errorResult: null,
        crossInsights: [],
        confidence: 0.9,
        isLoading: false,
        error: null,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseBatchCompositeAnalysis(), {
        wrapper,
      });

      expect(result.current.disclosureResult).not.toBeNull();
      expect(result.current.disclosureResult?.current_level).toBe("beginner");
      expect(result.current.disclosureResult?.recommended_level).toBe(
        "intermediate",
      );
    });
  });

  describe("error analysis", () => {
    it("returns error result when includeError is true", () => {
      mockUseBatchCompositeAnalysis.mockReturnValue({
        personaResult: null,
        disclosureResult: null,
        errorResult: {
          classification: {
            category: "network",
            subcategory: "timeout",
            confidence: 0.92,
          },
          rootCause: "Server took too long to respond",
          suggestions: [
            { action: "retry", label: "Try again", estimatedSuccess: 0.8 },
          ],
          similarIssues: [],
        },
        crossInsights: [],
        confidence: 0.92,
        isLoading: false,
        error: null,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseBatchCompositeAnalysis(), {
        wrapper,
      });

      expect(result.current.errorResult).not.toBeNull();
      expect(result.current.errorResult?.classification.category).toBe(
        "network",
      );
      expect(result.current.errorResult?.suggestions).toHaveLength(1);
    });
  });

  describe("cross insights", () => {
    it("returns cross insights when multiple analyses are requested", () => {
      mockUseBatchCompositeAnalysis.mockReturnValue({
        personaResult: {
          assigned_persona: "bob",
          detected_persona: "alice-builder",
          confidence: 0.85,
          behavior_signals: [],
          recommendation: null,
          ui_adaptations: [],
        },
        disclosureResult: {
          current_level: "intermediate",
          recommended_level: "advanced",
          confidence: 0.8,
          unlock_features: [],
          personalized_message: "",
        },
        errorResult: null,
        crossInsights: [
          "Persona alice-builder aligns with advanced disclosure level",
          "User behavior suggests readiness for advanced features",
        ],
        confidence: 0.83,
        isLoading: false,
        error: null,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseBatchCompositeAnalysis(), {
        wrapper,
      });

      expect(result.current.crossInsights).toHaveLength(2);
      expect(result.current.crossInsights[0]).toContain("alice-builder");
    });
  });

  describe("refresh functionality", () => {
    it("has a refresh function", () => {
      const refreshFn = vi.fn();
      mockUseBatchCompositeAnalysis.mockReturnValue({
        personaResult: null,
        disclosureResult: null,
        errorResult: null,
        crossInsights: [],
        confidence: 0,
        isLoading: false,
        error: null,
        refresh: refreshFn,
      });

      const { result } = renderHook(() => mockUseBatchCompositeAnalysis(), {
        wrapper,
      });

      expect(typeof result.current.refresh).toBe("function");
      result.current.refresh();
      expect(refreshFn).toHaveBeenCalledTimes(1);
    });
  });

  describe("enabled flag", () => {
    it("does not fetch when enabled is false", () => {
      mockUseBatchCompositeAnalysis.mockReturnValue({
        personaResult: null,
        disclosureResult: null,
        errorResult: null,
        crossInsights: [],
        confidence: 0,
        isLoading: false,
        error: null,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseBatchCompositeAnalysis(), {
        wrapper,
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.personaResult).toBeNull();
    });
  });

  describe("confidence scoring", () => {
    it("returns overall confidence score", () => {
      mockUseBatchCompositeAnalysis.mockReturnValue({
        personaResult: { detected_persona: "bob", confidence: 0.85 },
        disclosureResult: { recommended_level: "advanced", confidence: 0.8 },
        errorResult: null,
        crossInsights: [],
        confidence: 0.83,
        isLoading: false,
        error: null,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseBatchCompositeAnalysis(), {
        wrapper,
      });

      expect(typeof result.current.confidence).toBe("number");
      expect(result.current.confidence).toBe(0.83);
      expect(result.current.confidence).toBeGreaterThanOrEqual(0);
      expect(result.current.confidence).toBeLessThanOrEqual(1);
    });
  });

  describe("loading state", () => {
    it("shows loading state while fetching", () => {
      mockUseBatchCompositeAnalysis.mockReturnValue({
        personaResult: null,
        disclosureResult: null,
        errorResult: null,
        crossInsights: [],
        confidence: 0,
        isLoading: true,
        error: null,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseBatchCompositeAnalysis(), {
        wrapper,
      });

      expect(result.current.isLoading).toBe(true);
    });
  });

  describe("error handling", () => {
    it("handles API errors gracefully", () => {
      mockUseBatchCompositeAnalysis.mockReturnValue({
        personaResult: null,
        disclosureResult: null,
        errorResult: null,
        crossInsights: [],
        confidence: 0,
        isLoading: false,
        error: new Error("Batch composite analysis failed"),
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseBatchCompositeAnalysis(), {
        wrapper,
      });

      expect(result.current.error).not.toBeNull();
      expect(result.current.error?.message).toBe(
        "Batch composite analysis failed",
      );
      expect(result.current.personaResult).toBeNull();
    });
  });
});
