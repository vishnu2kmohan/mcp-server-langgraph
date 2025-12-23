/**
 * GoalsDefinition Tests
 *
 * TDD - RED Phase: Tests written first to define expected behavior
 *
 * Tests the HEART goals definition for Goals-Signals-Metrics framework.
 */

import { describe, it, expect, afterEach, vi } from "vitest";
import {
  HEART_GOALS,
  getGoalsForDimension,
  getAllGoals,
  getGoalById,
  type HeartDimension,
} from "./GoalsDefinition";

afterEach(() => {
  vi.clearAllMocks();
});

describe("GoalsDefinition", () => {
  describe("HEART_GOALS", () => {
    it("defines goals for all 5 HEART dimensions", () => {
      const dimensions: HeartDimension[] = [
        "happiness",
        "engagement",
        "adoption",
        "retention",
        "task_success",
      ];

      dimensions.forEach((dim) => {
        expect(HEART_GOALS[dim]).toBeDefined();
        expect(HEART_GOALS[dim].length).toBeGreaterThan(0);
      });
    });

    it("each goal has required properties", () => {
      const allGoals = getAllGoals();

      allGoals.forEach((goal) => {
        expect(goal.id).toBeDefined();
        expect(goal.dimension).toBeDefined();
        expect(goal.description).toBeDefined();
        expect(goal.targetValue).toBeDefined();
        expect(goal.signals).toBeDefined();
        expect(goal.signals.length).toBeGreaterThan(0);
      });
    });
  });

  describe("Happiness goals", () => {
    it("includes NPS goal", () => {
      const goals = getGoalsForDimension("happiness");
      const npsGoal = goals.find((g) => g.id === "happiness_nps");

      expect(npsGoal).toBeDefined();
      expect(npsGoal?.description).toContain("NPS");
      expect(npsGoal?.targetValue).toBeGreaterThanOrEqual(50);
    });

    it("includes satisfaction goal", () => {
      const goals = getGoalsForDimension("happiness");
      const satGoal = goals.find((g) => g.id === "happiness_satisfaction");

      expect(satGoal).toBeDefined();
      expect(satGoal?.targetValue).toBeGreaterThanOrEqual(4);
    });
  });

  describe("Engagement goals", () => {
    it("includes DAU/MAU goal", () => {
      const goals = getGoalsForDimension("engagement");
      const dauMauGoal = goals.find((g) => g.id === "engagement_dau_mau");

      expect(dauMauGoal).toBeDefined();
      expect(dauMauGoal?.targetValue).toBeGreaterThan(0);
      expect(dauMauGoal?.targetValue).toBeLessThanOrEqual(1);
    });

    it("includes session duration goal", () => {
      const goals = getGoalsForDimension("engagement");
      const sessionGoal = goals.find(
        (g) => g.id === "engagement_session_duration",
      );

      expect(sessionGoal).toBeDefined();
      expect(sessionGoal?.targetValue).toBeGreaterThan(0);
    });

    it("includes actions per session goal", () => {
      const goals = getGoalsForDimension("engagement");
      const actionsGoal = goals.find(
        (g) => g.id === "engagement_actions_per_session",
      );

      expect(actionsGoal).toBeDefined();
    });
  });

  describe("Adoption goals", () => {
    it("includes onboarding completion goal", () => {
      const goals = getGoalsForDimension("adoption");
      const onboardingGoal = goals.find((g) => g.id === "adoption_onboarding");

      expect(onboardingGoal).toBeDefined();
      expect(onboardingGoal?.targetValue).toBeGreaterThan(0.5);
    });

    it("includes feature adoption goal", () => {
      const goals = getGoalsForDimension("adoption");
      const featureGoal = goals.find((g) => g.id === "adoption_feature");

      expect(featureGoal).toBeDefined();
    });
  });

  describe("Retention goals", () => {
    it("includes D1 retention goal", () => {
      const goals = getGoalsForDimension("retention");
      const d1Goal = goals.find((g) => g.id === "retention_d1");

      expect(d1Goal).toBeDefined();
      expect(d1Goal?.targetValue).toBeGreaterThan(0);
    });

    it("includes D7 retention goal", () => {
      const goals = getGoalsForDimension("retention");
      const d7Goal = goals.find((g) => g.id === "retention_d7");

      expect(d7Goal).toBeDefined();
    });

    it("includes D30 retention goal", () => {
      const goals = getGoalsForDimension("retention");
      const d30Goal = goals.find((g) => g.id === "retention_d30");

      expect(d30Goal).toBeDefined();
    });
  });

  describe("Task Success goals", () => {
    it("includes task completion rate goal", () => {
      const goals = getGoalsForDimension("task_success");
      const completionGoal = goals.find(
        (g) => g.id === "task_success_completion",
      );

      expect(completionGoal).toBeDefined();
      expect(completionGoal?.targetValue).toBeGreaterThan(0.8);
    });

    it("includes error rate goal", () => {
      const goals = getGoalsForDimension("task_success");
      const errorGoal = goals.find((g) => g.id === "task_success_error_rate");

      expect(errorGoal).toBeDefined();
      expect(errorGoal?.targetValue).toBeLessThan(0.1);
    });
  });

  describe("getGoalsForDimension", () => {
    it("returns only goals for specified dimension", () => {
      const happinessGoals = getGoalsForDimension("happiness");

      happinessGoals.forEach((goal) => {
        expect(goal.dimension).toBe("happiness");
      });
    });

    it("returns empty array for unknown dimension", () => {
      const goals = getGoalsForDimension("unknown" as HeartDimension);

      expect(goals).toEqual([]);
    });
  });

  describe("getAllGoals", () => {
    it("returns goals from all dimensions", () => {
      const allGoals = getAllGoals();
      const dimensions = new Set(allGoals.map((g) => g.dimension));

      expect(dimensions.size).toBe(5);
      expect(dimensions.has("happiness")).toBe(true);
      expect(dimensions.has("engagement")).toBe(true);
      expect(dimensions.has("adoption")).toBe(true);
      expect(dimensions.has("retention")).toBe(true);
      expect(dimensions.has("task_success")).toBe(true);
    });
  });

  describe("getGoalById", () => {
    it("returns goal by ID", () => {
      const goal = getGoalById("happiness_nps");

      expect(goal).toBeDefined();
      expect(goal?.id).toBe("happiness_nps");
    });

    it("returns undefined for unknown ID", () => {
      const goal = getGoalById("unknown_goal");

      expect(goal).toBeUndefined();
    });
  });

  describe("goal signals", () => {
    it("each signal has an ID", () => {
      const allGoals = getAllGoals();

      allGoals.forEach((goal) => {
        goal.signals.forEach((signal) => {
          expect(signal).toBeDefined();
          expect(typeof signal).toBe("string");
          expect(signal.length).toBeGreaterThan(0);
        });
      });
    });
  });
});
