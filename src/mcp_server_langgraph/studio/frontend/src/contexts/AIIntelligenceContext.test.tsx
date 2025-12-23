/**
 * AIIntelligenceContext Tests
 *
 * TDD: Tests written FIRST before implementation.
 * Provides unified context for AI Intelligence feature flags and configuration.
 *
 * Features:
 * - Centralized AI feature flag management
 * - User context propagation
 * - Cache configuration
 * - WebSocket connection state
 * - Error boundary integration
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import { render, screen, renderHook, cleanup } from "@testing-library/react";
import type { ReactNode } from "react";
import {
  AIIntelligenceProvider,
  useAIIntelligence,
  type AIIntelligenceConfig,
} from "./AIIntelligenceContext";

// =============================================================================
// Test Utilities
// =============================================================================

function createWrapper(config?: Partial<AIIntelligenceConfig>) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <AIIntelligenceProvider config={config}>
        {children}
      </AIIntelligenceProvider>
    );
  };
}

// =============================================================================
// Tests
// =============================================================================

describe("AIIntelligenceContext", () => {
  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("Provider", () => {
    it("should render children", () => {
      render(
        <AIIntelligenceProvider>
          <div data-testid="child">Test Child</div>
        </AIIntelligenceProvider>,
      );

      expect(screen.getByTestId("child")).toBeInTheDocument();
    });

    it("should accept configuration props", () => {
      const config: AIIntelligenceConfig = {
        enabled: true,
        userId: "user-123",
        features: {
          navPrediction: true,
          contextualHelp: true,
          learningPath: false,
          riskAssessment: true,
          decisionHistory: true,
        },
      };

      render(
        <AIIntelligenceProvider config={config}>
          <div>Test</div>
        </AIIntelligenceProvider>,
      );

      // Should render without errors
      expect(screen.getByText("Test")).toBeInTheDocument();
    });
  });

  describe("useAIIntelligence hook", () => {
    it("should return default values when no provider", () => {
      // Hook should work without provider (returns disabled defaults)
      const { result } = renderHook(() => useAIIntelligence());

      expect(result.current.enabled).toBe(false);
      expect(result.current.userId).toBe("");
    });

    it("should return enabled state from provider", () => {
      const { result } = renderHook(() => useAIIntelligence(), {
        wrapper: createWrapper({ enabled: true }),
      });

      expect(result.current.enabled).toBe(true);
    });

    it("should return disabled state from provider", () => {
      const { result } = renderHook(() => useAIIntelligence(), {
        wrapper: createWrapper({ enabled: false }),
      });

      expect(result.current.enabled).toBe(false);
    });

    it("should return userId from provider", () => {
      const { result } = renderHook(() => useAIIntelligence(), {
        wrapper: createWrapper({ userId: "test-user-456" }),
      });

      expect(result.current.userId).toBe("test-user-456");
    });

    it("should return feature flags from provider", () => {
      const { result } = renderHook(() => useAIIntelligence(), {
        wrapper: createWrapper({
          features: {
            navPrediction: true,
            contextualHelp: false,
            learningPath: true,
            riskAssessment: true,
            decisionHistory: false,
          },
        }),
      });

      expect(result.current.features.navPrediction).toBe(true);
      expect(result.current.features.contextualHelp).toBe(false);
      expect(result.current.features.learningPath).toBe(true);
    });
  });

  describe("feature-specific helpers", () => {
    it("should provide isNavPredictionEnabled helper", () => {
      const { result } = renderHook(() => useAIIntelligence(), {
        wrapper: createWrapper({
          enabled: true,
          features: { navPrediction: true },
        }),
      });

      expect(result.current.isNavPredictionEnabled).toBe(true);
    });

    it("should return false for feature when globally disabled", () => {
      const { result } = renderHook(() => useAIIntelligence(), {
        wrapper: createWrapper({
          enabled: false, // Globally disabled
          features: { navPrediction: true }, // Feature enabled
        }),
      });

      // Should be false because global is disabled
      expect(result.current.isNavPredictionEnabled).toBe(false);
    });

    it("should provide isContextualHelpEnabled helper", () => {
      const { result } = renderHook(() => useAIIntelligence(), {
        wrapper: createWrapper({
          enabled: true,
          features: { contextualHelp: true },
        }),
      });

      expect(result.current.isContextualHelpEnabled).toBe(true);
    });

    it("should provide isLearningPathEnabled helper", () => {
      const { result } = renderHook(() => useAIIntelligence(), {
        wrapper: createWrapper({
          enabled: true,
          features: { learningPath: true },
        }),
      });

      expect(result.current.isLearningPathEnabled).toBe(true);
    });

    it("should provide isRiskAssessmentEnabled helper", () => {
      const { result } = renderHook(() => useAIIntelligence(), {
        wrapper: createWrapper({
          enabled: true,
          features: { riskAssessment: true },
        }),
      });

      expect(result.current.isRiskAssessmentEnabled).toBe(true);
    });

    it("should provide isDecisionHistoryEnabled helper", () => {
      const { result } = renderHook(() => useAIIntelligence(), {
        wrapper: createWrapper({
          enabled: true,
          features: { decisionHistory: true },
        }),
      });

      expect(result.current.isDecisionHistoryEnabled).toBe(true);
    });
  });

  describe("cache configuration", () => {
    it("should provide default cache stale times", () => {
      const { result } = renderHook(() => useAIIntelligence(), {
        wrapper: createWrapper({ enabled: true }),
      });

      expect(result.current.cacheConfig.navPredictionStaleTime).toBeDefined();
      expect(result.current.cacheConfig.contextualHelpStaleTime).toBeDefined();
      expect(result.current.cacheConfig.learningPathStaleTime).toBeDefined();
    });

    it("should allow custom cache stale times", () => {
      const { result } = renderHook(() => useAIIntelligence(), {
        wrapper: createWrapper({
          enabled: true,
          cacheConfig: {
            navPredictionStaleTime: 10 * 60 * 1000, // 10 minutes
          },
        }),
      });

      expect(result.current.cacheConfig.navPredictionStaleTime).toBe(
        10 * 60 * 1000,
      );
    });
  });

  describe("WebSocket configuration", () => {
    it("should indicate WebSocket availability", () => {
      const { result } = renderHook(() => useAIIntelligence(), {
        wrapper: createWrapper({
          enabled: true,
          webSocket: { enabled: true },
        }),
      });

      expect(result.current.webSocket.enabled).toBe(true);
    });

    it("should default WebSocket to disabled", () => {
      const { result } = renderHook(() => useAIIntelligence(), {
        wrapper: createWrapper({ enabled: true }),
      });

      expect(result.current.webSocket.enabled).toBe(false);
    });
  });

  describe("error handling", () => {
    it("should track global AI error state", () => {
      const { result } = renderHook(() => useAIIntelligence(), {
        wrapper: createWrapper({ enabled: true }),
      });

      expect(result.current.hasError).toBe(false);
      expect(result.current.error).toBeNull();
    });

    it("should provide reportError function", () => {
      const { result } = renderHook(() => useAIIntelligence(), {
        wrapper: createWrapper({ enabled: true }),
      });

      expect(typeof result.current.reportError).toBe("function");
    });
  });

  describe("persona integration", () => {
    it("should accept persona for context", () => {
      const { result } = renderHook(() => useAIIntelligence(), {
        wrapper: createWrapper({
          enabled: true,
          userId: "user-123",
          persona: "alice-builder",
        }),
      });

      expect(result.current.persona).toBe("alice-builder");
    });
  });
});
