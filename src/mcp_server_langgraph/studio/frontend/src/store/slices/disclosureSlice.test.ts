/**
 * Disclosure Slice Tests
 *
 * TDD - RED Phase: Tests written first to define expected behavior
 *
 * Tests the Redux slice for progressive disclosure state management.
 * Implements 4 disclosure levels: beginner, intermediate, advanced, expert
 */

import { describe, it, expect } from "vitest";
import disclosureReducer, {
  initialState,
  setDisclosureLevel,
  setAutoDetect,
  incrementFeatureUsage,
  recordAction,
  resetDisclosureState,
  selectDisclosureLevel,
  selectAutoDetect,
  selectFeatureUsageCount,
  selectShouldShowAdvancedFeature,
  selectLevelProgress,
  DisclosureLevel,
  type DisclosureState,
} from "./disclosureSlice";

describe("disclosureSlice", () => {
  describe("initial state", () => {
    it("should have beginner as default level", () => {
      expect(initialState.level).toBe("beginner");
    });

    it("should have autoDetect enabled by default", () => {
      expect(initialState.autoDetect).toBe(true);
    });

    it("should have zero feature usage counts", () => {
      expect(initialState.featureUsageCount).toBe(0);
    });

    it("should have empty actions history", () => {
      expect(initialState.actionsHistory).toEqual([]);
    });
  });

  describe("setDisclosureLevel", () => {
    it("should set level to beginner", () => {
      const state = disclosureReducer(
        initialState,
        setDisclosureLevel("beginner"),
      );
      expect(state.level).toBe("beginner");
    });

    it("should set level to intermediate", () => {
      const state = disclosureReducer(
        initialState,
        setDisclosureLevel("intermediate"),
      );
      expect(state.level).toBe("intermediate");
    });

    it("should set level to advanced", () => {
      const state = disclosureReducer(
        initialState,
        setDisclosureLevel("advanced"),
      );
      expect(state.level).toBe("advanced");
    });

    it("should set level to expert", () => {
      const state = disclosureReducer(
        initialState,
        setDisclosureLevel("expert"),
      );
      expect(state.level).toBe("expert");
    });

    it("should disable autoDetect when manually setting level", () => {
      const stateWithAutoDetect: DisclosureState = {
        ...initialState,
        autoDetect: true,
      };
      const state = disclosureReducer(
        stateWithAutoDetect,
        setDisclosureLevel("advanced"),
      );
      expect(state.autoDetect).toBe(false);
    });

    it("should update lastLevelChange timestamp", () => {
      const before = Date.now();
      const state = disclosureReducer(
        initialState,
        setDisclosureLevel("intermediate"),
      );
      const after = Date.now();

      expect(state.lastLevelChange).toBeGreaterThanOrEqual(before);
      expect(state.lastLevelChange).toBeLessThanOrEqual(after);
    });
  });

  describe("setAutoDetect", () => {
    it("should enable auto detection", () => {
      const stateWithDisabled: DisclosureState = {
        ...initialState,
        autoDetect: false,
      };
      const state = disclosureReducer(stateWithDisabled, setAutoDetect(true));
      expect(state.autoDetect).toBe(true);
    });

    it("should disable auto detection", () => {
      const state = disclosureReducer(initialState, setAutoDetect(false));
      expect(state.autoDetect).toBe(false);
    });
  });

  describe("incrementFeatureUsage", () => {
    it("should increment feature usage count", () => {
      const state = disclosureReducer(initialState, incrementFeatureUsage());
      expect(state.featureUsageCount).toBe(1);
    });

    it("should increment multiple times", () => {
      let state = disclosureReducer(initialState, incrementFeatureUsage());
      state = disclosureReducer(state, incrementFeatureUsage());
      state = disclosureReducer(state, incrementFeatureUsage());
      expect(state.featureUsageCount).toBe(3);
    });

    it("should auto-upgrade to intermediate after 10 feature uses with autoDetect", () => {
      let state: DisclosureState = { ...initialState, autoDetect: true };
      for (let i = 0; i < 10; i++) {
        state = disclosureReducer(state, incrementFeatureUsage());
      }
      expect(state.level).toBe("intermediate");
    });

    it("should auto-upgrade to advanced after 50 feature uses with autoDetect", () => {
      let state: DisclosureState = {
        ...initialState,
        autoDetect: true,
        level: "intermediate",
        featureUsageCount: 49,
      };
      state = disclosureReducer(state, incrementFeatureUsage());
      expect(state.level).toBe("advanced");
    });

    it("should auto-upgrade to expert after 100 feature uses with autoDetect", () => {
      let state: DisclosureState = {
        ...initialState,
        autoDetect: true,
        level: "advanced",
        featureUsageCount: 99,
      };
      state = disclosureReducer(state, incrementFeatureUsage());
      expect(state.level).toBe("expert");
    });

    it("should not auto-upgrade when autoDetect is disabled", () => {
      let state: DisclosureState = { ...initialState, autoDetect: false };
      for (let i = 0; i < 15; i++) {
        state = disclosureReducer(state, incrementFeatureUsage());
      }
      expect(state.level).toBe("beginner");
    });
  });

  describe("recordAction", () => {
    it("should add action to history", () => {
      const state = disclosureReducer(
        initialState,
        recordAction("click_button"),
      );
      expect(state.actionsHistory).toContain("click_button");
    });

    it("should limit history to 50 actions", () => {
      let state = initialState;
      // Add 55 actions
      for (let i = 0; i < 55; i++) {
        state = disclosureReducer(state, recordAction(`action_${i}`));
      }
      // Should only keep last 50
      expect(state.actionsHistory).toHaveLength(50);
      expect(state.actionsHistory[0]).toBe("action_5"); // First 5 should be removed
      expect(state.actionsHistory[49]).toBe("action_54");
    });
  });

  describe("resetDisclosureState", () => {
    it("should reset to initial state", () => {
      const modifiedState: DisclosureState = {
        level: "expert",
        autoDetect: false,
        featureUsageCount: 150,
        actionsHistory: ["action1", "action2"],
        lastLevelChange: Date.now(),
      };
      const state = disclosureReducer(modifiedState, resetDisclosureState());
      expect(state.level).toBe(initialState.level);
      expect(state.autoDetect).toBe(initialState.autoDetect);
      expect(state.featureUsageCount).toBe(initialState.featureUsageCount);
    });
  });

  describe("selectors", () => {
    const createRootState = (disclosure: DisclosureState) => ({ disclosure });

    describe("selectDisclosureLevel", () => {
      it("should return current disclosure level", () => {
        const state = createRootState({ ...initialState, level: "advanced" });
        expect(selectDisclosureLevel(state)).toBe("advanced");
      });
    });

    describe("selectAutoDetect", () => {
      it("should return autoDetect status", () => {
        const state = createRootState({ ...initialState, autoDetect: false });
        expect(selectAutoDetect(state)).toBe(false);
      });
    });

    describe("selectFeatureUsageCount", () => {
      it("should return feature usage count", () => {
        const state = createRootState({
          ...initialState,
          featureUsageCount: 42,
        });
        expect(selectFeatureUsageCount(state)).toBe(42);
      });
    });

    describe("selectShouldShowAdvancedFeature", () => {
      it("should return false for beginner level", () => {
        const state = createRootState({ ...initialState, level: "beginner" });
        expect(selectShouldShowAdvancedFeature("advanced")(state)).toBe(false);
      });

      it("should return false for intermediate requesting advanced", () => {
        const state = createRootState({
          ...initialState,
          level: "intermediate",
        });
        expect(selectShouldShowAdvancedFeature("advanced")(state)).toBe(false);
      });

      it("should return true for advanced level requesting advanced", () => {
        const state = createRootState({ ...initialState, level: "advanced" });
        expect(selectShouldShowAdvancedFeature("advanced")(state)).toBe(true);
      });

      it("should return true for expert level requesting any feature", () => {
        const state = createRootState({ ...initialState, level: "expert" });
        expect(selectShouldShowAdvancedFeature("beginner")(state)).toBe(true);
        expect(selectShouldShowAdvancedFeature("advanced")(state)).toBe(true);
        expect(selectShouldShowAdvancedFeature("expert")(state)).toBe(true);
      });
    });

    describe("selectLevelProgress", () => {
      it("should return progress to next level for beginner", () => {
        const state = createRootState({
          ...initialState,
          level: "beginner",
          featureUsageCount: 5,
        });
        const progress = selectLevelProgress(state);
        expect(progress.currentLevel).toBe("beginner");
        expect(progress.nextLevel).toBe("intermediate");
        expect(progress.progressPercent).toBe(50); // 5/10 = 50%
        expect(progress.actionsToNextLevel).toBe(5);
      });

      it("should return progress for intermediate", () => {
        const state = createRootState({
          ...initialState,
          level: "intermediate",
          featureUsageCount: 30,
        });
        const progress = selectLevelProgress(state);
        expect(progress.currentLevel).toBe("intermediate");
        expect(progress.nextLevel).toBe("advanced");
        expect(progress.progressPercent).toBe(50); // (30-10)/(50-10) = 50%
        expect(progress.actionsToNextLevel).toBe(20);
      });

      it("should return 100% progress for expert", () => {
        const state = createRootState({
          ...initialState,
          level: "expert",
          featureUsageCount: 150,
        });
        const progress = selectLevelProgress(state);
        expect(progress.currentLevel).toBe("expert");
        expect(progress.nextLevel).toBeNull();
        expect(progress.progressPercent).toBe(100);
        expect(progress.actionsToNextLevel).toBe(0);
      });
    });
  });

  describe("disclosure level ordering", () => {
    const levels: DisclosureLevel[] = [
      "beginner",
      "intermediate",
      "advanced",
      "expert",
    ];

    it("should have correct level progression", () => {
      expect(levels.indexOf("beginner")).toBeLessThan(
        levels.indexOf("intermediate"),
      );
      expect(levels.indexOf("intermediate")).toBeLessThan(
        levels.indexOf("advanced"),
      );
      expect(levels.indexOf("advanced")).toBeLessThan(levels.indexOf("expert"));
    });
  });
});
