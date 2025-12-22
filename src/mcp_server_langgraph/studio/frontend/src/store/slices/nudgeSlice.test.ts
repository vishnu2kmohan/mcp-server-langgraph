/**
 * nudgeSlice Tests
 *
 * TDD - Tests for nudge state management Redux slice.
 *
 * Features tested:
 * - Active nudge management
 * - Nudge queue handling
 * - History tracking (shown/dismissed/accepted)
 * - Frequency capping
 * - Session nudge limits
 * - Persistence integration
 */

import { describe, it, expect, vi } from "vitest";
import nudgeReducer, {
  initialState,
  setActiveNudge,
  dismissNudge,
  acceptNudge,
  queueNudge,
  processNextNudge,
  clearNudgeQueue,
  resetNudgeState,
  setSessionLimit,
  setSoundEnabled,
  selectActiveNudge,
  selectNudgeQueue,
  selectNudgeHistory,
  selectSessionNudgeCount,
  selectHasShownNudge,
  selectCanShowMoreNudges,
  selectNudgeStats,
  selectSoundEnabled,
  type NudgeState,
  type StoredNudge,
} from "./nudgeSlice";

// =============================================================================
// Test Data
// =============================================================================

const mockNudge: StoredNudge = {
  id: "nudge-1",
  type: "tooltip",
  message: "Did you know you can use Cmd+K for quick search?",
  priority: "medium",
  category: "keyboard-shortcut",
  targetElement: "[data-testid='search-input']",
  showAfterMs: 0,
};

const mockHighPriorityNudge: StoredNudge = {
  id: "nudge-high",
  type: "spotlight",
  message: "New feature: AI suggestions!",
  priority: "high",
  category: "feature-discovery",
};

const mockLowPriorityNudge: StoredNudge = {
  id: "nudge-low",
  type: "tooltip",
  message: "Tip: You can resize panels",
  priority: "low",
  category: "ui-tip",
};

// =============================================================================
// Helper Functions
// =============================================================================

function createRootState(nudgeState: NudgeState): { nudge: NudgeState } {
  return { nudge: nudgeState };
}

// =============================================================================
// Tests
// =============================================================================

describe("nudgeSlice", () => {
  describe("Initial State", () => {
    it("has correct initial state", () => {
      expect(initialState.activeNudge).toBeNull();
      expect(initialState.queue).toEqual([]);
      expect(initialState.history).toEqual([]);
      expect(initialState.sessionNudgeCount).toBe(0);
      expect(initialState.sessionLimit).toBe(5);
      expect(initialState.soundEnabled).toBe(false);
    });

    it("returns initial state for unknown action", () => {
      const result = nudgeReducer(undefined, { type: "UNKNOWN" });
      expect(result).toEqual(initialState);
    });
  });

  describe("setActiveNudge", () => {
    it("sets the active nudge", () => {
      const result = nudgeReducer(initialState, setActiveNudge(mockNudge));

      expect(result.activeNudge).toEqual(mockNudge);
      expect(result.sessionNudgeCount).toBe(1);
    });

    it("increments session nudge count", () => {
      let state = nudgeReducer(initialState, setActiveNudge(mockNudge));
      state = nudgeReducer(state, setActiveNudge(mockHighPriorityNudge));

      expect(state.sessionNudgeCount).toBe(2);
    });

    it("replaces existing active nudge", () => {
      let state = nudgeReducer(initialState, setActiveNudge(mockNudge));
      state = nudgeReducer(state, setActiveNudge(mockHighPriorityNudge));

      expect(state.activeNudge).toEqual(mockHighPriorityNudge);
    });

    it("clears active nudge when null is passed", () => {
      let state = nudgeReducer(initialState, setActiveNudge(mockNudge));
      state = nudgeReducer(state, setActiveNudge(null));

      expect(state.activeNudge).toBeNull();
    });
  });

  describe("dismissNudge", () => {
    it("clears active nudge when IDs match", () => {
      let state = nudgeReducer(initialState, setActiveNudge(mockNudge));
      state = nudgeReducer(state, dismissNudge(mockNudge.id));

      expect(state.activeNudge).toBeNull();
    });

    it("does not clear active nudge when IDs do not match", () => {
      let state = nudgeReducer(initialState, setActiveNudge(mockNudge));
      state = nudgeReducer(state, dismissNudge("other-nudge-id"));

      expect(state.activeNudge).toEqual(mockNudge);
    });

    it("adds entry to history with dismissed action", () => {
      vi.useFakeTimers();
      const now = Date.now();
      vi.setSystemTime(now);

      let state = nudgeReducer(initialState, setActiveNudge(mockNudge));
      state = nudgeReducer(state, dismissNudge(mockNudge.id));

      expect(state.history).toHaveLength(1);
      expect(state.history[0]).toEqual({
        id: mockNudge.id,
        action: "dismissed",
        timestamp: now,
      });

      vi.useRealTimers();
    });
  });

  describe("acceptNudge", () => {
    it("clears active nudge when IDs match", () => {
      let state = nudgeReducer(initialState, setActiveNudge(mockNudge));
      state = nudgeReducer(state, acceptNudge(mockNudge.id));

      expect(state.activeNudge).toBeNull();
    });

    it("does not clear active nudge when IDs do not match", () => {
      let state = nudgeReducer(initialState, setActiveNudge(mockNudge));
      state = nudgeReducer(state, acceptNudge("other-nudge-id"));

      expect(state.activeNudge).toEqual(mockNudge);
    });

    it("adds entry to history with accepted action", () => {
      vi.useFakeTimers();
      const now = Date.now();
      vi.setSystemTime(now);

      let state = nudgeReducer(initialState, setActiveNudge(mockNudge));
      state = nudgeReducer(state, acceptNudge(mockNudge.id));

      expect(state.history).toHaveLength(1);
      expect(state.history[0]).toEqual({
        id: mockNudge.id,
        action: "accepted",
        timestamp: now,
      });

      vi.useRealTimers();
    });
  });

  describe("queueNudge", () => {
    it("adds nudge to queue", () => {
      const result = nudgeReducer(initialState, queueNudge(mockNudge));

      expect(result.queue).toHaveLength(1);
      expect(result.queue[0]).toEqual(mockNudge);
    });

    it("does not add duplicate nudges", () => {
      let state = nudgeReducer(initialState, queueNudge(mockNudge));
      state = nudgeReducer(state, queueNudge(mockNudge));

      expect(state.queue).toHaveLength(1);
    });

    it("sorts queue by priority (high first)", () => {
      let state = nudgeReducer(initialState, queueNudge(mockLowPriorityNudge));
      state = nudgeReducer(state, queueNudge(mockHighPriorityNudge));
      state = nudgeReducer(state, queueNudge(mockNudge)); // medium

      expect(state.queue).toHaveLength(3);
      expect(state.queue[0].priority).toBe("high");
      expect(state.queue[1].priority).toBe("medium");
      expect(state.queue[2].priority).toBe("low");
    });

    it("does not queue nudges already shown in session", () => {
      let state = nudgeReducer(initialState, setActiveNudge(mockNudge));
      state = nudgeReducer(state, dismissNudge(mockNudge.id));
      state = nudgeReducer(state, queueNudge(mockNudge));

      expect(state.queue).toHaveLength(0);
    });
  });

  describe("processNextNudge", () => {
    it("sets active nudge from queue head", () => {
      let state = nudgeReducer(initialState, queueNudge(mockNudge));
      state = nudgeReducer(state, processNextNudge());

      expect(state.activeNudge).toEqual(mockNudge);
      expect(state.queue).toHaveLength(0);
    });

    it("does nothing if queue is empty", () => {
      const result = nudgeReducer(initialState, processNextNudge());

      expect(result.activeNudge).toBeNull();
      expect(result.queue).toHaveLength(0);
    });

    it("does nothing if there is already an active nudge", () => {
      let state = nudgeReducer(initialState, setActiveNudge(mockNudge));
      state = nudgeReducer(state, queueNudge(mockHighPriorityNudge));
      state = nudgeReducer(state, processNextNudge());

      expect(state.activeNudge).toEqual(mockNudge); // Original nudge unchanged
      expect(state.queue).toHaveLength(1);
    });

    it("does not process if session limit reached", () => {
      let state: NudgeState = { ...initialState, sessionLimit: 1 };
      state = nudgeReducer(state, setActiveNudge(mockNudge));
      state = nudgeReducer(state, dismissNudge(mockNudge.id));
      state = nudgeReducer(state, queueNudge(mockHighPriorityNudge));
      state = nudgeReducer(state, processNextNudge());

      expect(state.activeNudge).toBeNull();
      expect(state.queue).toHaveLength(1);
    });
  });

  describe("clearNudgeQueue", () => {
    it("clears all queued nudges", () => {
      let state = nudgeReducer(initialState, queueNudge(mockNudge));
      state = nudgeReducer(state, queueNudge(mockHighPriorityNudge));
      state = nudgeReducer(state, clearNudgeQueue());

      expect(state.queue).toHaveLength(0);
    });

    it("does not affect active nudge or history", () => {
      let state = nudgeReducer(initialState, setActiveNudge(mockNudge));
      state = nudgeReducer(state, dismissNudge(mockNudge.id));
      state = nudgeReducer(state, queueNudge(mockHighPriorityNudge));
      state = nudgeReducer(state, clearNudgeQueue());

      expect(state.history).toHaveLength(1);
    });
  });

  describe("resetNudgeState", () => {
    it("resets to initial state", () => {
      let state = nudgeReducer(initialState, setActiveNudge(mockNudge));
      state = nudgeReducer(state, dismissNudge(mockNudge.id));
      state = nudgeReducer(state, queueNudge(mockHighPriorityNudge));
      state = nudgeReducer(state, resetNudgeState());

      expect(state).toEqual(initialState);
    });
  });

  describe("setSessionLimit", () => {
    it("sets session nudge limit", () => {
      const result = nudgeReducer(initialState, setSessionLimit(10));

      expect(result.sessionLimit).toBe(10);
    });

    it("clamps to minimum of 1", () => {
      const result = nudgeReducer(initialState, setSessionLimit(0));

      expect(result.sessionLimit).toBe(1);
    });
  });

  describe("setSoundEnabled", () => {
    it("enables sound", () => {
      const result = nudgeReducer(initialState, setSoundEnabled(true));

      expect(result.soundEnabled).toBe(true);
    });

    it("disables sound", () => {
      let state = nudgeReducer(initialState, setSoundEnabled(true));
      state = nudgeReducer(state, setSoundEnabled(false));

      expect(state.soundEnabled).toBe(false);
    });
  });

  describe("History Management", () => {
    it("limits history to 100 entries when dismissing nudges", () => {
      let state = initialState;

      // Add 110 nudges
      for (let i = 0; i < 110; i++) {
        const nudge: StoredNudge = { ...mockNudge, id: `nudge-${i}` };
        state = nudgeReducer(state, setActiveNudge(nudge));
        state = nudgeReducer(state, dismissNudge(nudge.id));
      }

      expect(state.history.length).toBeLessThanOrEqual(100);
    });

    it("limits history to 100 entries when accepting nudges", () => {
      let state = initialState;

      // Add 110 nudges via acceptNudge
      for (let i = 0; i < 110; i++) {
        const nudge: StoredNudge = { ...mockNudge, id: `nudge-${i}` };
        state = nudgeReducer(state, setActiveNudge(nudge));
        state = nudgeReducer(state, acceptNudge(nudge.id));
      }

      expect(state.history.length).toBeLessThanOrEqual(100);
    });
  });

  describe("Selectors", () => {
    describe("selectActiveNudge", () => {
      it("returns active nudge", () => {
        const state = nudgeReducer(initialState, setActiveNudge(mockNudge));
        const rootState = createRootState(state);

        expect(selectActiveNudge(rootState)).toEqual(mockNudge);
      });

      it("returns null when no active nudge", () => {
        const rootState = createRootState(initialState);

        expect(selectActiveNudge(rootState)).toBeNull();
      });
    });

    describe("selectNudgeQueue", () => {
      it("returns queue", () => {
        let state = nudgeReducer(initialState, queueNudge(mockNudge));
        state = nudgeReducer(state, queueNudge(mockHighPriorityNudge));
        const rootState = createRootState(state);

        expect(selectNudgeQueue(rootState)).toHaveLength(2);
      });
    });

    describe("selectNudgeHistory", () => {
      it("returns history", () => {
        let state = nudgeReducer(initialState, setActiveNudge(mockNudge));
        state = nudgeReducer(state, dismissNudge(mockNudge.id));
        const rootState = createRootState(state);

        expect(selectNudgeHistory(rootState)).toHaveLength(1);
      });
    });

    describe("selectSessionNudgeCount", () => {
      it("returns session nudge count", () => {
        let state = nudgeReducer(initialState, setActiveNudge(mockNudge));
        state = nudgeReducer(state, setActiveNudge(mockHighPriorityNudge));
        const rootState = createRootState(state);

        expect(selectSessionNudgeCount(rootState)).toBe(2);
      });
    });

    describe("selectHasShownNudge", () => {
      it("returns true if nudge was shown", () => {
        let state = nudgeReducer(initialState, setActiveNudge(mockNudge));
        state = nudgeReducer(state, dismissNudge(mockNudge.id));
        const rootState = createRootState(state);

        expect(selectHasShownNudge(mockNudge.id)(rootState)).toBe(true);
      });

      it("returns false if nudge was not shown", () => {
        const rootState = createRootState(initialState);

        expect(selectHasShownNudge("never-shown")(rootState)).toBe(false);
      });
    });

    describe("selectCanShowMoreNudges", () => {
      it("returns true when under limit", () => {
        const rootState = createRootState(initialState);

        expect(selectCanShowMoreNudges(rootState)).toBe(true);
      });

      it("returns false when at limit", () => {
        let state: NudgeState = { ...initialState, sessionLimit: 1 };
        state = nudgeReducer(state, setActiveNudge(mockNudge));
        const rootState = createRootState(state);

        expect(selectCanShowMoreNudges(rootState)).toBe(false);
      });
    });

    describe("selectNudgeStats", () => {
      it("returns comprehensive stats", () => {
        vi.useFakeTimers();
        const now = Date.now();
        vi.setSystemTime(now);

        let state = nudgeReducer(initialState, setActiveNudge(mockNudge));
        state = nudgeReducer(state, acceptNudge(mockNudge.id));
        state = nudgeReducer(state, setActiveNudge(mockHighPriorityNudge));
        state = nudgeReducer(state, dismissNudge(mockHighPriorityNudge.id));
        const rootState = createRootState(state);

        const stats = selectNudgeStats(rootState);

        expect(stats.totalShown).toBe(2);
        expect(stats.accepted).toBe(1);
        expect(stats.dismissed).toBe(1);
        expect(stats.acceptanceRate).toBe(0.5);
        expect(stats.sessionNudgeCount).toBe(2);
        expect(stats.canShowMore).toBe(true);

        vi.useRealTimers();
      });
    });

    describe("selectSoundEnabled", () => {
      it("returns false by default", () => {
        const rootState = createRootState(initialState);

        expect(selectSoundEnabled(rootState)).toBe(false);
      });

      it("returns true when sound is enabled", () => {
        const state = nudgeReducer(initialState, setSoundEnabled(true));
        const rootState = createRootState(state);

        expect(selectSoundEnabled(rootState)).toBe(true);
      });
    });
  });
});
