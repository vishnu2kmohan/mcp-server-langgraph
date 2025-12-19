/**
 * ComplianceSlice Tests
 *
 * Phase 7: Integration - State Management
 */
import { describe, it, expect, beforeEach } from "vitest";
import complianceReducer, {
  setComplianceLoading,
  setFrameworkStatus,
  setAllFrameworkStatuses,
  setFrameworkError,
  resetCompliance,
  selectFrameworkStatus,
  selectOverallScore,
  type FrameworkStatus,
  type ComplianceState,
} from "./complianceSlice";

describe("complianceSlice", () => {
  const mockSOC2Status: FrameworkStatus = {
    framework: "SOC2",
    status: "compliant",
    score: 94,
    totalControls: 50,
    compliantControls: 47,
    lastAssessed: "2025-12-19T00:00:00Z",
  };

  let initialState: ComplianceState;

  beforeEach(() => {
    initialState = {
      frameworks: {
        SOC2: {
          framework: "SOC2",
          status: "loading",
          score: 0,
          totalControls: 0,
          compliantControls: 0,
          lastAssessed: null,
        },
        HIPAA: {
          framework: "HIPAA",
          status: "loading",
          score: 0,
          totalControls: 0,
          compliantControls: 0,
          lastAssessed: null,
        },
        GDPR: {
          framework: "GDPR",
          status: "loading",
          score: 0,
          totalControls: 0,
          compliantControls: 0,
          lastAssessed: null,
        },
        FEDRAMP: {
          framework: "FEDRAMP",
          status: "loading",
          score: 0,
          totalControls: 0,
          compliantControls: 0,
          lastAssessed: null,
        },
      },
      overallScore: 0,
      isLoading: false,
      lastRefresh: null,
    };
  });

  describe("setComplianceLoading", () => {
    it("sets loading state", () => {
      const state = complianceReducer(initialState, setComplianceLoading(true));
      expect(state.isLoading).toBe(true);
    });
  });

  describe("setFrameworkStatus", () => {
    it("updates framework status", () => {
      const state = complianceReducer(
        initialState,
        setFrameworkStatus(mockSOC2Status),
      );
      expect(state.frameworks.SOC2.status).toBe("compliant");
      expect(state.frameworks.SOC2.score).toBe(94);
    });

    it("recalculates overall score", () => {
      const state = complianceReducer(
        initialState,
        setFrameworkStatus(mockSOC2Status),
      );
      // (94 + 0 + 0 + 0) / 4 = 23.5 -> 24 (rounded)
      expect(state.overallScore).toBe(24);
    });
  });

  describe("setAllFrameworkStatuses", () => {
    it("updates multiple frameworks", () => {
      const statuses = {
        SOC2: mockSOC2Status,
        HIPAA: { ...mockSOC2Status, framework: "HIPAA" as const, score: 100 },
      };
      const state = complianceReducer(
        initialState,
        setAllFrameworkStatuses(statuses),
      );
      expect(state.frameworks.SOC2.score).toBe(94);
      expect(state.frameworks.HIPAA.score).toBe(100);
    });
  });

  describe("setFrameworkError", () => {
    it("sets error state", () => {
      const state = complianceReducer(
        initialState,
        setFrameworkError({ framework: "SOC2", error: "API error" }),
      );
      expect(state.frameworks.SOC2.status).toBe("error");
      expect(state.frameworks.SOC2.error).toBe("API error");
    });
  });

  describe("resetCompliance", () => {
    it("resets to initial state", () => {
      let state = complianceReducer(
        initialState,
        setFrameworkStatus(mockSOC2Status),
      );
      state = complianceReducer(state, resetCompliance());
      expect(state.frameworks.SOC2.status).toBe("loading");
    });
  });

  describe("Selectors", () => {
    const stateWithCompliance = {
      compliance: {
        frameworks: {
          SOC2: mockSOC2Status,
          HIPAA: { ...mockSOC2Status, framework: "HIPAA" as const, score: 100 },
          GDPR: { ...mockSOC2Status, framework: "GDPR" as const, score: 87 },
          FEDRAMP: {
            ...mockSOC2Status,
            framework: "FEDRAMP" as const,
            score: 92,
          },
        },
        overallScore: 93,
        isLoading: false,
        lastRefresh: "2025-12-19T00:00:00Z",
      },
    };

    it("selectFrameworkStatus returns framework", () => {
      const status = selectFrameworkStatus(stateWithCompliance, "SOC2");
      expect(status.score).toBe(94);
    });

    it("selectOverallScore returns score", () => {
      const score = selectOverallScore(stateWithCompliance);
      expect(score).toBe(93);
    });
  });
});
