/**
 * useTimelinePersistence Hook Tests
 *
 * TDD tests for timeline state persistence.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, act } from "@testing-library/react";

import { useTimelinePersistence } from "./useTimelinePersistence";

// =============================================================================
// Tests
// =============================================================================

describe("useTimelinePersistence", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("initialization", () => {
    it("should return default state when no saved data exists", () => {
      const { result } = renderHook(() =>
        useTimelinePersistence({ sessionId: "session-123" }),
      );

      expect(result.current.state).toEqual({
        bookmarks: [],
        playbackSpeed: 1,
        activeFilters: { types: [] },
      });
    });

    it("should restore state from localStorage", () => {
      const savedState = {
        bookmarks: [{ id: "b1", time: 100, label: "Bookmark 1" }],
        playbackSpeed: 2,
        activeFilters: { types: ["console", "network"] },
      };
      localStorage.setItem(
        "devtools-timeline-session-123",
        JSON.stringify(savedState),
      );

      const { result } = renderHook(() =>
        useTimelinePersistence({ sessionId: "session-123" }),
      );

      expect(result.current.state.bookmarks).toEqual(savedState.bookmarks);
      expect(result.current.state.playbackSpeed).toBe(2);
    });
  });

  describe("bookmark operations", () => {
    it("should add a bookmark", () => {
      const { result } = renderHook(() =>
        useTimelinePersistence({ sessionId: "session-123" }),
      );

      act(() => {
        result.current.addBookmark({
          id: "b1",
          time: 100,
          label: "Bookmark 1",
        });
      });

      expect(result.current.state.bookmarks).toHaveLength(1);
      expect(result.current.state.bookmarks[0].label).toBe("Bookmark 1");
    });

    it("should remove a bookmark", () => {
      const { result } = renderHook(() =>
        useTimelinePersistence({ sessionId: "session-123" }),
      );

      act(() => {
        result.current.addBookmark({
          id: "b1",
          time: 100,
          label: "Bookmark 1",
        });
        result.current.addBookmark({
          id: "b2",
          time: 200,
          label: "Bookmark 2",
        });
      });

      act(() => {
        result.current.removeBookmark("b1");
      });

      expect(result.current.state.bookmarks).toHaveLength(1);
      expect(result.current.state.bookmarks[0].id).toBe("b2");
    });

    it("should update a bookmark", () => {
      const { result } = renderHook(() =>
        useTimelinePersistence({ sessionId: "session-123" }),
      );

      act(() => {
        result.current.addBookmark({
          id: "b1",
          time: 100,
          label: "Bookmark 1",
        });
      });

      act(() => {
        result.current.updateBookmark("b1", { label: "Updated Label" });
      });

      expect(result.current.state.bookmarks[0].label).toBe("Updated Label");
    });
  });

  describe("playback speed", () => {
    it("should set playback speed", () => {
      const { result } = renderHook(() =>
        useTimelinePersistence({ sessionId: "session-123" }),
      );

      act(() => {
        result.current.setPlaybackSpeed(4);
      });

      expect(result.current.state.playbackSpeed).toBe(4);
    });
  });

  describe("active filters", () => {
    it("should set active filters", () => {
      const { result } = renderHook(() =>
        useTimelinePersistence({ sessionId: "session-123" }),
      );

      act(() => {
        result.current.setActiveFilters({ types: ["console", "network"] });
      });

      expect(result.current.state.activeFilters.types).toContain("console");
      expect(result.current.state.activeFilters.types).toContain("network");
    });
  });

  describe("reset", () => {
    it("should reset state to defaults", () => {
      const { result } = renderHook(() =>
        useTimelinePersistence({ sessionId: "session-123" }),
      );

      act(() => {
        result.current.addBookmark({
          id: "b1",
          time: 100,
          label: "Bookmark 1",
        });
        result.current.setPlaybackSpeed(4);
        result.current.setActiveFilters({ types: ["console"] });
      });

      act(() => {
        result.current.reset();
      });

      expect(result.current.state.bookmarks).toHaveLength(0);
      expect(result.current.state.playbackSpeed).toBe(1);
      expect(result.current.state.activeFilters.types).toHaveLength(0);
    });
  });

  describe("error handling", () => {
    it("should handle corrupted localStorage data gracefully", () => {
      localStorage.setItem("devtools-timeline-session-123", "invalid-json{");

      const { result } = renderHook(() =>
        useTimelinePersistence({ sessionId: "session-123" }),
      );

      // Should return default state
      expect(result.current.state).toEqual({
        bookmarks: [],
        playbackSpeed: 1,
        activeFilters: { types: [] },
      });
    });
  });
});
