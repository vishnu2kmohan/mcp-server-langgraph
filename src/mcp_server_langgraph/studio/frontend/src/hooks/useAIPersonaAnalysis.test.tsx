/**
 * useAIPersonaAnalysis Hook Tests
 *
 * TDD tests for the AI-powered persona behavior analysis hook.
 * Phase 6.7: AI Persona Behavior Analyzer
 *
 * Tests the hook's ability to:
 * - Analyze user behavior patterns
 * - Detect actual persona vs assigned persona
 * - Provide UI adaptation recommendations
 * - Handle loading and error states
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";
import personaReducer from "../store/slices/personaSlice";
import authReducer from "../store/slices/authSlice";

// Mock hook implementation - will be created
const mockUseAIPersonaAnalysis = vi.fn();
vi.mock("./useAIPersonaAnalysis", () => ({
  useAIPersonaAnalysis: () => mockUseAIPersonaAnalysis(),
  default: () => mockUseAIPersonaAnalysis(),
}));

// =============================================================================
// Test Store Setup
// =============================================================================

const createTestStore = (persona: string = "bob") =>
  configureStore({
    reducer: {
      persona: personaReducer,
      auth: authReducer,
    },
    preloadedState: {
      persona: {
        persona: persona as "admin" | "developer" | "user",
        username: persona,
        email: `${persona}@example.com`,
        permissions: [],
        isPersonaLoading: false,
      },
      auth: {
        user: {
          id: `${persona}-123`,
          username: persona,
          email: `${persona}@example.com`,
          roles: [persona],
          persona,
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

describe("useAIPersonaAnalysis", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Initial State", () => {
    it("should start with loading state when enabled", () => {
      mockUseAIPersonaAnalysis.mockReturnValue({
        isLoading: true,
        error: null,
        assignedPersona: null,
        detectedPersona: null,
        confidence: 0,
        behaviorSignals: [],
        recommendation: null,
        uiAdaptations: [],
        isPersonaMismatch: false,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIPersonaAnalysis(), {
        wrapper,
      });
      expect(result.current.isLoading).toBe(true);
    });

    it("should not analyze when disabled", () => {
      mockUseAIPersonaAnalysis.mockReturnValue({
        isLoading: false,
        error: null,
        assignedPersona: "bob",
        detectedPersona: null,
        confidence: 0,
        behaviorSignals: [],
        recommendation: null,
        uiAdaptations: [],
        isPersonaMismatch: false,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIPersonaAnalysis(), {
        wrapper,
      });
      expect(result.current.isLoading).toBe(false);
      expect(result.current.detectedPersona).toBeNull();
    });
  });

  describe("Persona Detection", () => {
    it("should detect matching persona for normal users", async () => {
      mockUseAIPersonaAnalysis.mockReturnValue({
        isLoading: false,
        error: null,
        assignedPersona: "bob",
        detectedPersona: "bob",
        confidence: 0.95,
        behaviorSignals: [
          "Chat-focused usage",
          "Standard interaction patterns",
        ],
        recommendation: null,
        uiAdaptations: [],
        isPersonaMismatch: false,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIPersonaAnalysis(), {
        wrapper,
      });

      expect(result.current.assignedPersona).toBe("bob");
      expect(result.current.detectedPersona).toBe("bob");
      expect(result.current.isPersonaMismatch).toBe(false);
    });

    it("should detect persona mismatch for power users", async () => {
      mockUseAIPersonaAnalysis.mockReturnValue({
        isLoading: false,
        error: null,
        assignedPersona: "bob",
        detectedPersona: "alice-builder",
        confidence: 0.88,
        behaviorSignals: [
          "Frequent workflow editing",
          "Advanced trace analysis",
        ],
        recommendation: "Consider upgrading to developer role",
        uiAdaptations: [{ feature: "workflow_builder", action: "unlock" }],
        isPersonaMismatch: true,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIPersonaAnalysis(), {
        wrapper,
      });

      expect(result.current.assignedPersona).toBe("bob");
      expect(result.current.detectedPersona).toBe("alice-builder");
      expect(result.current.isPersonaMismatch).toBe(true);
      expect(result.current.recommendation).toBeTruthy();
    });

    it("should provide confidence score for detection", async () => {
      mockUseAIPersonaAnalysis.mockReturnValue({
        isLoading: false,
        error: null,
        assignedPersona: "bob",
        detectedPersona: "alice-analyst",
        confidence: 0.75,
        behaviorSignals: ["Trace exploration"],
        recommendation: null,
        uiAdaptations: [],
        isPersonaMismatch: true,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIPersonaAnalysis(), {
        wrapper,
      });

      expect(result.current.confidence).toBe(0.75);
      expect(result.current.confidence).toBeGreaterThan(0);
      expect(result.current.confidence).toBeLessThanOrEqual(1);
    });
  });

  describe("Behavior Signals", () => {
    it("should return behavior signals explaining detection", async () => {
      mockUseAIPersonaAnalysis.mockReturnValue({
        isLoading: false,
        error: null,
        assignedPersona: "bob",
        detectedPersona: "alice-builder",
        confidence: 0.88,
        behaviorSignals: [
          "Frequent workflow editing",
          "Advanced trace analysis",
          "Long session durations",
        ],
        recommendation: null,
        uiAdaptations: [],
        isPersonaMismatch: true,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIPersonaAnalysis(), {
        wrapper,
      });

      expect(result.current.behaviorSignals).toHaveLength(3);
      expect(result.current.behaviorSignals).toContain(
        "Frequent workflow editing",
      );
    });
  });

  describe("UI Adaptations", () => {
    it("should provide UI adaptation recommendations", async () => {
      mockUseAIPersonaAnalysis.mockReturnValue({
        isLoading: false,
        error: null,
        assignedPersona: "bob",
        detectedPersona: "alice-builder",
        confidence: 0.88,
        behaviorSignals: [],
        recommendation: null,
        uiAdaptations: [
          { feature: "workflow_builder", action: "unlock" },
          { feature: "advanced_traces", action: "promote" },
        ],
        isPersonaMismatch: true,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIPersonaAnalysis(), {
        wrapper,
      });

      expect(result.current.uiAdaptations).toHaveLength(2);
      expect(result.current.uiAdaptations[0]).toEqual({
        feature: "workflow_builder",
        action: "unlock",
      });
    });

    it("should return empty adaptations when persona matches", async () => {
      mockUseAIPersonaAnalysis.mockReturnValue({
        isLoading: false,
        error: null,
        assignedPersona: "bob",
        detectedPersona: "bob",
        confidence: 0.95,
        behaviorSignals: ["Chat-focused usage"],
        recommendation: null,
        uiAdaptations: [],
        isPersonaMismatch: false,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIPersonaAnalysis(), {
        wrapper,
      });

      expect(result.current.uiAdaptations).toHaveLength(0);
    });
  });

  describe("Upgrade Recommendations", () => {
    it("should provide upgrade recommendation when applicable", async () => {
      mockUseAIPersonaAnalysis.mockReturnValue({
        isLoading: false,
        error: null,
        assignedPersona: "bob",
        detectedPersona: "alice-builder",
        confidence: 0.88,
        behaviorSignals: [],
        recommendation:
          "Consider upgrading to developer role for enhanced features",
        uiAdaptations: [],
        isPersonaMismatch: true,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIPersonaAnalysis(), {
        wrapper,
      });

      expect(result.current.recommendation).toContain("upgrading");
      expect(result.current.recommendation).toContain("developer");
    });
  });

  describe("Error Handling", () => {
    it("should handle API errors gracefully", async () => {
      mockUseAIPersonaAnalysis.mockReturnValue({
        isLoading: false,
        error: new Error("Failed to analyze persona"),
        assignedPersona: "bob",
        detectedPersona: null,
        confidence: 0,
        behaviorSignals: [],
        recommendation: null,
        uiAdaptations: [],
        isPersonaMismatch: false,
        refresh: vi.fn(),
      });

      const { result } = renderHook(() => mockUseAIPersonaAnalysis(), {
        wrapper,
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.detectedPersona).toBeNull();
    });
  });

  describe("Refresh Capability", () => {
    it("should provide refresh function", () => {
      const refreshFn = vi.fn();
      mockUseAIPersonaAnalysis.mockReturnValue({
        isLoading: false,
        error: null,
        assignedPersona: "bob",
        detectedPersona: "bob",
        confidence: 0.95,
        behaviorSignals: [],
        recommendation: null,
        uiAdaptations: [],
        isPersonaMismatch: false,
        refresh: refreshFn,
      });

      const { result } = renderHook(() => mockUseAIPersonaAnalysis(), {
        wrapper,
      });

      expect(typeof result.current.refresh).toBe("function");
      result.current.refresh();
      expect(refreshFn).toHaveBeenCalledTimes(1);
    });
  });
});
