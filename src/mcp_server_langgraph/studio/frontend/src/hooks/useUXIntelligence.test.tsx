/**
 * UX Intelligence Hooks Tests
 *
 * TDD: Tests written FIRST before implementation.
 * Sprint 6: UX Intelligence
 * - Nav prediction: Predict and reorder navigation items
 * - Contextual help: Show context-aware help content
 * - Learning path: Personalized learning recommendations
 *
 * These hooks integrate with the StudioOrchestrator via RTK Query.
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";

// Will implement these hooks
import {
  useNavPrediction,
  useContextualHelp,
  useLearningPath,
} from "./useUXIntelligence";

// Mock the API module
vi.mock("../api", () => ({
  useStudioAnalyzeMutation: vi.fn(() => [
    vi.fn(() => ({
      unwrap: () =>
        Promise.resolve({
          analyses: {
            nav_prediction: {
              predicted_items: [
                { id: "chat", score: 0.95, reason: "Most recently used" },
                { id: "agents", score: 0.75, reason: "Frequently accessed after chat" },
                { id: "observability", score: 0.60, reason: "Matches current workflow" },
              ],
              current_context: "debugging_session",
              confidence: 0.85,
            },
            contextual_help: {
              help_topics: [
                {
                  id: "agent-approval",
                  title: "How Agent Approvals Work",
                  summary: "Understand the HITL approval workflow",
                  relevance: 0.92,
                },
                {
                  id: "risk-assessment",
                  title: "Understanding Risk Scores",
                  summary: "Learn how risk is calculated",
                  relevance: 0.78,
                },
              ],
              quick_actions: [
                { label: "View pending approvals", action: "navigate:/admin" },
                { label: "Check audit log", action: "navigate:/audit" },
              ],
              suggested_reading: ["docs/hitl-workflow.md"],
            },
            learning_path: {
              current_level: "intermediate",
              progress_percentage: 65,
              next_steps: [
                {
                  id: "step-1",
                  title: "Configure custom agents",
                  description: "Learn to create and configure your own agents",
                  estimated_time_min: 15,
                  priority: "high",
                },
                {
                  id: "step-2",
                  title: "Set up monitoring alerts",
                  description: "Configure alerts for agent failures",
                  estimated_time_min: 10,
                  priority: "medium",
                },
              ],
              completed_items: ["basic-chat", "first-agent", "mcp-connections"],
              recommended_features: ["batch-approvals", "audit-export"],
            },
          },
          cross_insights: [],
          failed_analyses: [],
          total_cost: "0.002",
        }),
    })),
    { isLoading: false },
  ]),
}));

// Create test store
const createTestStore = () =>
  configureStore({
    reducer: {
      test: (state = {}) => state,
    },
  });

interface WrapperProps {
  children: ReactNode;
}

const Wrapper = ({ children }: WrapperProps) => {
  const store = createTestStore();
  return <Provider store={store}>{children}</Provider>;
};

// =============================================================================
// useNavPrediction Tests
// =============================================================================

describe("useNavPrediction", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("basic functionality", () => {
    it("returns predicted navigation items when enabled", async () => {
      const { result } = renderHook(
        () =>
          useNavPrediction({
            userId: "user-123",
            currentPage: "admin",
            recentPages: ["chat", "agents"],
            enabled: true,
          }),
        { wrapper: Wrapper }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.predictedItems).toHaveLength(3);
      expect(result.current.predictedItems[0]).toEqual({
        id: "chat",
        score: 0.95,
        reason: "Most recently used",
      });
    });

    it("returns context and confidence", async () => {
      const { result } = renderHook(
        () =>
          useNavPrediction({
            userId: "user-123",
            currentPage: "admin",
            recentPages: [],
            enabled: true,
          }),
        { wrapper: Wrapper }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.currentContext).toBe("debugging_session");
      expect(result.current.confidence).toBe(0.85);
    });
  });

  describe("disabled state", () => {
    it("returns empty values when disabled", async () => {
      const { result } = renderHook(
        () =>
          useNavPrediction({
            userId: "user-123",
            currentPage: "admin",
            recentPages: [],
            enabled: false,
          }),
        { wrapper: Wrapper }
      );

      expect(result.current.predictedItems).toEqual([]);
      expect(result.current.currentContext).toBeNull();
    });
  });
});

// =============================================================================
// useContextualHelp Tests
// =============================================================================

describe("useContextualHelp", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("basic functionality", () => {
    it("returns help topics when enabled", async () => {
      const { result } = renderHook(
        () =>
          useContextualHelp({
            userId: "user-123",
            currentPage: "admin",
            activeFeature: "agent-approvals",
            enabled: true,
          }),
        { wrapper: Wrapper }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.helpTopics).toHaveLength(2);
      expect(result.current.helpTopics[0]).toEqual({
        id: "agent-approval",
        title: "How Agent Approvals Work",
        summary: "Understand the HITL approval workflow",
        relevance: 0.92,
      });
    });

    it("returns quick actions", async () => {
      const { result } = renderHook(
        () =>
          useContextualHelp({
            userId: "user-123",
            currentPage: "admin",
            activeFeature: "agent-approvals",
            enabled: true,
          }),
        { wrapper: Wrapper }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.quickActions).toHaveLength(2);
      expect(result.current.quickActions[0].label).toBe("View pending approvals");
    });

    it("returns suggested reading", async () => {
      const { result } = renderHook(
        () =>
          useContextualHelp({
            userId: "user-123",
            currentPage: "admin",
            activeFeature: "agent-approvals",
            enabled: true,
          }),
        { wrapper: Wrapper }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.suggestedReading).toContain("docs/hitl-workflow.md");
    });
  });

  describe("disabled state", () => {
    it("returns empty values when disabled", async () => {
      const { result } = renderHook(
        () =>
          useContextualHelp({
            userId: "user-123",
            currentPage: "admin",
            activeFeature: "",
            enabled: false,
          }),
        { wrapper: Wrapper }
      );

      expect(result.current.helpTopics).toEqual([]);
      expect(result.current.quickActions).toEqual([]);
    });
  });
});

// =============================================================================
// useLearningPath Tests
// =============================================================================

describe("useLearningPath", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("basic functionality", () => {
    it("returns learning path when enabled", async () => {
      const { result } = renderHook(
        () =>
          useLearningPath({
            userId: "user-123",
            persona: "alice-builder",
            enabled: true,
          }),
        { wrapper: Wrapper }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.currentLevel).toBe("intermediate");
      expect(result.current.progressPercentage).toBe(65);
    });

    it("returns next steps with priorities", async () => {
      const { result } = renderHook(
        () =>
          useLearningPath({
            userId: "user-123",
            persona: "alice-builder",
            enabled: true,
          }),
        { wrapper: Wrapper }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.nextSteps).toHaveLength(2);
      expect(result.current.nextSteps[0]).toEqual({
        id: "step-1",
        title: "Configure custom agents",
        description: "Learn to create and configure your own agents",
        estimated_time_min: 15,
        priority: "high",
      });
    });

    it("returns completed items and recommendations", async () => {
      const { result } = renderHook(
        () =>
          useLearningPath({
            userId: "user-123",
            persona: "alice-builder",
            enabled: true,
          }),
        { wrapper: Wrapper }
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.completedItems).toContain("basic-chat");
      expect(result.current.recommendedFeatures).toContain("batch-approvals");
    });
  });

  describe("disabled state", () => {
    it("returns empty values when disabled", async () => {
      const { result } = renderHook(
        () =>
          useLearningPath({
            userId: "user-123",
            persona: "alice-builder",
            enabled: false,
          }),
        { wrapper: Wrapper }
      );

      expect(result.current.currentLevel).toBeNull();
      expect(result.current.nextSteps).toEqual([]);
    });
  });

  describe("error handling", () => {
    it("provides refetch function for retry", async () => {
      const { result } = renderHook(
        () =>
          useLearningPath({
            userId: "user-123",
            persona: "alice-builder",
            enabled: true,
          }),
        { wrapper: Wrapper }
      );

      expect(result.current.refetch).toBeDefined();
      expect(typeof result.current.refetch).toBe("function");
    });
  });
});
