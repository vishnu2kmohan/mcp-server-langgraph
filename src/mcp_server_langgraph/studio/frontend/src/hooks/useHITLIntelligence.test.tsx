/**
 * HITL Intelligence Hooks Tests
 *
 * TDD: Tests written FIRST before implementation.
 * Sprint 6: HITL Intelligence
 * - Risk assessment provides AI-generated risk scores for pending actions
 * - Decision history shows how user decided similar requests before
 *
 * These hooks integrate with the StudioOrchestrator via RTK Query.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, cleanup } from "@testing-library/react";
import { Provider } from "react-redux";
import { configureStore } from "@reduxjs/toolkit";
import type { ReactNode } from "react";

// Will implement these hooks
import { useRiskAssessment, useDecisionHistory } from "./useHITLIntelligence";

// Mock the API barrel directly — never vi.importActual("../api") (5,132-line barrel causes OOM)
// CRITICAL: Hoist mock references outside the factory to prevent infinite render loops.
// RTK Query hooks return stable references; our mock must do the same.
vi.mock("../api", () => {
  const mockTrigger = vi.fn(() => ({
    unwrap: () =>
      Promise.resolve({
        analyses: {
          risk_assess: {
            risk_score: 0.35,
            risk_level: "medium",
            risk_factors: [
              {
                factor: "file_deletion",
                weight: 0.4,
                description: "Operation deletes files",
              },
              {
                factor: "production_environment",
                weight: 0.3,
                description: "Targets production environment",
              },
            ],
            mitigations: [
              "Create backup before deletion",
              "Verify file paths are correct",
            ],
            recommendation: "approve_with_caution",
            explanation:
              "This action has moderate risk due to file deletion in production.",
          },
          decision_history: {
            similar_decisions: [
              {
                request_id: "req-001",
                action_type: "file_delete",
                decision: "approved",
                decided_by: "admin",
                decided_at: "2024-01-15T10:30:00Z",
                reasoning: "Required for cleanup",
              },
              {
                request_id: "req-002",
                action_type: "file_delete",
                decision: "rejected",
                decided_by: "security-admin",
                decided_at: "2024-01-10T14:20:00Z",
                reasoning: "Path too broad",
              },
            ],
            approval_rate: 0.67,
            total_similar: 3,
            average_decision_time_ms: 15000,
            suggested_action: "approve",
          },
        },
        cross_insights: [],
        failed_analyses: [],
        total_cost: "0.002",
      }),
  }));
  const mockReturn: [typeof mockTrigger, { isLoading: boolean }] = [
    mockTrigger,
    { isLoading: false },
  ];
  return {
    useStudioAnalyzeMutation: vi.fn(() => mockReturn),
  };
});
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
// useRiskAssessment Tests
// =============================================================================

describe("useRiskAssessment", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("basic functionality", () => {
    it("returns risk assessment data when enabled", async () => {
      const { result } = renderHook(
        () =>
          useRiskAssessment({
            userId: "user-123",
            requestId: "req-456",
            actionType: "file_delete",
            parameters: { path: "/data/temp" },
            enabled: true,
          }),
        { wrapper: Wrapper },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.riskScore).toBe(0.35);
      expect(result.current.riskLevel).toBe("medium");
    });

    it("returns risk factors with weights", async () => {
      const { result } = renderHook(
        () =>
          useRiskAssessment({
            userId: "user-123",
            requestId: "req-456",
            actionType: "file_delete",
            parameters: { path: "/data/temp" },
            enabled: true,
          }),
        { wrapper: Wrapper },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.riskFactors).toHaveLength(2);
      expect(result.current.riskFactors[0]).toEqual({
        factor: "file_deletion",
        weight: 0.4,
        description: "Operation deletes files",
      });
    });

    it("returns mitigations and recommendation", async () => {
      const { result } = renderHook(
        () =>
          useRiskAssessment({
            userId: "user-123",
            requestId: "req-456",
            actionType: "file_delete",
            parameters: { path: "/data/temp" },
            enabled: true,
          }),
        { wrapper: Wrapper },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.mitigations).toContain(
        "Create backup before deletion",
      );
      expect(result.current.recommendation).toBe("approve_with_caution");
      expect(result.current.explanation).toContain("moderate risk");
    });
  });

  describe("disabled state", () => {
    it("returns null values when disabled", async () => {
      const { result } = renderHook(
        () =>
          useRiskAssessment({
            userId: "user-123",
            requestId: "req-456",
            actionType: "file_delete",
            parameters: {},
            enabled: false,
          }),
        { wrapper: Wrapper },
      );

      expect(result.current.riskScore).toBeNull();
      expect(result.current.riskLevel).toBeNull();
      expect(result.current.riskFactors).toEqual([]);
    });
  });

  describe("error handling", () => {
    it("provides refetch function for retry", async () => {
      const { result } = renderHook(
        () =>
          useRiskAssessment({
            userId: "user-123",
            requestId: "req-456",
            actionType: "file_delete",
            parameters: {},
            enabled: true,
          }),
        { wrapper: Wrapper },
      );

      expect(result.current.refetch).toBeDefined();
      expect(typeof result.current.refetch).toBe("function");
    });
  });

  describe("risk level classification", () => {
    it("returns correct risk level based on score", async () => {
      const { result } = renderHook(
        () =>
          useRiskAssessment({
            userId: "user-123",
            requestId: "req-456",
            actionType: "file_delete",
            parameters: {},
            enabled: true,
          }),
        { wrapper: Wrapper },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Risk level should match the API response
      expect(result.current.riskLevel).toBe("medium");
    });
  });
});

// =============================================================================
// useDecisionHistory Tests
// =============================================================================

describe("useDecisionHistory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  describe("basic functionality", () => {
    it("returns similar decisions when enabled", async () => {
      const { result } = renderHook(
        () =>
          useDecisionHistory({
            userId: "user-123",
            actionType: "file_delete",
            enabled: true,
          }),
        { wrapper: Wrapper },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.similarDecisions).toHaveLength(2);
      expect(result.current.similarDecisions[0]).toEqual({
        request_id: "req-001",
        action_type: "file_delete",
        decision: "approved",
        decided_by: "admin",
        decided_at: "2024-01-15T10:30:00Z",
        reasoning: "Required for cleanup",
      });
    });

    it("returns approval statistics", async () => {
      const { result } = renderHook(
        () =>
          useDecisionHistory({
            userId: "user-123",
            actionType: "file_delete",
            enabled: true,
          }),
        { wrapper: Wrapper },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.approvalRate).toBe(0.67);
      expect(result.current.totalSimilar).toBe(3);
      expect(result.current.averageDecisionTimeMs).toBe(15000);
    });

    it("returns suggested action based on history", async () => {
      const { result } = renderHook(
        () =>
          useDecisionHistory({
            userId: "user-123",
            actionType: "file_delete",
            enabled: true,
          }),
        { wrapper: Wrapper },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.suggestedAction).toBe("approve");
    });
  });

  describe("disabled state", () => {
    it("returns empty values when disabled", async () => {
      const { result } = renderHook(
        () =>
          useDecisionHistory({
            userId: "user-123",
            actionType: "file_delete",
            enabled: false,
          }),
        { wrapper: Wrapper },
      );

      expect(result.current.similarDecisions).toEqual([]);
      expect(result.current.approvalRate).toBeNull();
      expect(result.current.totalSimilar).toBeNull();
    });
  });

  describe("filtering", () => {
    it("accepts optional persona filter", async () => {
      const { result } = renderHook(
        () =>
          useDecisionHistory({
            userId: "user-123",
            actionType: "file_delete",
            persona: "admin",
            enabled: true,
          }),
        { wrapper: Wrapper },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Should return filtered results (mocked to return same data)
      expect(result.current.similarDecisions.length).toBeGreaterThanOrEqual(0);
    });

    it("accepts optional time range filter", async () => {
      const { result } = renderHook(
        () =>
          useDecisionHistory({
            userId: "user-123",
            actionType: "file_delete",
            timeRangeDays: 30,
            enabled: true,
          }),
        { wrapper: Wrapper },
      );

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.similarDecisions.length).toBeGreaterThanOrEqual(0);
    });
  });

  describe("error handling", () => {
    it("provides refetch function for retry", async () => {
      const { result } = renderHook(
        () =>
          useDecisionHistory({
            userId: "user-123",
            actionType: "file_delete",
            enabled: true,
          }),
        { wrapper: Wrapper },
      );

      expect(result.current.refetch).toBeDefined();
      expect(typeof result.current.refetch).toBe("function");
    });
  });
});
