/**
 * sessionSlice Navigation Tests
 *
 * Tests for navigation tracking (Phase 4.2: AI Predictions Support):
 * - trackPageVisit action
 * - setNavigationContext action
 * - Navigation selectors
 *
 * @see sessionSlice.fixtures.ts for shared utilities
 */

import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  trackPageVisit,
  setNavigationContext,
  selectRecentPages,
  selectCurrentPage,
  selectNavigationContext,
} from "../sessionSlice";
import {
  createTestStore,
  setupMockFetch,
  resetMockFetch,
} from "./sessionSlice.fixtures";

describe("sessionSlice - Navigation", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMockFetch();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    resetMockFetch();
  });

  // ===========================================================================
  // NAVIGATION TRACKING (PHASE 4.2: AI PREDICTIONS SUPPORT)
  // ===========================================================================

  describe("navigation tracking", () => {
    describe("trackPageVisit action", () => {
      it("should add page to recentPages", () => {
        const store = createTestStore();
        store.dispatch(trackPageVisit("/studio/chat"));

        expect(selectRecentPages(store.getState())).toContain("/studio/chat");
      });

      it("should update currentPage", () => {
        const store = createTestStore();
        store.dispatch(trackPageVisit("/studio/workflows"));

        expect(selectCurrentPage(store.getState())).toBe("/studio/workflows");
      });

      it("should keep only last 5 pages in recentPages", () => {
        const store = createTestStore();

        // Visit 7 pages
        store.dispatch(trackPageVisit("/studio/chat"));
        store.dispatch(trackPageVisit("/studio/workflows"));
        store.dispatch(trackPageVisit("/studio/agents"));
        store.dispatch(trackPageVisit("/studio/mcp"));
        store.dispatch(trackPageVisit("/studio/traces"));
        store.dispatch(trackPageVisit("/studio/cost"));
        store.dispatch(trackPageVisit("/studio/admin"));

        const recentPages = selectRecentPages(store.getState());
        expect(recentPages).toHaveLength(5);
        // Most recent should be first
        expect(recentPages[0]).toBe("/studio/admin");
        // Oldest (chat, workflows) should be dropped
        expect(recentPages).not.toContain("/studio/chat");
        expect(recentPages).not.toContain("/studio/workflows");
      });

      it("should not duplicate pages - move to front if already visited", () => {
        const store = createTestStore();

        store.dispatch(trackPageVisit("/studio/chat"));
        store.dispatch(trackPageVisit("/studio/workflows"));
        store.dispatch(trackPageVisit("/studio/chat")); // Visit chat again

        const recentPages = selectRecentPages(store.getState());
        expect(recentPages).toHaveLength(2);
        expect(recentPages[0]).toBe("/studio/chat"); // Most recent
        expect(recentPages[1]).toBe("/studio/workflows");
      });

      it("should handle multiple sequential visits to same page", () => {
        const store = createTestStore();

        store.dispatch(trackPageVisit("/studio/chat"));
        store.dispatch(trackPageVisit("/studio/chat"));
        store.dispatch(trackPageVisit("/studio/chat"));

        const recentPages = selectRecentPages(store.getState());
        expect(recentPages).toHaveLength(1);
        expect(recentPages[0]).toBe("/studio/chat");
      });

      it("should handle empty path", () => {
        const store = createTestStore();
        store.dispatch(trackPageVisit(""));

        expect(selectRecentPages(store.getState())).toContain("");
        expect(selectCurrentPage(store.getState())).toBe("");
      });

      it("should handle deep nested paths", () => {
        const store = createTestStore();
        store.dispatch(
          trackPageVisit("/studio/projects/123/sessions/456/edit"),
        );

        expect(selectRecentPages(store.getState())).toContain(
          "/studio/projects/123/sessions/456/edit",
        );
        expect(selectCurrentPage(store.getState())).toBe(
          "/studio/projects/123/sessions/456/edit",
        );
      });

      it("should preserve order with mixed navigation", () => {
        const store = createTestStore();

        store.dispatch(trackPageVisit("/a"));
        store.dispatch(trackPageVisit("/b"));
        store.dispatch(trackPageVisit("/c"));
        store.dispatch(trackPageVisit("/b")); // Revisit /b
        store.dispatch(trackPageVisit("/d"));

        const recentPages = selectRecentPages(store.getState());
        expect(recentPages).toEqual(["/d", "/b", "/c", "/a"]);
      });
    });

    describe("setNavigationContext action", () => {
      it("should set navigation context with feature", () => {
        const store = createTestStore();
        store.dispatch(
          setNavigationContext({
            page: "/studio/chat",
            feature: "streaming",
          }),
        );

        const context = selectNavigationContext(store.getState());
        expect(context.page).toBe("/studio/chat");
        expect(context.feature).toBe("streaming");
      });

      it("should set navigation context with action", () => {
        const store = createTestStore();
        store.dispatch(
          setNavigationContext({
            page: "/studio/agents",
            action: "create",
          }),
        );

        const context = selectNavigationContext(store.getState());
        expect(context.page).toBe("/studio/agents");
        expect(context.action).toBe("create");
      });

      it("should set navigation context with both feature and action", () => {
        const store = createTestStore();
        store.dispatch(
          setNavigationContext({
            page: "/studio/workflows",
            feature: "builder",
            action: "edit",
          }),
        );

        const context = selectNavigationContext(store.getState());
        expect(context.page).toBe("/studio/workflows");
        expect(context.feature).toBe("builder");
        expect(context.action).toBe("edit");
      });

      it("should overwrite previous context", () => {
        const store = createTestStore();

        store.dispatch(
          setNavigationContext({
            page: "/studio/chat",
            feature: "streaming",
          }),
        );

        store.dispatch(
          setNavigationContext({
            page: "/studio/agents",
            action: "delete",
          }),
        );

        const context = selectNavigationContext(store.getState());
        expect(context.page).toBe("/studio/agents");
        expect(context.action).toBe("delete");
        // Note: feature might be undefined or preserved based on implementation
      });

      it("should handle context with only page", () => {
        const store = createTestStore();
        store.dispatch(
          setNavigationContext({
            page: "/studio/settings",
          }),
        );

        const context = selectNavigationContext(store.getState());
        expect(context.page).toBe("/studio/settings");
        expect(context.feature).toBeUndefined();
        expect(context.action).toBeUndefined();
      });
    });

    describe("navigation selectors", () => {
      it("selectRecentPages should return empty array initially", () => {
        const store = createTestStore();
        expect(selectRecentPages(store.getState())).toEqual([]);
      });

      it("selectCurrentPage should return empty string initially", () => {
        const store = createTestStore();
        expect(selectCurrentPage(store.getState())).toBe("");
      });

      it("selectNavigationContext should return default context initially", () => {
        const store = createTestStore();
        const context = selectNavigationContext(store.getState());
        expect(context).toEqual({
          page: "",
          feature: undefined,
          action: undefined,
        });
      });

      it("selectRecentPages should be an array type", () => {
        const store = createTestStore();
        const pages = selectRecentPages(store.getState());
        expect(Array.isArray(pages)).toBe(true);
      });

      it("selectCurrentPage should be a string type", () => {
        const store = createTestStore();
        const page = selectCurrentPage(store.getState());
        expect(typeof page).toBe("string");
      });

      it("selectNavigationContext should have expected shape", () => {
        const store = createTestStore();
        const context = selectNavigationContext(store.getState());
        expect(context).toHaveProperty("page");
        expect(context).toHaveProperty("feature");
        expect(context).toHaveProperty("action");
      });
    });

    describe("integration scenarios", () => {
      it("should work with typical user navigation flow", () => {
        const store = createTestStore();

        // User logs in, goes to chat
        store.dispatch(trackPageVisit("/studio/chat"));
        store.dispatch(
          setNavigationContext({ page: "/studio/chat", feature: "welcome" }),
        );

        // User starts streaming
        store.dispatch(
          setNavigationContext({ page: "/studio/chat", feature: "streaming" }),
        );

        // User navigates to workflows
        store.dispatch(trackPageVisit("/studio/workflows"));
        store.dispatch(
          setNavigationContext({ page: "/studio/workflows", action: "list" }),
        );

        // User opens a workflow
        store.dispatch(trackPageVisit("/studio/workflows/123"));
        store.dispatch(
          setNavigationContext({
            page: "/studio/workflows/123",
            feature: "builder",
            action: "view",
          }),
        );

        // Verify final state
        const recentPages = selectRecentPages(store.getState());
        expect(recentPages[0]).toBe("/studio/workflows/123");
        expect(recentPages).toContain("/studio/chat");

        const context = selectNavigationContext(store.getState());
        expect(context.page).toBe("/studio/workflows/123");
        expect(context.feature).toBe("builder");
        expect(context.action).toBe("view");
      });

      it("should handle rapid page switches", () => {
        const store = createTestStore();

        // Simulate rapid tab switching
        for (let i = 0; i < 20; i++) {
          store.dispatch(trackPageVisit(`/page/${i % 3}`));
        }

        const recentPages = selectRecentPages(store.getState());
        expect(recentPages.length).toBeLessThanOrEqual(5);
      });

      it("should handle back/forward navigation pattern", () => {
        const store = createTestStore();

        // Forward navigation
        store.dispatch(trackPageVisit("/a"));
        store.dispatch(trackPageVisit("/b"));
        store.dispatch(trackPageVisit("/c"));

        // Back
        store.dispatch(trackPageVisit("/b"));
        store.dispatch(trackPageVisit("/a"));

        // Forward again
        store.dispatch(trackPageVisit("/d"));

        const recentPages = selectRecentPages(store.getState());
        expect(recentPages[0]).toBe("/d");
        expect(selectCurrentPage(store.getState())).toBe("/d");
      });
    });
  });
});
