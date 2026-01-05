/**
 * Tests for ObservabilitySlice
 *
 * TDD tests for persistent observability filter state.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import observabilityReducer, {
  setStatusFilter,
  setSessionIdFilter,
  setUserIdFilter,
  setWorkflowIdFilter,
  setProjectIdFilter,
  setTimeRange,
  setActiveTab,
  setSelectedTraceId,
  resetFilters,
  selectStatusFilter,
  selectSessionIdFilter,
  selectUserIdFilter,
  selectWorkflowIdFilter,
  selectProjectIdFilter,
  selectTimeRange,
  selectActiveTab,
  selectSelectedTraceId,
  type ObservabilityState,
} from "./observabilitySlice";

describe("observabilitySlice", () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  const initialState: ObservabilityState = {
    statusFilter: "",
    sessionIdFilter: "",
    userIdFilter: "",
    workflowIdFilter: "",
    projectIdFilter: "",
    timeRange: "1h",
    activeTab: "agent-sessions",
    selectedTraceId: null,
    webSocketMetrics: {},
  };

  describe("reducers", () => {
    it("should return initial state", () => {
      expect(observabilityReducer(undefined, { type: "unknown" })).toEqual(
        initialState,
      );
    });

    it("should set status filter", () => {
      const state = observabilityReducer(
        initialState,
        setStatusFilter("error"),
      );
      expect(state.statusFilter).toBe("error");
    });

    it("should set session ID filter", () => {
      const state = observabilityReducer(
        initialState,
        setSessionIdFilter("session-123"),
      );
      expect(state.sessionIdFilter).toBe("session-123");
    });

    it("should set user ID filter", () => {
      const state = observabilityReducer(
        initialState,
        setUserIdFilter("user-456"),
      );
      expect(state.userIdFilter).toBe("user-456");
    });

    it("should set workflow ID filter", () => {
      const state = observabilityReducer(
        initialState,
        setWorkflowIdFilter("workflow-789"),
      );
      expect(state.workflowIdFilter).toBe("workflow-789");
    });

    it("should set project ID filter", () => {
      const state = observabilityReducer(
        initialState,
        setProjectIdFilter("project-abc"),
      );
      expect(state.projectIdFilter).toBe("project-abc");
    });

    it("should set time range", () => {
      const state = observabilityReducer(initialState, setTimeRange("24h"));
      expect(state.timeRange).toBe("24h");
    });

    it("should set active tab", () => {
      const state = observabilityReducer(initialState, setActiveTab("logs"));
      expect(state.activeTab).toBe("logs");
    });

    it("should set selected trace ID", () => {
      const state = observabilityReducer(
        initialState,
        setSelectedTraceId("trace-xyz"),
      );
      expect(state.selectedTraceId).toBe("trace-xyz");
    });

    it("should reset all filters", () => {
      const modifiedState: ObservabilityState = {
        statusFilter: "error",
        sessionIdFilter: "session-123",
        userIdFilter: "user-456",
        workflowIdFilter: "workflow-789",
        projectIdFilter: "project-abc",
        timeRange: "24h",
        activeTab: "logs",
        selectedTraceId: "trace-xyz",
      };

      const state = observabilityReducer(modifiedState, resetFilters());

      expect(state.statusFilter).toBe("");
      expect(state.sessionIdFilter).toBe("");
      expect(state.userIdFilter).toBe("");
      expect(state.workflowIdFilter).toBe("");
      expect(state.projectIdFilter).toBe("");
      // Note: timeRange and activeTab are NOT reset (intentional UX decision)
      expect(state.timeRange).toBe("24h");
      expect(state.activeTab).toBe("logs");
      expect(state.selectedTraceId).toBeNull();
    });
  });

  describe("selectors", () => {
    const rootState = {
      observability: {
        statusFilter: "success",
        sessionIdFilter: "session-sel",
        userIdFilter: "user-sel",
        workflowIdFilter: "workflow-sel",
        projectIdFilter: "project-sel",
        timeRange: "7d",
        activeTab: "metrics" as const,
        selectedTraceId: "trace-sel",
      },
    };

    it("should select status filter", () => {
      expect(selectStatusFilter(rootState)).toBe("success");
    });

    it("should select session ID filter", () => {
      expect(selectSessionIdFilter(rootState)).toBe("session-sel");
    });

    it("should select user ID filter", () => {
      expect(selectUserIdFilter(rootState)).toBe("user-sel");
    });

    it("should select workflow ID filter", () => {
      expect(selectWorkflowIdFilter(rootState)).toBe("workflow-sel");
    });

    it("should select project ID filter", () => {
      expect(selectProjectIdFilter(rootState)).toBe("project-sel");
    });

    it("should select time range", () => {
      expect(selectTimeRange(rootState)).toBe("7d");
    });

    it("should select active tab", () => {
      expect(selectActiveTab(rootState)).toBe("metrics");
    });

    it("should select selected trace ID", () => {
      expect(selectSelectedTraceId(rootState)).toBe("trace-sel");
    });
  });
});
