/**
 * AIContextSlice - Phase 7
 *
 * State management for AI context and inline suggestions.
 * Tracks current context for AI features and manages suggestions.
 */
import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

// =============================================================================
// Types
// =============================================================================

export type SuggestionType = "completion" | "refactor" | "fix" | "explain";

export interface CursorPosition {
  line: number;
  column: number;
}

export interface AISuggestion {
  id: string;
  type: SuggestionType;
  content: string;
  position: CursorPosition;
  confidence: number;
}

export interface AIContext {
  sessionId: string;
  artifactId: string | null;
  cursorPosition: CursorPosition | null;
}

export interface AIContextState {
  /** Current inline suggestions */
  suggestions: AISuggestion[];
  /** Current AI context (session, artifact, cursor) */
  context: AIContext | null;
  /** Whether AI is loading suggestions */
  isLoading: boolean;
}

// =============================================================================
// Initial State
// =============================================================================

const initialState: AIContextState = {
  suggestions: [],
  context: null,
  isLoading: false,
};

// =============================================================================
// Slice
// =============================================================================

const aiContextSlice = createSlice({
  name: "aiContext",
  initialState,
  reducers: {
    /**
     * Set suggestions (replaces existing)
     */
    setSuggestions(state, action: PayloadAction<AISuggestion[]>) {
      state.suggestions = action.payload;
    },

    /**
     * Accept a suggestion (removes from list)
     */
    acceptSuggestion(state, action: PayloadAction<string>) {
      state.suggestions = state.suggestions.filter(
        (s) => s.id !== action.payload,
      );
    },

    /**
     * Dismiss a suggestion (removes from list)
     */
    dismissSuggestion(state, action: PayloadAction<string>) {
      state.suggestions = state.suggestions.filter(
        (s) => s.id !== action.payload,
      );
    },

    /**
     * Clear all suggestions
     */
    clearSuggestions(state) {
      state.suggestions = [];
    },

    /**
     * Set AI context
     */
    setAIContext(state, action: PayloadAction<AIContext | null>) {
      state.context = action.payload;
    },

    /**
     * Set loading state
     */
    setAILoading(state, action: PayloadAction<boolean>) {
      state.isLoading = action.payload;
    },

    /**
     * Reset AI context state
     */
    resetAIContext() {
      return initialState;
    },
  },
});

// =============================================================================
// Selectors
// =============================================================================

type StateWithAIContext = { aiContext: AIContextState };

export const selectSuggestions = (state: StateWithAIContext): AISuggestion[] =>
  state.aiContext.suggestions;

export const selectAIContext = (state: StateWithAIContext): AIContext | null =>
  state.aiContext.context;

export const selectAILoading = (state: StateWithAIContext): boolean =>
  state.aiContext.isLoading;

export const selectHighConfidenceSuggestions = (
  state: StateWithAIContext,
): AISuggestion[] =>
  state.aiContext.suggestions.filter((s) => s.confidence >= 0.7);

// =============================================================================
// Exports
// =============================================================================

export const {
  setSuggestions,
  acceptSuggestion,
  dismissSuggestion,
  clearSuggestions,
  setAIContext,
  setAILoading,
  resetAIContext,
} = aiContextSlice.actions;

export default aiContextSlice.reducer;
