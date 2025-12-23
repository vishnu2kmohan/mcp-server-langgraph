/**
 * useStateHistory Hook Tests
 *
 * TDD tests for time-travel debugging functionality.
 * Records state snapshots and allows navigation through history.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useStateHistory } from "./useStateHistory";

// =============================================================================
// Tests
// =============================================================================

describe("useStateHistory", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
  });

  describe("initialization", () => {
    it("should return initial state with empty history", () => {
      const { result } = renderHook(() => useStateHistory());

      expect(result.current.snapshots).toEqual([]);
      expect(result.current.currentIndex).toBe(-1);
      expect(result.current.isAtLatest).toBe(true);
      expect(result.current.isPlaying).toBe(false);
    });

    it("should accept initial snapshot if provided", () => {
      const initialState = { counter: 0 };
      const { result } = renderHook(() => useStateHistory({ initialState }));

      expect(result.current.snapshots).toHaveLength(1);
      expect(result.current.snapshots[0].state).toEqual(initialState);
      expect(result.current.currentIndex).toBe(0);
    });

    it("should accept maxSnapshots option", () => {
      const { result } = renderHook(() => useStateHistory({ maxSnapshots: 5 }));

      // Record 10 snapshots
      for (let i = 0; i < 10; i++) {
        act(() => {
          result.current.recordSnapshot({ counter: i });
        });
      }

      // Should only keep the last 5
      expect(result.current.snapshots).toHaveLength(5);
      expect(result.current.snapshots[0].state).toEqual({ counter: 5 });
      expect(result.current.snapshots[4].state).toEqual({ counter: 9 });
    });
  });

  describe("recordSnapshot", () => {
    it("should add a new snapshot to history", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ counter: 1 });
      });

      expect(result.current.snapshots).toHaveLength(1);
      expect(result.current.snapshots[0].state).toEqual({ counter: 1 });
      expect(result.current.currentIndex).toBe(0);
    });

    it("should record timestamp with each snapshot", () => {
      const now = Date.now();
      vi.setSystemTime(now);

      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ counter: 1 });
      });

      expect(result.current.snapshots[0].timestamp).toBe(now);
    });

    it("should record multiple snapshots in order", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 3 });
      });

      expect(result.current.snapshots).toHaveLength(3);
      expect(result.current.snapshots[0].state).toEqual({ step: 1 });
      expect(result.current.snapshots[1].state).toEqual({ step: 2 });
      expect(result.current.snapshots[2].state).toEqual({ step: 3 });
    });

    it("should update currentIndex to latest when recording", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });

      expect(result.current.currentIndex).toBe(1);
      expect(result.current.isAtLatest).toBe(true);
    });

    it("should accept optional label for snapshot", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ counter: 1 }, "Initial state");
      });

      expect(result.current.snapshots[0].label).toBe("Initial state");
    });
  });

  describe("navigation", () => {
    it("should navigate to previous snapshot", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 3 });
      });

      act(() => {
        result.current.goBack();
      });

      expect(result.current.currentIndex).toBe(1);
      expect(result.current.currentSnapshot?.state).toEqual({ step: 2 });
    });

    it("should navigate to next snapshot", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });
      act(() => {
        result.current.goBack();
      });
      act(() => {
        result.current.goForward();
      });

      expect(result.current.currentIndex).toBe(1);
      expect(result.current.currentSnapshot?.state).toEqual({ step: 2 });
    });

    it("should not go back past the first snapshot", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.goBack();
      });
      act(() => {
        result.current.goBack();
      });

      expect(result.current.currentIndex).toBe(0);
    });

    it("should not go forward past the last snapshot", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.goForward();
      });

      expect(result.current.currentIndex).toBe(0);
    });

    it("should jump to specific index", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 3 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 4 });
      });

      act(() => {
        result.current.jumpTo(1);
      });

      expect(result.current.currentIndex).toBe(1);
      expect(result.current.currentSnapshot?.state).toEqual({ step: 2 });
    });

    it("should jump to latest", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 3 });
      });
      act(() => {
        result.current.jumpTo(0);
      });
      act(() => {
        result.current.jumpToLatest();
      });

      expect(result.current.currentIndex).toBe(2);
      expect(result.current.isAtLatest).toBe(true);
    });
  });

  describe("navigation state", () => {
    it("should return canGoBack correctly", () => {
      const { result } = renderHook(() => useStateHistory());

      expect(result.current.canGoBack).toBe(false);

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      expect(result.current.canGoBack).toBe(false);

      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });
      expect(result.current.canGoBack).toBe(true);
    });

    it("should return canGoForward correctly", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });

      expect(result.current.canGoForward).toBe(false);

      act(() => {
        result.current.goBack();
      });

      expect(result.current.canGoForward).toBe(true);
    });

    it("should return isAtLatest correctly", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });

      expect(result.current.isAtLatest).toBe(true);

      act(() => {
        result.current.goBack();
      });

      expect(result.current.isAtLatest).toBe(false);
    });
  });

  describe("currentSnapshot", () => {
    it("should return null when no snapshots", () => {
      const { result } = renderHook(() => useStateHistory());

      expect(result.current.currentSnapshot).toBeNull();
    });

    it("should return current snapshot based on index", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });

      expect(result.current.currentSnapshot?.state).toEqual({ step: 2 });

      act(() => {
        result.current.goBack();
      });

      expect(result.current.currentSnapshot?.state).toEqual({ step: 1 });
    });
  });

  describe("diff calculation", () => {
    it("should calculate diff between current and previous snapshot", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ a: 1, b: 2 });
      });
      act(() => {
        result.current.recordSnapshot({ a: 1, b: 3, c: 4 });
      });

      const diff = result.current.getDiff();

      expect(diff).not.toBeNull();
      expect(diff?.changed).toContain("b");
      expect(diff?.added).toContain("c");
    });

    it("should detect removed properties", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ a: 1, b: 2, c: 3 });
      });
      act(() => {
        result.current.recordSnapshot({ a: 1 });
      });

      const diff = result.current.getDiff();

      expect(diff?.removed).toContain("b");
      expect(diff?.removed).toContain("c");
    });

    it("should return null when no previous snapshot", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ a: 1 });
      });

      const diff = result.current.getDiff();

      expect(diff).toBeNull();
    });

    it("should allow getting diff between any two snapshots", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ version: 1 });
      });
      act(() => {
        result.current.recordSnapshot({ version: 2 });
      });
      act(() => {
        result.current.recordSnapshot({ version: 3, extra: true });
      });

      const diff = result.current.getDiffBetween(0, 2);

      expect(diff?.changed).toContain("version");
      expect(diff?.added).toContain("extra");
    });
  });

  describe("clear history", () => {
    it("should clear all snapshots", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });
      act(() => {
        result.current.clearHistory();
      });

      expect(result.current.snapshots).toHaveLength(0);
      expect(result.current.currentIndex).toBe(-1);
    });
  });

  describe("playback", () => {
    it("should start playback from beginning", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 3 });
      });

      act(() => {
        result.current.startPlayback();
      });

      expect(result.current.isPlaying).toBe(true);
      expect(result.current.currentIndex).toBe(0);
    });

    it("should stop playback", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });
      act(() => {
        result.current.startPlayback();
      });
      act(() => {
        result.current.stopPlayback();
      });

      expect(result.current.isPlaying).toBe(false);
    });

    it("should advance through snapshots during playback", () => {
      const { result } = renderHook(() =>
        useStateHistory({ playbackInterval: 100 }),
      );

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 3 });
      });

      act(() => {
        result.current.startPlayback();
      });

      expect(result.current.currentIndex).toBe(0);

      act(() => {
        vi.advanceTimersByTime(100);
      });

      expect(result.current.currentIndex).toBe(1);

      act(() => {
        vi.advanceTimersByTime(100);
      });

      expect(result.current.currentIndex).toBe(2);
    });

    it("should stop playback when reaching the end", () => {
      const { result } = renderHook(() =>
        useStateHistory({ playbackInterval: 100 }),
      );

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });

      act(() => {
        result.current.startPlayback();
      });

      act(() => {
        vi.advanceTimersByTime(100);
      });
      act(() => {
        vi.advanceTimersByTime(100);
      });

      expect(result.current.isPlaying).toBe(false);
      expect(result.current.currentIndex).toBe(1);
    });

    it("should support custom playback speed", () => {
      const { result } = renderHook(() =>
        useStateHistory({ playbackInterval: 50 }),
      );

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });

      act(() => {
        result.current.startPlayback();
      });

      act(() => {
        vi.advanceTimersByTime(50);
      });

      expect(result.current.currentIndex).toBe(1);
    });
  });

  describe("callbacks", () => {
    it("should call onSnapshotChange when snapshot changes", () => {
      const onSnapshotChange = vi.fn();
      const { result } = renderHook(() =>
        useStateHistory({ onSnapshotChange }),
      );

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });

      expect(onSnapshotChange).toHaveBeenCalledWith(
        expect.objectContaining({ state: { step: 1 } }),
        0,
      );
    });

    it("should call onNavigate when navigating", () => {
      const onNavigate = vi.fn();
      const { result } = renderHook(() => useStateHistory({ onNavigate }));

      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });
      act(() => {
        result.current.goBack();
      });

      expect(onNavigate).toHaveBeenCalledWith(0, 1);
    });
  });

  describe("snapshot filtering", () => {
    it("should filter snapshots by label", () => {
      const { result } = renderHook(() => useStateHistory());

      act(() => {
        result.current.recordSnapshot({ step: 1 }, "Initial");
      });
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });
      act(() => {
        result.current.recordSnapshot({ step: 3 }, "Important");
      });

      const labeled = result.current.getSnapshotsWithLabel();

      expect(labeled).toHaveLength(2);
      expect(labeled[0].label).toBe("Initial");
      expect(labeled[1].label).toBe("Important");
    });

    it("should get snapshots within time range", () => {
      const { result } = renderHook(() => useStateHistory());
      const baseTime = Date.now();

      vi.setSystemTime(baseTime);
      act(() => {
        result.current.recordSnapshot({ step: 1 });
      });

      vi.setSystemTime(baseTime + 1000);
      act(() => {
        result.current.recordSnapshot({ step: 2 });
      });

      vi.setSystemTime(baseTime + 2000);
      act(() => {
        result.current.recordSnapshot({ step: 3 });
      });

      const range = result.current.getSnapshotsInRange(
        baseTime + 500,
        baseTime + 1500,
      );

      expect(range).toHaveLength(1);
      expect(range[0].state).toEqual({ step: 2 });
    });
  });
});
