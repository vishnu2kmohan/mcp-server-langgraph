/**
 * HelpSlice - Phase 7
 *
 * State management for in-app help panel.
 * Tracks help pane visibility, search, and contextual tips.
 */
import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

// =============================================================================
// Types
// =============================================================================

export interface HelpTopic {
  id: string;
  title: string;
  category: string;
  content: string;
  keywords: string[];
}

export interface ContextualTip {
  id: string;
  title: string;
  content: string;
  route: string;
  dismissed: boolean;
}

export interface HelpState {
  /** Whether help pane is open */
  isOpen: boolean;
  /** Current search query */
  searchQuery: string;
  /** Selected topic ID */
  selectedTopicId: string | null;
  /** Dismissed tip IDs */
  dismissedTipIds: string[];
  /** Currently visible contextual tips */
  visibleTips: ContextualTip[];
}

// =============================================================================
// Initial State
// =============================================================================

const initialState: HelpState = {
  isOpen: false,
  searchQuery: "",
  selectedTopicId: null,
  dismissedTipIds: [],
  visibleTips: [],
};

// =============================================================================
// Slice
// =============================================================================

const helpSlice = createSlice({
  name: "help",
  initialState,
  reducers: {
    /**
     * Toggle help pane visibility
     */
    toggleHelpPane(state) {
      state.isOpen = !state.isOpen;
    },

    /**
     * Set help pane open state
     */
    setHelpPaneOpen(state, action: PayloadAction<boolean>) {
      state.isOpen = action.payload;
    },

    /**
     * Set search query
     */
    setHelpSearchQuery(state, action: PayloadAction<string>) {
      state.searchQuery = action.payload;
    },

    /**
     * Select a topic
     */
    selectHelpTopic(state, action: PayloadAction<string | null>) {
      state.selectedTopicId = action.payload;
    },

    /**
     * Dismiss a contextual tip
     */
    dismissTip(state, action: PayloadAction<string>) {
      const tipId = action.payload;
      if (!state.dismissedTipIds.includes(tipId)) {
        state.dismissedTipIds.push(tipId);
      }
      state.visibleTips = state.visibleTips.filter((t) => t.id !== tipId);
    },

    /**
     * Show contextual tips for a route
     */
    showTipsForRoute(
      state,
      action: PayloadAction<{ route: string; tips: ContextualTip[] }>,
    ) {
      const { tips } = action.payload;
      // Filter out dismissed tips
      state.visibleTips = tips.filter(
        (t) => !state.dismissedTipIds.includes(t.id),
      );
    },

    /**
     * Clear all visible tips
     */
    clearVisibleTips(state) {
      state.visibleTips = [];
    },

    /**
     * Reset dismissed tips (for testing/onboarding reset)
     */
    resetDismissedTips(state) {
      state.dismissedTipIds = [];
    },

    /**
     * Reset help state
     */
    resetHelp() {
      return initialState;
    },
  },
});

// =============================================================================
// Selectors
// =============================================================================

type StateWithHelp = { help: HelpState };

export const selectHelpPaneOpen = (state: StateWithHelp): boolean =>
  state.help.isOpen;

export const selectHelpSearchQuery = (state: StateWithHelp): string =>
  state.help.searchQuery;

export const selectSelectedTopicId = (state: StateWithHelp): string | null =>
  state.help.selectedTopicId;

export const selectVisibleTips = (state: StateWithHelp): ContextualTip[] =>
  state.help.visibleTips;

export const selectDismissedTipIds = (state: StateWithHelp): string[] =>
  state.help.dismissedTipIds;

// =============================================================================
// Exports
// =============================================================================

export const {
  toggleHelpPane,
  setHelpPaneOpen,
  setHelpSearchQuery,
  selectHelpTopic,
  dismissTip,
  showTipsForRoute,
  clearVisibleTips,
  resetDismissedTips,
  resetHelp,
} = helpSlice.actions;

export default helpSlice.reducer;
