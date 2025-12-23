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
  selectAllFrameworks,
  selectComplianceLoading,
  selectLastRefresh,
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

    it("skips undefined statuses in partial update", () => {
      // Test the branch where status is undefined/falsy
      const statuses: Partial<
        Record<
          "SOC2" | "HIPAA" | "GDPR" | "FEDRAMP",
          FrameworkStatus | undefined
        >
      > = {
        SOC2: mockSOC2Status,
        HIPAA: undefined, // This should be skipped
      };
      const state = complianceReducer(
        initialState,
        setAllFrameworkStatuses(
          statuses as Parameters<typeof setAllFrameworkStatuses>[0],
        ),
      );
      expect(state.frameworks.SOC2.score).toBe(94);
      // HIPAA should remain unchanged (original loading state)
      expect(state.frameworks.HIPAA.status).toBe("loading");
      expect(state.frameworks.HIPAA.score).toBe(0);
    });

    it("sets lastRefresh timestamp after update", () => {
      const statuses = {
        SOC2: mockSOC2Status,
      };
      const state = complianceReducer(
        initialState,
        setAllFrameworkStatuses(statuses),
      );
      expect(state.lastRefresh).not.toBeNull();
      expect(new Date(state.lastRefresh!).getTime()).toBeLessThanOrEqual(
        Date.now(),
      );
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

    it("selectAllFrameworks returns array of all frameworks", () => {
      const frameworks = selectAllFrameworks(stateWithCompliance);
      expect(Array.isArray(frameworks)).toBe(true);
      expect(frameworks).toHaveLength(4);
      expect(frameworks.map((f) => f.framework)).toEqual(
        expect.arrayContaining(["SOC2", "HIPAA", "GDPR", "FEDRAMP"]),
      );
    });

    it("selectComplianceLoading returns loading state", () => {
      const isLoading = selectComplianceLoading(stateWithCompliance);
      expect(isLoading).toBe(false);
    });

    it("selectComplianceLoading returns true when loading", () => {
      const loadingState = {
        compliance: {
          ...stateWithCompliance.compliance,
          isLoading: true,
        },
      };
      const isLoading = selectComplianceLoading(loadingState);
      expect(isLoading).toBe(true);
    });

    it("selectLastRefresh returns last refresh timestamp", () => {
      const lastRefresh = selectLastRefresh(stateWithCompliance);
      expect(lastRefresh).toBe("2025-12-19T00:00:00Z");
    });

    it("selectLastRefresh returns null when never refreshed", () => {
      const neverRefreshed = {
        compliance: {
          ...stateWithCompliance.compliance,
          lastRefresh: null,
        },
      };
      const lastRefresh = selectLastRefresh(neverRefreshed);
      expect(lastRefresh).toBeNull();
    });
  });
});
