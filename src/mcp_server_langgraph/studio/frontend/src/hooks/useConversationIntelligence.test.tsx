/**
 * Tests for useConversationIntelligence hooks.
 *
 * Sprint 3: Conversation Intelligence
 * - Intent detection classifies user intent before submit
 * - Context optimization suggests trimming when approaching token limit
 * - Goal tracking tracks session goals across messages
 *
 * TDD: Tests written FIRST before implementation.
 * NOTE: Consolidated tests to reduce memory footprint.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

// Mock the API module - single mock at top level to avoid memory leaks
vi.mock("../api", () => ({
  useStudioAnalyzeMutation: vi.fn(() => [
    vi.fn(() => ({
      unwrap: () =>
        Promise.resolve({
          analyses: {
            intent_detect: {
              intent: "code_request",
              confidence: 0.92,
              sub_intents: ["generate", "explain"],
            },
            context_optimize: {
              current_tokens: 120000,
              max_tokens: 128000,
              usage_percent: 93.75,
              suggestions: [
                {
                  type: "remove_old_messages",
                  description: "Remove messages older than 1 hour",
                  tokens_saved: 25000,
                },
              ],
              recommended_action: "remove_old_messages",
            },
            goal_track: {
              primary_goal: "Build a REST API",
              sub_goals: ["Implement auth", "Add endpoints"],
              progress_percent: 45,
              current_focus: "Implement auth",
              completed_sub_goals: [],
            },
          },
          cross_insights: [],
          failed_analyses: [],
          total_cost: "0.001",
        }),
    })),
    { isLoading: false },
  ]),
}));

// =============================================================================
// Test Utilities
// =============================================================================

const createTestStore = () =>
  configureStore({
    reducer: {
      test: (state = {}) => state,
    },
  });

interface WrapperProps {
  children: React.ReactNode;
}

const createWrapper = () => {
  const store = createTestStore();
  return function Wrapper({ children }: WrapperProps) {
    return <Provider store={store}>{children}</Provider>;
  };
};

// =============================================================================
// Consolidated Hook Tests (memory-optimized)
// =============================================================================

describe("Conversation Intelligence Hooks", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("useIntentDetection returns intent with confidence", async () => {
    const { useIntentDetection } =
      await import("./useConversationIntelligence");

    const { result } = renderHook(
      () =>
        useIntentDetection({
          userId: "test-user",
          sessionId: "session-123",
          query: "Write a Python function",
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.intent).toBe("code_request");
    expect(result.current.confidence).toBe(0.92);
    expect(typeof result.current.refetch).toBe("function");
  });

  it("useIntentDetection handles disabled state", async () => {
    const { useIntentDetection } =
      await import("./useConversationIntelligence");

    const { result } = renderHook(
      () =>
        useIntentDetection({
          userId: "test-user",
          sessionId: "session-123",
          query: "Test",
          enabled: false,
        }),
      { wrapper: createWrapper() },
    );

    expect(result.current.isLoading).toBe(false);
    expect(result.current.intent).toBeNull();
  });

  it("useContextOptimization returns suggestions and usage", async () => {
    const { useContextOptimization } =
      await import("./useConversationIntelligence");

    const { result } = renderHook(
      () =>
        useContextOptimization({
          userId: "test-user",
          sessionId: "session-123",
          currentTokens: 120000,
          maxTokens: 128000,
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.suggestions).toBeDefined();
    expect(result.current.usagePercent).toBe(93.75);
    expect(typeof result.current.refetch).toBe("function");
  });

  it("useGoalTracking returns goals and progress", async () => {
    const { useGoalTracking } = await import("./useConversationIntelligence");

    const { result } = renderHook(
      () =>
        useGoalTracking({
          userId: "test-user",
          sessionId: "session-123",
        }),
      { wrapper: createWrapper() },
    );

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.primaryGoal).toBe("Build a REST API");
    expect(result.current.subGoals).toEqual([
      "Implement auth",
      "Add endpoints",
    ]);
    expect(result.current.progressPercent).toBe(45);
    expect(typeof result.current.refetch).toBe("function");
  });
});
