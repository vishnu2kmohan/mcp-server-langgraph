/**
 * HelpSlice Tests
 *
 * Phase 7: Integration - State Management
 */
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import helpReducer, {
  toggleHelpPane,
  setHelpPaneOpen,
  setHelpSearchQuery,
  selectHelpTopic,
  dismissTip,
  showTipsForRoute,
  clearVisibleTips,
  resetDismissedTips,
  selectHelpPaneOpen,
  selectVisibleTips,
  selectHelpSearchQuery,
  selectSelectedTopicId,
  selectDismissedTipIds,
  resetHelp,
  type ContextualTip,
  type HelpState,
} from "./helpSlice";

describe("helpSlice", () => {
  const mockTip: ContextualTip = {
    id: "tip-1",
    title: "Getting Started",
    content: "Welcome to the platform!",
    route: "/studio",
    dismissed: false,
  };

  let initialState: HelpState;

  beforeEach(() => {
    initialState = {
      isOpen: false,
      searchQuery: "",
      selectedTopicId: null,
      dismissedTipIds: [],
      visibleTips: [],
    };
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe("toggleHelpPane", () => {
    it("toggles help pane open state", () => {
      const state1 = helpReducer(initialState, toggleHelpPane());
      expect(state1.isOpen).toBe(true);

      const state2 = helpReducer(state1, toggleHelpPane());
      expect(state2.isOpen).toBe(false);
    });
  });

  describe("setHelpPaneOpen", () => {
    it("sets help pane open state", () => {
      const state = helpReducer(initialState, setHelpPaneOpen(true));
      expect(state.isOpen).toBe(true);
    });
  });

  describe("setHelpSearchQuery", () => {
    it("sets search query", () => {
      const state = helpReducer(initialState, setHelpSearchQuery("keyboard"));
      expect(state.searchQuery).toBe("keyboard");
    });
  });

  describe("selectHelpTopic", () => {
    it("selects a topic", () => {
      const state = helpReducer(initialState, selectHelpTopic("topic-1"));
      expect(state.selectedTopicId).toBe("topic-1");
    });

    it("clears selection with null", () => {
      let state = helpReducer(initialState, selectHelpTopic("topic-1"));
      state = helpReducer(state, selectHelpTopic(null));
      expect(state.selectedTopicId).toBeNull();
    });
  });

  describe("dismissTip", () => {
    it("adds tip ID to dismissed list", () => {
      const state = helpReducer(initialState, dismissTip("tip-1"));
      expect(state.dismissedTipIds).toContain("tip-1");
    });

    it("removes tip from visible tips", () => {
      let state = helpReducer(
        initialState,
        showTipsForRoute({ route: "/studio", tips: [mockTip] }),
      );
      state = helpReducer(state, dismissTip("tip-1"));
      expect(state.visibleTips).toHaveLength(0);
    });

    it("does not duplicate dismissed IDs", () => {
      let state = helpReducer(initialState, dismissTip("tip-1"));
      state = helpReducer(state, dismissTip("tip-1"));
      expect(state.dismissedTipIds.filter((id) => id === "tip-1")).toHaveLength(
        1,
      );
    });
  });

  describe("showTipsForRoute", () => {
    it("shows tips for a route", () => {
      const state = helpReducer(
        initialState,
        showTipsForRoute({ route: "/studio", tips: [mockTip] }),
      );
      expect(state.visibleTips).toHaveLength(1);
    });

    it("filters out dismissed tips", () => {
      let state = helpReducer(initialState, dismissTip("tip-1"));
      state = helpReducer(
        state,
        showTipsForRoute({ route: "/studio", tips: [mockTip] }),
      );
      expect(state.visibleTips).toHaveLength(0);
    });
  });

  describe("clearVisibleTips", () => {
    it("clears all visible tips", () => {
      let state = helpReducer(
        initialState,
        showTipsForRoute({ route: "/studio", tips: [mockTip] }),
      );
      state = helpReducer(state, clearVisibleTips());
      expect(state.visibleTips).toHaveLength(0);
    });
  });

  describe("resetDismissedTips", () => {
    it("clears dismissed tip IDs", () => {
      let state = helpReducer(initialState, dismissTip("tip-1"));
      state = helpReducer(state, resetDismissedTips());
      expect(state.dismissedTipIds).toHaveLength(0);
    });
  });

  describe("Selectors", () => {
    const stateWithHelp = {
      help: {
        isOpen: true,
        searchQuery: "test",
        selectedTopicId: "topic-1",
        dismissedTipIds: ["tip-1"],
        visibleTips: [mockTip],
      },
    };

    it("selectHelpPaneOpen returns open state", () => {
      expect(selectHelpPaneOpen(stateWithHelp)).toBe(true);
    });

    it("selectVisibleTips returns tips array", () => {
      expect(selectVisibleTips(stateWithHelp)).toHaveLength(1);
    });

    it("selectHelpSearchQuery returns search query", () => {
      expect(selectHelpSearchQuery(stateWithHelp)).toBe("test");
    });

    it("selectSelectedTopicId returns selected topic id", () => {
      expect(selectSelectedTopicId(stateWithHelp)).toBe("topic-1");
    });

    it("selectDismissedTipIds returns dismissed tip ids", () => {
      expect(selectDismissedTipIds(stateWithHelp)).toEqual(["tip-1"]);
    });
  });

  describe("resetHelp", () => {
    it("resets to initial state", () => {
      const modifiedState: HelpState = {
        isOpen: true,
        searchQuery: "test",
        selectedTopicId: "topic-1",
        dismissedTipIds: ["tip-1", "tip-2"],
        visibleTips: [mockTip],
      };
      const state = helpReducer(modifiedState, resetHelp());
      expect(state.isOpen).toBe(false);
      expect(state.searchQuery).toBe("");
      expect(state.selectedTopicId).toBeNull();
      expect(state.dismissedTipIds).toHaveLength(0);
      expect(state.visibleTips).toHaveLength(0);
    });
  });
});
