/**
 * MetricsCalculator Tests
 *
 * TDD - RED Phase: Tests written first to define expected behavior
 *
 * Tests the metrics calculator that computes HEART metrics from signals.
 */

import { describe, it, expect, beforeEach } from "vitest";
import {
  calculateMetric,
  calculateGoalProgress,
  calculateDimensionScore,
  getMetricsSummary,
} from "./MetricsCalculator";
import { recordSignal, clearSignals } from "./SignalsRegistry";

describe("MetricsCalculator", () => {
  beforeEach(() => {
    clearSignals();
  });

  describe("calculateMetric", () => {
    describe("NPS calculation", () => {
      it("calculates NPS from promoters and detractors", () => {
        // Promoters (9-10): 3
        recordSignal("happiness_nps_score", 9);
        recordSignal("happiness_nps_score", 10);
        recordSignal("happiness_nps_score", 9);
        // Passives (7-8): 2
        recordSignal("happiness_nps_score", 7);
        recordSignal("happiness_nps_score", 8);
        // Detractors (0-6): 1
        recordSignal("happiness_nps_score", 5);

        const result = calculateMetric("nps");

        // NPS = (3/6 - 1/6) * 100 = 33.33...
        expect(result.value).toBeCloseTo(33.33, 1);
        expect(result.sampleSize).toBe(6);
      });

      it("returns null when no data", () => {
        const result = calculateMetric("nps");

        expect(result.value).toBeNull();
        expect(result.sampleSize).toBe(0);
      });
    });

    describe("satisfaction calculation", () => {
      it("calculates average satisfaction rating", () => {
        recordSignal("happiness_satisfaction_rating", 4);
        recordSignal("happiness_satisfaction_rating", 5);
        recordSignal("happiness_satisfaction_rating", 4);

        const result = calculateMetric("satisfaction");

        expect(result.value).toBeCloseTo(4.33, 2);
        expect(result.sampleSize).toBe(3);
      });
    });

    describe("session duration calculation", () => {
      it("calculates average session duration", () => {
        recordSignal("engagement_session_duration", 120000); // 2 min
        recordSignal("engagement_session_duration", 180000); // 3 min
        recordSignal("engagement_session_duration", 240000); // 4 min

        const result = calculateMetric("session_duration");

        expect(result.value).toBe(180000); // 3 min average
      });
    });

    describe("actions per session calculation", () => {
      it("calculates average actions per session", () => {
        recordSignal("engagement_actions_per_session", 10);
        recordSignal("engagement_actions_per_session", 15);
        recordSignal("engagement_actions_per_session", 20);

        const result = calculateMetric("actions_per_session");

        expect(result.value).toBe(15);
      });
    });

    describe("onboarding completion rate", () => {
      it("calculates completion rate", () => {
        recordSignal("adoption_onboarding_complete", true);
        recordSignal("adoption_onboarding_complete", true);
        recordSignal("adoption_onboarding_complete", false);
        recordSignal("adoption_onboarding_complete", true);

        const result = calculateMetric("onboarding_completion_rate");

        expect(result.value).toBe(0.75);
      });
    });

    describe("task success rate", () => {
      it("calculates task success rate", () => {
        recordSignal("task_completed", true);
        recordSignal("task_completed", true);
        recordSignal("task_completed", true);
        recordSignal("task_failed", true);

        const result = calculateMetric("task_success_rate");

        expect(result.value).toBe(0.75); // 3 successes / 4 total
      });
    });

    describe("error rate", () => {
      it("calculates error rate", () => {
        recordSignal("task_completed", true);
        recordSignal("task_completed", true);
        recordSignal("task_failed", true);

        const result = calculateMetric("error_rate");

        expect(result.value).toBeCloseTo(0.33, 2); // 1 failure / 3 total
      });
    });
  });

  describe("calculateGoalProgress", () => {
    it("calculates progress toward NPS goal", () => {
      // Record some NPS scores
      recordSignal("happiness_nps_score", 9);
      recordSignal("happiness_nps_score", 10);
      recordSignal("happiness_nps_score", 9);
      recordSignal("happiness_nps_score", 8);
      recordSignal("happiness_nps_score", 6);

      const progress = calculateGoalProgress("happiness_nps");

      expect(progress.goalId).toBe("happiness_nps");
      expect(progress.currentValue).toBeDefined();
      expect(progress.targetValue).toBeGreaterThan(0);
      expect(progress.progressPercent).toBeDefined();
      expect(progress.isAchieved).toBeDefined();
    });

    it("marks goal as achieved when target met", () => {
      // All promoters - NPS = 100
      recordSignal("happiness_nps_score", 10);
      recordSignal("happiness_nps_score", 9);
      recordSignal("happiness_nps_score", 10);

      const progress = calculateGoalProgress("happiness_nps");

      // NPS of 100 should exceed target
      expect(progress.currentValue).toBe(100);
      expect(progress.isAchieved).toBe(true);
    });

    it("returns null progress for unknown goal", () => {
      const progress = calculateGoalProgress("unknown_goal");

      expect(progress.currentValue).toBeNull();
      expect(progress.progressPercent).toBe(0);
    });
  });

  describe("calculateDimensionScore", () => {
    it("calculates happiness dimension score", () => {
      recordSignal("happiness_nps_score", 9);
      recordSignal("happiness_satisfaction_rating", 4);

      const score = calculateDimensionScore("happiness");

      expect(score.dimension).toBe("happiness");
      expect(score.overallScore).toBeDefined();
      expect(score.goalProgresses.length).toBeGreaterThan(0);
    });

    it("returns 0 score when no data", () => {
      const score = calculateDimensionScore("happiness");

      expect(score.overallScore).toBe(0);
      expect(score.hasData).toBe(false);
    });

    it("calculates engagement dimension score", () => {
      recordSignal("engagement_feature_click", 1);
      recordSignal("engagement_session_duration", 300000);

      const score = calculateDimensionScore("engagement");

      expect(score.dimension).toBe("engagement");
      expect(score.hasData).toBe(true);
    });
  });

  describe("getMetricsSummary", () => {
    it("returns summary for all dimensions", () => {
      // Add some data for each dimension
      recordSignal("happiness_nps_score", 9);
      recordSignal("engagement_feature_click", 1);
      recordSignal("adoption_onboarding_complete", true);
      recordSignal("retention_return_visit", true);
      recordSignal("task_completed", true);

      const summary = getMetricsSummary();

      expect(summary.dimensions).toHaveLength(5);
      expect(summary.dimensions.some((d) => d.dimension === "happiness")).toBe(
        true,
      );
      expect(summary.dimensions.some((d) => d.dimension === "engagement")).toBe(
        true,
      );
      expect(summary.dimensions.some((d) => d.dimension === "adoption")).toBe(
        true,
      );
      expect(summary.dimensions.some((d) => d.dimension === "retention")).toBe(
        true,
      );
      expect(
        summary.dimensions.some((d) => d.dimension === "task_success"),
      ).toBe(true);
    });

    it("includes overall health score", () => {
      recordSignal("happiness_nps_score", 9);
      recordSignal("task_completed", true);

      const summary = getMetricsSummary();

      expect(summary.overallHealthScore).toBeDefined();
      expect(summary.overallHealthScore).toBeGreaterThanOrEqual(0);
      expect(summary.overallHealthScore).toBeLessThanOrEqual(100);
    });

    it("includes timestamp", () => {
      const before = Date.now();
      const summary = getMetricsSummary();
      const after = Date.now();

      expect(summary.timestamp).toBeGreaterThanOrEqual(before);
      expect(summary.timestamp).toBeLessThanOrEqual(after);
    });

    it("includes data freshness info", () => {
      recordSignal("happiness_nps_score", 9);

      const summary = getMetricsSummary();

      expect(summary.dataPointCount).toBeGreaterThan(0);
      expect(summary.oldestDataPoint).toBeDefined();
      expect(summary.newestDataPoint).toBeDefined();
    });
  });

  describe("MetricResult interface", () => {
    it("includes confidence when enough data", () => {
      // Record many values for high confidence
      for (let i = 0; i < 30; i++) {
        recordSignal("happiness_nps_score", Math.floor(Math.random() * 11));
      }

      const result = calculateMetric("nps");

      expect(result.confidence).toBeDefined();
      expect(result.confidence).toBeGreaterThan(0);
    });

    it("includes low confidence with limited data", () => {
      recordSignal("happiness_nps_score", 9);

      const result = calculateMetric("nps");

      expect(result.confidence).toBeDefined();
      expect(result.confidence).toBeLessThan(0.5);
    });
  });
});
