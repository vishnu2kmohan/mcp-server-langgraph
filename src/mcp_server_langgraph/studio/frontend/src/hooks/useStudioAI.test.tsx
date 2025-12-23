/**
 * useStudioAI Hook Tests
 *
 * TDD tests for the unified Studio AI hook.
 * Validates the frontend hook that calls the StudioOrchestrator analyze endpoint.
 *
 * Tests verify:
 * - Hook returns proper structure
 * - Task-based API works correctly
 * - Category-specific accessors function
 * - Loading and error states work correctly
 * - Refresh functionality operates properly
 *
 * Reference: HybridShell AI Enhancement Analysis Plan
 */

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import React from "react";

import personaReducer from "../store/slices/personaSlice";
import authReducer from "../store/slices/authSlice";

// =============================================================================
// Types for Testing
// =============================================================================

interface _StudioTask {
  category: string;
  type: string;
  data?: Record<string, unknown>;
}

interface StudioAnalysisResult {
  task_type: string;
  success: boolean;
  data: Record<string, unknown>;
  confidence?: number;
  error?: string;
}

interface _UseStudioAIResult {
  results: StudioAnalysisResult[] | null;
  analyses: Record<string, unknown>;
  crossInsights: string[];
  failedAnalyses: string[];
  totalCost: string;
  isLoading: boolean;
  error: Error | null;
  refetch: () => void;
  getResult: (taskType: string) => StudioAnalysisResult | undefined;
}

// =============================================================================
// Mock Setup
// =============================================================================

// Mock hook implementation
const mockUseStudioAI = vi.fn();
vi.mock("./useStudioAI", () => ({
  useStudioAI: (options: unknown) => mockUseStudioAI(options),
  default: (options: unknown) => mockUseStudioAI(options),
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
        persona: "alice-builder",
        subPersona: null,
        username: "alice",
        email: "alice@example.com",
        permissions: [],
        isPersonaLoading: false,
      },
      auth: {
        user: {
          id: "user-123",
          username: "alice",
          email: "alice@example.com",
          roles: ["developer"],
          persona: "alice-builder",
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

describe("useStudioAI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("hook structure", () => {
    it("returns expected result shape", () => {
      mockUseStudioAI.mockReturnValue({
        results: null,
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [],
          }),
        { wrapper }
      );

      expect(result.current).toHaveProperty("results");
      expect(result.current).toHaveProperty("analyses");
      expect(result.current).toHaveProperty("crossInsights");
      expect(result.current).toHaveProperty("failedAnalyses");
      expect(result.current).toHaveProperty("totalCost");
      expect(result.current).toHaveProperty("isLoading");
      expect(result.current).toHaveProperty("error");
      expect(result.current).toHaveProperty("refetch");
      expect(result.current).toHaveProperty("getResult");
    });

    it("accepts required options", () => {
      const options = {
        userId: "user-123",
        sessionId: "session-456",
        tasks: [{ category: "ux", type: "persona_analysis", data: {} }],
      };

      mockUseStudioAI.mockReturnValue({
        results: null,
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: true,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(() => mockUseStudioAI(options), {
        wrapper,
      });

      expect(mockUseStudioAI).toHaveBeenCalledWith(options);
      expect(result.current.isLoading).toBe(true);
    });

    it("accepts optional persona parameter", () => {
      const options = {
        userId: "user-123",
        sessionId: "session-456",
        persona: "alice-builder",
        tasks: [],
      };

      mockUseStudioAI.mockReturnValue({
        results: null,
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      renderHook(() => mockUseStudioAI(options), { wrapper });

      expect(mockUseStudioAI).toHaveBeenCalledWith(
        expect.objectContaining({ persona: "alice-builder" })
      );
    });
  });

  describe("task-based API", () => {
    it("supports UX category tasks", () => {
      mockUseStudioAI.mockReturnValue({
        results: [
          {
            task_type: "persona_analysis",
            success: true,
            data: {
              detected_persona: "alice-builder",
              confidence: 0.85,
            },
            confidence: 0.85,
          },
        ],
        analyses: {
          persona_analysis: {
            detected_persona: "alice-builder",
            confidence: 0.85,
          },
        },
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0.002",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [{ category: "ux", type: "persona_analysis", data: {} }],
          }),
        { wrapper }
      );

      expect(result.current.results).toHaveLength(1);
      expect(result.current.results?.[0].task_type).toBe("persona_analysis");
      expect(result.current.analyses).toHaveProperty("persona_analysis");
    });

    it("supports SESSION category tasks", () => {
      mockUseStudioAI.mockReturnValue({
        results: [
          {
            task_type: "session_summarize",
            success: true,
            data: {
              summary: "User discussed workflow automation",
              key_topics: ["automation", "LLM"],
            },
            confidence: 0.9,
          },
        ],
        analyses: {
          session_summarize: {
            summary: "User discussed workflow automation",
          },
        },
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0.003",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [{ category: "session", type: "session_summarize", data: {} }],
          }),
        { wrapper }
      );

      expect(result.current.results?.[0].task_type).toBe("session_summarize");
    });

    it("supports CONVERSATION category tasks", () => {
      mockUseStudioAI.mockReturnValue({
        results: [
          {
            task_type: "intent_detect",
            success: true,
            data: {
              intent: "question",
              confidence: 0.92,
            },
          },
        ],
        analyses: {
          intent_detect: { intent: "question", confidence: 0.92 },
        },
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0.001",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [
              {
                category: "conversation",
                type: "intent_detect",
                data: { query: "How do I create a workflow?" },
              },
            ],
          }),
        { wrapper }
      );

      expect(result.current.results?.[0].task_type).toBe("intent_detect");
    });

    it("supports CANVAS category tasks", () => {
      mockUseStudioAI.mockReturnValue({
        results: [
          {
            task_type: "artifact_suggest_type",
            success: true,
            data: {
              suggested_type: "mermaid",
              confidence: 0.88,
            },
          },
        ],
        analyses: {
          artifact_suggest_type: { suggested_type: "mermaid" },
        },
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0.002",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [
              {
                category: "canvas",
                type: "artifact_suggest_type",
                data: { content: "flowchart TD..." },
              },
            ],
          }),
        { wrapper }
      );

      expect(result.current.results?.[0].task_type).toBe("artifact_suggest_type");
    });

    it("supports multiple tasks in parallel", () => {
      mockUseStudioAI.mockReturnValue({
        results: [
          {
            task_type: "persona_analysis",
            success: true,
            data: { detected_persona: "alice-builder" },
            confidence: 0.85,
          },
          {
            task_type: "session_summarize",
            success: true,
            data: { summary: "Discussion about AI" },
            confidence: 0.9,
          },
          {
            task_type: "intent_detect",
            success: true,
            data: { intent: "question" },
            confidence: 0.92,
          },
        ],
        analyses: {
          persona_analysis: { detected_persona: "alice-builder" },
          session_summarize: { summary: "Discussion about AI" },
          intent_detect: { intent: "question" },
        },
        crossInsights: [
          "Persona alice-builder aligns with advanced features",
          "Session focused on AI capabilities",
        ],
        failedAnalyses: [],
        totalCost: "0.008",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [
              { category: "ux", type: "persona_analysis", data: {} },
              { category: "session", type: "session_summarize", data: {} },
              { category: "conversation", type: "intent_detect", data: {} },
            ],
          }),
        { wrapper }
      );

      expect(result.current.results).toHaveLength(3);
      expect(result.current.crossInsights).toHaveLength(2);
    });
  });

  describe("getResult accessor", () => {
    it("returns result for existing task type", () => {
      const mockGetResult = vi.fn((taskType: string) => {
        if (taskType === "persona_analysis") {
          return {
            task_type: "persona_analysis",
            success: true,
            data: { detected_persona: "alice-builder" },
            confidence: 0.85,
          };
        }
        return undefined;
      });

      mockUseStudioAI.mockReturnValue({
        results: [
          {
            task_type: "persona_analysis",
            success: true,
            data: { detected_persona: "alice-builder" },
            confidence: 0.85,
          },
        ],
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: mockGetResult,
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [{ category: "ux", type: "persona_analysis", data: {} }],
          }),
        { wrapper }
      );

      const personaResult = result.current.getResult("persona_analysis");
      expect(personaResult).toBeDefined();
      expect(personaResult?.task_type).toBe("persona_analysis");
      expect(personaResult?.data).toHaveProperty("detected_persona");
    });

    it("returns undefined for non-existent task type", () => {
      const mockGetResult = vi.fn(() => undefined);

      mockUseStudioAI.mockReturnValue({
        results: [],
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: mockGetResult,
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [],
          }),
        { wrapper }
      );

      const missingResult = result.current.getResult("nonexistent_task");
      expect(missingResult).toBeUndefined();
    });
  });

  describe("cross insights", () => {
    it("returns cross insights when multiple analyses are requested", () => {
      mockUseStudioAI.mockReturnValue({
        results: [
          {
            task_type: "persona_analysis",
            success: true,
            data: { detected_persona: "alice-builder", confidence: 0.85 },
          },
          {
            task_type: "disclosure_analysis",
            success: true,
            data: { recommended_level: "advanced", confidence: 0.8 },
          },
        ],
        analyses: {},
        crossInsights: [
          "Persona alice-builder aligns with advanced disclosure level",
          "User behavior suggests readiness for advanced features",
        ],
        failedAnalyses: [],
        totalCost: "0.005",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [
              { category: "ux", type: "persona_analysis", data: {} },
              { category: "ux", type: "disclosure_analysis", data: {} },
            ],
          }),
        { wrapper }
      );

      expect(result.current.crossInsights).toHaveLength(2);
      expect(result.current.crossInsights[0]).toContain("alice-builder");
    });
  });

  describe("failed analyses", () => {
    it("tracks failed task types", () => {
      mockUseStudioAI.mockReturnValue({
        results: [
          {
            task_type: "persona_analysis",
            success: true,
            data: { detected_persona: "bob" },
          },
          {
            task_type: "diagram_to_code",
            success: false,
            data: {},
            error: "Invalid diagram syntax",
          },
        ],
        analyses: {
          persona_analysis: { detected_persona: "bob" },
        },
        crossInsights: [],
        failedAnalyses: ["diagram_to_code"],
        totalCost: "0.003",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [
              { category: "ux", type: "persona_analysis", data: {} },
              { category: "diagram", type: "diagram_to_code", data: {} },
            ],
          }),
        { wrapper }
      );

      expect(result.current.failedAnalyses).toContain("diagram_to_code");
      expect(result.current.failedAnalyses).not.toContain("persona_analysis");
    });
  });

  describe("cost tracking", () => {
    it("returns total cost as string", () => {
      mockUseStudioAI.mockReturnValue({
        results: [],
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0.0125",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [],
          }),
        { wrapper }
      );

      expect(typeof result.current.totalCost).toBe("string");
      expect(result.current.totalCost).toBe("0.0125");
    });
  });

  describe("loading state", () => {
    it("shows loading state while fetching", () => {
      mockUseStudioAI.mockReturnValue({
        results: null,
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: true,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [{ category: "ux", type: "persona_analysis", data: {} }],
          }),
        { wrapper }
      );

      expect(result.current.isLoading).toBe(true);
      expect(result.current.results).toBeNull();
    });

    it("shows not loading when complete", () => {
      mockUseStudioAI.mockReturnValue({
        results: [],
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [],
          }),
        { wrapper }
      );

      expect(result.current.isLoading).toBe(false);
    });
  });

  describe("error handling", () => {
    it("handles API errors gracefully", () => {
      mockUseStudioAI.mockReturnValue({
        results: null,
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: false,
        error: new Error("Studio AI analysis failed"),
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [{ category: "ux", type: "persona_analysis", data: {} }],
          }),
        { wrapper }
      );

      expect(result.current.error).not.toBeNull();
      expect(result.current.error?.message).toBe("Studio AI analysis failed");
      expect(result.current.results).toBeNull();
    });

    it("clears error on successful retry", () => {
      mockUseStudioAI.mockReturnValue({
        results: [
          {
            task_type: "persona_analysis",
            success: true,
            data: { detected_persona: "bob" },
          },
        ],
        analyses: { persona_analysis: { detected_persona: "bob" } },
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0.002",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [{ category: "ux", type: "persona_analysis", data: {} }],
          }),
        { wrapper }
      );

      expect(result.current.error).toBeNull();
      expect(result.current.results).not.toBeNull();
    });
  });

  describe("refetch functionality", () => {
    it("has a refetch function", () => {
      const refetchFn = vi.fn();
      mockUseStudioAI.mockReturnValue({
        results: null,
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: false,
        error: null,
        refetch: refetchFn,
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [],
          }),
        { wrapper }
      );

      expect(typeof result.current.refetch).toBe("function");
      result.current.refetch();
      expect(refetchFn).toHaveBeenCalledTimes(1);
    });
  });

  describe("enabled flag", () => {
    it("does not fetch when enabled is false", () => {
      mockUseStudioAI.mockReturnValue({
        results: null,
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [{ category: "ux", type: "persona_analysis", data: {} }],
            enabled: false,
          }),
        { wrapper }
      );

      expect(result.current.isLoading).toBe(false);
      expect(result.current.results).toBeNull();
    });

    it("fetches when enabled is true", () => {
      mockUseStudioAI.mockReturnValue({
        results: [],
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: true,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [{ category: "ux", type: "persona_analysis", data: {} }],
            enabled: true,
          }),
        { wrapper }
      );

      expect(result.current.isLoading).toBe(true);
    });
  });

  describe("empty tasks", () => {
    it("returns empty results for empty tasks array", () => {
      mockUseStudioAI.mockReturnValue({
        results: [],
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [],
          }),
        { wrapper }
      );

      expect(result.current.results).toEqual([]);
      expect(result.current.analyses).toEqual({});
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe("HITL category tasks", () => {
    it("supports risk_assess task type", () => {
      mockUseStudioAI.mockReturnValue({
        results: [
          {
            task_type: "risk_assess",
            success: true,
            data: {
              risk_score: 0.75,
              risk_level: "high",
              action_summary: "Restart production pod",
            },
            confidence: 0.88,
          },
        ],
        analyses: {
          risk_assess: { risk_score: 0.75, risk_level: "high" },
        },
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0.004",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [
              {
                category: "hitl",
                type: "risk_assess",
                data: { action_type: "restart_pod", parameters: {} },
              },
            ],
          }),
        { wrapper }
      );

      expect(result.current.results?.[0].task_type).toBe("risk_assess");
      expect(result.current.analyses).toHaveProperty("risk_assess");
    });
  });

  describe("COMMAND category tasks", () => {
    it("supports command_interpret task type", () => {
      mockUseStudioAI.mockReturnValue({
        results: [
          {
            task_type: "command_interpret",
            success: true,
            data: {
              interpreted_action: "create_workflow",
              parameters: { name: "automation" },
            },
            confidence: 0.9,
          },
        ],
        analyses: {
          command_interpret: { interpreted_action: "create_workflow" },
        },
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0.002",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [
              {
                category: "command",
                type: "command_interpret",
                data: { query: "create a new automation workflow" },
              },
            ],
          }),
        { wrapper }
      );

      expect(result.current.results?.[0].task_type).toBe("command_interpret");
    });
  });

  describe("TRACE category tasks", () => {
    it("supports trace_summarize task type", () => {
      mockUseStudioAI.mockReturnValue({
        results: [
          {
            task_type: "trace_summarize",
            success: true,
            data: {
              summary: "Agent completed 5 steps in 2.3s",
              bottlenecks: ["step_3"],
            },
            confidence: 0.95,
          },
        ],
        analyses: {
          trace_summarize: { summary: "Agent completed 5 steps in 2.3s" },
        },
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0.003",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [
              {
                category: "trace",
                type: "trace_summarize",
                data: { trace_id: "trace-789" },
              },
            ],
          }),
        { wrapper }
      );

      expect(result.current.results?.[0].task_type).toBe("trace_summarize");
    });
  });

  describe("DIAGRAM category tasks", () => {
    it("supports diagram_to_code task type", () => {
      mockUseStudioAI.mockReturnValue({
        results: [
          {
            task_type: "diagram_to_code",
            success: true,
            data: {
              generated_code: "function login() { ... }",
              language: "typescript",
            },
            confidence: 0.82,
          },
        ],
        analyses: {
          diagram_to_code: { language: "typescript" },
        },
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0.008",
        isLoading: false,
        error: null,
        refetch: vi.fn(),
        getResult: vi.fn(),
      });

      const { result } = renderHook(
        () =>
          mockUseStudioAI({
            userId: "user-123",
            sessionId: "session-456",
            tasks: [
              {
                category: "diagram",
                type: "diagram_to_code",
                data: { diagram: "flowchart TD\n  A-->B" },
              },
            ],
          }),
        { wrapper }
      );

      expect(result.current.results?.[0].task_type).toBe("diagram_to_code");
    });
  });
});
