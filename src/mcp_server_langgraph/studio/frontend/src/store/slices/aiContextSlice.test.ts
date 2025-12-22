/**
 * AIContextSlice Tests
 *
 * Phase 7: Integration - State Management
 * Tests for AI context and suggestions state.
 */
import { describe, it, expect, beforeEach } from "vitest";
import aiContextReducer, {
  setSuggestions,
  acceptSuggestion,
  dismissSuggestion,
  clearSuggestions,
  setAIContext,
  setAILoading,
  resetAIContext,
  selectSuggestions,
  selectAIContext,
  selectAILoading,
  selectHighConfidenceSuggestions,
  type AISuggestion,
  type AIContextState,
} from "./aiContextSlice";

describe("aiContextSlice", () => {
  const mockSuggestion: AISuggestion = {
    id: "sug-1",
    type: "completion",
    content: "const result = await fetch(url);",
    position: { line: 10, column: 5 },
    confidence: 0.85,
  };

  let initialState: AIContextState;

  beforeEach(() => {
    initialState = {
      suggestions: [],
      context: null,
      isLoading: false,
    };
  });

  describe("setSuggestions", () => {
    it("sets suggestions array", () => {
      const state = aiContextReducer(
        initialState,
        setSuggestions([mockSuggestion]),
      );

      expect(state.suggestions).toHaveLength(1);
      expect(state.suggestions[0].id).toBe("sug-1");
    });

    it("replaces existing suggestions", () => {
      const state1 = aiContextReducer(
        initialState,
        setSuggestions([mockSuggestion]),
      );
      const newSuggestion = { ...mockSuggestion, id: "sug-2" };
      const state2 = aiContextReducer(state1, setSuggestions([newSuggestion]));

      expect(state2.suggestions).toHaveLength(1);
      expect(state2.suggestions[0].id).toBe("sug-2");
    });
  });

  describe("acceptSuggestion", () => {
    it("removes accepted suggestion from list", () => {
      const state1 = aiContextReducer(
        initialState,
        setSuggestions([mockSuggestion]),
      );
      const state2 = aiContextReducer(state1, acceptSuggestion("sug-1"));

      expect(state2.suggestions).toHaveLength(0);
    });

    it("keeps other suggestions", () => {
      const suggestions = [mockSuggestion, { ...mockSuggestion, id: "sug-2" }];
      const state1 = aiContextReducer(
        initialState,
        setSuggestions(suggestions),
      );
      const state2 = aiContextReducer(state1, acceptSuggestion("sug-1"));

      expect(state2.suggestions).toHaveLength(1);
      expect(state2.suggestions[0].id).toBe("sug-2");
    });
  });

  describe("dismissSuggestion", () => {
    it("removes dismissed suggestion from list", () => {
      const state1 = aiContextReducer(
        initialState,
        setSuggestions([mockSuggestion]),
      );
      const state2 = aiContextReducer(state1, dismissSuggestion("sug-1"));

      expect(state2.suggestions).toHaveLength(0);
    });
  });

  describe("clearSuggestions", () => {
    it("clears all suggestions", () => {
      const suggestions = [
        mockSuggestion,
        { ...mockSuggestion, id: "sug-2" },
        { ...mockSuggestion, id: "sug-3" },
      ];
      const state1 = aiContextReducer(
        initialState,
        setSuggestions(suggestions),
      );
      const state2 = aiContextReducer(state1, clearSuggestions());

      expect(state2.suggestions).toHaveLength(0);
    });
  });

  describe("setAIContext", () => {
    it("sets AI context", () => {
      const context = {
        sessionId: "session-1",
        artifactId: "artifact-1",
        cursorPosition: { line: 10, column: 5 },
      };
      const state = aiContextReducer(initialState, setAIContext(context));

      expect(state.context).toEqual(context);
    });

    it("clears context when null", () => {
      const context = {
        sessionId: "session-1",
        artifactId: null,
        cursorPosition: null,
      };
      const state1 = aiContextReducer(initialState, setAIContext(context));
      const state2 = aiContextReducer(state1, setAIContext(null));

      expect(state2.context).toBeNull();
    });
  });

  describe("Selectors", () => {
    const stateWithSuggestions = {
      aiContext: {
        suggestions: [mockSuggestion],
        context: {
          sessionId: "session-1",
          artifactId: null,
          cursorPosition: null,
        },
        isLoading: false,
      },
    };

    it("selectSuggestions returns suggestions array", () => {
      const suggestions = selectSuggestions(stateWithSuggestions);
      expect(suggestions).toHaveLength(1);
    });

    it("selectAIContext returns context", () => {
      const context = selectAIContext(stateWithSuggestions);
      expect(context?.sessionId).toBe("session-1");
    });

    it("selectAILoading returns loading state", () => {
      const isLoading = selectAILoading(stateWithSuggestions);
      expect(isLoading).toBe(false);
    });

    it("selectHighConfidenceSuggestions filters by confidence >= 0.7", () => {
      const lowConfidenceSuggestion: AISuggestion = {
        id: "sug-2",
        type: "completion",
        content: "low confidence",
        position: { line: 5, column: 0 },
        confidence: 0.5,
      };
      const stateWithMixedConfidence = {
        aiContext: {
          suggestions: [mockSuggestion, lowConfidenceSuggestion], // 0.85 and 0.5
          context: null,
          isLoading: false,
        },
      };

      const highConfidence = selectHighConfidenceSuggestions(stateWithMixedConfidence);
      expect(highConfidence).toHaveLength(1);
      expect(highConfidence[0].id).toBe("sug-1");
      expect(highConfidence[0].confidence).toBe(0.85);
    });
  });

  describe("setAILoading", () => {
    it("sets loading state to true", () => {
      const state = aiContextReducer(initialState, setAILoading(true));
      expect(state.isLoading).toBe(true);
    });

    it("sets loading state to false", () => {
      const loadingState = { ...initialState, isLoading: true };
      const state = aiContextReducer(loadingState, setAILoading(false));
      expect(state.isLoading).toBe(false);
    });
  });

  describe("resetAIContext", () => {
    it("resets to initial state", () => {
      const modifiedState: AIContextState = {
        suggestions: [mockSuggestion],
        context: {
          sessionId: "session-1",
          artifactId: "artifact-1",
          cursorPosition: { line: 10, column: 5 },
        },
        isLoading: true,
      };
      const state = aiContextReducer(modifiedState, resetAIContext());

      expect(state.suggestions).toHaveLength(0);
      expect(state.context).toBeNull();
      expect(state.isLoading).toBe(false);
    });
  });
});
