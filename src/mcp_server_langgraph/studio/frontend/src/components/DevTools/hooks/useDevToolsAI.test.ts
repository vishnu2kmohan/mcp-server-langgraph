/**
 * useDevToolsAI Hook Tests
 *
 * TDD tests for AI-powered DevTools features.
 * Provides layout suggestions and insights based on context.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";

import { useDevToolsAI } from "./useDevToolsAI";
import type { DevToolsTabId } from "../../../store/slices/devToolsSlice";

// =============================================================================
// Mock Dependencies
// =============================================================================

const mockRefetch = vi.fn();
const mockGetResult = vi.fn();

vi.mock("../../../hooks/useStudioAI", () => ({
  useStudioAI: vi.fn(() => ({
    results: [],
    analyses: {},
    crossInsights: [],
    failedAnalyses: [],
    totalCost: "0",
    isLoading: false,
    error: null,
    refetch: mockRefetch,
    getResult: mockGetResult,
  })),
}));

// Get the mocked useStudioAI for updating in tests
import { useStudioAI } from "../../../hooks/useStudioAI";
const mockedUseStudioAI = vi.mocked(useStudioAI);

// =============================================================================
// Tests
// =============================================================================

describe("useDevToolsAI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockRefetch.mockClear();
    mockGetResult.mockReturnValue(undefined);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("initialization", () => {
    it("should return initial state", () => {
      const { result } = renderHook(() =>
        useDevToolsAI({
          context: "session",
          entityId: "session-123",
          userId: "user-1",
          enabled: true,
        })
      );

      expect(result.current.suggestedLayout).toBeNull();
      expect(result.current.confidence).toBe(0);
      expect(result.current.insights).toEqual([]);
      expect(result.current.isLoading).toBe(false);
    });

    it("should not fetch when disabled", () => {
      const { result } = renderHook(() =>
        useDevToolsAI({
          context: "session",
          entityId: "session-123",
          userId: "user-1",
          enabled: false,
        })
      );

      expect(result.current.suggestedLayout).toBeNull();
      expect(result.current.isLoading).toBe(false);
    });
  });

  describe("layout suggestions", () => {
    it("should process layout suggestions from results", async () => {
      // Setup mock to return layout data
      mockGetResult.mockReturnValue({
        success: true,
        data: {
          suggestedLayout: ["problems", "console", "network"] as DevToolsTabId[],
          insights: [],
          confidence: 0.9,
        },
      });

      mockedUseStudioAI.mockReturnValue({
        results: [{ task_type: "devtools_layout", success: true, data: {} }],
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        getResult: mockGetResult,
      });

      const { result } = renderHook(() =>
        useDevToolsAI({
          context: "session",
          entityId: "session-123",
          userId: "user-1",
          enabled: true,
        })
      );

      await waitFor(() => {
        expect(result.current.suggestedLayout).toEqual([
          "problems",
          "console",
          "network",
        ]);
      });
    });

    it("should return confidence score", async () => {
      mockGetResult.mockReturnValue({
        success: true,
        data: {
          suggestedLayout: ["problems"] as DevToolsTabId[],
          insights: [],
          confidence: 0.85,
        },
      });

      mockedUseStudioAI.mockReturnValue({
        results: [{ task_type: "devtools_layout", success: true, data: {} }],
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        getResult: mockGetResult,
      });

      const { result } = renderHook(() =>
        useDevToolsAI({
          context: "session",
          entityId: "session-123",
          userId: "user-1",
          enabled: true,
        })
      );

      await waitFor(() => {
        expect(result.current.confidence).toBe(0.85);
      });
    });

    it("should handle context-specific suggestions", async () => {
      mockGetResult.mockReturnValue({
        success: true,
        data: {
          suggestedLayout: ["agent-trace", "console"] as DevToolsTabId[],
          insights: [],
          confidence: 0.8,
        },
      });

      mockedUseStudioAI.mockReturnValue({
        results: [{ task_type: "devtools_layout", success: true, data: {} }],
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        getResult: mockGetResult,
      });

      const { result } = renderHook(() =>
        useDevToolsAI({
          context: "session",
          entityId: "session-123",
          userId: "user-1",
          enabled: true,
        })
      );

      await waitFor(() => {
        expect(result.current.suggestedLayout).toContain("agent-trace");
      });
    });
  });

  describe("insights", () => {
    it("should return AI insights", async () => {
      const mockInsights = [
        {
          id: "insight-1",
          type: "anomaly" as const,
          title: "High latency detected",
          description: "Node 3 took 500ms longer than average",
          severity: "medium" as const,
          confidence: 0.9,
          timestamp: Date.now(),
        },
      ];

      mockGetResult.mockReturnValue({
        success: true,
        data: {
          suggestedLayout: ["console"] as DevToolsTabId[],
          insights: mockInsights,
          confidence: 0.8,
        },
      });

      mockedUseStudioAI.mockReturnValue({
        results: [{ task_type: "devtools_layout", success: true, data: {} }],
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        getResult: mockGetResult,
      });

      const { result } = renderHook(() =>
        useDevToolsAI({
          context: "session",
          entityId: "session-123",
          userId: "user-1",
          enabled: true,
        })
      );

      await waitFor(() => {
        expect(result.current.insights).toHaveLength(1);
        expect(result.current.insights[0].title).toBe("High latency detected");
      });
    });
  });

  describe("error handling", () => {
    it("should handle errors from studioAI", async () => {
      const testError = new Error("AI service unavailable");

      mockedUseStudioAI.mockReturnValue({
        results: null,
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: false,
        error: testError,
        refetch: mockRefetch,
        getResult: mockGetResult,
      });

      const { result } = renderHook(() =>
        useDevToolsAI({
          context: "session",
          entityId: "session-123",
          userId: "user-1",
          enabled: true,
        })
      );

      await waitFor(() => {
        expect(result.current.error).toBe(testError);
      });
    });

    it("should show loading state", async () => {
      mockedUseStudioAI.mockReturnValue({
        results: null,
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: true,
        error: null,
        refetch: mockRefetch,
        getResult: mockGetResult,
      });

      const { result } = renderHook(() =>
        useDevToolsAI({
          context: "session",
          entityId: "session-123",
          userId: "user-1",
          enabled: true,
        })
      );

      expect(result.current.isLoading).toBe(true);
    });
  });

  describe("fetchSuggestions", () => {
    it("should call refetch when fetchSuggestions is called", () => {
      const { result } = renderHook(() =>
        useDevToolsAI({
          context: "session",
          entityId: "session-123",
          userId: "user-1",
          enabled: true,
        })
      );

      act(() => {
        result.current.fetchSuggestions();
      });

      expect(mockRefetch).toHaveBeenCalled();
    });

    it("should not call refetch when disabled", () => {
      const { result } = renderHook(() =>
        useDevToolsAI({
          context: "session",
          entityId: "session-123",
          userId: "user-1",
          enabled: false,
        })
      );

      act(() => {
        result.current.fetchSuggestions();
      });

      expect(mockRefetch).not.toHaveBeenCalled();
    });
  });

  describe("applyLayout", () => {
    it("should call onApplyLayout with suggested layout", async () => {
      const onApplyLayout = vi.fn();

      mockGetResult.mockReturnValue({
        success: true,
        data: {
          suggestedLayout: ["console", "problems"] as DevToolsTabId[],
          insights: [],
          confidence: 0.9,
        },
      });

      mockedUseStudioAI.mockReturnValue({
        results: [{ task_type: "devtools_layout", success: true, data: {} }],
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        getResult: mockGetResult,
      });

      const { result } = renderHook(() =>
        useDevToolsAI({
          context: "session",
          entityId: "session-123",
          userId: "user-1",
          enabled: true,
          onApplyLayout,
        })
      );

      // Wait for layout to be processed
      await waitFor(() => {
        expect(result.current.suggestedLayout).not.toBeNull();
      });

      act(() => {
        result.current.applyLayout();
      });

      expect(onApplyLayout).toHaveBeenCalledWith(["console", "problems"]);
    });

    it("should not call onApplyLayout when no suggested layout", () => {
      const onApplyLayout = vi.fn();

      const { result } = renderHook(() =>
        useDevToolsAI({
          context: "session",
          entityId: "session-123",
          userId: "user-1",
          enabled: true,
          onApplyLayout,
        })
      );

      act(() => {
        result.current.applyLayout();
      });

      expect(onApplyLayout).not.toHaveBeenCalled();
    });
  });

  describe("dismissInsight", () => {
    it("should remove insight from list", async () => {
      const mockInsights = [
        {
          id: "insight-1",
          type: "anomaly" as const,
          title: "Insight 1",
          description: "Description 1",
          severity: "medium" as const,
          confidence: 0.9,
          timestamp: Date.now(),
        },
        {
          id: "insight-2",
          type: "bottleneck" as const,
          title: "Insight 2",
          description: "Description 2",
          severity: "low" as const,
          confidence: 0.8,
          timestamp: Date.now(),
        },
      ];

      mockGetResult.mockReturnValue({
        success: true,
        data: {
          suggestedLayout: ["console"] as DevToolsTabId[],
          insights: mockInsights,
          confidence: 0.8,
        },
      });

      mockedUseStudioAI.mockReturnValue({
        results: [{ task_type: "devtools_layout", success: true, data: {} }],
        analyses: {},
        crossInsights: [],
        failedAnalyses: [],
        totalCost: "0",
        isLoading: false,
        error: null,
        refetch: mockRefetch,
        getResult: mockGetResult,
      });

      const { result } = renderHook(() =>
        useDevToolsAI({
          context: "session",
          entityId: "session-123",
          userId: "user-1",
          enabled: true,
        })
      );

      await waitFor(() => {
        expect(result.current.insights).toHaveLength(2);
      });

      act(() => {
        result.current.dismissInsight("insight-1");
      });

      expect(result.current.insights).toHaveLength(1);
      expect(result.current.insights[0].id).toBe("insight-2");
    });
  });
});
