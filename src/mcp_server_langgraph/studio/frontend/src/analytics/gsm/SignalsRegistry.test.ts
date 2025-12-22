/**
 * SignalsRegistry Tests
 *
 * TDD - RED Phase: Tests written first to define expected behavior
 *
 * Tests the signals registry for tracking HEART metric signals.
 */

import { describe, it, expect, beforeEach } from "vitest";
import {
  getSignalById,
  getSignalsForGoal,
  getAllSignals,
  recordSignal,
  getSignalValues,
  clearSignals,
} from "./SignalsRegistry";

describe("SignalsRegistry", () => {
  beforeEach(() => {
    clearSignals();
  });

  describe("SIGNALS", () => {
    it("defines signals for happiness metrics", () => {
      const happinessSignals = getAllSignals().filter((s) =>
        s.id.startsWith("happiness_")
      );

      expect(happinessSignals.length).toBeGreaterThan(0);
      expect(happinessSignals.some((s) => s.id === "happiness_nps_score")).toBe(
        true
      );
      expect(
        happinessSignals.some((s) => s.id === "happiness_satisfaction_rating")
      ).toBe(true);
    });

    it("defines signals for engagement metrics", () => {
      const engagementSignals = getAllSignals().filter((s) =>
        s.id.startsWith("engagement_")
      );

      expect(engagementSignals.length).toBeGreaterThan(0);
      expect(
        engagementSignals.some((s) => s.id === "engagement_feature_click")
      ).toBe(true);
      expect(
        engagementSignals.some((s) => s.id === "engagement_session_duration")
      ).toBe(true);
    });

    it("defines signals for adoption metrics", () => {
      const adoptionSignals = getAllSignals().filter((s) =>
        s.id.startsWith("adoption_")
      );

      expect(adoptionSignals.length).toBeGreaterThan(0);
      expect(
        adoptionSignals.some((s) => s.id === "adoption_onboarding_complete")
      ).toBe(true);
      expect(
        adoptionSignals.some((s) => s.id === "adoption_feature_first_use")
      ).toBe(true);
    });

    it("defines signals for retention metrics", () => {
      const retentionSignals = getAllSignals().filter((s) =>
        s.id.startsWith("retention_")
      );

      expect(retentionSignals.length).toBeGreaterThan(0);
      expect(
        retentionSignals.some((s) => s.id === "retention_return_visit")
      ).toBe(true);
    });

    it("defines signals for task success metrics", () => {
      const taskSignals = getAllSignals().filter((s) =>
        s.id.startsWith("task_")
      );

      expect(taskSignals.length).toBeGreaterThan(0);
      expect(taskSignals.some((s) => s.id === "task_completed")).toBe(true);
      expect(taskSignals.some((s) => s.id === "task_failed")).toBe(true);
    });
  });

  describe("Signal interface", () => {
    it("each signal has required properties", () => {
      const allSignals = getAllSignals();

      allSignals.forEach((signal) => {
        expect(signal.id).toBeDefined();
        expect(signal.name).toBeDefined();
        expect(signal.description).toBeDefined();
        expect(signal.valueType).toBeDefined();
        expect(["number", "boolean", "string", "counter"]).toContain(
          signal.valueType
        );
      });
    });
  });

  describe("getSignalById", () => {
    it("returns signal by ID", () => {
      const signal = getSignalById("happiness_nps_score");

      expect(signal).toBeDefined();
      expect(signal?.id).toBe("happiness_nps_score");
      expect(signal?.valueType).toBe("number");
    });

    it("returns undefined for unknown ID", () => {
      const signal = getSignalById("unknown_signal");

      expect(signal).toBeUndefined();
    });
  });

  describe("getSignalsForGoal", () => {
    it("returns signals associated with a goal", () => {
      const signals = getSignalsForGoal("happiness_nps");

      expect(signals.length).toBeGreaterThan(0);
      expect(signals.some((s) => s.id === "happiness_nps_score")).toBe(true);
    });

    it("returns empty array for unknown goal", () => {
      const signals = getSignalsForGoal("unknown_goal");

      expect(signals).toEqual([]);
    });
  });

  describe("recordSignal", () => {
    it("records a numeric signal value", () => {
      recordSignal("happiness_nps_score", 9);

      const values = getSignalValues("happiness_nps_score");
      expect(values.length).toBe(1);
      expect(values[0].value).toBe(9);
    });

    it("records a boolean signal value", () => {
      recordSignal("adoption_onboarding_complete", true);

      const values = getSignalValues("adoption_onboarding_complete");
      expect(values.length).toBe(1);
      expect(values[0].value).toBe(true);
    });

    it("includes timestamp with each recorded value", () => {
      const before = Date.now();
      recordSignal("happiness_nps_score", 8);
      const after = Date.now();

      const values = getSignalValues("happiness_nps_score");
      expect(values[0].timestamp).toBeGreaterThanOrEqual(before);
      expect(values[0].timestamp).toBeLessThanOrEqual(after);
    });

    it("includes optional metadata", () => {
      recordSignal("engagement_feature_click", 1, {
        feature: "workflow_builder",
        action: "create_node",
      });

      const values = getSignalValues("engagement_feature_click");
      expect(values[0].metadata?.feature).toBe("workflow_builder");
      expect(values[0].metadata?.action).toBe("create_node");
    });

    it("accumulates multiple values for same signal", () => {
      recordSignal("happiness_nps_score", 7);
      recordSignal("happiness_nps_score", 8);
      recordSignal("happiness_nps_score", 9);

      const values = getSignalValues("happiness_nps_score");
      expect(values.length).toBe(3);
    });
  });

  describe("getSignalValues", () => {
    it("returns all recorded values for a signal", () => {
      recordSignal("happiness_nps_score", 9);
      recordSignal("happiness_nps_score", 8);

      const values = getSignalValues("happiness_nps_score");
      expect(values).toHaveLength(2);
    });

    it("returns empty array for signal with no values", () => {
      const values = getSignalValues("happiness_nps_score");

      expect(values).toEqual([]);
    });

    it("returns values in chronological order", () => {
      recordSignal("happiness_nps_score", 7);
      recordSignal("happiness_nps_score", 8);
      recordSignal("happiness_nps_score", 9);

      const values = getSignalValues("happiness_nps_score");
      expect(values[0].value).toBe(7);
      expect(values[1].value).toBe(8);
      expect(values[2].value).toBe(9);
    });

    it("can filter by time range", () => {
      const now = Date.now();
      recordSignal("happiness_nps_score", 7);

      const recentValues = getSignalValues("happiness_nps_score", {
        since: now - 1000,
      });
      expect(recentValues.length).toBe(1);

      const futureValues = getSignalValues("happiness_nps_score", {
        since: now + 1000,
      });
      expect(futureValues.length).toBe(0);
    });
  });

  describe("clearSignals", () => {
    it("removes all recorded signal values", () => {
      recordSignal("happiness_nps_score", 9);
      recordSignal("engagement_feature_click", 1);

      clearSignals();

      expect(getSignalValues("happiness_nps_score")).toEqual([]);
      expect(getSignalValues("engagement_feature_click")).toEqual([]);
    });

    it("can clear values for specific signal", () => {
      recordSignal("happiness_nps_score", 9);
      recordSignal("engagement_feature_click", 1);

      clearSignals("happiness_nps_score");

      expect(getSignalValues("happiness_nps_score")).toEqual([]);
      expect(getSignalValues("engagement_feature_click").length).toBe(1);
    });
  });
});
